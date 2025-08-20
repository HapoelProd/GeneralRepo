# app.py
import io
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Installments Splitter", layout="centered")

# --- Custom styling ---
st.markdown("""
<style>
/* Center the main title */
h1 {
    text-align: center !important;
    font-size: 3rem !important;
    margin-bottom: 2rem !important;
}

/* Force the "Upload CSV" label to be huge and bold */
div.stFileUploader label {
    display: block;
    text-align: center !important;
    font-size: 3rem !important;    /* much bigger now */
    font-weight: 900 !important;   /* extra bold */
    margin-bottom: 1.5rem !important;
    color: #222 !important;        /* darker for visibility */
}

/* Make the uploader dropzone taller */
div[data-testid="stFileUploaderDropzone"] {
    min-height: 220px;
    padding: 2rem 1.5rem;
    border-width: 2px;
}
div[data-testid="stFileUploaderDropzone"] * {
    font-size: 1.2rem;
}

/* Make buttons bigger */
.stButton > button, .stDownloadButton > button {
    font-size: 1.2rem !important;
    padding: 1rem 2rem !important;
    border-radius: 12px !important;
    display: block;
    margin: 1.2rem auto;   /* center buttons */
}
</style>
""", unsafe_allow_html=True)

st.title("Installments Splitter")

# Fixed target value
TARGET_VAL = "79991"

uploaded = st.file_uploader("Upload CSV", type=["csv"])
process_clicked = st.button("Process")

def make_excel_bytes(only_df: pd.DataFrame, rest_df: pd.DataFrame,
                     name_only="Only_79991", name_rest="Rest") -> bytes:
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:
        only_df.to_excel(w, sheet_name=name_only, index=False)
        rest_df.to_excel(w, sheet_name=name_rest, index=False)
    bio.seek(0)
    return bio.read()

if uploaded is not None and process_clicked:
    try:
        df = pd.read_csv(uploaded, encoding="utf-8-sig", sep=None, engine="python")
    except Exception as e:
        st.error("Failed to read CSV:")
        st.exception(e)
        st.stop()

    try:
        df['block_key'] = df['InstallmentPaymentExtRef'].replace(
            {"": pd.NA, "nan": pd.NA, "NaN": pd.NA}
        ).ffill()
        df["block_key"] = pd.to_numeric(df["block_key"], errors="coerce").astype("Int64").astype(str)

        only_79991 = df[df["block_key"] == TARGET_VAL].drop(columns=["block_key"])
        rest = df[df["block_key"] != TARGET_VAL].drop(columns=["block_key"])
    except Exception as e:
        st.error("Processing error:")
        st.exception(e)
        st.stop()

    st.success(f"Rows in {TARGET_VAL} block: {only_79991.shape[0]} | Rows in rest: {rest.shape[0]}")

    st.subheader(f"Preview – Only {TARGET_VAL} block")
    st.dataframe(only_79991, use_container_width=True, hide_index=True)

    st.subheader("Preview – Rest")
    st.dataframe(rest, use_container_width=True, hide_index=True)

    xbytes = make_excel_bytes(only_79991, rest, name_only="Only_79991", name_rest="Rest")
    default_name = Path(uploaded.name).with_suffix("").name + "_split.xlsx"
    st.download_button(
        "Download Excel (2 sheets)",
        data=xbytes,
        file_name=default_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
