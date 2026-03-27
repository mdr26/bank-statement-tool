import streamlit as st
import pandas as pd
import re
import pdfplumber
from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()

from database import (
    get_clients, add_client, get_client_id, delete_client,
    get_banks, add_bank, get_bank_id, delete_bank,
    get_vendor_memory, save_vendor_memory, delete_memory
)

st.set_page_config(page_title="LedgerMind", layout="wide")

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "df" not in st.session_state:
    st.session_state.df = None

# --------------------------------------------------
# STOPWORDS SYSTEM (FIXED)
# --------------------------------------------------

def load_stopwords():
    try:
        file_path = os.path.join(os.getcwd(), "stopwords.xlsx")

        if not os.path.exists(file_path):
            st.error("❌ stopwords.xlsx not found in project")
            return set()

        df = pd.read_excel(file_path, header=None)

        words = set(
            df.iloc[:, 0]
            .dropna()
            .astype(str)
            .str.upper()
            .str.strip()
        )

        return words

    except Exception as e:
        st.error(f"Error loading stopwords: {e}")
        return set()

if "stopwords" not in st.session_state:
    st.session_state.stopwords = load_stopwords()

STOP_WORDS = st.session_state.stopwords

# --------------------------------------------------
# CONSTANTS
# --------------------------------------------------

COMPANY_WORDS = {
"PVT","LTD","PRIVATE","LIMITED","INDIA","SERVICES",
"SERVICE","TECHNOLOGIES","TECH","PAYMENTS","PAYMENT"
}

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
# EXTRACTOR
# --------------------------------------------------

def extract_head(text):

    text = str(text).upper()
    text = re.sub(r"\d+", " ", text)
    text = re.sub(r"[^A-Z ]", " ", text)

    tokens = text.split()
    cleaned = []

    for token in tokens:
        if len(token) < 3:
            continue
        if token in STOP_WORDS:
            continue
        if token in COMPANY_WORDS:
            continue
        cleaned.append(token)

    if not cleaned:
        return "SUSPENSE"

    return " ".join(cleaned)

# --------------------------------------------------
# APPLY MEMORY
# --------------------------------------------------

def apply_vendor_memory(df, client_id, bank_id):

    memory = get_vendor_memory(client_id, bank_id)

    df["Ledger"] = df["Transaction_Head"].map(
        lambda x: memory.get(x, ("", ""))[0]
    )

    df["Ledger Group"] = df["Transaction_Head"].map(
        lambda x: memory.get(x, ("", ""))[1]
    )

    return df

# --------------------------------------------------
# PDF PARSER
# --------------------------------------------------

def parse_pdf_statement(file):

    tables = []

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                df = pd.DataFrame(table[1:], columns=table[0])
                tables.append(df)

    if tables:
        return pd.concat(tables, ignore_index=True)

    return None

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.title("LedgerMind")

page = st.sidebar.selectbox(
    "Menu",
    ["Classifier", "Memory Manager", "Stopwords Manager"]
)

clients = get_clients()
client = st.sidebar.selectbox("Client", clients + ["➕ Add Client"])

if client == "➕ Add Client":

    new_client = st.sidebar.text_input("New Client Name")

    if st.sidebar.button("Create Client"):
        add_client(new_client)
        st.cache_data.clear()
        st.rerun()

else:

    client_id = get_client_id(client)

    if st.sidebar.button("🗑 Delete Client"):
        delete_client(client_id)
        st.cache_data.clear()
        st.rerun()

    banks = get_banks(client_id)
    bank = st.sidebar.selectbox("Bank", banks + ["➕ Add Bank"])

    if bank == "➕ Add Bank":

        new_bank = st.sidebar.text_input("New Bank Name")

        if st.sidebar.button("Create Bank"):
            add_bank(client_id, new_bank)
            st.cache_data.clear()
            st.rerun()

    else:

        bank_id = get_bank_id(client_id, bank)

        if st.sidebar.button("🗑 Delete Bank"):
            delete_bank(bank_id)
            st.cache_data.clear()
            st.rerun()

# --------------------------------------------------
# CLASSIFIER
# --------------------------------------------------

if page == "Classifier":

    st.title("LedgerMind")

    files = st.file_uploader(
        "Upload Statements",
        type=["xlsx","xls","csv","pdf"],
        accept_multiple_files=True
    )

    if files:

        dfs = []

        for file in files:

            if file.name.endswith(".csv"):
                df_temp = pd.read_csv(file)
            elif file.name.endswith(".pdf"):
                df_temp = parse_pdf_statement(file)
            else:
                df_temp = pd.read_excel(file)

            cols = df_temp.columns.tolist()

            date_col = st.selectbox("Date Column", cols, key=file.name+"d")
            nar_col = st.selectbox("Narration Column", cols, key=file.name+"n")
            deb_col = st.selectbox("Debit Column", cols, key=file.name+"db")
            cre_col = st.selectbox("Credit Column", cols, key=file.name+"cr")

            df_temp = df_temp.rename(columns={
                date_col:"Date",
                nar_col:"Narration",
                deb_col:"Debit",
                cre_col:"Credit"
            })

            df_temp["Narration"] = df_temp["Narration"].astype(str).str.upper()

            df_temp["Debit"] = pd.to_numeric(
                df_temp["Debit"].astype(str).str.replace(",",""),
                errors="coerce"
            ).fillna(0)

            df_temp["Credit"] = pd.to_numeric(
                df_temp["Credit"].astype(str).str.replace(",",""),
                errors="coerce"
            ).fillna(0)

            dfs.append(df_temp)

        df = pd.concat(dfs, ignore_index=True)
        df["Transaction_Head"] = df["Narration"].apply(extract_head)

        if "client_id" in locals() and "bank_id" in locals():
            df = apply_vendor_memory(df, client_id, bank_id)

        st.session_state.df = df

    if st.session_state.df is not None:

        st.subheader("Transactions")

        edited_df = st.data_editor(st.session_state.df, use_container_width=True)
        st.session_state.df = edited_df

        if st.button("Re-Extract Transaction Heads"):
            st.session_state.df["Transaction_Head"] = st.session_state.df["Narration"].apply(extract_head)
            st.rerun()

        st.markdown("---")
        st.subheader("Bulk Ledger Assignment")

        unmapped = st.session_state.df[
            st.session_state.df["Ledger"] == ""
        ]["Transaction_Head"].unique()

        selected = st.multiselect("Select Vendors", sorted(unmapped))

        ledger = st.text_input("Ledger Name")
        group = st.selectbox("Ledger Group", LEDGER_GROUPS)

        if st.button("Save Ledger Mapping"):
            for v in selected:
                save_vendor_memory(client_id, bank_id, v, ledger, group)

            st.cache_data.clear()
            st.success("Saved")
            st.rerun()

# --------------------------------------------------
# STOPWORDS MANAGER (FIXED)
# --------------------------------------------------

i# --------------------------------------------------
# STOPWORDS MANAGER (FULL CRUD)
# --------------------------------------------------

if page == "Stopwords Manager":

    st.title("Stopwords Manager")

    words = sorted(list(st.session_state.stopwords))

    # DISPLAY
    if not words:
        st.warning("⚠️ No stopwords found.")
    else:
        st.dataframe(pd.DataFrame(words, columns=["Word"]), use_container_width=True)

    st.markdown("---")

    # ➕ ADD STOPWORD
    st.subheader("Add Stopword")

    new_word = st.text_input("Enter new stopword").upper().strip()

    if st.button("Add Stopword"):
        if not new_word:
            st.warning("Enter a valid word")
        elif new_word in st.session_state.stopwords:
            st.warning(f"{new_word} already exists")
        else:
            st.session_state.stopwords.add(new_word)
            st.success(f"{new_word} added")
            st.rerun()

    st.markdown("---")

    # ❌ DELETE STOPWORD
    st.subheader("Delete Stopword")

    if words:
        delete_word = st.selectbox("Select word to delete", words)

        if st.button("Delete Stopword"):
            st.session_state.stopwords.remove(delete_word)
            st.success(f"{delete_word} removed")
            st.rerun()

    st.markdown("---")

    # 💾 SAVE TO EXCEL
    st.subheader("Save Changes")

    if st.button("💾 Save Stopwords to File"):
        try:
            df = pd.DataFrame(sorted(st.session_state.stopwords), columns=["Word"])
            df.to_excel("stopwords.xlsx", index=False)
            st.success("Stopwords saved successfully!")
        except Exception as e:
            st.error(f"Error saving file: {e}")