# app.py
import io
from pathlib import Path

import pandas as pd
import streamlit as st

DEFAULT_COL = "InstallmentPaymentExtRef"
DEFAULT_TARGET = 79991

def find_col(df: pd.DataFrame, wanted: str) -> str:
    """Find column name ignoring spaces/case; raise if missing."""
    norm = {c: "".join(str(c).split()).lower() for c in df.columns}
    key = "".join(wanted.split()).lower()
    for orig, n in norm.items():
        if n == key:
            return orig
    raise KeyError(f"Column '{wanted}' not found. Available: {list(df.columns)}")

def split_by_extref_block_df(df: pd.DataFrame, extref_col: str, target_value: int | float):
    """
    Split into two DataFrames by 'blocks':
    a block begins where extref_col is non-null; rows below with empty extref_col
    belong to the same block until the next non-empty appears.
    All blocks whose header equals target_value go to 'only', the rest to 'except'.
    """
    # treat as numeric to avoid '79991' vs '79991.0' issues
    col = find_col(df, extref_col)
    ext_numeric = pd.to_numeric(df[col], errors="coerce")

    # block id: every non-null value in the raw column starts a new block
    block_id = df[col].notna().cumsum()

    # which blocks are target blocks (header row equals target)
    target_blocks = block_id[ext_numeric == float(target_value)].unique()

    mask = block_id.isin(target_blocks)
    only_df = df[mask].copy()
    except_df = df[~mask].copy()
    return only_df, except_df

def to_excel_bytes(df1: pd.DataFrame, df2: pd.DataFrame, name1="except_79991", name2="only_79991") -> bytes:
    """Write two DataFrames to a single XLSX in-memory and return bytes."""
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df1.to_excel(writer, sheet_name=name1, index=False)
        df2.to_excel(writer, sheet_name=name2, index=False)
    bio.seek(0)
    return bio.getvalue()

# -------------------------- UI --------------------------

st.set_page_config(page_title="Split Installments by ExtRef", page_icon="🗂️", layout="centered")
st.title("🗂️ Split Installments by ExtRef (CSV → Excel with 2 sheets)")

st.markdown(
    "Upload the CSV report. The app will group rows into blocks by "
    f"**{DEFAULT_COL}** and move the block(s) where the header equals the target value into a separate sheet."
)

uploaded = st.file_uploader("Upload CSV", type=["csv"])
col_name = st.text_input("Column name to check", value=DEFAULT_COL)
target_val = st.text_input("Target value", value=str(DEFAULT_TARGET))
target_val_num = pd.to_numeric(target_val, errors="coerce")

advanced = st.expander("Advanced CSV read options")
with advanced:
    sep = st.text_input("Delimiter (leave empty to auto-detect)", value="")
    encoding = st.text_input("Encoding", value="utf-8-sig")
    has_header = st.checkbox("File has header row", value=True)

if uploaded is not None and st.button("Process file"):
    if pd.isna(target_val_num):
        st.error("Target value must be numeric (e.g., 79991).")
        st.stop()

    # Read CSV (try auto sep if not provided)
    try:
        read_kwargs = dict(encoding=encoding)
        if sep.strip():
            read_kwargs["sep"] = sep
        else:
            read_kwargs["sep"] = None  # auto-detect with Python engine
            read_kwargs["engine"] = "python"
        if not has_header:
            read_kwargs["header"] = None

        df = pd.read_csv(uploaded, **read_kwargs)
    except Exception as e:
        st.exception(e)
        st.stop()

    try:
        only_df, except_df = split_by_extref_block_df(df, col_name, target_val_num)
    except Exception as e:
        st.exception(e)
        st.stop()

    st.success(f"Done. Found {len(only_df)} row(s) in target block(s); {len(except_df)} row(s) in the rest.")

    st.subheader("Preview – only 79991 block(s)")
    st.dataframe(only_df, use_container_width=True, hide_index=True)

    st.subheader("Preview – everything else")
    st.dataframe(except_df, use_container_width=True, hide_index=True)

    # Build Excel download
    xlsx_bytes = to_excel_bytes(except_df, only_df, name1="except_79991", name2="only_79991")
    default_name = Path(uploaded.name).with_suffix("").name + "_split.xlsx"
    st.download_button(
        "⬇️ Download Excel (2 sheets)",
        data=xlsx_bytes,
        file_name=default_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.markdown("---")
st.caption("Tip: If the column header in your CSV has spaces or different casing, the app will still find it.")
