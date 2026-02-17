mode = st.radio(
    "Select Processing Mode:",
    ["Normal Classification", "Interbank Detection"]
)

uploaded_files = st.file_uploader(
    "Upload Bank Statement(s)",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

if uploaded_files:

    dfs = []

    for file in uploaded_files:
        df = pd.read_excel(file)
        df["Source_File"] = file.name
        dfs.append(df)

    combined_df = pd.concat(dfs, ignore_index=True)

    # ---- Always do normal classification first ----
    combined_df = classify_transactions(combined_df)

    # ---- Interbank detection only if selected ----
    if mode == "Interbank Detection" and len(uploaded_files) > 1:

        debit_cols = ["DEBIT", "WITHDRAWAL", "PAYMENT"]
        credit_cols = ["CREDIT", "DEPOSIT", "RECEIPT"]

        debit_col = next((c for c in combined_df.columns if c.upper() in debit_cols), None)
        credit_col = next((c for c in combined_df.columns if c.upper() in credit_cols), None)

        date_col = next((c for c in combined_df.columns if "DATE" in c.upper()), None)

        if debit_col and credit_col and date_col:

            combined_df["Amount"] = (
                combined_df[debit_col].fillna(0) +
                combined_df[credit_col].fillna(0)
            )

            grouped = combined_df.groupby([date_col, "Amount"])

            for _, grp in grouped:
                if len(grp) == 2:
                    if grp[debit_col].notna().any() and grp[credit_col].notna().any():
                        combined_df.loc[grp.index, "Transaction_Head"] = "Interbank Transfer"

    # ---- Download output ----
    buffer = BytesIO()
    combined_df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        "Download Processed Statement",
        data=buffer,
        file_name="processed_statement.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
