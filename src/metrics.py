import pandas as pd


def filter_operational(df: pd.DataFrame, stores: pd.DataFrame) -> pd.DataFrame:
    operational_sites = stores["Site"].unique()
    return df[df["SITE"].isin(operational_sites)].copy()


def site_summary(df: pd.DataFrame, stores: pd.DataFrame) -> pd.DataFrame:
    rf_mask = df["RP Type"] == "RF"
    nd_mask = df["RP Type"] == "ND"

    rf_df = df[rf_mask].groupby("SITE").agg(RF_SKU_count=("SKU", "nunique"), RF_Stock=("Stock on hand", "sum"))
    nd_df = df[nd_mask].groupby("SITE").agg(ND_SKU_count=("SKU", "nunique"), ND_Stock=("Stock on hand", "sum"))

    result = rf_df.join(nd_df, how="outer").fillna(0).reset_index()

    meta = stores[["Site", "Shop", "Regional", "OM", "Class 1", "Class 2", "Type"]].rename(
        columns={"Site": "SITE", "Class 1": "Class1", "Class 2": "Class2"}
    )

    result = meta.merge(result, on="SITE", how="left").fillna(0)

    for col in ["RF_SKU_count", "ND_SKU_count"]:
        if col in result.columns:
            result[col] = result[col].astype(int)

    return result.sort_values("Shop").reset_index(drop=True)


def nd00_analysis(df: pd.DataFrame, stores: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    mask = df["NDRF Code"].str.strip() == "ND00"
    nd00 = df[mask].copy()

    detail_cols = [
        "SITE",
        "SKU",
        "RP Type",
        "Sasa ABC",
        "SKU status",
        "Stock on hand",
        "Planned receiving",
        "Sasa Launch Date",
    ]

    if nd00.empty:
        empty = stores[["Site", "Shop", "Regional", "OM"]].copy()
        empty.columns = ["SITE", "Shop", "Regional", "OM"]
        for c in ["Both", "Stock only", "Planned only", "Neither", "Total ND00"]:
            empty[c] = 0
        return empty, pd.DataFrame(columns=detail_cols + ["Shop", "Regional", "OM"])

    def classify(row):
        has_stock = row["Stock on hand"] > 0
        has_planned = row["Planned receiving"] > 0
        if has_stock and has_planned:
            return "Both"
        if has_stock:
            return "Stock only"
        if has_planned:
            return "Planned only"
        return "Neither"

    nd00["Bucket"] = nd00.apply(classify, axis=1)

    per_site = nd00.groupby(["SITE", "Bucket"]).size().unstack(fill_value=0).reset_index()
    for col in ["Both", "Stock only", "Planned only", "Neither"]:
        if col not in per_site.columns:
            per_site[col] = 0
    per_site["Total ND00"] = per_site[["Both", "Stock only", "Planned only", "Neither"]].sum(axis=1)

    meta = stores[["Site", "Shop", "Regional", "OM"]].rename(columns={"Site": "SITE"})
    per_site = meta.merge(per_site, on="SITE", how="left").fillna(0)
    for col in ["Both", "Stock only", "Planned only", "Neither", "Total ND00"]:
        per_site[col] = per_site[col].astype(int)

    detail = nd00[detail_cols].merge(meta, on="SITE", how="left")
    detail["Bucket"] = nd00["Bucket"].values
    detail = detail[
        ["SITE", "Shop", "Regional", "OM", "SKU", "RP Type", "Sasa ABC", "SKU status", "Stock on hand", "Planned receiving", "Sasa Launch Date", "Bucket"]
    ]

    return per_site, detail
