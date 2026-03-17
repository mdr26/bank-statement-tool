import streamlit as st
import pandas as pd
import re
import pdfplumber
from database import get_connection

st.set_page_config(page_title="LedgerMind", layout="wide")

conn = get_connection()
cur = conn.cursor()

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "df" not in st.session_state:
    st.session_state.df = None

# --------------------------------------------------
# STOPWORDS SYSTEM (INSIDE APP)
# --------------------------------------------------

def load_stopwords():
    try:
        df = pd.read_excel("stopwords.xlsx")
        col = df.columns[0]
        return set(df[col].dropna().astype(str).str.upper().str.strip())
    except:
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

    cur.execute("""
    SELECT vendor,ledger,ledger_group
    FROM vendor_memory
    WHERE client_id=? AND bank_id=?
    """,(client_id,bank_id))

    memory = {v:(l,g) for v,l,g in cur.fetchall()}

    df["Ledger"] = df["Transaction_Head"].map(
        lambda x: memory.get(x,("", ""))[0]
    )

    df["Ledger Group"] = df["Transaction_Head"].map(
        lambda x: memory.get(x,("", ""))[1]
    )

    return df

# --------------------------------------------------
# INTERBANK DETECTION
# --------------------------------------------------

def detect_interbank_transfers(df):

    if "Debit" not in df.columns or "Credit" not in df.columns:
        return df

    df["Transfer Flag"] = ""

    debit_df = df[df["Debit"] > 0]
    credit_df = df[df["Credit"] > 0]

    matches = debit_df.merge(
        credit_df,
        left_on="Debit",
        right_on="Credit",
        suffixes=("_d","_c")
    )

    for _, row in matches.iterrows():
        try:
            date_diff = abs(
                (pd.to_datetime(row["Date_d"]) -
                 pd.to_datetime(row["Date_c"])).days
            )

            if date_diff <= 1:
                amt = row["Debit"]

                df.loc[df["Debit"] == amt, "Ledger"] = "Interbank Transfer"
                df.loc[df["Credit"] == amt, "Ledger"] = "Interbank Transfer"

                df.loc[df["Debit"] == amt, "Ledger Group"] = "Bank Accounts"
                df.loc[df["Credit"] == amt, "Ledger Group"] = "Bank Accounts"

                df.loc[df["Debit"] == amt, "Transfer Flag"] = "Yes"
                df.loc[df["Credit"] == amt, "Transfer Flag"] = "Yes"

        except:
            pass

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
# TALLY EXPORT
# --------------------------------------------------

def prepare_tally_export(df, bank_name):

    export_df = df.copy()

    def get_type(row):
        if row["Credit"] > 0:
            return "Receipt"
        elif row["Debit"] > 0:
            return "Payment"
        return ""

    export_df["Voucher Type"] = export_df.apply(get_type, axis=1)
    export_df["Bank Ledger"] = bank_name

    return export_df[
        ["Date","Ledger","Ledger Group","Narration","Debit","Credit","Bank Ledger","Voucher Type"]
    ]

# --------------------------------------------------
# SIDEBAR - CLIENT & BANK MANAGEMENT
# --------------------------------------------------

st.sidebar.title("LedgerMind")

if st.sidebar.button("🔄 Reset Session"):
    st.session_state.df = None
    st.rerun()

# CLIENT
cur.execute("SELECT client_name FROM clients")
clients = [c[0] for c in cur.fetchall()]
client_options = clients + ["➕ Add Client"]

client = st.sidebar.selectbox("Client", client_options)

if client == "➕ Add Client":

    new_client = st.sidebar.text_input("New Client Name")

    if st.sidebar.button("Create Client"):
        cur.execute("INSERT OR IGNORE INTO clients(client_name) VALUES(?)",(new_client,))
        conn.commit()
        st.rerun()

else:

    cur.execute("SELECT id FROM clients WHERE client_name=?",(client,))
    client_id = cur.fetchone()[0]

    # BANK
    cur.execute("SELECT bank_name FROM banks WHERE client_id=?",(client_id,))
    banks = [b[0] for b in cur.fetchall()]
    bank_options = banks + ["➕ Add Bank"]

    bank = st.sidebar.selectbox("Bank", bank_options)

    if bank == "➕ Add Bank":

        new_bank = st.sidebar.text_input("New Bank Name")

        if st.sidebar.button("Create Bank"):
            cur.execute("INSERT INTO banks(client_id,bank_name) VALUES(?,?)",(client_id,new_bank))
            conn.commit()
            st.rerun()

    else:

        cur.execute("SELECT id FROM banks WHERE client_id=? AND bank_name=?",(client_id,bank))
        bank_id = cur.fetchone()[0]

# --------------------------------------------------
# MENU
# --------------------------------------------------

page = st.sidebar.selectbox(
    "Menu",
    ["Classifier","Memory Manager","Dashboard","Stopwords Manager"]
)

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
            if df_temp is None or df_temp.empty:
                st.error(f"{file.name} - PDF parsing failed. Please upload Excel instead.")
                continue

            cols = df_temp.columns.tolist()

            date_col = st.selectbox("Date Column",cols,key=file.name+"d")
            nar_col = st.selectbox("Narration Column",cols,key=file.name+"n")
            deb_col = st.selectbox("Debit Column",cols,key=file.name+"db")
            cre_col = st.selectbox("Credit Column",cols,key=file.name+"cr")

            df_temp = df_temp.rename(columns={
                date_col:"Date",
                nar_col:"Narration",
                deb_col:"Debit",
                cre_col:"Credit"
            })

            df_temp["Narration"] = df_temp["Narration"].astype(str).str.upper()

            df_temp["Debit"] = pd.to_numeric(df_temp["Debit"].astype(str).str.replace(",",""), errors="coerce").fillna(0)
            df_temp["Credit"] = pd.to_numeric(df_temp["Credit"].astype(str).str.replace(",",""), errors="coerce").fillna(0)

            dfs.append(df_temp)

        df = pd.concat(dfs, ignore_index=True)

        df["Transaction_Head"] = df["Narration"].apply(extract_head)

        df = apply_vendor_memory(df, client_id, bank_id)

        df = detect_interbank_transfers(df)

        st.session_state.df = df

    if st.session_state.df is not None:

        st.subheader("Transactions")

        edited_df = st.data_editor(st.session_state.df, use_container_width=True)
        st.session_state.df = edited_df

        if st.button("Re-Extract Transaction Heads"):
            st.session_state.df["Transaction_Head"] = st.session_state.df["Narration"].apply(extract_head)
            st.rerun()

        # BULK
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
                cur.execute("""
                INSERT OR REPLACE INTO vendor_memory
                (client_id,bank_id,vendor,ledger,ledger_group)
                VALUES(?,?,?,?,?)
                """,(client_id,bank_id,v,ledger,group))
            conn.commit()
            st.rerun()

        # REVIEW
        pending = st.session_state.df[st.session_state.df["Ledger"] == ""]
        if len(pending) > 0:
            st.warning(f"{len(pending)} pending")
            st.dataframe(pending[["Date","Narration","Transaction_Head"]])

        # EXPORT
        st.markdown("---")
        tally_df = prepare_tally_export(st.session_state.df, bank)

        st.download_button(
            "Download Tally File",
            tally_df.to_csv(index=False).encode(),
            "tally.csv"
        )

# --------------------------------------------------
# STOPWORDS MANAGER
# --------------------------------------------------

if page == "Stopwords Manager":

    st.title("Stopwords Manager")

    words = sorted(list(st.session_state.stopwords))
    st.dataframe(pd.DataFrame(words, columns=["Word"]))

    if "stopword_input" not in st.session_state:
        st.session_state.stopword_input = ""

    new = st.text_input("Add Stopword", key="stopword_input").upper().strip()

    if st.button("Add Stopword"):

        if not new:
            st.warning("Enter a valid word")

        elif new in st.session_state.stopwords:
            st.warning(f"{new} already exists")

        else:
            st.session_state.stopwords.add(new)
            st.session_state.stopword_input = ""
            st.success(f"{new} added")
            st.rerun()

    delete_word = st.selectbox("Delete Stopword", words)

    if st.button("Delete Stopword"):
        st.session_state.stopwords.remove(delete_word)
        st.success(f"{delete_word} removed")
        st.rerun()

    if st.button("💾 Save Stopwords"):
        try:
            pd.DataFrame(words, columns=["word"]).to_excel("stopwords.xlsx", index=False)
            st.success("Saved")
        except:
            st.error("Close Excel file before saving")
