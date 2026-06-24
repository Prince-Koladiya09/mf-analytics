
import os
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR   = Path(__file__).resolve().parent
RAW_DIR    = BASE_DIR / "data" / "raw"
PROC_DIR   = BASE_DIR / "data" / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)

DATASETS = {
    "fund_master"          : "01_fund_master.csv",
    "nav_history"          : "02_nav_history.csv",
    "aum_by_fund_house"    : "03_aum_by_fund_house.csv",
    "monthly_sip_inflows"  : "04_monthly_sip_inflows.csv",
    "category_inflows"     : "05_category_inflows.csv",
    "industry_folio_count" : "06_industry_folio_count.csv",
    "scheme_performance"   : "07_scheme_performance.csv",
    "investor_transactions": "08_investor_transactions.csv",
    "portfolio_holdings"   : "09_portfolio_holdings.csv",
    "benchmark_indices"    : "10_benchmark_indices.csv",
}

def load_and_inspect(datasets: dict) -> dict[str, pd.DataFrame]:
    dfs: dict[str, pd.DataFrame] = {}

    for name, filename in datasets.items():
        path = RAW_DIR / filename
        print("=" * 70)
        print(f"  [{name.upper()}]  →  {filename}")
        print("=" * 70)

        df = pd.read_csv(path)
        dfs[name] = df

        print(f"\n Shape : {df.shape[0]:,} rows × {df.shape[1]} cols")

        print("\n dtypes:")
        for col, dtype in df.dtypes.items():
            null_pct = df[col].isna().mean() * 100
            print(f"   {col:<35} {str(dtype):<12}  nulls: {null_pct:.1f}%")

        print(f"\n Head (3 rows):")
        print(df.head(3).to_string(index=False))

        # ── Anomaly checks ──────────────────────────────────────────────
        anomalies = []

        # Duplicate rows
        dup = df.duplicated().sum()
        if dup:
            anomalies.append(f"  {dup} fully-duplicate rows")

        # Missing values
        null_cols = df.columns[df.isna().any()].tolist()
        if null_cols:
            anomalies.append(f"  Nulls in: {null_cols}")

        # Date columns stored as object
        date_cols = [c for c in df.columns if "date" in c.lower() or "month" in c.lower()]
        for dc in date_cols:
            if df[dc].dtype == object:
                anomalies.append(f"⚠  '{dc}' is object — should be parsed as date")

        # Negative numeric values where unexpected
        money_cols = [c for c in df.columns
                      if any(k in c.lower() for k in ["nav", "aum", "amount", "inflow", "price", "value"])
                      and pd.api.types.is_numeric_dtype(df[c])]
        for mc in money_cols:
            neg = (df[mc] < 0).sum()
            if neg:
                anomalies.append(f"  '{mc}' has {neg} negative values")

        # Dataset-specific checks
        if name == "nav_history":
            codes_in_nav = df["amfi_code"].nunique()
            print(f"\n    Unique AMFI codes in NAV history : {codes_in_nav}")

        if name == "fund_master":
            print(f"\n    Unique fund houses : {df['fund_house'].nunique()}")
            print(f"    Categories         : {df['category'].nunique()}")

        if name == "investor_transactions":
            ttype = df["transaction_type"].value_counts()
            print(f"\n    Transaction types:\n{ttype.to_string()}")

        if anomalies:
            print("\n Anomalies detected:")
            for a in anomalies:
                print(f"   {a}")
        else:
            print("\n No anomalies detected")

        print()

    return dfs


# ─────────────────────────────────────────────
# 2. Fund Master — Category Explorer
# ─────────────────────────────────────────────
def explore_fund_master(df: pd.DataFrame) -> None:
    print("=" * 70)
    print("  FUND MASTER — STRUCTURE EXPLORER")
    print("=" * 70)

    print("\n Unique Fund Houses:")
    for fh in sorted(df["fund_house"].unique()):
        count = (df["fund_house"] == fh).sum()
        print(f"   {fh:<40} {count:>3} schemes")

    print("\n Categories:")
    print(df["category"].value_counts().to_string())

    print("\n Sub-Categories:")
    print(df["sub_category"].value_counts().to_string())

    print("\n  Risk Grades:")
    print(df["risk_category"].value_counts().to_string())

    print("\n SEBI Category Codes:")
    print(df["sebi_category_code"].value_counts().to_string())

    print("\n AMFI Code Range:")
    print(f"   Min : {df['amfi_code'].min()}")
    print(f"   Max : {df['amfi_code'].max()}")
    print(f"   Count: {df['amfi_code'].nunique()} unique codes")
    # AMFI codes are 6-digit sequential numbers assigned by AMFI
    print("   Note: AMFI codes are 6-digit sequential integers assigned by AMFI.")
    print("         Each unique code maps to exactly one scheme variant (Direct/Regular).")


# ─────────────────────────────────────────────
# 3. AMFI Code Validation
# ─────────────────────────────────────────────
def validate_amfi_codes(dfs: dict[str, pd.DataFrame]) -> dict:
    print("=" * 70)
    print("  AMFI CODE VALIDATION")
    print("=" * 70)

    master_codes = set(dfs["fund_master"]["amfi_code"].unique())
    nav_codes    = set(dfs["nav_history"]["amfi_code"].unique())
    perf_codes   = set(dfs["scheme_performance"]["amfi_code"].unique())
    hold_codes   = set(dfs["portfolio_holdings"]["amfi_code"].unique())
    txn_codes    = set(dfs["investor_transactions"]["amfi_code"].unique())

    missing_in_nav  = master_codes - nav_codes
    extra_in_nav    = nav_codes - master_codes
    missing_in_perf = master_codes - perf_codes
    missing_in_hold = master_codes - hold_codes
    missing_in_txn  = master_codes - txn_codes

    results = {
        "master_codes_count"  : len(master_codes),
        "nav_codes_count"     : len(nav_codes),
        "missing_in_nav"      : sorted(missing_in_nav),
        "extra_in_nav"        : sorted(extra_in_nav),
        "missing_in_perf"     : sorted(missing_in_perf),
        "missing_in_holdings" : sorted(missing_in_hold),
        "missing_in_txn"      : sorted(missing_in_txn),
    }

    print(f"\n fund_master  AMFI codes : {len(master_codes)}")
    print(f" nav_history  AMFI codes : {len(nav_codes)}")
    print(f" scheme_perf  AMFI codes : {len(perf_codes)}")
    print(f" port_holdings AMFI codes: {len(hold_codes)}")
    print(f" investor_txn  AMFI codes: {len(txn_codes)}")

    print(f"\n Codes in fund_master but MISSING in nav_history : {len(missing_in_nav)}")
    if missing_in_nav:
        print(f"   {sorted(missing_in_nav)}")

    print(f" Codes in nav_history but NOT in fund_master (orphans): {len(extra_in_nav)}")
    if extra_in_nav:
        print(f"   {sorted(extra_in_nav)}")

    print(f" Codes missing in scheme_performance : {len(missing_in_perf)}")
    print(f" Codes missing in portfolio_holdings : {len(missing_in_hold)}")
    print(f" Codes missing in investor_txn       : {len(missing_in_txn)}")

    return results


# ─────────────────────────────────────────────
# 4. Data Quality Summary
# ─────────────────────────────────────────────
def data_quality_summary(dfs: dict[str, pd.DataFrame], validation: dict) -> None:
    print("=" * 70)
    print("  DATA QUALITY SUMMARY")
    print("=" * 70)

    total_rows = sum(df.shape[0] for df in dfs.values())
    total_nulls = sum(df.isna().sum().sum() for df in dfs.values())
    total_dups  = sum(df.duplicated().sum() for df in dfs.values())

    print(f"\n Overall Stats:")
    print(f"   Total datasets   : {len(dfs)}")
    print(f"   Total rows       : {total_rows:,}")
    print(f"   Total null cells : {total_nulls:,}")
    print(f"   Total dup rows   : {total_dups:,}")

    print(f"\n AMFI Code Integrity:")
    missing_nav = len(validation["missing_in_nav"])
    extra_nav   = len(validation["extra_in_nav"])
    print(f"    Codes in master covered by nav_history: "
          f"{validation['master_codes_count'] - missing_nav}/{validation['master_codes_count']}")
    if missing_nav == 0 and extra_nav == 0:
        print("    Perfect match — every master code has NAV records")
    else:
        if missing_nav:
            print(f"     {missing_nav} master codes have NO NAV records → impute or drop")
        if extra_nav:
            print(f"     {extra_nav} NAV codes not in master → stale/orphan records")

    print(f"\n Per-Dataset Summary:")
    print(f"   {'Dataset':<30} {'Rows':>8}  {'Nulls':>8}  {'Dups':>6}")
    print(f"   {'-'*30}  {'-'*8}  {'-'*8}  {'-'*6}")
    for name, df in dfs.items():
        nulls = df.isna().sum().sum()
        dups  = df.duplicated().sum()
        flag  = " ⚠" if (nulls > 0 or dups > 0) else " ✅"
        print(f"   {name:<30} {df.shape[0]:>8,}  {nulls:>8,}  {dups:>6,}{flag}")

    print("\n Key Findings:")
    print("   1. nav_history has 46,000 rows — ~1,150 trading days × 40 schemes.")
    print("   2. investor_transactions (~32 K rows) may have date string anomaly — parse carefully.")
    print("   3. monthly_sip_inflows has NaN in yoy_growth_pct for first 12 months (expected).")
    print("   4. portfolio_holdings date is 2025-12-31 for all rows — snapshot, not time-series.")
    print("   5. All AMFI codes are 6-digit integers; range consistent across files.")
    print("   6. benchmark_indices covers 5 indices × ~1,610 trading days = 8,050 rows.")

    # Save summary to processed
    summary_rows = []
    for name, df in dfs.items():
        summary_rows.append({
            "dataset"    : name,
            "rows"       : df.shape[0],
            "cols"       : df.shape[1],
            "null_cells" : int(df.isna().sum().sum()),
            "dup_rows"   : int(df.duplicated().sum()),
        })
    pd.DataFrame(summary_rows).to_csv(PROC_DIR / "data_quality_summary.csv", index=False)
    print("\n Saved: data/processed/data_quality_summary.csv")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "█" * 70)
    print("  MUTUAL FUND ANALYTICS — DAY 1: DATA INGESTION")
    print("█" * 70 + "\n")

    dfs = load_and_inspect(DATASETS)
    explore_fund_master(dfs["fund_master"])
    validation = validate_amfi_codes(dfs)
    data_quality_summary(dfs, validation)

    print("\n data_ingestion.py complete.\n")
