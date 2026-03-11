import streamlit as st
import pandas as pd
import re
from collections import Counter
from io import BytesIO

st.set_page_config(page_title="Bank Statement Intelligent Classifier", layout="wide")

st.title("Bank Statement Classifier")

# --------------------------------------------------
# LOAD STOPWORDS FROM EXCEL
# --------------------------------------------------

def load_stopwords():

    try:
        df = pd.read_excel("stopwords.xlsx")

        words = (
            df["word"]
            .dropna()
            .astype(str)
            .str.upper()
            .str.strip()
            .tolist()
        )

        return set(words)

    except Exception as e:
        st.warning("Stopwords file not found or incorrect format.")
        return set()

STOP_WORDS = load_stopwords()

# --------------------------------------------------
# UNKNOWN WORD LOG
# --------------------------------------------------

unknown_words = set()

# --------------------------------------------------
# TALLY LEDGER GROUPS
# --------------------------------------------------

LEDGER_GROUPS = sorted([
"Bank Accounts","Bank OCC A/c","Bank OD A/c","Branch / Divisions",
"Capital Account","Cash-in-Hand","Current Assets","Current Liabilities",
"Deposits (Asset)","Direct Expenses","Direct Incomes","Duties & Taxes",
"Expenses (Direct)","Expenses (Indirect)","Fixed Assets","Income (Direct)",
"Income (Indirect)","Indirect Expenses","Indirect Incomes","Investments",
"Loans & Advances (Asset)","Loans (Liability)","Misc. Expenses (ASSET)",
"Provisions","Purchase Accounts","Reserves & Surplus","Retained Earnings",
"Sales Accounts","Secured Loans","Stock-in-Hand","Sundry Creditors",
"Sundry Debtors","Suspense A/c","Unsecured Loans"
])

# --------------------------------------------------
# CLEAN WORD
# --------------------------------------------------

def clean_word(text):
    return re.sub(r'[^A-Z]', '', text)

# --------------------------------------------------
# EXTRACT TRANSACTION HEAD
# --------------------------------------------------

def extract_head(text, freq):

    text = str(text).upper()
    words = re.sub(r'[^A-Z]', ' ', text).split()

    candidates = []

    for w in words:

        w_clean = clean_word(w)

        if len(w_clean) < 3:
            continue

        if w_clean in STOP_WORDS:
            continue

        if w_clean.startswith("OK"):
            continue

        if any(char.isdigit() for char in w_clean):
            continue

        # log possible stopwords
        if len(w_clean) >= 4 and freq.get(w_clean,0) < 3:
            unknown_words.add(w_clean)

        candidates.append((w_clean, freq.get(w_clean,0)))

    if candidates:
        return max(candidates, key=lambda x: x[1])[0]

    return "SUSPENSE"

# --------------------------------------------------
# FIND NARRATION COLUMN
# --------------------------------------------------

def find_narration(df):

    for col in df.columns:
        c = col.upper()

        if "NARR" in c or "PARTICULAR" in c or "DESC" in c:
            return col

    text_cols = df.select_dtypes(include="object")

    return text_cols.columns[0]

# --------------------------------------------------
# FILE UPLOAD
# --------------------------------------------------

file = st.file_uploader("Upload Bank Statement", type=["xlsx","xls","csv"])

if file:

    if file.name.endswith(".csv"):
        df = pd.read_csv(file)

    else:
        df = pd.read_excel(file)

    narration_col = find_narration(df)

    st.success(f"Narration column detected: {narration_col}")

# --------------------------------------------------
# WORD FREQUENCY
# --------------------------------------------------

    words = []

    for val in df[narration_col]:

        words.extend(
            re.sub(r'[^A-Z]', ' ', str(val).upper()).split()
        )

    freq = Counter(words)

# --------------------------------------------------
# TRANSACTION HEAD
# --------------------------------------------------

    df["Transaction_Head"] = df[narration_col].apply(
        lambda x: extract_head(x,freq)
    )

# --------------------------------------------------
# POSSIBLE STOPWORDS REVIEW
# --------------------------------------------------

    if unknown_words:

        st.subheader("Possible Stopwords (Review)")

        review_df = pd.DataFrame(
            sorted(unknown_words),
            columns=["Possible_Stopword"]
        )

        st.dataframe(review_df, use_container_width=True)

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

    if "merge_map" not in st.session_state:
        st.session_state.merge_map = {}

    if "ledger_map" not in st.session_state:
        st.session_state.ledger_map = {}

    if "ledger_group_map" not in st.session_state:
        st.session_state.ledger_group_map = {}

# --------------------------------------------------
# MERGE TRANSACTION HEADS
# --------------------------------------------------

    st.subheader("Merge Transaction Heads")

    heads = sorted(df["Transaction_Head"].unique())

    merge_select = st.multiselect("Select heads to merge", heads)

    merge_into = st.text_input("Merge into")

    if st.button("Merge Heads"):

        for h in merge_select:

            st.session_state.merge_map[h] = merge_into

        df["Transaction_Head"] = df["Transaction_Head"].replace(
            st.session_state.merge_map
        )

        st.success("Heads merged")

# --------------------------------------------------
# GROUP COUNTS
# --------------------------------------------------

    group_counts = (
        df["Transaction_Head"]
        .value_counts()
        .reset_index()
    )

    group_counts.columns = ["Transaction_Head","Transactions"]

# --------------------------------------------------
# MAJOR / MINOR GROUPS
# --------------------------------------------------

    major = group_counts[group_counts["Transactions"] >= 5]
    minor = group_counts[group_counts["Transactions"] < 5]

# --------------------------------------------------
# DISPLAY GROUPS
# --------------------------------------------------

    st.subheader("Major Groups")

    major_display = major.copy()

    major_display["Ledger"] = (
        major_display["Transaction_Head"]
        .map(st.session_state.ledger_map)
    )

    st.dataframe(major_display, use_container_width=True)

    st.subheader("Minor Groups")

    minor_display = minor.copy()

    minor_display["Ledger"] = (
        minor_display["Transaction_Head"]
        .map(st.session_state.ledger_map)
    )

    st.dataframe(minor_display, use_container_width=True)

# --------------------------------------------------
# BULK LEDGER ASSIGNMENT
# --------------------------------------------------

    st.subheader("Bulk Ledger Assignment")

    groups = group_counts["Transaction_Head"].tolist()

    selected = st.multiselect("Select Groups", groups)

    ledger_name = st.text_input("Ledger Name")

    ledger_group = st.selectbox("Ledger Group", LEDGER_GROUPS)

    if st.button("Apply Ledger"):

        for g in selected:

            st.session_state.ledger_map[g] = ledger_name
            st.session_state.ledger_group_map[g] = ledger_group

        st.success("Ledger Assigned")

# --------------------------------------------------
# APPLY LEDGER
# --------------------------------------------------

    df["Ledger"] = df["Transaction_Head"].map(
        st.session_state.ledger_map
    )

    df["Ledger Group"] = df["Transaction_Head"].map(
        st.session_state.ledger_group_map
    )

# --------------------------------------------------
# TRANSACTIONS TABLE
# --------------------------------------------------

    st.subheader("Transactions")

    edited_df = st.data_editor(
        df,
        use_container_width=True
    )

# --------------------------------------------------
# FIND AMOUNT COLUMNS
# --------------------------------------------------

    withdraw_col = None
    deposit_col = None
    date_col = None

    for col in edited_df.columns:

        c = col.upper()

        if any(x in c for x in ["WITHDRAW","DEBIT","DR"]):
            withdraw_col = col

        if any(x in c for x in ["DEPOSIT","CREDIT","CR"]):
            deposit_col = col

        if "DATE" in c:
            date_col = col

# --------------------------------------------------
# TALLY EXPORT
# --------------------------------------------------

    tally_df = pd.DataFrame()

    tally_df["Date"] = edited_df[date_col]
    tally_df["Ledger"] = edited_df["Ledger"]
    tally_df["Ledger Group"] = edited_df["Ledger Group"]
    tally_df["Narration"] = edited_df[narration_col]

    tally_df["Debit"] = pd.to_numeric(
        edited_df[withdraw_col].astype(str).str.replace(",",""),
        errors="coerce"
    ).fillna(0)

    tally_df["Credit"] = pd.to_numeric(
        edited_df[deposit_col].astype(str).str.replace(",",""),
        errors="coerce"
    ).fillna(0)

    tally_df["Bank Ledger"] = file.name.upper()

    tally_df["Voucher Type"] = tally_df.apply(
        lambda r: "Payment" if r["Debit"] > 0 else "Receipt",
        axis=1
    )

# --------------------------------------------------
# DOWNLOAD
# --------------------------------------------------

    buffer = BytesIO()

    tally_df.to_csv(buffer, index=False)

    buffer.seek(0)

    st.download_button(
        "Download Tally Import File",
        buffer,
        "tally_import.csv",
        "text/csv"
    )
