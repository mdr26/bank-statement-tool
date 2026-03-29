import streamlit as st
import pandas as pd
import re
import pdfplumber

from database import (
    get_clients, add_client, get_client_id, delete_client,
    get_banks, add_bank, get_bank_id, delete_bank,
    get_vendor_memory, save_vendor_memory, delete_memory
)

st.set_page_config(page_title="LedgerMind", layout="wide")

# ---------------- HIDE BROWSER AUTOFILL ----------------
st.markdown("""
    <style>
    input[type="text"] {
        autocomplete: off;
    }
    </style>
    <script>
    document.querySelectorAll('input[type="text"]').forEach(el => {
        el.setAttribute('autocomplete', 'off');
    });
    </script>
""", unsafe_allow_html=True)

# ---------------- SESSION ----------------
if "df" not in st.session_state:
    st.session_state.df = None

# ---------------- STOPWORDS ----------------
def load_stopwords():
    try:
        df = pd.read_excel("stopwords.xlsx", header=None)
        return set(df.iloc[:, 0].dropna().astype(str).str.upper().str.strip())
    except:
        return set()

if "stopwords" not in st.session_state:
    st.session_state.stopwords = load_stopwords()

# ---------------- CONSTANTS ----------------
COMPANY_WORDS = {
    "PVT", "LTD", "PRIVATE", "LIMITED", "INDIA", "SERVICES",
    "SERVICE", "TECHNOLOGIES", "TECH", "PAYMENTS", "PAYMENT"
}

LEDGER_GROUPS = sorted([
    "Bank Accounts", "Cash-in-Hand", "Direct Expenses", "Indirect Expenses",
    "Sales Accounts", "Purchase Accounts", "Sundry Creditors", "Sundry Debtors"
])

# ---------------- FUNCTIONS ----------------
def extract_head(text):
    stop_words = st.session_state.stopwords

    text = str(text).upper()
    text = re.sub(r"\d+", " ", text)
    text = re.sub(r"[^A-Z ]", " ", text)

    tokens = text.split()
    cleaned = []

    for token in tokens:
        if len(token) < 3:
            continue
        if token in stop_words or token in COMPANY_WORDS:
            continue
        cleaned.append(token)

    return " ".join(cleaned) if cleaned else "SUSPENSE"


def apply_vendor_memory(df, client_id, bank_id):
    memory = get_vendor_memory(client_id, bank_id)

    df["Ledger"]       = df["Transaction_Head"].map(lambda x: memory.get(x, ("", ""))[0])
    df["Ledger Group"] = df["Transaction_Head"].map(lambda x: memory.get(x, ("", ""))[1])

    return df


def parse_pdf_statement(file):
    tables = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                df = pd.DataFrame(table[1:], columns=table[0])
                tables.append(df)

    return pd.concat(tables, ignore_index=True) if tables else None


def prepare_tally_export(df, bank_name):
    export_df = df.copy()

    export_df["Voucher Type"] = export_df.apply(
        lambda row: "Receipt" if row["Credit"] > 0 else ("Payment" if row["Debit"] > 0 else ""),
        axis=1
    )
    export_df["Bank Ledger"] = bank_name

    return export_df


def parse_date_column(series):
    try:
        return pd.to_datetime(series).dt.strftime("%d-%m-%Y")
    except:
        return series


def guess_column(cols, keywords):
    for keyword in keywords:
        for col in cols:
            if keyword.lower() in str(col).lower():
                return col
    return cols[0]


# ---------------- SIDEBAR ----------------
st.sidebar.title("LedgerMind")

page = st.sidebar.selectbox(
    "Menu",
    ["Classifier", "Memory Manager", "Stopwords Manager"],
    key="menu"
)

# ---------- HANDLE PENDING DELETES ----------
if st.session_state.get("pending_delete_client"):
    client_id_to_delete = st.session_state.pop("pending_delete_client")
    delete_client(client_id_to_delete)
    for key in ["client", "bank", "client_id", "bank_id"]:
        st.session_state.pop(key, None)
    st.rerun()

if st.session_state.get("pending_delete_bank"):
    bank_id_to_delete = st.session_state.pop("pending_delete_bank")
    delete_bank(bank_id_to_delete)
    for key in ["bank", "bank_id"]:
        st.session_state.pop(key, None)
    st.rerun()

# ---------- CLIENT ----------
clients        = get_clients()
client_options = clients + ["➕ Add Client"]

if "select_client" in st.session_state:
    st.session_state["client"] = st.session_state.pop("select_client")

if "client" not in st.session_state or st.session_state["client"] not in client_options:
    st.session_state["client"] = client_options[0]

client = st.sidebar.selectbox("Client", client_options, key="client")

if client == "➕ Add Client":

    new_client = st.sidebar.text_input("New Client Name", key="new_client")

    if st.sidebar.button("Create Client"):
        if new_client.strip():
            clean = new_client.strip().upper()

            if clean not in [c.upper() for c in get_clients()]:
                add_client(clean)

            st.session_state["select_client"] = clean
            st.rerun()

else:

    client_id = get_client_id(client)
    st.session_state["client_id"] = client_id

    if st.sidebar.button("🗑 Delete Client"):
        st.session_state["pending_delete_client"] = client_id
        st.rerun()

    # ---------- BANK (FIXED) ----------
    banks = get_banks(client_id)
    bank_options = banks + ["➕ Add Bank"]

    if "bank" not in st.session_state or st.session_state["bank"] not in bank_options:
        st.session_state["bank"] = bank_options[0]

    if "select_bank" in st.session_state:
        st.session_state["bank"] = st.session_state.pop("select_bank")

    bank = st.sidebar.selectbox("Bank", bank_options, key="bank")

    if bank == "➕ Add Bank":

        new_bank = st.sidebar.text_input("New Bank Name", key="new_bank")

        if st.sidebar.button("Create Bank"):
            if new_bank.strip():
                clean = new_bank.strip().upper()

                if clean not in [b.upper() for b in get_banks(client_id)]:
                    add_bank(client_id, clean)

                st.session_state["select_bank"] = clean
                st.rerun()

    else:

        bank_id = get_bank_id(client_id, bank)
        st.session_state["bank_id"] = bank_id

        if st.sidebar.button("🗑 Delete Bank"):
            st.session_state["pending_delete_bank"] = bank_id
            st.rerun()

# ---------------- CLASSIFIER ----------------
if page == "Classifier":

    st.title("LedgerMind")

    files = st.file_uploader("Upload Files", accept_multiple_files=True)

    if files:

        dfs = []

        for file in files:
            df = pd.read_excel(file) if not file.name.endswith(".pdf") else parse_pdf_statement(file)

            df = df.dropna(how="all").reset_index(drop=True)

            cols = df.columns.tolist()

            default_date = guess_column(cols, ["date"])
            default_nar  = guess_column(cols, ["narration"])
            default_deb  = guess_column(cols, ["debit"])
            default_cre  = guess_column(cols, ["credit"])

            date = st.selectbox("Date", cols, key=file.name+"d")
            nar  = st.selectbox("Narration", cols, key=file.name+"n")
            deb  = st.selectbox("Debit", cols, key=file.name+"db")
            cre  = st.selectbox("Credit", cols, key=file.name+"cr")

            df = df.rename(columns={date:"Date", nar:"Narration", deb:"Debit", cre:"Credit"})
            df = df[["Date","Narration","Debit","Credit"]]

            df["Date"] = parse_date_column(df["Date"])
            df["Narration"] = df["Narration"].astype(str).str.upper()
            df["Debit"] = pd.to_numeric(df["Debit"], errors="coerce").fillna(0)
            df["Credit"] = pd.to_numeric(df["Credit"], errors="coerce").fillna(0)

            df = df[(df["Debit"] != 0) | (df["Credit"] != 0)]
            dfs.append(df)

        df = pd.concat(dfs)
        df["Transaction_Head"] = df["Narration"].apply(extract_head)

        if "client_id" in st.session_state and "bank_id" in st.session_state:
            df = apply_vendor_memory(df, st.session_state["client_id"], st.session_state["bank_id"])
        else:
            df["Ledger"] = ""
            df["Ledger Group"] = ""

        st.session_state.df = df

    if st.session_state.df is not None:

        st.data_editor(st.session_state.df)

        st.subheader("Bulk Ledger Assignment")

        if "client_id" in st.session_state and "bank_id" in st.session_state:

            unmapped = st.session_state.df[
                st.session_state.df["Ledger"] == ""
            ]["Transaction_Head"].unique()

            selected = st.multiselect("Select Vendors", unmapped)
            ledger = st.text_input("Ledger Name")
            group = st.selectbox("Ledger Group", LEDGER_GROUPS)

            if st.button("Save Ledger Mapping"):
                for v in selected:
                    save_vendor_memory(st.session_state["client_id"], st.session_state["bank_id"], v, ledger, group)
                st.rerun()

        else:
            st.warning("Select client and bank first")