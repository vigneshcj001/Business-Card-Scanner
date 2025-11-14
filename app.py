# app.py
import os
import time
from typing import Any, Dict, List

import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# ----------------------------
# Page Configuration
# ----------------------------
st.set_page_config(
    page_title="Business Card OCR → MongoDB",
    page_icon="📇",
    layout="wide",
)

# Backend URL (env var or default)
BACKEND = os.environ.get("BACKEND_URL", "https://business-card-scanner-backend.onrender.com")

st.title("📇 Business Card OCR → MongoDB")
st.write("Upload → Extract OCR → Store → Edit → Download")

# ----------------------------
# Helpers
# ----------------------------
def to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def list_to_csv_str(v):
    if isinstance(v, list):
        return ", ".join([str(x) for x in v])
    return v if v is not None else ""

def csv_str_to_list(s: str):
    if s is None:
        return []
    return [x.strip() for x in str(s).split(",") if x.strip()]

def _clean_payload_for_backend(payload: dict) -> dict:
    out = {}
    for k, v in payload.items():
        if v is None:
            continue
        if k in ("phone_numbers", "social_links"):
            out[k] = csv_str_to_list(v) if not isinstance(v, list) else v
        else:
            out[k] = v
    return out

def fetch_all_cards(timeout=20) -> List[Dict[str, Any]]:
    try:
        resp = requests.get(f"{BACKEND}/all_cards", timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])
    except Exception as e:
        st.error(f"Failed to fetch cards: {e}")
        return []

# ----------------------------
# Layout: Tabs
# ----------------------------
tab1, tab2 = st.tabs(["📤 Upload Card", "📁 View All Cards"])

# ----------------------------
# TAB 1 — Upload Card
# ----------------------------
with tab1:
    col_preview, col_upload = st.columns([3, 7])

    # Upload column
    with col_upload:
        st.markdown("### Upload card")
        uploaded_file = st.file_uploader(
            "Drag and drop file here\nLimit 200MB • JPG, JPEG, PNG",
            type=["jpg", "jpeg", "png"]
        )

        if uploaded_file:
            progress = st.progress(10)
            time.sleep(0.08)
            progress.progress(30)

            with st.spinner("Processing image with OCR and uploading..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                try:
                    response = requests.post(f"{BACKEND}/upload_card", files=files, timeout=120)
                    response.raise_for_status()
                except Exception as e:
                    st.error(f"Failed to reach backend: {e}")
                    response = None

                if response and response.status_code in (200, 201):
                    res = response.json()
                    if "data" in res:
                        st.success("Inserted Successfully!")
                        card = res["data"]
                        df = pd.DataFrame([card]).drop(columns=["_id"], errors="ignore")
                        st.dataframe(df, use_container_width=True)
                        st.download_button(
                            "📥 Download as Excel",
                            to_excel_bytes(df),
                            "business_card.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.warning("Backend returned success but no data payload.")
                else:
                    st.error("Upload failed.")

            progress.progress(100)

    with col_preview:
        st.markdown("### Preview")
        if uploaded_file:
            st.image(uploaded_file, use_container_width=True)
        else:
            st.info("Upload a card to preview here.")

    st.markdown("---")

    # Manual entry form
    with st.expander("📋 Or fill details manually"):
        with st.form("manual_card_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Full name")
            designation = c2.text_input("Designation / Title")
            company = c1.text_input("Company")
            phones = c2.text_input("Phone numbers (comma separated)")
            email = c1.text_input("Email")
            website = c2.text_input("Website")
            address = st.text_area("Address")
            social_links = st.text_input("Social links (comma separated)")
            additional_notes = st.text_area("Notes / extra info")
            submitted = st.form_submit_button("📤 Create Card (manual)")

        if submitted:
            payload = {
                "name": name,
                "designation": designation,
                "company": company,
                "phone_numbers": phones,
                "email": email,
                "website": website,
                "address": address,
                "social_links": social_links,
                "additional_notes": additional_notes,
            }
            with st.spinner("Saving..."):
                try:
                    r = requests.post(
                        f"{BACKEND}/create_card",
                        json=_clean_payload_for_backend(payload),
                        timeout=30
                    )
                    r.raise_for_status()
                except Exception as e:
                    st.error(f"Failed to reach backend: {e}")
                    r = None

                if r and r.status_code in (200, 201):
                    res = r.json()
                    if "data" in res:
                        st.success("Inserted Successfully!")
                        card = res["data"]
                        df = pd.DataFrame([card]).drop(columns=["_id"], errors="ignore")
                        st.dataframe(df, use_container_width=True)
                        st.download_button(
                            "📥 Download as Excel",
                            to_excel_bytes(df),
                            "business_card_manual.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

# ======================================================================
# TAB 2 — View & Edit All Cards (NO drawer, NO row selector)
# ======================================================================
with tab2:
    st.markdown("### All business cards")

    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        st.info("Edit any field below → click **Save Changes** to update the backend.")
    with top_col2:
        data = fetch_all_cards()
        if data:
            df_all_for_download = pd.DataFrame(data)
            for col in ["phone_numbers", "social_links"]:
                df_all_for_download[col] = df_all_for_download[col].apply(list_to_csv_str)
            st.download_button(
                "📥 Download All as Excel",
                to_excel_bytes(df_all_for_download.drop(columns=["_id"], errors="ignore")),
                "all_business_cards.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with st.spinner("Fetching all business cards..."):
        data = fetch_all_cards()

    if not data:
        st.warning("No cards found.")
    else:
        df_all = pd.DataFrame(data)

        expected_cols = [
            "_id", "name", "designation", "company", "phone_numbers", "email",
            "website", "address", "social_links", "additional_notes",
            "created_at", "edited_at"
        ]
        for c in expected_cols:
            if c not in df_all.columns:
                df_all[c] = ""

        _ids = df_all["_id"].astype(str).tolist()

        display_df = df_all.copy()
        for col in ["phone_numbers", "social_links"]:
            display_df[col] = display_df[col].apply(list_to_csv_str)

        display_df = display_df.drop(columns=["_id"])

        # Save button
        save_clicked = st.button("💾 Save Changes")

        try:
            edited = st.experimental_data_editor(
                display_df, use_container_width=True, num_rows="fixed"
            )
        except Exception:
            edited = st.data_editor(
                display_df, use_container_width=True, num_rows="fixed"
            )

        # Save logic
        if save_clicked:
            updates = 0
            problems = 0

            for i in range(len(edited)):
                orig = display_df.iloc[i]
                new = edited.iloc[i]

                change_set = {}
                for col in display_df.columns:
                    o = "" if pd.isna(orig[col]) else orig[col]
                    n = "" if pd.isna(new[col]) else new[col]
                    if str(o) != str(n):
                        change_set[col] = csv_str_to_list(n) if col in ["phone_numbers", "social_links"] else n

                if change_set:
                    card_id = _ids[i]
                    try:
                        r = requests.patch(
                            f"{BACKEND}/update_card/{card_id}",
                            json=change_set,
                            timeout=30
                        )
                        if r.status_code in (200, 201):
                            updates += 1
                        else:
                            problems += 1
                            st.error(f"Failed to update {card_id}: {r.text}")
                    except Exception as e:
                        problems += 1
                        st.error(f"Failed to update {card_id}: {e}")

            if updates:
                st.success(f"✅ Updated {updates} card(s). Refreshing...")
                st.experimental_rerun()
            elif problems == 0:
                st.info("No changes detected.")
            else:
                st.warning(f"Save completed with {problems} failures.")
