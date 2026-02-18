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
    text = str(text).replace("\n", " ")   # remove line breaks
    text = re.sub(r"\s+", " ", text)
    return text.upper().strip()


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

    # SBI UPI format
    if "UPI/" in narration:
        parts = narration.split("/")

        for p in reversed(parts):
            p = p.strip()

            if not p:
                continue

            if p.isdigit():
                continue

            if p in ["CR", "DR", "UPI", "REV"]:
                continue

            if len(p) > 2:
                return re.sub(r"[^A-Z ]", "", p).strip()

    # Generic cleanup
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

        # STEP 1 → APPLY RULES FIRST
        matched = False

        for _, r in rules.iterrows():
            keyword = clean_text(r.get("Keyword", ""))

            if keyword and keyword in narration:

                head = r.get("Transaction_Head", "Review Required")
                extract_flag = str(
                    r.get("Extract_Client_Name", "NO")
                ).upper()

                # Only extract name if rule says YES
                if extract_flag == "YES":
                    name = extract_client_name(narration)
                    if name:
                        df.at[i, "Transaction_Head"] = name
                    else:
                        df.at[i, "Transaction_Head"] = head
                else:
                    df.at[i, "Transaction_Head"] = head

                matched = True
                break

        # STEP 2 → IF NO RULE MATCHED
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

    # dynamic filename
    original_name = uploaded_file.name.split(".")[0]
    output_name = f"{original_name}_classified.xlsx"

    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        label="Download Classified Statement",
        data=buffer,
        file_name=output_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
