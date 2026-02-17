import streamlit as st
import pandas as pd
from io import BytesIO
import os

st.set_page_config(page_title="Bank Statement Tool", layout="wide")
st.title("Bank Statement Classification Tool")

# -------------------------
# MODE SELECTION
# -------------------------
mode = st.radio(
    "Choose Mode",
    ["Normal Classification", "Interbank Detection"]
)


# ============================================================
# NORMAL CLASSIFICATION MODE
# ============================================================
if mode == "Normal Classification":

    uploaded_file = st.file_uploader(
        "Upload Bank Statement Excel",
        type=["xlsx", "xls"]
    )

    # Rules file expected in repo root
    rules_file_path = "key words.xlsx"

    def clean_text(x):
        if pd.isna(x):
            return ""
        return str(x).upper().strip()

    def extract_name(narration):
        narration = str(narration)

        # Remove common noise words
        remove_words = [
            "UPI", "IMPS", "NEFT", "RTGS", "TRANSFER",
            "PAYMENT", "DR", "CR", "BY", "TO",
            "BANK", "REF", "ID", "MB"
        ]

        words = narration.split()
        filtered = [w for w in words if w.upper() not in remove_words]

        # Keep first 3 useful words only
        return " ".join(filtered[:3]).title()

    def classify_transactions(df):
        if not os.path.exists(rules_file_path):
            st.warning("Rules Excel not found.")
            df["Transaction_Head"] = "Review Required"
            return df

        rules_df = pd.read_excel(rules_file_path)
        rules_df.columns = rules_df.columns.str.strip()

        df["Transaction_Head"] = "Review Required"

        for _, r in rules_df.iterrows():
            keyword = clean_text(r.get("Keyword", ""))
            head = r.get("Transaction_Head", "Review Required")
            extract_flag = clean_text(r.get("Extract_Client_Name", "NO"))

            mask = df["Narration"].astype(str).str.upper().str.contains(keyword, na=False)

            if extract_flag == "YES":
                df.loc[mask, "Transaction_Head"] = df.loc[mask, "Narration"].apply(extract_name)
            else:
                df.loc[mask, "Transaction_Head"] = head

        return df

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip()

        if "Narration" not in df.columns:
            st.error("Narration column missing in statement.")
        else:
            df = classify_transactions(df)

            buffer = BytesIO()
            df.to_excel(buffer, index=False, engine="openpyxl")

            st.success("Classification completed.")
            st.download_button(
                "Download Classified Statement",
                data=buffer.getvalue(),
                file_name="classified_statement.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


# ============================================================
# INTERBANK DETECTION MODE
# ============================================================
else:

    files = st.file_uploader(
        "Upload TWO bank statements",
        type=["xlsx", "xls"],
        accept_multiple_files=True
    )

    if files and len(files) == 2:
        df1 = pd.read_excel(files[0])
        df2 = pd.read_excel(files[1])

        # Normalize column names
        for df in [df1, df2]:
            df.columns = df.columns.str.strip()

        required_cols = ["Date", "Payment", "Receipt"]

        if not all(col in df1.columns for col in required_cols) or not all(col in df2.columns for col in required_cols):
            st.error("Statements must contain Date, Payment, Receipt columns.")

        else:
            df1["Date"] = pd.to_datetime(df1["Date"], errors="coerce")
            df2["Date"] = pd.to_datetime(df2["Date"], errors="coerce")

            matches = []

            for _, r1 in df1.iterrows():
                for _, r2 in df2.iterrows():

                    if r1["Date"] == r2["Date"]:

                        if (
                            pd.notna(r1["Payment"]) and
                            pd.notna(r2["Receipt"]) and
                            abs(r1["Payment"] - r2["Receipt"]) < 1
                        ):
                            matches.append([r1["Date"], r1["Payment"], "Interbank"])

                        if (
                            pd.notna(r1["Receipt"]) and
                            pd.notna(r2["Payment"]) and
                            abs(r1["Receipt"] - r2["Payment"]) < 1
                        ):
                            matches.append([r1["Date"], r1["Receipt"], "Interbank"])

            if matches:
                result = pd.DataFrame(matches, columns=["Date", "Amount", "Transaction_Head"])

                buffer = BytesIO()
                result.to_excel(buffer, index=False, engine="openpyxl")

                st.success("Interbank transactions detected.")
                st.download_button(
                    "Download Interbank Report",
                    data=buffer.getvalue(),
                    file_name="interbank_transactions.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            else:
                st.warning("No interbank transactions found.")

    elif files:
        st.info("Upload exactly TWO statements for interbank detection.")
