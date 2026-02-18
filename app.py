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

    # Split by / common in SBI/UPI
    parts = re.split(r"[\/\-:]", narration)

    cleaned = []

    for p in parts:

        p = p.strip()

        if not p:
            continue

        # Ignore technical words
        if p in [
            "UPI",
            "IMPS",
            "NEFT",
            "RTGS",
            "BANK",
            "CR",
            "DR",
            "REF",
            "TXN",
            "MB",
            "AXOMB",
            "CLG",
            "BRN",
        ]:
            continue

        # Ignore numbers
        if re.search(r"\d", p):
            continue

        cleaned.append(p)

    if cleaned:
        return cleaned[-1].title()

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

        matched = False

        # ===== RULE MATCH FIRST =====
        for _, r in rules.iterrows():

            keyword = clean_text(r.get("Keyword", ""))
            head = r.get("Transaction_Head", "Review Required")
            extract_flag = clean_text(r.get("Extract_Client_Name", "NO"))

            if keyword and keyword in narration:

                matched = True

                if extract_flag == "YES":
                    name = extract_client_name(narration)
                    df.at[i, "Transaction_Head"] = name if name else head
                else:
                    df.at[i, "Transaction_Head"] = head

                break

        # ===== NO MATCH =====
        if not matched:
            df.at[i, "Transaction_Head"] = "Review Required"

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

    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        label="Download Classified Statement",
        data=buffer,
        file_name="classified_statement.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
