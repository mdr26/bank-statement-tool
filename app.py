import streamlit as st
import pandas as pd
import re
from collections import Counter
from io import BytesIO


# -----------------------------------------------------------
# App Configuration
# -----------------------------------------------------------

st.set_page_config(
    page_title="Bank Statement Classifier",
    layout="wide"
)

st.title("Bank Statement Intelligent Classifier")


# -----------------------------------------------------------
# Session State
# -----------------------------------------------------------

if "ledger_map" not in st.session_state:
    st.session_state.ledger_map = {}

if "merged_heads" not in st.session_state:
    st.session_state.merged_heads = {}


# -----------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------

def find_narration_column(df: pd.DataFrame) -> str:
    """Identify narration/description column."""

    candidates = [
        "NARRATION", "DESCRIPTION", "PARTICULARS",
        "DETAILS", "REMARKS", "DESC"
    ]

    for col in df.columns:
        if col.upper() in candidates:
            return col

    for col in df.columns:
        if "NARR" in col.upper() or "DESC" in col.upper():
            return col

    return df.select_dtypes(include="object").columns[0]


def clean_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert numeric columns safely."""

    for col in df.columns:
        if any(x in col.upper() for x in ["WITHDRAW", "DEBIT", "DEPOSIT", "CREDIT", "BALANCE"]):
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def flag_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Mark possible duplicate transactions."""

    cols = []

    for col in df.columns:
        if any(x in col.upper() for x in ["DATE", "WITHDRAW", "DEPOSIT", "NARR"]):
            cols.append(col)

    df["Possible_Duplicate"] = df.duplicated(subset=cols, keep=False)

    return df


def clean_alpha(text: str) -> str:
    return re.sub(r'[^A-Z]', '', text)


# -----------------------------------------------------------
# Transaction Head Extraction
# -----------------------------------------------------------

STOP_WORDS = {
    "UPI","IMPS","NEFT","RTGS","CR","DR",
    "BANK","PAYMENT","TRANSFER",
    "CHARGE","CHARGES","FEE",

    "ENTER","SUCCESS","TRANSACTION",
    "REFERENCE","REF","DETAIL","DETAILS",
    "VALUE","DATE","INFO","MESSAGE",
    "TRF","BY","TO","FROM","OF","THE"
}

BANK_PREFIXES = (
    "OK","SBIN","HDFC","ICICI","UBIN",
    "AXIS","BARB","YESB","FDRL",
    "YBL","IBL","UPI"
)

def score_token(token, position, total_words, freq):
    score = 0

    if 4 <= len(token) <= 15:
        score += 2

    if freq > 2:
        score += 3

    center = total_words / 2
    if abs(position - center) <= 2:
        score += 2

    if token in STOP_WORDS:
        score -= 5

    if token.startswith(BANK_PREFIXES):
        score -= 5

    if any(c.isdigit() for c in token):
        score -= 3

    return score


def extract_transaction_head(narration, word_freq):

    text = str(narration).upper()
    words = re.sub(r'[^A-Z0-9]', ' ', text).split()

    candidates = []

    for i, word in enumerate(words):

        token = clean_alpha(word)

        if len(token) < 3:
            continue

        score = score_token(token, i, len(words), word_freq.get(token, 0))
        candidates.append((token, score))

    if candidates:
        return max(candidates, key=lambda x: x[1])[0]

    return "UNKNOWN"


# -----------------------------------------------------------
# File Upload
# -----------------------------------------------------------

file = st.file_uploader("Upload Bank Statement", type=["xlsx", "xls", "csv"])

if file:

    bank_ledger = file.name.split(".")[0].upper()

    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    narration_col = find_narration_column(df)

    st.success(f"Narration column detected: {narration_col}")

    df = clean_numeric_columns(df)
    df = flag_duplicates(df)

    # Build word frequency
    words = []
    for val in df[narration_col]:
        words.extend(re.sub(r'[^A-Z]', ' ', str(val).upper()).split())

    word_freq = Counter(words)

    # Extract transaction heads
    df["Transaction_Head"] = df[narration_col].apply(
        lambda x: extract_transaction_head(x, word_freq)
    )

    # Apply merge corrections
    for old, new in st.session_state.merged_heads.items():
        df.loc[df["Transaction_Head"] == old, "Transaction_Head"] = new

    # -------------------------------------------------------
    # Merge Transaction Heads
    # -------------------------------------------------------

    st.subheader("Merge Transaction Heads")

    unique_heads = sorted(df["Transaction_Head"].unique())

    merge_from = st.multiselect(
        "Select heads to merge",
        unique_heads
    )

    merge_into = st.text_input("Merge into")

    if st.button("Merge Heads") and merge_into:

        for head in merge_from:
            st.session_state.merged_heads[head] = merge_into

        st.rerun()

    # -------------------------------------------------------
    # Group Summary
    # -------------------------------------------------------

    group_summary = (
        df.groupby("Transaction_Head")
        .size()
        .reset_index(name="Transactions")
        .sort_values("Transactions", ascending=False)
    )

    group_summary["Ledger"] = group_summary["Transaction_Head"].map(
        st.session_state.ledger_map
    ).fillna("")

    group_summary["Ledger Group"] = ""

    major_groups = group_summary[group_summary["Transactions"] >= 3]
    minor_groups = group_summary[group_summary["Transactions"] < 3]

    st.subheader("Major Groups")
    edited_major = st.data_editor(major_groups, use_container_width=True)

    st.subheader("Minor Groups")
    edited_minor = st.data_editor(minor_groups, use_container_width=True)

    edited_groups = pd.concat([edited_major, edited_minor])

    # -------------------------------------------------------
    # Bulk Ledger Assignment
    # -------------------------------------------------------

    st.subheader("Bulk Ledger Assignment")

    unassigned = [
        g for g in group_summary["Transaction_Head"]
        if g not in st.session_state.ledger_map
    ]

    selected_groups = st.multiselect(
        "Select Groups",
        unassigned
    )

    ledger_input = st.text_input("Ledger Name")

    if st.button("Apply Ledger") and ledger_input:

        for g in selected_groups:
            st.session_state.ledger_map[g] = ledger_input

        st.rerun()

    if st.button("Reset Ledgers"):
        st.session_state.ledger_map = {}
        st.rerun()

    st.info(
        f"Assigned Groups: {len(st.session_state.ledger_map)} | "
        f"Remaining Groups: {len(unassigned)}"
    )

    # -------------------------------------------------------
    # Apply Ledger Mapping
    # -------------------------------------------------------

    df["Ledger"] = df["Transaction_Head"].map(st.session_state.ledger_map)

    # -------------------------------------------------------
    # Editable Transactions
    # -------------------------------------------------------

    st.subheader("Transactions")

    edited_df = st.data_editor(df, use_container_width=True)

    # -------------------------------------------------------
    # Validation
    # -------------------------------------------------------

    missing = edited_df[
        edited_df["Ledger"].isna() | (edited_df["Ledger"] == "")
    ]

    if len(missing) > 0:
        st.warning("Some transactions have no ledger assigned.")
        st.dataframe(missing[["Transaction_Head", narration_col]])

    # -------------------------------------------------------
    # Classified Download
    # -------------------------------------------------------

    buffer = BytesIO()
    edited_df.to_csv(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        "Download Classified File",
        buffer,
        "classified_transactions.csv",
        "text/csv"
    )

    # -------------------------------------------------------
    # Tally Export
    # -------------------------------------------------------

    withdraw_col = None
    deposit_col = None
    date_col = None

    for col in edited_df.columns:

        if "WITHDRAW" in col.upper() or "DEBIT" in col.upper():
            withdraw_col = col

        if "DEPOSIT" in col.upper() or "CREDIT" in col.upper():
            deposit_col = col

        if "DATE" in col.upper():
            date_col = col

    tally_df = pd.DataFrame()

    tally_df["Date"] = edited_df[date_col]
    tally_df["Ledger"] = edited_df["Ledger"]
    tally_df["Ledger Group"] = ""
    tally_df["Narration"] = edited_df[narration_col]

    tally_df["Amount"] = edited_df[withdraw_col].fillna(0)
    tally_df["Amount2"] = edited_df[deposit_col].fillna(0)

    tally_df["Bank Ledger"] = bank_ledger

    tally_df["Voucher Type"] = tally_df.apply(
        lambda r: "Payment" if r["Amount"] > 0 else "Receipt",
        axis=1
    )

    buffer2 = BytesIO()
    tally_df.to_csv(buffer2, index=False)
    buffer2.seek(0)

    st.download_button(
        "Download Tally Import File",
        buffer2,
        "tally_import.csv",
        "text/csv"
    )
