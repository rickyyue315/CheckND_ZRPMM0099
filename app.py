import streamlit as st

from src.data_loader import load_stores, parse_report
from src.metrics import filter_operational, nd_analysis, site_summary
from src.ui_components import (
    render_charts,
    render_excluded_note,
    render_kpis,
    render_nd_aggregate,
    render_nd_section,
    render_summary_table,
)

st.set_page_config(page_title="安全庫存檢查", layout="wide")

st.title("安全庫存檢查 — RP 類型與 ND00 警示報告")
st.markdown(
    "上載 ZRPMM0099 報表（Tab 分隔的 `.TXT`），即可查看各分店按 RP 類型（RF / ND）的 SKU 與庫存總數，"
    "以及仍持有庫存之未審核天生 ND 項目的 **ND00** 警示。"
)

stores = load_stores()

uploaded = st.sidebar.file_uploader(
    "上載 ZRPMM0099 報表（.TXT）",
    type=["txt"],
    help="預期檔案名稱：ZRPMM0099_YYYYMMDD.TXT",
)

if uploaded is None:
    st.info("請上載 ZRPMM0099 報表以開始。")
    st.stop()

try:
    file_bytes = uploaded.getvalue()
    df = parse_report(file_bytes)
except Exception as e:
    st.error(f"無法解析報表：{e}")
    st.stop()

len_full = len(df)
sites_in_txt = df["SITE"].unique()

df_op = filter_operational(df, stores)
len_op = len(df_op)
excluded = len_full - len_op
excluded_sites = sorted(set(sites_in_txt) - set(stores["Site"].unique()))

render_excluded_note(excluded, excluded_sites)

summary = site_summary(df_op, stores)
per_site_nd, detail_nd = nd_analysis(df_op, stores)

side_cols = st.sidebar.columns(2)
report_date_str = uploaded.name.replace("ZRPMM0099_", "").replace(".TXT", "") if "_" in uploaded.name else ""
side_cols[0].metric("報表日期", report_date_str)
side_cols[1].metric("已載入行數", f"{len_full:,}")

regions = sorted(stores["Regional"].dropna().unique())
oms = sorted(stores["OM"].dropna().unique())

sel_regions = st.sidebar.multiselect("篩選地區", options=regions, default=None)
sel_oms = st.sidebar.multiselect("篩選 OM", options=oms, default=None)

if sel_regions:
    summary = summary[summary["Regional"].isin(sel_regions)]
if sel_oms:
    summary = summary[summary["OM"].isin(sel_oms)]

st.divider()

render_kpis(summary, per_site_nd["Total ND"].sum())

st.divider()
render_nd_aggregate(per_site_nd)

st.divider()
st.subheader("分店摘要（RF / ND）")
render_summary_table(summary)

st.divider()
render_charts(summary, per_site_nd)

st.divider()
render_nd_section(per_site_nd, detail_nd)

st.divider()
st.markdown(
    "<div style='text-align: center; color: #888; font-size: 0.85rem; line-height: 1.6;'>"
    "資料來源：ZRPMM0099 庫存報表  ·  分店主檔：stores-template.csv（內置）<br>"
    "由 Ricky Yue 開發  ·  只限 RP Team 使用"
    "</div>",
    unsafe_allow_html=True,
)
