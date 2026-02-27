import streamlit as st
import pandas as pd
import re
from io import BytesIO
from collections import Counter

st.set_page_config(page_title="Bank Statement Auto Classifier V5.2", layout="wide")
st.title("Bank Statement – V5.2 Intelligent Layered Classifier")


# --------------------------------------------------
# FIND NARRATION COLUMN
# --------------------------------------------------
def find_narration_column(df):
    possible = ["NARRATION", "DESCRIPTION", "PARTICULARS", "DETAILS", "REMARKS", "DESC"]

    for col in df.columns:
        if col.strip().upper() in possible:
            return col

    for col in df.columns:
        if any(x in col.strip().upper() for x in ["NARR", "DESC", "DETAIL", "PARTIC"]):
            return col

    text_cols = df.select_dtypes(include="object")
    return text_cols.apply(lambda x: x.astype(str).str.len().mean()).idxmax()


# --------------------------------------------------
# CLEAN NUMERIC COLUMNS
# --------------------------------------------------
def clean_numeric_columns(df):
    for col in df.columns:
        if any(x in col.upper() for x in ["WITHDRAW", "DEPOSIT", "BALANCE"]):
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# --------------------------------------------------
# SAFE DUPLICATE REMOVAL
# --------------------------------------------------
def remove_safe_duplicates(df):
    initial = len(df)

    dedupe_cols = []
    for col in df.columns:
        col_up = col.upper()
        if any(x in col_up for x in ["DATE", "WITHDRAW", "DEPOSIT", "NARR", "TRAN ID"]):
            dedupe_cols.append(col)

    if dedupe_cols:
        df = df.drop_duplicates(subset=dedupe_cols, keep="first")

    removed = initial - len(df)
    return df, removed


# --------------------------------------------------
# STOP WORDS + BANK PATTERNS
# --------------------------------------------------
STOP_WORDS = {
    "UPI", "UPIIN", "UPIOUT", "IN", "OUT",
    "MB", "FTB", "TRF", "NA", "IMPS", "NEFT", "RTGS",
    "PAYMENT", "PAID",
    "BANK", "LTD", "LIMITED", "PVT",
    "CR", "DR", "IFO", "NFT"
}

BANK_PREFIXES = (
    "OK", "SBIN", "HDFC", "ICICI", "BARB", "FDRL"
)


def clean_alpha(text):
    return re.sub(r'[^A-Z]', '', text)


# --------------------------------------------------
# LAYERED EXTRACTION ENGINE (V5.2)
# --------------------------------------------------
def extract_transaction_head(narration, word_freq):

    text = str(narration).upper()

    # ---------------- LAYER 1: UPI HANDLE ----------------
    if "@" in text:
        before_at = text.split("@")[0]
        candidate = before_at.split("/")[-1]
        candidate = clean_alpha(candidate)

        if len(candidate) >= 4:
            return candidate

    # ---------------- LAYER 2: SLASH + SPACE SPLIT ----------------
    parts = text.split("/")
    candidates = []

    for part in parts:
        words = part.split()  # split by space also

        for word in words:
            word_clean = clean_alpha(word)

            if (
                len(word_clean) >= 4 and
                word_clean not in STOP_WORDS and
                not word_clean.startswith(BANK_PREFIXES)
            ):
                candidates.append(word_clean)

    if candidates:
        # Prefer last meaningful word (merchant usually last)
        return candidates[-1]

    # ---------------- LAYER 3: FREQUENCY FALLBACK ----------------
    words = re.sub(r'[^A-Z]', ' ', text).split()

    valid_words = [
        w for w in words
        if (
            w not in STOP_WORDS and
            not w.startswith(BANK_PREFIXES) and
            len(w) >= 4 and
            word_freq.get(w, 0) > 1
        )
    ]

    if valid_words:
        return max(valid_words, key=lambda w: (word_freq[w], len(w)))

    return "SINGLE"


# --------------------------------------------------
# FILE UPLOAD
# --------------------------------------------------
file = st.file_uploader("Upload Bank Statement", type=["xlsx", "xls", "csv"])

if file:

    if file.name.endswith(".csv"):
        df = pd.read_csv(file, thousands=",")
    else:
        df = pd.read_excel(file)

    narration_col = find_narration_column(df)
    st.success(f"Narration column detected: {narration_col}")

    # Clean numeric columns
    df = clean_numeric_columns(df)

    # Remove safe duplicates
    df, removed_count = remove_safe_duplicates(df)
    if removed_count > 0:
        st.warning(f"{removed_count} duplicate rows removed safely.")

    # Build frequency dictionary
    all_words = []
    for val in df[narration_col]:
        words = re.sub(r'[^A-Z]', ' ', str(val).upper()).split()
        all_words.extend(words)

    word_freq = Counter(all_words)

    # Apply extraction
    df["Transaction_Head"] = df[narration_col].apply(
        lambda x: extract_transaction_head(x, word_freq)
    )

    # Group size calculation
    group_counts = df["Transaction_Head"].value_counts()
    df["_GroupCount"] = df["Transaction_Head"].map(group_counts)

    # Sort largest groups first
    df = df.sort_values(by="_GroupCount", ascending=False)

    original_cols = df.columns.tolist()
    original_cols.remove("_GroupCount")

    final_df = pd.DataFrame(columns=original_cols)

    last_group = None

    for _, row in df.iterrows():

        if last_group is not None and row["Transaction_Head"] != last_group:
            blank_row = {col: "" for col in original_cols}
            final_df = pd.concat([final_df, pd.DataFrame([blank_row])], ignore_index=True)

        final_df = pd.concat(
            [final_df, pd.DataFrame([row[original_cols]])],
            ignore_index=True
        )

        last_group = row["Transaction_Head"]

    st.success("V5.2 Classification Completed")

    st.dataframe(final_df, use_container_width=True)

    buffer = BytesIO()
    final_df.to_csv(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        label="Download Classified CSV",
        data=buffer,
        file_name="v5_2_auto_classified_transactions.csv",
        mime="text/csv"
    )
