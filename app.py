import streamlit as st
import pandas as pd
import re
import os
from io import BytesIO


st.title("Bank Statement Classification Tool")


# -------- CLEAN TEXT --------
def clean_text(text):
    if pd.isna(text):
        return ""
    return str(text).upper().strip()


# -------- DETECT NARRATION COLUMN --------
def find_narration_column(df):
    possible_cols = [
        "NARRATION",
        "DESCRIPTION",
        "REMARKS",
        "PARTICULARS",
        "TRANSACTION DETAILS",
        "TXN REMARKS",
    ]

    for col in df.columns:
        if clean_text(col) in possible_cols:
            return col

    return None


# -------- CLIENT NAME EXTRACTION --------
def extract_client_name(narration):

    narration = clean_text(narration)

    # ===== SBI SPECIFIC UPI FORMAT =====
    # Example:
    # DEP TFR UPI/CR/409293829100/METRO
    if "UPI/" in narration:
        parts = narration.split("/")

        for p in reversed(parts):
            p = p.strip()

            if not p:
                continue

            if p.isdigit():
                continue

            if p in ["CR", "DR", "REV", "UPI"]:
                continue

            if len(p) > 2:
                return re.sub(r"[^A-Z ]", "", p).strip()

    # ===== GENERIC CLEANUP =====
    narration = re.sub(
        r"\b(DR|CR|UPI|IMPS|NEFT|RTGS|BANK|TXN|REF|MB|AXOMB|BRN|CLG)\b",
        "",
        narration,
    )

    narration = re.sub(r"\d+", "", narration)
    narration = re.sub(r"[@*/\-_:]", " ", narration)
    narration = re.sub(r"\s+", " ", narration).strip()

    words = narration.split()

    if len(words) >= 2:
        return " ".join(words[:3])

    return ""


# -------- CLASSIFICATION --------
def classify_transactions(df):

    rules_path = "key words.xlsx"

    if not os.path.exists(rules_path):
        st.warning("Rules Excel not found.")
        df["Transaction_Head"] = "Review Required"
        return df

    rules = pd.read_excel(rules_path)
    rules.columns = rules.columns.str.strip()

    narration_col = find_narration_column(df)

    if narration_col is None:
        st.error("Narration column missing.")
        df["Transaction_Head"] = "Review Required"
        return df

    df["Transaction_Head"] = "Review Required"

    for i, row in df.iterrows():

        narration = clean_text(row[narration_col])

        # First try extracting name
        name = extract_client_name(narration)
        if name:
            df.at[i, "Transaction_Head"] = name
            continue

        # Otherwise use rules
        for _, r in rules.iterrows():
            keyword = clean_text(r.get("Keyword", ""))

            if keyword and keyword in narration:
                df.at[i, "Transaction_Head"] = r.get(
                    "Transaction_Head",
                    "Review Required",
                )
                break

    return df


# -------- FILE UPLOAD --------
uploaded_file = st.file_uploader(
    "Upload Bank Statement Excel",
    type=["xlsx", "xls"],
)

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    df = classify_transactions(df)

    st.success("Classification completed.")

    # Download Excel
    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        label="Download Classified Statement",
        data=buffer,
        file_name="classified_statement.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
