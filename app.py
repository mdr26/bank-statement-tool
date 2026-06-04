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
#  CUSTOM CSS — Forest Green Theme
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0d2018;
    color: #e8f5ee;
}

#MainMenu, footer, header { visibility: hidden; }

/* ── Lock sidebar open — hide collapse arrow ── */
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
section[data-testid="stSidebar"] { min-width: 240px !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0a1a12 !important;
    border-right: 1px solid #1d4a2d;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] p {
    color: #2d6b42 !important;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.sidebar-brand {
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
    font-size: 1.4rem;
    color: #e8f5ee;
    letter-spacing: -0.02em;
    padding: 0.5rem 0 1.5rem 0;
}
.sidebar-brand span { color: #3ecf8e; }

.page-title {
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
    font-size: 1.8rem;
    color: #e8f5ee;
    letter-spacing: -0.03em;
    margin-bottom: 0.25rem;
}
.page-subtitle {
    font-size: 0.82rem;
    color: #2d6b42;
    margin-bottom: 1.5rem;
    font-family: 'IBM Plex Mono', monospace;
}

.metric-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
}
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
.metric-badge .val.coral  { color: #ff6b6b; }
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
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    padding: 0.4rem 1rem !important;
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
    font-size: 0.85rem !important;
    padding: 0.5rem 1.5rem !important;
    width: 100% !important;
}

[data-testid="stFileUploader"] {
    background: #112a1c !important;
    border: 2px dashed #1d4a2d !important;
    border-radius: 10px !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #3ecf8e !important;
}

[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
    border: 1px solid #1d4a2d !important;
    border-radius: 8px !important;
}

[data-testid="stAlert"] { border-radius: 8px !important; font-size: 0.85rem !important; }

hr { border-color: #1d4a2d !important; }

[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
    background: #1d4a2d !important;
    color: #3ecf8e !important;
    border-radius: 4px !important;
}

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
.pill-red    { background: #1c0a0a; color: #ff6b6b; border: 1px solid #7f1d1d; }

/* Interbank row highlight */
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

if "df" not in st.session_state:
    st.session_state.df = None

if "stopwords" not in st.session_state:
    try:
        st.session_state.stopwords = get_stopwords()
    except Exception as e:
        st.session_state.stopwords = set()
        st.warning(f"Could not load stopwords: {e}")


# ─────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────

def clean_number(val):
    """
    Convert any number format to float.
    Handles: ₹1,23,456 / 1,234.56 / "60,000" / "1.23.456" / blanks / dashes
    """
    if pd.isna(val):
        return 0.0
    s = str(val).strip()
    # Remove currency symbols, spaces
    s = re.sub(r'[₹$€£\s]', '', s)
    # Remove commas (Indian and international format)
    s = s.replace(',', '')
    # Remove trailing/leading dashes treated as zero
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
    cleaned = [
        t for t in tokens
        if len(t) >= 3
        and t not in stop_words
        and t not in COMPANY_WORDS
    ]
    return " ".join(cleaned) if cleaned else "SUSPENSE"


def apply_vendor_memory(df, client_id, bank_id):
    """
    Apply saved ledger mappings to the dataframe.
    Only fills rows that are not already marked as Interbank.
    """
    memory = get_vendor_memory(client_id, bank_id)
    for idx, row in df.iterrows():
        if row.get("Ledger") == "Interbank":
            continue  # Don't overwrite interbank flags
        vendor = row["Transaction_Head"]
        if vendor in memory:
            df.at[idx, "Ledger"]       = memory[vendor][0]
            df.at[idx, "Ledger Group"] = memory[vendor][1]
    return df


def detect_interbank(dfs_with_names):
    """
    Find transactions that appear in 2+ bank statements
    with the same date and same amount (debit or credit).
    Returns a set of (date, amount) tuples that are interbank.
    Each pair is only matched once — not repeated.

    dfs_with_names: list of (bank_name, dataframe)
    """
    if len(dfs_with_names) < 2:
        return set()

    interbank_indices = {}  # key=(date, amount) → list of (bank_name, df_index)

    for bank_name, df in dfs_with_names:
        for idx, row in df.iterrows():
            date   = str(row["Date"])
            debit  = row["Debit"]
            credit = row["Credit"]
            amount = debit if debit > 0 else credit
            if amount > 0:
                key = (date, amount)
                if key not in interbank_indices:
                    interbank_indices[key] = []
                interbank_indices[key].append((bank_name, idx))

    # Only flag keys that appear in 2+ different banks
    flagged = set()
    for key, entries in interbank_indices.items():
        banks_involved = set(b for b, _ in entries)
        if len(banks_involved) >= 2:
            flagged.add(key)

    return flagged


def parse_pdf_statement(file):
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

    st.markdown("---")
    st.markdown('<p style="font-size:0.7rem;color:#2d6b42;font-family:IBM Plex Mono,monospace;">LedgerMind v2.0<br>Built for CA Firms</p>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  PAGE: CLASSIFIER
# ─────────────────────────────────────────────

if page == "📊 Classifier":

    st.markdown('<div class="page-title">Statement Classifier</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Upload → Extract → Map → Export</div>', unsafe_allow_html=True)

    if "client_id" not in st.session_state or "bank_id" not in st.session_state:
        st.info("👈 Select a client and bank from the sidebar to get started.")
        st.stop()

    files = st.file_uploader(
        "Upload bank statements (Excel or PDF) — upload multiple for interbank detection",
        accept_multiple_files=True,
        type=["xlsx", "xls", "pdf"]
    )

    if files:
        dfs_with_names = []  # list of (filename, dataframe) for interbank detection

        for file in files:
            try:
                if file.name.lower().endswith(".pdf"):
                    df_raw = parse_pdf_statement(file)
                    if df_raw is None:
                        st.error(f"Could not extract table from {file.name}.")
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

                df_raw = df_raw.rename(columns={
                    date_col: "Date", nar_col: "Narration",
                    deb_col: "Debit", cre_col: "Credit"
                })
                df_raw = df_raw[["Date", "Narration", "Debit", "Credit"]]

                df_raw["Date"]      = parse_date_column(df_raw["Date"])
                df_raw["Narration"] = df_raw["Narration"].astype(str).str.upper().str.strip()

                # ── Feature 4: Auto-convert numbers in any format ──
                df_raw["Debit"]  = df_raw["Debit"].apply(clean_number)
                df_raw["Credit"] = df_raw["Credit"].apply(clean_number)

                df_raw = df_raw[(df_raw["Debit"] != 0) | (df_raw["Credit"] != 0)]
                df_raw["Source_File"] = file.name  # track which file each row came from

                dfs_with_names.append((file.name, df_raw.copy()))

            except Exception as e:
                st.error(f"Error reading {file.name}: {e}")

        if dfs_with_names:
            # ── Feature 1: Interbank Detection ──
            interbank_keys = detect_interbank(dfs_with_names)

            # Combine all files into one dataframe
            df_combined = pd.concat([df for _, df in dfs_with_names], ignore_index=True)
            df_combined["Transaction_Head"] = df_combined["Narration"].apply(extract_head)
            df_combined["Ledger"]           = ""
            df_combined["Ledger Group"]     = ""
            df_combined["Interbank"]        = False

            # Flag interbank rows
            interbank_count = 0
            seen_keys = set()
            for idx, row in df_combined.iterrows():
                date   = str(row["Date"])
                amount = row["Debit"] if row["Debit"] > 0 else row["Credit"]
                key    = (date, amount)
                if key in interbank_keys:
                    df_combined.at[idx, "Ledger"]    = "Interbank"
                    df_combined.at[idx, "Ledger Group"] = "Bank Accounts"
                    df_combined.at[idx, "Interbank"] = True
                    if key not in seen_keys:
                        interbank_count += 1
                        seen_keys.add(key)

            # ── Feature 3: Auto-apply vendor memory ──
            df_combined = apply_vendor_memory(
                df_combined,
                st.session_state["client_id"],
                st.session_state["bank_id"]
            )

            st.session_state.df = df_combined

    # ── Results ──
    if st.session_state.df is not None:
        df = st.session_state.df

        total        = len(df)
        interbank_n  = int(df["Interbank"].sum()) if "Interbank" in df.columns else 0
        mapped       = int((df["Ledger"] != "").sum())
        unmapped     = total - mapped
        pct          = int((mapped / total * 100)) if total > 0 else 0

        # Metric badges
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
                f'same date & amount found across multiple statements. '
                f'Marked as "Interbank" under Ledger. Please verify manually.</div>',
                unsafe_allow_html=True
            )

        # ── Feature 2: Search / Filter ──
        st.markdown('<div class="section-label">Search Transactions</div>', unsafe_allow_html=True)
        search = st.text_input("Filter by narration, transaction head, ledger, or date", placeholder="e.g. NEFT or CHARUMMOODU or 05-04-2024", label_visibility="collapsed")

        display_df = df.copy()

        # Drop internal helper column from display
        display_cols = [c for c in display_df.columns if c != "Interbank"]
        display_df = display_df[display_cols]

        if search.strip():
            mask = display_df.apply(
                lambda col: col.astype(str).str.contains(search.strip(), case=False, na=False)
            ).any(axis=1)
            display_df = display_df[mask]

        st.dataframe(display_df, use_container_width=True, height=380)
        st.caption(f"Showing {len(display_df)} of {total} transactions")

        # ── Bulk Ledger Assignment ──
        st.markdown("---")
        st.markdown('<div class="section-label">Bulk Ledger Assignment</div>', unsafe_allow_html=True)

        # Only show vendors that are not interbank and not yet mapped
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
                            st.success(f"✓ Saved {saved} mapping(s) — will auto-apply next upload")
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
        # Remove internal helper column from export
        export_df = export_df[[c for c in export_df.columns if c != "Interbank"]]

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
    st.markdown('<div class="page-subtitle">Saved vendor → ledger mappings for this client & bank</div>', unsafe_allow_html=True)

    if "client_id" not in st.session_state or "bank_id" not in st.session_state:
        st.info("👈 Select a client and bank from the sidebar.")
        st.stop()

    # Show client/bank context clearly
    client_name = st.session_state.get("client", "—")
    bank_name   = st.session_state.get("bank", "—")
    st.markdown(
        f'<span class="pill pill-green">{client_name}</span> &nbsp;→&nbsp; '
        f'<span class="pill pill-blue">{bank_name}</span>',
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)

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

    st.markdown(f'<span class="pill pill-blue">{len(df_mem)} mappings saved</span>', unsafe_allow_html=True)
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
                        if st.session_state.df is not None:
                            st.session_state.df["Transaction_Head"] = (
                                st.session_state.df["Narration"].apply(extract_head)
                            )
                        st.success(f"Added: {clean}")
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
                    st.success(f"Deleted: {del_word}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not delete: {e}")
        else:
            st.info("No stopwords to delete.")
