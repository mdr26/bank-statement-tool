import streamlit as st
import pandas as pd
import re
import os
from io import BytesIO


st.title("Bank Statement Classification Tool")


# ---------- CLEAN TEXT ----------
def clean_text(text):
    if pd.isna(text):
        return ""
    return str(text).upper().strip()


# ---------- FIND NARRATION COLUMN ----------
def find_narration_column(df):
    for col in df.columns:
        if (
            "NARRATION" in col.upper()
            or "DESCRIPTION" in col.upper()
            or "PARTICULARS" in col.upper()
        ):
            return col
    return None


# ---------- CLIENT NAME EXTRACTION ----------
def extract_client_name(narration, keyword):

    narration = clean_text(narration)

    # Remove keyword first
    narration = narration.replace(keyword, "")

    # Split narration by common separators
    parts = re.split(r"[\/\-]", narration)

    bank_words = [
        "SBIN", "HDFC", "ICICI", "AXIS", "FDRL",
        "UBIN", "KKBK", "CNBR", "BANK", "TXN",
        "REF", "MB", "BRN", "CLG", "UPI",
        "IMPS", "NEFT", "RTGS", "TRANSFER",
        "PAYMENT", "DR", "CR"
    ]

    for part in parts:

        part = part.strip()

        # Skip numeric-only parts
        if part.isdigit():
            continue

        # Skip mostly numeric tokens
        if sum(c.isdigit() for c in part) > 3:
            continue

        # Skip bank codes
        if any(b in part for b in bank_words):
            continue

        # Skip very short tokens
        if len(part) < 3:
            continue

        # Valid name must contain alphabets
        if re.search(r"[A-Z]", part):
            return part.strip()

    return ""


# ---------- CLASSIFICATION ----------
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

        for _, r in rules.iterrows():

            keyword = clean_text(r.get("Keyword", ""))

            if keyword and keyword in narration:

                extract_flag = str(
                    r.get("Extract_Client_Name", "NO")
                ).upper()

                if extract_flag == "YES":

                    name = extract_client_name(narration, keyword)

                    if name:
                        df.at[i, "Transaction_Head"] = name
                    else:
                        df.at[i, "Transaction_Head"] = r.get(
                            "Transaction_Head",
                            "Review Required",
                        )

                else:
                    df.at[i, "Transaction_Head"] = r.get(
                        "Transaction_Head",
                        "Review Required",
                    )

                break

    return df


# ---------- FILE UPLOAD ----------
uploaded_file = st.file_uploader(
    "Upload Bank Statement Excel",
    type=["xlsx", "xls"]
)

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    df = classify_transactions(df)

    st.success("Classification completed.")

    # Excel download
    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        label="Download Classified Statement",
        data=buffer,
        file_name="classified_statement.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
