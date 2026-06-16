import io

import pandas as pd
import streamlit as st

TXT_COLUMNS = [
    "SITE",
    "Storage Loc",
    "SKU",
    "RP Type",
    "SKU status",
    "Sasa ABC",
    "Stock on hand",
    "Open DN",
    "Net Stock",
    "Planned receiving",
    "Unrest. consignment",
    "Source of Supply",
    "Sasa Launch Date",
    "MOQ",
    "Display Stock",
    "Safety Stock",
    "NDRF Code",
]

NUMERIC_COLS = [
    "Stock on hand",
    "Open DN",
    "Net Stock",
    "Planned receiving",
    "Unrest. consignment",
    "MOQ",
    "Display Stock",
    "Safety Stock",
]

STRING_COLS = [
    "SITE",
    "Storage Loc",
    "SKU",
    "RP Type",
    "SKU status",
    "Sasa ABC",
    "Source of Supply",
    "NDRF Code",
]


def _clean_sap_numeric(series: pd.Series) -> pd.Series:
    cleaned = series.fillna("0").str.replace(",", "", regex=False)
    neg_mask = cleaned.str.endswith("-")
    cleaned = cleaned.str.rstrip("-")
    cleaned = cleaned.replace("", "0")
    result = pd.to_numeric(cleaned, errors="coerce").fillna(0.0)
    result[neg_mask] = -result[neg_mask]
    return result


@st.cache_data
def load_stores():
    return pd.read_csv("stores-template.csv")


@st.cache_data
def parse_report(file_bytes: bytes) -> pd.DataFrame:
    df = pd.read_csv(
        io.BytesIO(file_bytes),
        sep="\t",
        names=TXT_COLUMNS,
        skiprows=1,
        dtype=str,
        keep_default_na=False,
    )

    for c in STRING_COLS:
        df[c] = df[c].str.strip()

    for c in NUMERIC_COLS:
        df[c] = _clean_sap_numeric(df[c])

    df["Sasa Launch Date"] = pd.to_datetime(
        df["Sasa Launch Date"].str.strip().replace("00000000", pd.NA), errors="coerce"
    )

    return df
