import pandas as pd
import plotly.express as px
import streamlit as st


def render_kpis(summary: pd.DataFrame, nd00_count: int):
    total_sites = len(summary)
    rf_sku_total = int(summary["RF_SKU_count"].sum())
    rf_stock_total = int(summary["RF_Stock"].sum())
    nd_sku_total = int(summary["ND_SKU_count"].sum())
    nd_stock_total = int(summary["ND_Stock"].sum())

    cols = st.columns(5)
    cols[0].metric("Operational Sites", total_sites)
    cols[1].metric("RF SKU Count", f"{rf_sku_total:,}")
    cols[2].metric("RF Stock (units)", f"{rf_stock_total:,}")
    cols[3].metric("ND SKU Count", f"{nd_sku_total:,}")
    cols[4].metric("ND Stock (units)", f"{nd_stock_total:,}")

    st.caption(f"ND00 alerts: {nd00_count} SKU(s) flagged (born-ND / unreviewed) — expand the ND00 section below for details.")


def render_summary_table(df: pd.DataFrame):
    col_order = ["SITE", "Shop", "Regional", "OM", "Class1", "Class2", "Type", "RF_SKU_count", "RF_Stock", "ND_SKU_count", "ND_Stock"]
    display = df[[c for c in col_order if c in df.columns]].copy()

    display = display.rename(
        columns={
            "SITE": "Site",
            "Shop": "Shop",
            "Regional": "Regional",
            "OM": "OM",
            "Class1": "Class 1",
            "Class2": "Class 2",
            "Type": "Type",
            "RF_SKU_count": "RF SKUs",
            "RF_Stock": "RF Stock",
            "ND_SKU_count": "ND SKUs",
            "ND_Stock": "ND Stock",
        }
    )

    st.dataframe(
        display,
        column_config={
            "RF Stock": st.column_config.NumberColumn(format="%,.0f"),
            "ND Stock": st.column_config.NumberColumn(format="%,.0f"),
        },
        use_container_width=True,
        hide_index=True,
    )

    csv = display.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Download Summary CSV", data=csv, file_name="site_summary.csv", mime="text/csv")


def render_charts(summary: pd.DataFrame):
    col_left, col_right = st.columns(2)

    with col_left:
        rf_nd = summary[["Shop", "RF_Stock", "ND_Stock"]].melt(id_vars="Shop", var_name="RP Type", value_name="Stock")
        rf_nd["RP Type"] = rf_nd["RP Type"].replace({"RF_Stock": "RF", "ND_Stock": "ND"})
        fig1 = px.bar(rf_nd, x="Shop", y="Stock", color="RP Type", title="Stock by Site and RP Type", barmode="group")
        fig1.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig1, use_container_width=True)

    with col_right:
        top_n = 20
        nd00_sites = summary[summary["Total ND00"] > 0].sort_values("Total ND00", ascending=False).head(top_n)
        if not nd00_sites.empty:
            fig2 = px.bar(
                nd00_sites,
                x="Shop",
                y=["Stock only", "Planned only", "Both"],
                title=f"ND00 Breakdown — Top {top_n} Sites",
                barmode="stack",
                color_discrete_map={"Stock only": "#ef553b", "Planned only": "#636efa", "Both": "#00cc96"},
            )
            fig2.update_layout(xaxis_tickangle=-45, height=500)
            st.plotly_chart(fig2, use_container_width=True)


def render_nd00_section(per_site: pd.DataFrame, detail: pd.DataFrame):
    st.subheader("ND00 Detail & Filters")

    if detail.empty:
        st.info("No ND00 (born-ND / unreviewed) records found for operational sites.")
        return

    with st.expander("2×2 Breakdown by Site", expanded=True):
        display_site = per_site[per_site["Total ND00"] > 0][
            ["SITE", "Shop", "Regional", "OM", "Stock only", "Planned only", "Both", "Neither", "Total ND00"]
        ].copy()
        display_site.columns = ["Site", "Shop", "Regional", "OM", "Stock only", "Planned only", "Both", "Neither", "Total"]
        st.dataframe(display_site, use_container_width=True, hide_index=True)

    with st.expander("Filters & Detail Table", expanded=True):
        col1, col2, col3 = st.columns(3)
        regions = sorted(detail["Regional"].dropna().unique())
        oms = sorted(detail["OM"].dropna().unique())
        sites = sorted(detail["SITE"].unique())

        sel_region = col1.multiselect("Regional", options=regions, default=None)
        sel_om = col2.multiselect("OM", options=oms, default=None)
        sel_site = col3.multiselect("Site", options=sites, default=None)

        filtered = detail.copy()
        if sel_region:
            filtered = filtered[filtered["Regional"].isin(sel_region)]
        if sel_om:
            filtered = filtered[filtered["OM"].isin(sel_om)]
        if sel_site:
            filtered = filtered[filtered["SITE"].isin(sel_site)]

        st.dataframe(
            filtered,
            column_config={
                "Stock on hand": st.column_config.NumberColumn(format="%,.0f"),
                "Planned receiving": st.column_config.NumberColumn(format="%,.0f"),
                "Sasa Launch Date": st.column_config.DateColumn(format="YYYY-MM-DD"),
            },
            use_container_width=True,
            hide_index=True,
        )

        csv_detail = filtered.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Download Detail CSV", data=csv_detail, file_name="nd00_detail.csv", mime="text/csv")


def render_nd00_aggregate(per_site: pd.DataFrame):
    total = per_site["Total ND00"].sum()
    stock_only = per_site["Stock only"].sum()
    planned_only = per_site["Planned only"].sum()
    both = per_site["Both"].sum()
    neither = per_site["Neither"].sum()

    st.subheader("ND00 Alert Summary")
    cols = st.columns(5)
    cols[0].metric("Total ND00", total)
    cols[1].metric("With Stock Only", stock_only)
    cols[2].metric("With Planned Only", planned_only)
    cols[3].metric("With Both", both)
    cols[4].metric("With Neither", neither)

    st.caption(
        "**ND00** = NDRF Code ND00 (born-ND, Buyer has not reviewed). "
        "These SKUs should theoretically not hold stock or have planned receipts. "
        "The counts above highlight potential missed reviews."
    )


def render_excluded_note(excluded_count: int, excluded_sites: list[str]):
    if excluded_count > 0:
        st.sidebar.caption(f"Excluded {excluded_count:,} rows from non-operational sites: {', '.join(excluded_sites)}")
