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

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="LedgerMind",
    page_icon="📒",
    layout="wide"
)

# ─────────────────────────────────────────────
#  CUSTOM CSS  — dark, professional, impressive
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@300;400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0a0d12;
    color: #e2e8f0;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0f1318 !important;
    border-right: 1px solid #1e2530;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] p {
    color: #94a3b8 !important;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* ── Sidebar brand ── */
.sidebar-brand {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 1.5rem;
    color: #f8fafc;
    letter-spacing: -0.02em;
    padding: 0.5rem 0 1.5rem 0;
}
.sidebar-brand span {
    color: #3b82f6;
}

/* ── Page title ── */
.page-title {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 2rem;
    color: #f8fafc;
    letter-spacing: -0.03em;
    margin-bottom: 0.25rem;
}
.page-subtitle {
    font-size: 0.85rem;
    color: #64748b;
    margin-bottom: 1.5rem;
    font-family: 'IBM Plex Mono', monospace;
}

/* ── Cards / containers ── */
.lm-card {
    background: #111722;
    border: 1px solid #1e2d45;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}

/* ── Metric badges ── */
.metric-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
}
.metric-badge {
    background: #111722;
    border: 1px solid #1e2d45;
    border-radius: 8px;
    padding: 0.75rem 1.25rem;
    min-width: 140px;
}
.metric-badge .val {
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: #3b82f6;
    line-height: 1;
}
.metric-badge .lbl {
    font-size: 0.72rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-top: 0.25rem;
}

/* ── Inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background: #161d27 !important;
    border: 1px solid #263044 !important;
    color: #e2e8f0 !important;
    border-radius: 7px !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.15) !important;
}

/* ── Buttons ── */
[data-testid="stButton"] > button {
    background: #1e3a5f !important;
    color: #93c5fd !important;
    border: 1px solid #2563eb !important;
    border-radius: 7px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    padding: 0.4rem 1rem !important;
    transition: all 0.15s ease !important;
}
[data-testid="stButton"] > button:hover {
    background: #2563eb !important;
    color: #fff !important;
    border-color: #3b82f6 !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
    background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 7px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.5rem 1.5rem !important;
    width: 100% !important;
}

/* ── Danger button (delete) ── */
button[kind="secondary"] {
    background: #1c1018 !important;
    color: #f87171 !important;
    border-color: #7f1d1d !important;
}
button[kind="secondary"]:hover {
    background: #7f1d1d !important;
    color: #fff !important;
}

/* ── Data editor / dataframe ── */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
    border: 1px solid #1e2d45 !important;
    border-radius: 8px !important;
    overflow: hidden;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #111722 !important;
    border: 2px dashed #1e2d45 !important;
    border-radius: 10px !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #3b82f6 !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    font-size: 0.85rem !important;
}

/* ── Divider ── */
hr { border-color: #1e2d45 !important; }

/* ── Multiselect ── */
[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
    background: #1e3a5f !important;
    color: #93c5fd !important;
    border-radius: 4px !important;
}

/* ── Section label ── */
.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: #3b82f6;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.5rem;
    margin-top: 1.5rem;
}

/* ── Status pill ── */
.pill {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 500;
}
.pill-green { background: #052e16; color: #4ade80; border: 1px solid #166534; }
.pill-yellow { background: #1c1503; color: #fbbf24; border: 1px solid #92400e; }
.pill-blue  { background: #0c1a2e; color: #60a5fa; border: 1px solid #1e3a5f; }
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
#  SESSION STATE  (initialise once)
# ─────────────────────────────────────────────

if "df" not in st.session_state:
    st.session_state.df = None

if "stopwords" not in st.session_state:
    try:
        st.session_state.stopwords = get_stopwords()
    except Exception as e:
        st.session_state.stopwords = set()
        st.warning(f"Could not load stopwords from database: {e}")


# ─────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────

def extract_head(text):
    """Clean a bank narration down to a meaningful vendor/transaction head."""
    stop_words = st.session_state.stopwords
    text = str(text).upper()
    text = re.sub(r"\d+", " ", text)          # remove all numbers
    text = re.sub(r"[^A-Z ]", " ", text)      # keep only letters and spaces

    tokens = text.split()
    cleaned = [
        t for t in tokens
        if len(t) >= 3
        and t not in stop_words
        and t not in COMPANY_WORDS
    ]
    return " ".join(cleaned) if cleaned else "SUSPENSE"


def apply_vendor_memory(df, client_id, bank_id):
    """Look up and apply any saved ledger mappings to the dataframe."""
    memory = get_vendor_memory(client_id, bank_id)
    df["Ledger"]       = df["Transaction_Head"].map(lambda x: memory.get(x, ("", ""))[0])
    df["Ledger Group"] = df["Transaction_Head"].map(lambda x: memory.get(x, ("", ""))[1])
    return df


def parse_pdf_statement(file):
    """Extract tables from a PDF bank statement using pdfplumber."""
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
        return pd.to_datetime(series).dt.strftime("%d-%m-%Y")
    except Exception:
        return series


def guess_column(cols, keywords):
    """Auto-detect a column by matching keywords to column names."""
    for keyword in keywords:
        for col in cols:
            if keyword.lower() in str(col).lower():
                return col
    return cols[0]


def prepare_tally_export(df, bank_name):
    """Add Tally-required columns (Voucher Type, Bank Ledger) to the dataframe."""
    export_df = df.copy()
    export_df["Voucher Type"] = export_df.apply(
        lambda row: "Receipt" if row["Credit"] > 0 else ("Payment" if row["Debit"] > 0 else ""),
        axis=1
    )
    export_df["Bank Ledger"] = bank_name
    return export_df


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="sidebar-brand">Ledger<span>Mind</span></div>', unsafe_allow_html=True)

    page = st.selectbox("Navigation", ["📊 Classifier", "🧠 Memory Manager", "🔤 Stopwords Manager"])

    st.markdown("---")
    st.markdown('<div class="section-label">Client</div>', unsafe_allow_html=True)

    # ── Delete handlers (run before widgets rebuild) ──
    if st.session_state.get("pending_delete_client"):
        try:
            delete_client(st.session_state.pop("pending_delete_client"))
        except Exception as e:
            st.error(f"Delete failed: {e}")
        for k in ["client", "bank", "client_id", "bank_id"]:
            st.session_state.pop(k, None)
        st.rerun()

    if st.session_state.get("pending_delete_bank"):
        try:
            delete_bank(st.session_state.pop("pending_delete_bank"))
        except Exception as e:
            st.error(f"Delete failed: {e}")
        for k in ["bank", "bank_id"]:
            st.session_state.pop(k, None)
        st.rerun()

    # ── Client selector ──
    clients = get_clients()
    client_options = clients + ["➕ Add New Client"]

    if "select_client" in st.session_state:
        st.session_state["client"] = st.session_state.pop("select_client")

    if "client" not in st.session_state or st.session_state["client"] not in client_options:
        st.session_state["client"] = client_options[0]

    client = st.selectbox("Select Client", client_options, key="client")

    if client == "➕ Add New Client":
        new_client = st.text_input("Client Name", placeholder="e.g. ASWIN & CO.")
        if st.button("✚ Create Client"):
            if new_client.strip():
                clean = new_client.strip().upper()
                if clean not in [c.upper() for c in get_clients()]:
                    add_client(clean)
                st.session_state["select_client"] = clean
                st.rerun()
            else:
                st.warning("Enter a client name.")
    else:
        client_id = get_client_id(client)
        st.session_state["client_id"] = client_id

        if st.button("🗑 Delete Client", key="del_client"):
            st.session_state["pending_delete_client"] = client_id
            st.rerun()

        st.markdown('<div class="section-label">Bank</div>', unsafe_allow_html=True)

        banks = get_banks(client_id)
        bank_options = banks + ["➕ Add New Bank"]

        if "select_bank" in st.session_state:
            st.session_state["bank"] = st.session_state.pop("select_bank")

        if "bank" not in st.session_state or st.session_state["bank"] not in bank_options:
            st.session_state["bank"] = bank_options[0]

        bank = st.selectbox("Select Bank", bank_options, key="bank")

        if bank == "➕ Add New Bank":
            new_bank = st.text_input("Bank Name", placeholder="e.g. CANARA BANK")
            if st.button("✚ Create Bank"):
                if new_bank.strip():
                    clean = new_bank.strip().upper()
                    if clean not in [b.upper() for b in get_banks(client_id)]:
                        add_bank(client_id, clean)
                    st.session_state["select_bank"] = clean
                    st.rerun()
                else:
                    st.warning("Enter a bank name.")
        else:
            bank_id = get_bank_id(client_id, bank)
            st.session_state["bank_id"] = bank_id

            if st.button("🗑 Delete Bank", key="del_bank"):
                st.session_state["pending_delete_bank"] = bank_id
                st.rerun()

    # ── Sidebar footer ──
    st.markdown("---")
    st.markdown('<p style="font-size:0.7rem;color:#334155;font-family:IBM Plex Mono,monospace;">LedgerMind v2.0<br>Built for CA Firms</p>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  PAGE: CLASSIFIER
# ─────────────────────────────────────────────

if page == "📊 Classifier":

    st.markdown('<div class="page-title">Statement Classifier</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Upload → Extract → Map → Export</div>', unsafe_allow_html=True)

    # Check client/bank selected
    if "client_id" not in st.session_state or "bank_id" not in st.session_state:
        st.info("👈 Select a client and bank from the sidebar to get started.")
        st.stop()

    # ── File Upload ──
    files = st.file_uploader(
        "Upload bank statements (Excel or PDF)",
        accept_multiple_files=True,
        type=["xlsx", "xls", "pdf"]
    )

    if files:
        dfs = []
        for file in files:
            try:
                if file.name.lower().endswith(".pdf"):
                    df_raw = parse_pdf_statement(file)
                    if df_raw is None:
                        st.error(f"Could not extract table from {file.name}. Check if it has a proper table structure.")
                        continue
                else:
                    df_raw = pd.read_excel(file)

                df_raw = df_raw.dropna(how="all").reset_index(drop=True)
                cols = df_raw.columns.tolist()

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

                df_raw = df_raw.rename(columns={date_col:"Date", nar_col:"Narration", deb_col:"Debit", cre_col:"Credit"})
                df_raw = df_raw[["Date","Narration","Debit","Credit"]]
                df_raw["Date"]      = parse_date_column(df_raw["Date"])
                df_raw["Narration"] = df_raw["Narration"].astype(str).str.upper()
                df_raw["Debit"]     = pd.to_numeric(df_raw["Debit"], errors="coerce").fillna(0)
                df_raw["Credit"]    = pd.to_numeric(df_raw["Credit"], errors="coerce").fillna(0)
                df_raw = df_raw[(df_raw["Debit"] != 0) | (df_raw["Credit"] != 0)]
                dfs.append(df_raw)

            except Exception as e:
                st.error(f"Error reading {file.name}: {e}")

        if dfs:
            df_combined = pd.concat(dfs, ignore_index=True)
            df_combined["Transaction_Head"] = df_combined["Narration"].apply(extract_head)
            df_combined = apply_vendor_memory(df_combined, st.session_state["client_id"], st.session_state["bank_id"])
            st.session_state.df = df_combined

    # ── Results ──
    if st.session_state.df is not None:
        df = st.session_state.df

        # Metric badges
        total     = len(df)
        mapped    = (df["Ledger"] != "").sum()
        unmapped  = total - mapped
        pct       = int((mapped / total * 100)) if total > 0 else 0

        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-badge"><div class="val">{total}</div><div class="lbl">Transactions</div></div>
            <div class="metric-badge"><div class="val">{mapped}</div><div class="lbl">Mapped</div></div>
            <div class="metric-badge"><div class="val">{unmapped}</div><div class="lbl">Unmapped</div></div>
            <div class="metric-badge"><div class="val">{pct}%</div><div class="lbl">Coverage</div></div>
        </div>
        """, unsafe_allow_html=True)

        st.dataframe(df, use_container_width=True, height=350)

        # ── Bulk Ledger Assignment ──
        st.markdown("---")
        st.markdown('<div class="section-label">Bulk Ledger Assignment</div>', unsafe_allow_html=True)

        unmapped_vendors = sorted(df[df["Ledger"] == ""]["Transaction_Head"].unique())

        if unmapped_vendors:
            col1, col2 = st.columns([2, 1])
            with col1:
                selected = st.multiselect("Select vendors to map", unmapped_vendors)
                ledger_name = st.text_input("Ledger Name", placeholder="e.g. Office Supplies")
            with col2:
                ledger_group = st.selectbox("Ledger Group", LEDGER_GROUPS)
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 Save Mapping"):
                    if selected and ledger_name.strip():
                        saved = 0
                        for v in selected:
                            try:
                                save_vendor_memory(
                                    st.session_state["client_id"],
                                    st.session_state["bank_id"],
                                    v, ledger_name.strip(), ledger_group
                                )
                                saved += 1
                            except Exception as e:
                                st.error(f"Failed to save {v}: {e}")
                        if saved:
                            st.success(f"✓ Saved {saved} mapping(s)")
                            df = apply_vendor_memory(df, st.session_state["client_id"], st.session_state["bank_id"])
                            st.session_state.df = df
                            st.rerun()
                    else:
                        st.warning("Select vendors and enter a ledger name.")
        else:
            st.markdown('<span class="pill pill-green">✓ All vendors mapped</span>', unsafe_allow_html=True)

        # ── Export ──
        st.markdown("---")
        st.markdown('<div class="section-label">Export to Tally</div>', unsafe_allow_html=True)

        export_df = prepare_tally_export(df, st.session_state.get("bank", ""))
        st.download_button(
            label="⬇ Download Tally CSV",
            data=export_df.to_csv(index=False),
            file_name=f"tally_{st.session_state.get('bank','export').replace(' ','_')}.csv",
            mime="text/csv"
        )


# ─────────────────────────────────────────────
#  PAGE: MEMORY MANAGER
# ─────────────────────────────────────────────

elif page == "🧠 Memory Manager":

    st.markdown('<div class="page-title">Memory Manager</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">View, edit, and delete saved vendor → ledger mappings</div>', unsafe_allow_html=True)

    if "client_id" not in st.session_state or "bank_id" not in st.session_state:
        st.info("👈 Select a client and bank from the sidebar.")
        st.stop()

    try:
        mem = get_vendor_memory(st.session_state["client_id"], st.session_state["bank_id"])
    except Exception as e:
        st.error(f"Could not load memory: {e}")
        st.stop()

    if not mem:
        st.warning("No vendor memory found for this client and bank. Start by mapping vendors in the Classifier.")
        st.stop()

    df_mem = pd.DataFrame([
        {"Vendor": k, "Ledger": v[0], "Ledger Group": v[1]}
        for k, v in mem.items()
    ]).sort_values("Vendor").reset_index(drop=True)

    st.markdown(f'<span class="pill pill-blue">{len(df_mem)} mappings</span>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    edited = st.data_editor(df_mem, use_container_width=True, num_rows="fixed")

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("💾 Save All Changes"):
            errors = 0
            for _, row in edited.iterrows():
                try:
                    save_vendor_memory(
                        st.session_state["client_id"],
                        st.session_state["bank_id"],
                        row["Vendor"], row["Ledger"], row["Ledger Group"]
                    )
                except Exception as e:
                    errors += 1
                    st.error(f"Failed to update {row['Vendor']}: {e}")
            if not errors:
                st.success("✓ All changes saved")

    st.markdown("---")
    st.markdown('<div class="section-label">Delete a Mapping</div>', unsafe_allow_html=True)

    col3, col4 = st.columns([3, 1])
    with col3:
        delete_v = st.selectbox("Select vendor to delete", df_mem["Vendor"].tolist())
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑 Delete", key="del_vendor"):
            try:
                delete_memory(st.session_state["client_id"], st.session_state["bank_id"], delete_v)
                st.success(f"Deleted: {delete_v}")
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")


# ─────────────────────────────────────────────
#  PAGE: STOPWORDS MANAGER
# ─────────────────────────────────────────────

elif page == "🔤 Stopwords Manager":

    st.markdown('<div class="page-title">Stopwords Manager</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Words filtered out during transaction head extraction — shared across all clients</div>', unsafe_allow_html=True)

    # Reload fresh from DB each time this page is visited
    try:
        current_words = get_stopwords()
        st.session_state.stopwords = current_words
    except Exception as e:
        st.error(f"Could not load stopwords: {e}")
        st.stop()

    words_sorted = sorted(list(current_words))

    st.markdown(f'<span class="pill pill-blue">{len(words_sorted)} stopwords</span>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Display as a clean dataframe
    st.dataframe(
        pd.DataFrame({"Stopword": words_sorted}),
        use_container_width=True,
        height=300
    )

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-label">Add Stopword</div>', unsafe_allow_html=True)
        new_word = st.text_input("New word", placeholder="e.g. NEFT", key="sw_add_input")
        if st.button("✚ Add", key="sw_add_btn"):
            clean = new_word.upper().strip()
            if clean:
                if clean in current_words:
                    st.warning(f'"{clean}" already exists.')
                else:
                    try:
                        add_stopword(clean)
                        st.session_state.stopwords.add(clean)
                        # Re-extract transaction heads if data is loaded
                        if st.session_state.df is not None:
                            st.session_state.df["Transaction_Head"] = (
                                st.session_state.df["Narration"].apply(extract_head)
                            )
                        st.success(f'Added: {clean}')
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not add stopword: {e}")
            else:
                st.warning("Enter a word.")

    with col2:
        st.markdown('<div class="section-label">Delete Stopword</div>', unsafe_allow_html=True)
        if words_sorted:
            del_word = st.selectbox("Select word", words_sorted, key="sw_del_select")
            if st.button("🗑 Delete", key="sw_del_btn"):
                try:
                    delete_stopword(del_word)
                    st.session_state.stopwords.discard(del_word)
                    if st.session_state.df is not None:
                        st.session_state.df["Transaction_Head"] = (
                            st.session_state.df["Narration"].apply(extract_head)
                        )
                    st.success(f'Deleted: {del_word}')
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not delete: {e}")
        else:
            st.info("No stopwords to delete.")
