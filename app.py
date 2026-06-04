import streamlit as st
import pandas as pd
import re
import pdfplumber

from database import (
    get_clients, add_client, get_client_id, delete_client,
    get_banks, add_bank, get_bank_id, delete_bank,
    get_vendor_memory, save_vendor_memory, delete_memory,
    get_stopwords, add_stopword, delete_stopword
)

st.set_page_config(
    page_title="LedgerMind",
    page_icon="📒",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0d2018;
    color: #e8f5ee;
}

#MainMenu, footer, header { visibility: hidden; }

[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }

.page-title {
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
    font-size: 1.6rem;
    color: #e8f5ee;
    margin-bottom: 0.25rem;
}
.page-subtitle {
    font-size: 0.82rem;
    color: #2d6b42;
    margin-bottom: 1.5rem;
    font-family: 'IBM Plex Mono', monospace;
}
.brand {
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
    font-size: 1.4rem;
    color: #e8f5ee;
}
.brand span { color: #3ecf8e; }

.metric-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.metric-badge {
    background: #112a1c;
    border: 1px solid #1d4a2d;
    border-radius: 8px;
    padding: 0.75rem 1.25rem;
    min-width: 130px;
}
.metric-badge .val {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.6rem;
    font-weight: 600;
    color: #3ecf8e;
    line-height: 1;
}
.metric-badge .val.yellow { color: #f7c94f; }
.metric-badge .lbl {
    font-size: 0.7rem;
    color: #2d6b42;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-top: 0.25rem;
}

[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background: #112a1c !important;
    border: 1px solid #1d4a2d !important;
    color: #e8f5ee !important;
    border-radius: 7px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #3ecf8e !important;
    box-shadow: 0 0 0 2px rgba(62,207,142,0.15) !important;
}

[data-testid="stButton"] > button {
    background: #112a1c !important;
    color: #3ecf8e !important;
    border: 1px solid #1d4a2d !important;
    border-radius: 7px !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    transition: all 0.15s ease !important;
}
[data-testid="stButton"] > button:hover {
    background: #1d4a2d !important;
    border-color: #3ecf8e !important;
}

[data-testid="stDownloadButton"] > button {
    background: #1d4a2d !important;
    color: #3ecf8e !important;
    border: 1px solid #3ecf8e !important;
    border-radius: 7px !important;
    font-weight: 600 !important;
    width: 100% !important;
}

[data-testid="stFileUploader"] {
    background: #112a1c !important;
    border: 2px dashed #1d4a2d !important;
    border-radius: 10px !important;
}

[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
    border: 1px solid #1d4a2d !important;
    border-radius: 8px !important;
}

[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
    background: #1d4a2d !important;
    color: #3ecf8e !important;
    border-radius: 4px !important;
}

hr { border-color: #1d4a2d !important; }

.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: #3ecf8e;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.5rem;
    margin-top: 1.5rem;
}

.pill { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.72rem; font-weight: 500; }
.pill-green  { background: #0a1a12; color: #3ecf8e; border: 1px solid #1d4a2d; }
.pill-yellow { background: #1c1503; color: #f7c94f; border: 1px solid #92400e; }
.pill-blue   { background: #0c1a2e; color: #60a5fa; border: 1px solid #1e3a5f; }

.interbank-note {
    background: #1c1503;
    border: 1px solid #92400e;
    border-radius: 6px;
    padding: 0.5rem 1rem;
    font-size: 0.8rem;
    color: #f7c94f;
    margin-bottom: 1rem;
    font-family: 'IBM Plex Mono', monospace;
}

[data-testid="stAlert"] { border-radius: 8px !important; font-size: 0.85rem !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────

COMPANY_WORDS = {
    "PVT", "LTD", "PRIVATE", "LIMITED", "INDIA", "SERVICES",
    "SERVICE", "TECHNOLOGIES", "TECH", "PAYMENTS", "PAYMENT"
}

LEDGER_GROUPS = sorted([
    "Bank Accounts", "Cash-in-Hand", "Direct Expenses", "Indirect Expenses",
    "Sales Accounts", "Purchase Accounts", "Sundry Creditors", "Sundry Debtors"
])


# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────

for key in ["df", "client_id", "bank_id"]:
    if key not in st.session_state:
        st.session_state[key] = None

if "stopwords" not in st.session_state:
    try:
        st.session_state.stopwords = get_stopwords()
    except Exception:
        st.session_state.stopwords = set()


# ─────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────

def clean_number(val):
    """Convert any number format to float — handles ₹, commas, blanks, dashes."""
    if pd.isna(val):
        return 0.0
    s = str(val).strip()
    s = re.sub(r'[₹$€£\s]', '', s)
    s = s.replace(',', '')
    if s in ('-', '', 'nan', 'NaN', 'None'):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def extract_head(text):
    """Clean a narration down to a meaningful transaction head."""
    stop_words = st.session_state.stopwords
    text = str(text).upper()
    text = re.sub(r"\d+", " ", text)
    text = re.sub(r"[^A-Z ]", " ", text)
    tokens = text.split()
    cleaned = [t for t in tokens if len(t) >= 3 and t not in stop_words and t not in COMPANY_WORDS]
    return " ".join(cleaned) if cleaned else "SUSPENSE"


def apply_vendor_memory(df, client_id, bank_id):
    """Apply saved ledger mappings. Never overwrites Interbank rows."""
    memory = get_vendor_memory(client_id, bank_id)
    for idx, row in df.iterrows():
        if row.get("Ledger") == "Interbank":
            continue
        vendor = row["Transaction_Head"]
        if vendor in memory:
            df.at[idx, "Ledger"]       = memory[vendor][0]
            df.at[idx, "Ledger Group"] = memory[vendor][1]
    return df


def detect_interbank(dfs_with_names):
    """Find same date + same amount across 2+ different bank files."""
    if len(dfs_with_names) < 2:
        return set()
    key_banks = {}
    for bank_name, df in dfs_with_names:
        for _, row in df.iterrows():
            date   = str(row["Date"])
            amount = row["Debit"] if row["Debit"] > 0 else row["Credit"]
            if amount > 0:
                key = (date, amount)
                if key not in key_banks:
                    key_banks[key] = set()
                key_banks[key].add(bank_name)
    return {key for key, banks in key_banks.items() if len(banks) >= 2}


def parse_pdf_statement(file):
    """Extract tables from a PDF bank statement."""
    tables = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                df = pd.DataFrame(table[1:], columns=table[0])
                tables.append(df)
    return pd.concat(tables, ignore_index=True) if tables else None


def parse_date_column(series):
    try:
        return pd.to_datetime(series, dayfirst=True).dt.strftime("%d-%m-%Y")
    except Exception:
        return series.astype(str)


def guess_column(cols, keywords):
    for keyword in keywords:
        for col in cols:
            if keyword.lower() in str(col).lower():
                return col
    return cols[0]


def prepare_tally_export(df, bank_name):
    export_df = df.copy()
    export_df["Voucher Type"] = export_df.apply(
        lambda row: "Receipt" if row["Credit"] > 0 else ("Payment" if row["Debit"] > 0 else ""), axis=1
    )
    export_df["Bank Ledger"] = bank_name
    return export_df


def read_file(file):
    """Read Excel, CSV, or PDF into a dataframe."""
    name = file.name.lower()
    if name.endswith(".pdf"):
        df = parse_pdf_statement(file)
        if df is None:
            st.error(f"Could not extract table from {file.name}.")
        return df
    elif name.endswith(".csv"):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)


# ─────────────────────────────────────────────
#  CLIENT / BANK SELECTOR
# ─────────────────────────────────────────────

def render_client_bank_selector(suffix=""):
    """Renders client + bank dropdowns inline. Returns True if both are selected."""

    if st.session_state.get(f"pending_delete_client_{suffix}"):
        try:
            delete_client(st.session_state.pop(f"pending_delete_client_{suffix}"))
        except Exception as e:
            st.error(f"Delete failed: {e}")
        st.session_state.client_id = None
        st.session_state.bank_id   = None
        st.rerun()

    if st.session_state.get(f"pending_delete_bank_{suffix}"):
        try:
            delete_bank(st.session_state.pop(f"pending_delete_bank_{suffix}"))
        except Exception as e:
            st.error(f"Delete failed: {e}")
        st.session_state.bank_id = None
        st.rerun()

    clients        = get_clients()
    client_options = clients + ["➕ Add New Client"]

    col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 1, 2])

    with col1:
        if f"sel_client_{suffix}" in st.session_state:
            default = st.session_state.pop(f"sel_client_{suffix}")
            idx = client_options.index(default) if default in client_options else 0
        else:
            idx = 0
        client = st.selectbox("Client", client_options, index=idx, key=f"client_dd_{suffix}")

    if client == "➕ Add New Client":
        with col3:
            new_client = st.text_input("New client name", key=f"new_client_{suffix}")
        with col4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Create", key=f"create_client_{suffix}"):
                if new_client.strip():
                    clean = new_client.strip().upper()
                    add_client(clean)
                    st.session_state[f"sel_client_{suffix}"] = clean
                    st.rerun()
        st.session_state.client_id = None
        st.session_state.bank_id   = None
        return False

    client_id = get_client_id(client)
    st.session_state.client_id = client_id

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑", key=f"del_client_{suffix}", help="Delete client"):
            st.session_state[f"pending_delete_client_{suffix}"] = client_id
            st.rerun()

    banks        = get_banks(client_id)
    bank_options = banks + ["➕ Add New Bank"]

    with col3:
        if f"sel_bank_{suffix}" in st.session_state:
            default = st.session_state.pop(f"sel_bank_{suffix}")
            bidx = bank_options.index(default) if default in bank_options else 0
        else:
            bidx = 0
        bank = st.selectbox("Bank", bank_options, index=bidx, key=f"bank_dd_{suffix}")

    if bank == "➕ Add New Bank":
        with col5:
            new_bank = st.text_input("New bank name", key=f"new_bank_{suffix}")
        with col4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Create", key=f"create_bank_{suffix}"):
                if new_bank.strip():
                    clean = new_bank.strip().upper()
                    add_bank(client_id, clean)
                    st.session_state[f"sel_bank_{suffix}"] = clean
                    st.rerun()
        st.session_state.bank_id = None
        return False

    bank_id = get_bank_id(client_id, bank)
    st.session_state.bank_id   = bank_id
    st.session_state[f"current_bank_name_{suffix}"] = bank

    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑", key=f"del_bank_{suffix}", help="Delete bank"):
            st.session_state[f"pending_delete_bank_{suffix}"] = bank_id
            st.rerun()

    with col5:
        st.markdown(
            f'<div style="padding-top:1.8rem;">'
            f'<span class="pill pill-green">{client}</span>&nbsp;→&nbsp;'
            f'<span class="pill pill-blue">{bank}</span></div>',
            unsafe_allow_html=True
        )

    return True


# ─────────────────────────────────────────────
#  TOP BRAND
# ─────────────────────────────────────────────

st.markdown('<p class="brand">Ledger<span>Mind</span></p>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📊 Classifier", "🧠 Memory Manager", "🔤 Stopwords Manager"])


# ─────────────────────────────────────────────
#  TAB 1: CLASSIFIER
# ─────────────────────────────────────────────

with tab1:
    st.markdown('<div class="page-title">Statement Classifier</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Upload → Extract → Map → Export</div>', unsafe_allow_html=True)

    ready = render_client_bank_selector("clf")

    if not ready:
        st.info("Select a client and bank above to continue.")
        st.stop()

    st.markdown("---")

    files = st.file_uploader(
        "Upload bank statements — multiple files supported for interbank detection",
        accept_multiple_files=True,
        type=["xlsx", "xls", "csv", "pdf"]
    )

    if files:
        dfs_with_names = []

        for file in files:
            try:
                df_raw = read_file(file)
                if df_raw is None:
                    continue

                df_raw = df_raw.dropna(how="all").reset_index(drop=True)
                cols   = df_raw.columns.tolist()

                st.markdown(f'<div class="section-label">Column Mapping — {file.name}</div>', unsafe_allow_html=True)
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    date_col = st.selectbox("Date", cols, index=cols.index(guess_column(cols, ["date","dt","txn date","value date"])), key=file.name+"d")
                with c2:
                    nar_col  = st.selectbox("Narration", cols, index=cols.index(guess_column(cols, ["narration","description","particulars","remarks","nar"])), key=file.name+"n")
                with c3:
                    deb_col  = st.selectbox("Debit", cols, index=cols.index(guess_column(cols, ["debit","dr"])), key=file.name+"db")
                with c4:
                    cre_col  = st.selectbox("Credit", cols, index=cols.index(guess_column(cols, ["credit","cr"])), key=file.name+"cr")

                df_raw = df_raw.rename(columns={
                    date_col: "Date", nar_col: "Narration",
                    deb_col: "Debit", cre_col: "Credit"
                })
                df_raw = df_raw[["Date", "Narration", "Debit", "Credit"]]
                df_raw["Date"]      = parse_date_column(df_raw["Date"])
                df_raw["Narration"] = df_raw["Narration"].astype(str).str.upper().str.strip()
                df_raw["Debit"]     = df_raw["Debit"].apply(clean_number)
                df_raw["Credit"]    = df_raw["Credit"].apply(clean_number)
                df_raw = df_raw[(df_raw["Debit"] != 0) | (df_raw["Credit"] != 0)]
                df_raw["Source_File"] = file.name
                dfs_with_names.append((file.name, df_raw.copy()))

            except Exception as e:
                st.error(f"Error reading {file.name}: {e}")

        if dfs_with_names:
            interbank_keys = detect_interbank(dfs_with_names)
            df_combined    = pd.concat([df for _, df in dfs_with_names], ignore_index=True)

            df_combined["Transaction_Head"] = df_combined["Narration"].apply(extract_head)
            df_combined["Ledger"]           = ""
            df_combined["Ledger Group"]     = ""
            df_combined["Interbank"]        = False

            for idx, row in df_combined.iterrows():
                date   = str(row["Date"])
                amount = row["Debit"] if row["Debit"] > 0 else row["Credit"]
                key    = (date, amount)
                if key in interbank_keys:
                    df_combined.at[idx, "Ledger"]       = "Interbank"
                    df_combined.at[idx, "Ledger Group"] = "Bank Accounts"
                    df_combined.at[idx, "Interbank"]    = True

            df_combined = apply_vendor_memory(
                df_combined,
                st.session_state.client_id,
                st.session_state.bank_id
            )
            st.session_state.df = df_combined

    if st.session_state.df is not None:
        df = st.session_state.df

        total       = len(df)
        interbank_n = int(df["Interbank"].sum()) if "Interbank" in df.columns else 0
        mapped      = int((df["Ledger"] != "").sum())
        unmapped    = total - mapped
        pct         = int((mapped / total * 100)) if total > 0 else 0

        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-badge"><div class="val">{total}</div><div class="lbl">Transactions</div></div>
            <div class="metric-badge"><div class="val">{mapped}</div><div class="lbl">Mapped</div></div>
            <div class="metric-badge"><div class="val yellow">{unmapped}</div><div class="lbl">Unmapped</div></div>
            <div class="metric-badge"><div class="val">{pct}%</div><div class="lbl">Coverage</div></div>
            <div class="metric-badge"><div class="val yellow">{interbank_n}</div><div class="lbl">Interbank</div></div>
        </div>
        """, unsafe_allow_html=True)

        if interbank_n > 0:
            st.markdown(
                f'<div class="interbank-note">⚠ {interbank_n} interbank transaction(s) detected — '
                f'same date & amount across multiple statements. Marked as "Interbank". Please verify manually.</div>',
                unsafe_allow_html=True
            )

        st.markdown('<div class="section-label">Search Transactions</div>', unsafe_allow_html=True)
        search = st.text_input("Filter", placeholder="Search by narration, vendor, ledger, or date...", label_visibility="collapsed")

        display_df = df[[c for c in df.columns if c != "Interbank"]].copy()
        if search.strip():
            mask       = display_df.apply(lambda col: col.astype(str).str.contains(search.strip(), case=False, na=False)).any(axis=1)
            display_df = display_df[mask]

        st.dataframe(display_df, use_container_width=True, height=380)
        st.caption(f"Showing {len(display_df)} of {total} transactions")

        st.markdown("---")
        st.markdown('<div class="section-label">Bulk Ledger Assignment</div>', unsafe_allow_html=True)

        unmapped_vendors = sorted(
            df[(df["Ledger"] == "") & (~df.get("Interbank", pd.Series(False, index=df.index)))]["Transaction_Head"].unique()
        )

        if unmapped_vendors:
            col1, col2 = st.columns([2, 1])
            with col1:
                selected    = st.multiselect("Select vendors to map", unmapped_vendors)
                ledger_name = st.text_input("Ledger Name", placeholder="e.g. Office Supplies")
            with col2:
                ledger_group = st.selectbox("Ledger Group", LEDGER_GROUPS)
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 Save Mapping"):
                    if selected and ledger_name.strip():
                        for v in selected:
                            try:
                                save_vendor_memory(
                                    st.session_state.client_id,
                                    st.session_state.bank_id,
                                    v, ledger_name.strip(), ledger_group
                                )
                            except Exception as e:
                                st.error(f"Failed to save {v}: {e}")
                        st.success(f"✓ Saved {len(selected)} mapping(s)")
                        df = apply_vendor_memory(df, st.session_state.client_id, st.session_state.bank_id)
                        st.session_state.df = df
                        st.rerun()
                    else:
                        st.warning("Select vendors and enter a ledger name.")
        else:
            st.markdown('<span class="pill pill-green">✓ All vendors mapped</span>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="section-label">Export to Tally</div>', unsafe_allow_html=True)

        bank_name  = st.session_state.get("current_bank_name_clf", "export")
        export_df  = prepare_tally_export(df, bank_name)
        export_df  = export_df[[c for c in export_df.columns if c != "Interbank"]]

        st.download_button(
            label="⬇ Download Tally CSV",
            data=export_df.to_csv(index=False),
            file_name=f"tally_{str(bank_name).replace(' ', '_')}.csv",
            mime="text/csv"
        )


# ─────────────────────────────────────────────
#  TAB 2: MEMORY MANAGER
# ─────────────────────────────────────────────

with tab2:
    st.markdown('<div class="page-title">Memory Manager</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Saved vendor → ledger mappings for this client & bank</div>', unsafe_allow_html=True)

    ready2 = render_client_bank_selector("mem")
    if not ready2:
        st.info("Select a client and bank above to continue.")
        st.stop()

    st.markdown("---")

    try:
        mem = get_vendor_memory(st.session_state.client_id, st.session_state.bank_id)
    except Exception as e:
        st.error(f"Could not load memory: {e}")
        st.stop()

    if not mem:
        st.warning("No vendor memory found. Map vendors in the Classifier first.")
        st.stop()

    df_mem = pd.DataFrame([
        {"Vendor": k, "Ledger": v[0], "Ledger Group": v[1]}
        for k, v in mem.items()
    ]).sort_values("Vendor").reset_index(drop=True)

    st.markdown(f'<span class="pill pill-blue">{len(df_mem)} mappings saved</span>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    edited = st.data_editor(df_mem, use_container_width=True, num_rows="fixed")

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("💾 Save All Changes", key="mem_save"):
            for _, row in edited.iterrows():
                try:
                    save_vendor_memory(
                        st.session_state.client_id,
                        st.session_state.bank_id,
                        row["Vendor"], row["Ledger"], row["Ledger Group"]
                    )
                except Exception as e:
                    st.error(f"Failed: {row['Vendor']}: {e}")
            st.success("✓ All changes saved")

    st.markdown("---")
    st.markdown('<div class="section-label">Delete a Mapping</div>', unsafe_allow_html=True)

    col3, col4 = st.columns([3, 1])
    with col3:
        delete_v = st.selectbox("Select vendor", df_mem["Vendor"].tolist(), key="del_vendor_select")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑 Delete", key="del_vendor_btn"):
            try:
                delete_memory(st.session_state.client_id, st.session_state.bank_id, delete_v)
                st.success(f"Deleted: {delete_v}")
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")


# ─────────────────────────────────────────────
#  TAB 3: STOPWORDS MANAGER
# ─────────────────────────────────────────────

with tab3:
    st.markdown('<div class="page-title">Stopwords Manager</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Words filtered during extraction — shared across all clients</div>', unsafe_allow_html=True)

    try:
        current_words = get_stopwords()
        st.session_state.stopwords = current_words
    except Exception as e:
        st.error(f"Could not load stopwords: {e}")
        st.stop()

    words_sorted = sorted(list(current_words))
    st.markdown(f'<span class="pill pill-blue">{len(words_sorted)} stopwords</span>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    st.dataframe(pd.DataFrame({"Stopword": words_sorted}), use_container_width=True, height=300)

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-label">Add Stopword</div>', unsafe_allow_html=True)
        new_word = st.text_input("New word", placeholder="e.g. NEFT", key="sw_add")
        if st.button("✚ Add", key="sw_add_btn"):
            clean = new_word.upper().strip()
            if clean:
                if clean in current_words:
                    st.warning(f'"{clean}" already exists.')
                else:
                    try:
                        add_stopword(clean)
                        st.session_state.stopwords.add(clean)
                        if st.session_state.df is not None:
                            st.session_state.df["Transaction_Head"] = st.session_state.df["Narration"].apply(extract_head)
                        st.success(f"Added: {clean}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not add: {e}")
            else:
                st.warning("Enter a word.")

    with col2:
        st.markdown('<div class="section-label">Delete Stopword</div>', unsafe_allow_html=True)
        if words_sorted:
            del_word = st.selectbox("Select word", words_sorted, key="sw_del")
            if st.button("🗑 Delete", key="sw_del_btn"):
                try:
                    delete_stopword(del_word)
                    st.session_state.stopwords.discard(del_word)
                    if st.session_state.df is not None:
                        st.session_state.df["Transaction_Head"] = st.session_state.df["Narration"].apply(extract_head)
                    st.success(f"Deleted: {del_word}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not delete: {e}")
        else:
            st.info("No stopwords to delete.")
