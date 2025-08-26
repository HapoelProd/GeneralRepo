# app.py
import io
import base64
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Installments Splitter", layout="centered")

# --- Set background image with dark overlay ---
def set_background(image_file):
    with open(image_file, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: linear-gradient(rgba(0,0,0,0.55), rgba(0,0,0,0.55)),
                        url("data:image/jpg;base64,{b64}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

set_background("fans.jpg")

# --- Custom styling ---
st.markdown("""
<style>
/* ----------- Title ----------- */
h1 {
    text-align: center !important;
    font-size: 3rem !important;
    margin-bottom: 2rem !important;
    color: #fff !important;
    text-shadow: 2px 2px 6px #000;
}

/* ----------- File Uploader ----------- */
div.stFileUploader label {
    display: block;
    text-align: center !important;
    font-size: 3rem !important;
    font-weight: 900 !important;
    margin-bottom: 1.5rem !important;
    color: #fff !important;
    text-shadow: 2px 2px 6px #000;
}

/* Make ALL uploader text white */
div[data-testid="stFileUploader"] * {
    color: #fff !important;
    text-shadow: 1px 1px 3px #000 !important;
}

/* Uploader dropzone */
div[data-testid="stFileUploaderDropzone"] {
    min-height: 220px;
    padding: 2rem 1.5rem;
    border-width: 2px;
}
div[data-testid="stFileUploaderDropzone"] * {
    font-size: 1.2rem;
}

/* ----------- Alerts (success, error, warning, info) ----------- */
div[data-testid="stAlert"] {
    background-color: rgba(0, 0, 0, 0.6) !important;
    border-radius: 8px !important;
    padding: 1rem !important;
}
div[data-testid="stAlert"] p {
    color: #fff !important;
    font-weight: 600 !important;
    text-shadow: 1px 1px 3px #000;
}

/* ----------- Expanders (Preview sections) ----------- */
div[data-testid="stExpander"] div[role="button"] p {
    color: #fff !important;
    font-weight: 700 !important;
    text-shadow: 1px 1px 3px #000 !important;
    font-size: 1.2rem !important;
}

/* Expander arrow */
div[data-testid="stExpander"] div[role="button"] svg {
    fill: #fff !important;
    stroke: #fff !important;
}

/* Expander content background */
div.streamlit-expanderContent {
    background-color: rgba(0, 0, 0, 0.6) !important;
    border-radius: 6px !important;
    padding: 0.5rem !important;
}

/* ----------- Buttons ----------- */
.stButton > button, .stDownloadButton > button {
    font-size: 1.2rem !important;
    padding: 1rem 2rem !important;
    border-radius: 12px !important;
    display: block;
    margin: 1.2rem auto;
}
</style>
""", unsafe_allow_html=True)



st.title("Installments Splitter")

TARGET_VAL = "79991"      # InstallmentPaymentExtRef block to keep
AD_CODE    = 4118         # InstallmentProductExtRef that flags advertisement

uploaded = st.file_uploader("Upload CSV", type=["csv"])
process_clicked = st.button("Process")

def make_excel_bytes(df_without_ad: pd.DataFrame,
                     df_ad: pd.DataFrame,
                     df_rest: pd.DataFrame) -> bytes:
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:
        df_without_ad.to_excel(w, sheet_name="79991_without_ad", index=False)
        df_ad.to_excel(w,          sheet_name="79991_advertisement", index=False)
        df_rest.to_excel(w,        sheet_name="Rest", index=False)
    bio.seek(0)
    return bio.read()

if uploaded is not None and process_clicked:
    # --- Read CSV robustly
    try:
        df = pd.read_csv(uploaded, encoding="utf-8-sig", sep=None, engine="python")
    except Exception as e:
        st.error("Failed to read CSV:")
        st.exception(e)
        st.stop()

    # --- Split 79991 vs rest using forward-filled InstallmentPaymentExtRef
    try:
        block_key = df['InstallmentPaymentExtRef'].replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA}).ffill()
        block_key = pd.to_numeric(block_key, errors="coerce").astype("Int64").astype(str)

        only_79991 = df[block_key == TARGET_VAL].copy()
        rest       = df[block_key != TARGET_VAL].copy()
    except Exception as e:
        st.error("Processing error while splitting 79991 vs Rest:")
        st.exception(e)
        st.stop()

    # --- Inside 79991: segment-by-blanks; take whole segment if it contains 4118 anywhere
    try:
        code = pd.to_numeric(only_79991["InstallmentProductExtRef"], errors="coerce")
        only_79991["InstallmentProductExtRef"] = code

        # segment id: increases at each blank (NaN)
        seg_id = code.isna().cumsum()

        # whether a segment has AD_CODE
        seg_has_ad = (code == AD_CODE).groupby(seg_id).transform("any")

        advertisment          = only_79991[seg_has_ad].copy()
        without_advertisement = only_79991[~seg_has_ad].copy()
    except Exception as e:
        st.error("Processing error while extracting advertisement segments:")
        st.exception(e)
        st.stop()

    # --- Stats
    st.success(
        f"Rows in {TARGET_VAL}: {only_79991.shape[0]} | "
        f"Ad rows: {advertisment.shape[0]} | "
        f"Without ad: {without_advertisement.shape[0]} | "
        f"Rest: {rest.shape[0]}"
    )

    # --- Previews
    with st.expander(f"Preview – {TARGET_VAL} Advertisement ({advertisment.shape[0]})", expanded=False):
        st.dataframe(advertisment, use_container_width=True, hide_index=True)

    with st.expander(f"Preview – {TARGET_VAL} Without Advertisement ({without_advertisement.shape[0]})", expanded=False):
        st.dataframe(without_advertisement, use_container_width=True, hide_index=True)

    with st.expander(f"Preview – Rest ({rest.shape[0]})", expanded=False):
        st.dataframe(rest, use_container_width=True, hide_index=True)

    # --- Download (3 sheets)
    xbytes = make_excel_bytes(without_advertisement, advertisment, rest)
    default_name = Path(uploaded.name).with_suffix("").name + "_split.xlsx"
    st.download_button(
        "Download Excel (3 sheets)",
        data=xbytes,
        file_name=default_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
