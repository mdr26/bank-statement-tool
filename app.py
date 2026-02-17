import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="Bank Statement Tool", layout="wide")

st.title("Bank Statement Classification Tool")

# ---------- MODE SELECTION ----------
mode = st.radio(
    "Choose Mode",
    ["Normal Classification", "Interbank Detection"]
)

# ---------- FILE UPLOAD ----------
uploaded_files = st.file_uploader(
    "Upload Bank Statement(s)",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)


# ---------- RULES LOADING ----------
def load_rules():
    try:
        rules = pd.read_excel("rules/key words.xlsx")
        rules.columns = [c.strip() for c in rules.columns]
        return rules
    except:
        return None


# ---------- NAME EXTRACTION ----------
def extract_name(text):
    text = str(text).upper()

    # Remove common noise
    text = re.sub(r"UPI|IMPS|NEFT|RTGS|CR|DR|TRANSFER|PAYMENT", "", text)
    text = re.sub(r"[^A-Z ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    words = text.split()
    name_words = [w for w in words if len(w) > 2]

    return " ".join(name_words[:3])


# ---------- NORMAL CLASSIFICATION ----------
def classify_transactions(df):
    rules = load_rules()

    if rules is None:
        st.warning("Rules Excel not found.")
        df["Transaction_Head"] = "Review Required"
        return df

    df.columns = [c.strip() for c in df.columns]

    if "Narration" not in df.columns:
        st.error("Narration column missing in statement.")
        df["Transaction_Head"] = "Review Required"
        return df

    df["Transaction_Head"] = "Review Required"

    for _, r in rules.iterrows():
        keyword = str(r.get("Keyword", "")).upper()
        head = r.get("Transaction_Head", "Review Required")
        extract_flag = str(r.get("Extract_Client_Name", "NO")).upper()

        mask = df["Narration"].astype(str).str.upper().str.contains(keyword, na=False)

        if extract_flag == "YES":
            df.loc[mask, "Transaction_Head"] = (
                df.loc[mask, "Narration"].apply(extract_name)
            )
        else:
            df.loc[mask, "Transaction_Head"] = head

    return df


# ---------- INTERBANK DETECTION ----------
def detect_interbank(dfs):
    combined = pd.concat(dfs, ignore_index=True)

    combined.columns = [c.strip() for c in combined.columns]

    if not {"Payment", "Receipt", "Tran Date"}.issubset(set(combined.columns)):
        st.error("Required columns missing for interbank detection.")
        return combined

    combined["Transaction_Head"] = "Normal"

    for i, row in combined.iterrows():
        payment = row.get("Payment", 0)
        receipt = row.get("Receipt", 0)
        date = row.get("Tran Date")

        match = combined[
            (combined["Tran Date"] == date)
            & ((combined["Payment"] == receipt) | (combined["Receipt"] == payment))
        ]

        if len(match) > 1:
            combined.loc[i, "Transaction_Head"] = "Interbank"

    return combined


# ---------- PROCESS ----------
if uploaded_files:

    dfs = []

    for file in uploaded_files:
        df = pd.read_excel(file)
        dfs.append(df)

    if mode == "Normal Classification":
        result_df = pd.concat([classify_transactions(df) for df in dfs])
    else:
        result_df = detect_interbank(dfs)

    st.success("Processing completed.")

    buffer = BytesIO()
    result_df.to_excel(buffer, index=False, engine="openpyxl")

    st.download_button(
        "Download Classified Statement",
        buffer.getvalue(),
        "classified_statement.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
