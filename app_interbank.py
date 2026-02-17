import streamlit as st
import pandas as pd
from io import BytesIO

st.title("Interbank Transaction Finder")

files = st.file_uploader(
    "Upload TWO bank statements",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

def prepare_df(df):

    df.columns = df.columns.str.strip().str.upper()

    date_col = [c for c in df.columns if "DATE" in c][0]
    pay_col = [c for c in df.columns if "PAYMENT" in c or "DEBIT" in c][0]
    rec_col = [c for c in df.columns if "RECEIPT" in c or "CREDIT" in c][0]

    df["DATE"] = pd.to_datetime(df[date_col], errors="coerce").dt.date
    df["PAYMENT"] = pd.to_numeric(df[pay_col], errors="coerce")
    df["RECEIPT"] = pd.to_numeric(df[rec_col], errors="coerce")

    return df[["DATE", "PAYMENT", "RECEIPT"]]


if files and len(files) == 2:

    df1 = prepare_df(pd.read_excel(files[0]))
    df2 = prepare_df(pd.read_excel(files[1]))

    matches = []

    for _, r1 in df1.iterrows():

        cond = (
            (df2["DATE"] == r1["DATE"]) &
            (df2["RECEIPT"].round(2) == round(r1["PAYMENT"], 2))
        )

        if not df2[cond].empty:
            matches.append({
                "Date": r1["DATE"],
                "Amount": r1["PAYMENT"],
                "Transaction_Head": "Interbank"
            })

    result = pd.DataFrame(matches).drop_duplicates()

    st.success(f"{len(result)} Interbank transactions found")

    buffer = BytesIO()
    result.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        "Download Interbank Matches",
        buffer,
        file_name="interbank_matches.xlsx"
    )
