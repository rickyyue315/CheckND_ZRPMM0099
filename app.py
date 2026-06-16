import streamlit as st

from src.data_loader import DTYPE_MAP, TXT_COLUMNS, load_stores, parse_report
from src.metrics import filter_operational, nd00_analysis, site_summary
from src.ui_components import (
    render_charts,
    render_excluded_note,
    render_kpis,
    render_nd00_aggregate,
    render_nd00_section,
    render_summary_table,
)

st.set_page_config(page_title="Safety Stock Checking", layout="wide")

st.title("Safety Stock Checking — RP Type & ND00 Alert Report")
st.markdown(
    "Upload a ZRPMM0099 report (tab-separated `.TXT`) to see per-site SKU and stock totals "
    "by RP Type (RF / ND), plus **ND00** alerts for unreviewed born-ND items that still hold stock."
)

stores = load_stores()

uploaded = st.sidebar.file_uploader(
    "Upload ZRPMM0099 report (.TXT)",
    type=["txt"],
    help="Expected filename: ZRPMM0099_YYYYMMDD.TXT",
)

if uploaded is None:
    st.info("Upload a ZRPMM0099 report to begin.")
    st.stop()

try:
    file_bytes = uploaded.getvalue()
    df = parse_report(file_bytes)
except Exception as e:
    st.error(f"Failed to parse report: {e}")
    st.stop()

len_full = len(df)
sites_in_txt = df["SITE"].unique()

df_op = filter_operational(df, stores)
len_op = len(df_op)
excluded = len_full - len_op
excluded_sites = sorted(set(sites_in_txt) - set(stores["Site"].unique()))

render_excluded_note(excluded, excluded_sites)

summary = site_summary(df_op, stores)
per_site_nd00, detail_nd00 = nd00_analysis(df_op, stores)

side_cols = st.sidebar.columns(2)
report_date_str = uploaded.name.replace("ZRPMM0099_", "").replace(".TXT", "") if "_" in uploaded.name else ""
side_cols[0].metric("Report date", report_date_str)
side_cols[1].metric("Rows loaded", f"{len_full:,}")

regions = sorted(stores["Regional"].dropna().unique())
oms = sorted(stores["OM"].dropna().unique())

sel_regions = st.sidebar.multiselect("Filter Region", options=regions, default=None)
sel_oms = st.sidebar.multiselect("Filter OM", options=oms, default=None)

if sel_regions:
    summary = summary[summary["Regional"].isin(sel_regions)]
if sel_oms:
    summary = summary[summary["OM"].isin(sel_oms)]

st.divider()

render_kpis(summary, per_site_nd00["Total ND00"].sum())

st.divider()
render_nd00_aggregate(per_site_nd00)

st.divider()
st.subheader("Per-Site Summary (RF / ND)")
render_summary_table(summary)

st.divider()
render_charts(summary)

st.divider()
render_nd00_section(per_site_nd00, detail_nd00)

st.caption("Data source: ZRPMM0099 stock report  ·  Store master: stores-template.csv (bundled)")
