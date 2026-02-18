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

    text = str(text).replace("\n", " ")  # remove line breaks
    text = text.replace("\r", " ")
    text = re.sub(r"\s+", " ", text)

    return text.upper().strip()


# -------- FIND NARRATION COLUMN --------
def find_narration_column(df):

    possible_cols = [
        "NARRATION",
        "DESCRIPTION",
        "PARTICULARS",
        "REMARKS",
        "TRANSACTION DETAILS",
    ]

    for col in df.columns:
        if clean_text(col) in possible_cols:
            return col

    return None


# -------- CLIENT NAME EXTRACTION --------
def extract_client_name(narration):

    narration = clean_text(narration)

    # Remove banking noise words
    narration = re.sub(
        r"\b(DR|CR|UPI|IMPS|NEFT|RTGS|BANK|TXN|REF|MB|AXOMB|BRN|CLG)\b",
        "",
        narration,
    )

    narration = re.sub(r"\d+", "", narration)
    narration = re.sub(r"[@*/\-_:]", " ", narration)
    narration = re.sub(r"\s+", " ", narration).strip()

    words = narration.split()

    # Take first meaningful words as name
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

        # --- Name extraction first ---
        name = extract_client_name(narration)
        if name:
            df.at[i, "Transaction_Head"] = name
            continue

        # --- Keyword rule fallback ---
        for _, r in rules.iterrows():

            keyword = clean_text(r.get("Keyword", ""))

            if keyword and keyword in narration:
                df.at[i, "Transaction_Head"] = r.get(
                    "Transaction_Head", "Review Required"
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

    # ===== AUTO FILE NAME =====
    original_name = uploaded_file.name.split(".")[0]
    output_name = f"{original_name}_classified.xlsx"

    # ===== DOWNLOAD FILE =====
    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        label="Download Classified Statement",
        data=buffer,
        file_name=output_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
