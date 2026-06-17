import io

import pandas as pd
import plotly.express as px
import streamlit as st


def _to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    return buffer.getvalue()


def render_kpis(summary: pd.DataFrame, nd00_count: int):
    total_sites = len(summary)
    rf_sku_total = int(summary["RF_SKU_count"].sum())
    rf_stock_total = int(summary["RF_Stock"].sum())
    nd_sku_total = int(summary["ND_SKU_count"].sum())
    nd_stock_total = int(summary["ND_Stock"].sum())

    cols = st.columns(5)
    cols[0].metric("營運分店數", total_sites)
    cols[1].metric("RF SKU 數量", f"{rf_sku_total:,}")
    cols[2].metric("RF 庫存（件）", f"{rf_stock_total:,}")
    cols[3].metric("ND SKU 數量", f"{nd_sku_total:,}")
    cols[4].metric("ND 庫存（件）", f"{nd_stock_total:,}")

    st.caption(f"ND00 警示：已標記 {nd00_count} 個 SKU（天生 ND／未審核）— 展開下方 ND00 區段查看詳情。")


def render_summary_table(df: pd.DataFrame):
    col_order = ["SITE", "Shop", "Regional", "OM", "Class1", "Class2", "Type", "RF_SKU_count", "RF_Stock", "ND_SKU_count", "ND_Stock"]
    display = df[[c for c in col_order if c in df.columns]].copy()

    display = display.rename(
        columns={
            "SITE": "分店",
            "Shop": "店名",
            "Regional": "地區",
            "OM": "OM",
            "Class1": "級別 1",
            "Class2": "級別 2",
            "Type": "類型",
            "RF_SKU_count": "RF SKU",
            "RF_Stock": "RF 庫存",
            "ND_SKU_count": "ND SKU",
            "ND_Stock": "ND 庫存",
        }
    )

    st.dataframe(
        display,
        column_config={
            "RF 庫存": st.column_config.NumberColumn(format="%,.0f"),
            "ND 庫存": st.column_config.NumberColumn(format="%,.0f"),
        },
        use_container_width=True,
        hide_index=True,
    )

    excel = _to_excel_bytes(display)
    st.download_button("下載摘要 Excel", data=excel, file_name="site_summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def render_charts(summary: pd.DataFrame, nd00_per_site: pd.DataFrame):
    col_left, col_right = st.columns(2)

    with col_left:
        rf_nd = summary[["Shop", "RF_Stock", "ND_Stock"]].melt(id_vars="Shop", var_name="RP 類型", value_name="庫存")
        rf_nd["RP 類型"] = rf_nd["RP 類型"].replace({"RF_Stock": "RF", "ND_Stock": "ND"})
        fig1 = px.bar(rf_nd, x="Shop", y="庫存", color="RP 類型", title="各分店按 RP 類型之庫存", barmode="group")
        fig1.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig1, use_container_width=True)

    with col_right:
        top_n = 20
        nd00_sites = nd00_per_site[nd00_per_site["Total ND00"] > 0].sort_values("Total ND00", ascending=False).head(top_n)
        if not nd00_sites.empty:
            nd00_sites_disp = nd00_sites.rename(
                columns={"Stock only": "僅有庫存", "Planned only": "僅有計劃到貨", "Both": "兩者皆有"}
            )
            fig2 = px.bar(
                nd00_sites_disp,
                x="Shop",
                y=["僅有庫存", "僅有計劃到貨", "兩者皆有"],
                title=f"ND00 分佈 — 前 {top_n} 個分店",
                barmode="stack",
                color_discrete_map={"僅有庫存": "#ef553b", "僅有計劃到貨": "#636efa", "兩者皆有": "#00cc96"},
            )
            fig2.update_layout(xaxis_tickangle=-45, height=500)
            st.plotly_chart(fig2, use_container_width=True)


def render_nd00_section(per_site: pd.DataFrame, detail: pd.DataFrame):
    st.subheader("ND00 明細與篩選")

    if detail.empty:
        st.info("未找到營運分店的 ND00（天生 ND／未審核）記錄。")
        return

    with st.expander("各分店 2×2 分佈", expanded=True):
        display_site = per_site[per_site["Total ND00"] > 0][
            ["SITE", "Shop", "Regional", "OM", "Stock only", "Planned only", "Both", "Neither", "Total ND00"]
        ].copy()
        display_site.columns = ["分店", "店名", "地區", "OM", "僅有庫存", "僅有計劃到貨", "兩者皆有", "兩者皆無", "總數"]
        st.dataframe(display_site, use_container_width=True, hide_index=True)

    with st.expander("篩選與明細表", expanded=True):
        st.caption("明細涵蓋所有 ND 開頭代碼（如 ND00、ND01…），最後一欄「ND Code」可直接於 Excel 篩選任一代碼。")
        col1, col2, col3 = st.columns(3)
        regions = sorted(detail["Regional"].dropna().unique())
        oms = sorted(detail["OM"].dropna().unique())
        sites = sorted(detail["SITE"].unique())

        sel_region = col1.multiselect("地區", options=regions, default=None)
        sel_om = col2.multiselect("OM", options=oms, default=None)
        sel_site = col3.multiselect("分店", options=sites, default=None)

        filtered = detail.copy()
        if sel_region:
            filtered = filtered[filtered["Regional"].isin(sel_region)]
        if sel_om:
            filtered = filtered[filtered["OM"].isin(sel_om)]
        if sel_site:
            filtered = filtered[filtered["SITE"].isin(sel_site)]

        filtered_disp = filtered.rename(
            columns={
                "SITE": "分店",
                "Shop": "店名",
                "Regional": "地區",
                "OM": "OM",
                "SKU": "SKU",
                "RP Type": "RP 類型",
                "Sasa ABC": "Sasa ABC",
                "SKU status": "SKU 狀態",
                "Stock on hand": "現有庫存",
                "Planned receiving": "計劃到貨",
                "Sasa Launch Date": "Sasa 推出日期",
                "Bucket": "分類",
                "ND Code": "ND Code",
            }
        )

        st.dataframe(
            filtered_disp,
            column_config={
                "現有庫存": st.column_config.NumberColumn(format="%,.0f"),
                "計劃到貨": st.column_config.NumberColumn(format="%,.0f"),
                "Sasa 推出日期": st.column_config.DateColumn(format="YYYY-MM-DD"),
            },
            use_container_width=True,
            hide_index=True,
        )

        excel_detail = _to_excel_bytes(filtered)
        st.download_button("下載明細 Excel", data=excel_detail, file_name="nd00_detail.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def render_nd00_aggregate(per_site: pd.DataFrame):
    total = per_site["Total ND00"].sum()
    stock_only = per_site["Stock only"].sum()
    planned_only = per_site["Planned only"].sum()
    both = per_site["Both"].sum()
    neither = per_site["Neither"].sum()

    st.subheader("ND00 警示摘要")
    cols = st.columns(5)
    cols[0].metric("ND00 總數", total)
    cols[1].metric("僅有庫存", stock_only)
    cols[2].metric("僅有計劃到貨", planned_only)
    cols[3].metric("兩者皆有", both)
    cols[4].metric("兩者皆無", neither)

    st.caption(
        "**ND00** = NDRF 代碼 ND00（天生 ND，採購尚未審核）。"
        "這些 SKU 理論上不應持有庫存或有計劃到貨。"
        "上方數字反映可能遺漏的審核。"
    )


def render_excluded_note(excluded_count: int, excluded_sites: list[str]):
    if excluded_count > 0:
        st.sidebar.caption(f"已剔除來自非營運分店的 {excluded_count:,} 行：{', '.join(excluded_sites)}")
