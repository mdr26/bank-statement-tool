import streamlit as st
import pandas as pd
from io import BytesIO

st.title("Bank Statement Classification Tool")

uploaded_file = st.file_uploader(
    "Upload Bank Statement Excel",
    type=["xlsx", "xls"]
)

def load_rules():
    try:
        rules = pd.read_excel("rules/rules.xlsx")
        rules.columns = rules.columns.str.strip().str.upper()
        return rules
    except:
        st.warning("Rules Excel not found inside /rules folder.")
        return None


def classify_transactions(df, rules):

    narration_col = [c for c in df.columns if "NARRATION" in c.upper()]
    if not narration_col:
        st.error("Narration column missing.")
        return df

    narration_col = narration_col[0]

    df["Transaction_Head"] = "Review Required"

    for _, r in rules.iterrows():

        keyword = str(r["KEYWORD"]).upper()
        head = r["TRANSACTION_HEAD"]

        df.loc[
            df[narration_col].astype(str).str.upper().str.contains(keyword, na=False),
            "Transaction_Head"
        ] = head

    return df


if uploaded_file:

    df = pd.read_excel(uploaded_file)
    rules = load_rules()

    if rules is not None:

        df = classify_transactions(df, rules)
        st.success("Classification completed")

        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            "Download Classified Statement",
            buffer,
            file_name="classified_statement.xlsx"
        )
