"""
data_cleaning.py
Day 2 — Clean all 10 datasets and save to data/processed/
"""

import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR  = BASE_DIR / "data" / "raw"
PROC_DIR = BASE_DIR / "data" / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)

DIVIDER = "=" * 70

def log(msg): print(f"   {msg}")


# ─────────────────────────────────────────────────────────────────────
# 1. nav_history
# ─────────────────────────────────────────────────────────────────────
def clean_nav_history() -> pd.DataFrame:
    print(f"\n{DIVIDER}\n  [1/10] nav_history\n{DIVIDER}")
    df = pd.read_csv(RAW_DIR / "02_nav_history.csv")
    log(f"Raw shape          : {df.shape}")

    # Parse dates
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
    bad_dates = df["date"].isna().sum()
    if bad_dates: log(f"⚠  Unparseable dates : {bad_dates} → dropped")
    df = df.dropna(subset=["date"])

    # Remove duplicates
    before = len(df)
    df = df.drop_duplicates(subset=["amfi_code", "date"])
    log(f"Duplicates removed : {before - len(df)}")

    # Sort
    df = df.sort_values(["amfi_code", "date"]).reset_index(drop=True)

    # Forward-fill missing NAV for weekends/holidays (per scheme)
    full_range = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    filled_frames = []
    for code, grp in df.groupby("amfi_code"):
        grp = grp.set_index("date").reindex(full_range)
        grp["amfi_code"] = code
        grp["nav"] = grp["nav"].ffill()
        grp.index.name = "date"
        filled_frames.append(grp.reset_index())
    df_filled = pd.concat(filled_frames, ignore_index=True)
    log(f"Rows after ffill   : {len(df_filled):,}  (was {len(df):,})")

    # Validate NAV > 0
    neg = (df_filled["nav"] <= 0).sum()
    if neg:
        log(f"⚠  NAV ≤ 0 rows : {neg} → dropped")
        df_filled = df_filled[df_filled["nav"] > 0]

    # Drop NaN nav (could occur at start before any trading day)
    df_filled = df_filled.dropna(subset=["nav"])

    # Dtype clean-up
    df_filled["amfi_code"] = df_filled["amfi_code"].astype(int)
    df_filled["nav"]       = df_filled["nav"].round(4)
    df_filled = df_filled.sort_values(["amfi_code", "date"]).reset_index(drop=True)

    out = PROC_DIR / "02_nav_history_clean.csv"
    df_filled.to_csv(out, index=False)
    log(f"✅ Saved → {out.name}  ({len(df_filled):,} rows)")
    return df_filled


# ─────────────────────────────────────────────────────────────────────
# 2. investor_transactions
# ─────────────────────────────────────────────────────────────────────
def clean_investor_transactions() -> pd.DataFrame:
    print(f"\n{DIVIDER}\n  [2/10] investor_transactions\n{DIVIDER}")
    df = pd.read_csv(RAW_DIR / "08_investor_transactions.csv")
    log(f"Raw shape          : {df.shape}")

    # Standardise transaction_type
    TYPE_MAP = {
        "sip": "SIP", "s.i.p": "SIP", "sip investment": "SIP",
        "lumpsum": "Lumpsum", "lump sum": "Lumpsum", "one time": "Lumpsum",
        "redemption": "Redemption", "redeem": "Redemption", "withdrawal": "Redemption",
    }
    raw_types = df["transaction_type"].unique()
    df["transaction_type"] = (df["transaction_type"]
                               .str.strip()
                               .str.lower()
                               .map(lambda x: TYPE_MAP.get(x, x.title())))
    valid_types = {"SIP", "Lumpsum", "Redemption"}
    invalid = ~df["transaction_type"].isin(valid_types)
    if invalid.sum():
        log(f"⚠  Unknown types    : {df.loc[invalid, 'transaction_type'].unique()} → dropped")
        df = df[~invalid]
    log(f"Transaction types  : {df['transaction_type'].value_counts().to_dict()}")

    # Parse dates
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    bad = df["transaction_date"].isna().sum()
    if bad: log(f"⚠  Bad dates        : {bad} → dropped")
    df = df.dropna(subset=["transaction_date"])

    # Validate amount > 0
    before = len(df)
    df = df[df["amount_inr"] > 0]
    log(f"Amount ≤ 0 dropped : {before - len(df)}")

    # KYC status enum
    valid_kyc = {"Verified", "Pending", "Rejected", "Expired"}
    bad_kyc = ~df["kyc_status"].isin(valid_kyc)
    if bad_kyc.sum():
        log(f"⚠  Unknown KYC vals : {df.loc[bad_kyc, 'kyc_status'].unique()}")
        df.loc[bad_kyc, "kyc_status"] = "Unknown"
    log(f"KYC distribution   : {df['kyc_status'].value_counts().to_dict()}")

    # Dedup
    before = len(df)
    df = df.drop_duplicates()
    log(f"Duplicates removed : {before - len(df)}")

    df = df.sort_values("transaction_date").reset_index(drop=True)

    out = PROC_DIR / "08_investor_transactions_clean.csv"
    df.to_csv(out, index=False)
    log(f"✅ Saved → {out.name}  ({len(df):,} rows)")
    return df


# ─────────────────────────────────────────────────────────────────────
# 3. scheme_performance
# ─────────────────────────────────────────────────────────────────────
def clean_scheme_performance() -> pd.DataFrame:
    print(f"\n{DIVIDER}\n  [3/10] scheme_performance\n{DIVIDER}")
    df = pd.read_csv(RAW_DIR / "07_scheme_performance.csv")
    log(f"Raw shape          : {df.shape}")

    return_cols = ["return_1yr_pct", "return_3yr_pct", "return_5yr_pct", "benchmark_3yr_pct"]
    numeric_cols = return_cols + ["alpha", "beta", "sharpe_ratio", "sortino_ratio",
                                   "std_dev_ann_pct", "max_drawdown_pct", "expense_ratio_pct"]

    # Coerce to numeric
    for col in numeric_cols:
        before_nulls = df[col].isna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        new_nulls = df[col].isna().sum() - before_nulls
        if new_nulls: log(f"⚠  {col}: {new_nulls} non-numeric → NaN")

    # Flag anomalies on return columns
    print("\n   📊 Return value ranges:")
    for col in return_cols:
        mn, mx = df[col].min(), df[col].max()
        outliers = ((df[col] < -50) | (df[col] > 100)).sum()
        print(f"   {col:<25} min={mn:>8.2f}  max={mx:>8.2f}  outliers={outliers}")
        if outliers:
            log(f"⚠  {col} has {outliers} suspicious values (< -50% or > 100%)")

    # Validate expense_ratio in 0.1% – 2.5%
    er = df["expense_ratio_pct"]
    below = (er < 0.1).sum()
    above = (er > 2.5).sum()
    log(f"expense_ratio < 0.1% : {below}  |  > 2.5% : {above}")
    df["expense_ratio_flag"] = "OK"
    df.loc[er < 0.1, "expense_ratio_flag"] = "BELOW_MIN"
    df.loc[er > 2.5, "expense_ratio_flag"] = "ABOVE_MAX"
    log(f"expense_ratio flags  : {df['expense_ratio_flag'].value_counts().to_dict()}")

    # Validate morningstar_rating 1-5
    bad_star = ~df["morningstar_rating"].between(1, 5)
    if bad_star.sum():
        log(f"⚠  Morningstar ratings out of 1-5: {df.loc[bad_star, 'morningstar_rating'].tolist()}")

    # max_drawdown should be <= 0
    bad_dd = (df["max_drawdown_pct"] > 0).sum()
    if bad_dd:
        log(f"⚠  max_drawdown_pct > 0 (should be negative): {bad_dd} rows → negated")
        df.loc[df["max_drawdown_pct"] > 0, "max_drawdown_pct"] *= -1

    df = df.drop_duplicates().reset_index(drop=True)

    out = PROC_DIR / "07_scheme_performance_clean.csv"
    df.to_csv(out, index=False)
    log(f"✅ Saved → {out.name}  ({len(df):,} rows)")
    return df


# ─────────────────────────────────────────────────────────────────────
# 4-10. Remaining datasets (lighter cleaning)
# ─────────────────────────────────────────────────────────────────────
def clean_fund_master() -> pd.DataFrame:
    print(f"\n{DIVIDER}\n  [4/10] fund_master\n{DIVIDER}")
    df = pd.read_csv(RAW_DIR / "01_fund_master.csv")
    df["launch_date"] = pd.to_datetime(df["launch_date"], errors="coerce")
    df["expense_ratio_pct"] = pd.to_numeric(df["expense_ratio_pct"], errors="coerce")
    df["exit_load_pct"]     = pd.to_numeric(df["exit_load_pct"],     errors="coerce")
    df["plan"] = df["plan"].str.strip().str.title()
    df = df.drop_duplicates(subset=["amfi_code"])
    out = PROC_DIR / "01_fund_master_clean.csv"
    df.to_csv(out, index=False)
    log(f"✅ Saved → {out.name}  ({len(df):,} rows)")
    return df


def clean_aum() -> pd.DataFrame:
    print(f"\n{DIVIDER}\n  [5/10] aum_by_fund_house\n{DIVIDER}")
    df = pd.read_csv(RAW_DIR / "03_aum_by_fund_house.csv")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).drop_duplicates()
    out = PROC_DIR / "03_aum_by_fund_house_clean.csv"
    df.to_csv(out, index=False)
    log(f"✅ Saved → {out.name}  ({len(df):,} rows)")
    return df


def clean_sip_inflows() -> pd.DataFrame:
    print(f"\n{DIVIDER}\n  [6/10] monthly_sip_inflows\n{DIVIDER}")
    df = pd.read_csv(RAW_DIR / "04_monthly_sip_inflows.csv")
    df["month"] = pd.to_datetime(df["month"], format="%Y-%m", errors="coerce")
    df = df.dropna(subset=["month"]).drop_duplicates()
    # yoy_growth NaN for first 12 months is expected — leave as-is
    out = PROC_DIR / "04_monthly_sip_inflows_clean.csv"
    df.to_csv(out, index=False)
    log(f"✅ Saved → {out.name}  ({len(df):,} rows)")
    return df


def clean_category_inflows() -> pd.DataFrame:
    print(f"\n{DIVIDER}\n  [7/10] category_inflows\n{DIVIDER}")
    df = pd.read_csv(RAW_DIR / "05_category_inflows.csv")
    df["month"] = pd.to_datetime(df["month"], format="%Y-%m", errors="coerce")
    df = df.dropna(subset=["month"]).drop_duplicates()
    out = PROC_DIR / "05_category_inflows_clean.csv"
    df.to_csv(out, index=False)
    log(f"✅ Saved → {out.name}  ({len(df):,} rows)")
    return df


def clean_folio_count() -> pd.DataFrame:
    print(f"\n{DIVIDER}\n  [8/10] industry_folio_count\n{DIVIDER}")
    df = pd.read_csv(RAW_DIR / "06_industry_folio_count.csv")
    df["month"] = pd.to_datetime(df["month"], format="%Y-%m", errors="coerce")
    df = df.dropna(subset=["month"]).drop_duplicates()
    out = PROC_DIR / "06_industry_folio_count_clean.csv"
    df.to_csv(out, index=False)
    log(f"✅ Saved → {out.name}  ({len(df):,} rows)")
    return df


def clean_portfolio_holdings() -> pd.DataFrame:
    print(f"\n{DIVIDER}\n  [9/10] portfolio_holdings\n{DIVIDER}")
    df = pd.read_csv(RAW_DIR / "09_portfolio_holdings.csv")
    df["portfolio_date"] = pd.to_datetime(df["portfolio_date"], errors="coerce")
    df["weight_pct"] = pd.to_numeric(df["weight_pct"], errors="coerce")
    df = df.dropna(subset=["portfolio_date"]).drop_duplicates()
    out = PROC_DIR / "09_portfolio_holdings_clean.csv"
    df.to_csv(out, index=False)
    log(f"✅ Saved → {out.name}  ({len(df):,} rows)")
    return df


def clean_benchmark_indices() -> pd.DataFrame:
    print(f"\n{DIVIDER}\n  [10/10] benchmark_indices\n{DIVIDER}")
    df = pd.read_csv(RAW_DIR / "10_benchmark_indices.csv")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).drop_duplicates()
    df = df.sort_values(["index_name", "date"]).reset_index(drop=True)
    out = PROC_DIR / "10_benchmark_indices_clean.csv"
    df.to_csv(out, index=False)
    log(f"✅ Saved → {out.name}  ({len(df):,} rows)")
    return df


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "█" * 70)
    print("  DAY 2: DATA CLEANING")
    print("█" * 70)

    results = {
        "fund_master"          : clean_fund_master(),
        "nav_history"          : clean_nav_history(),
        "aum_by_fund_house"    : clean_aum(),
        "monthly_sip_inflows"  : clean_sip_inflows(),
        "category_inflows"     : clean_category_inflows(),
        "industry_folio_count" : clean_folio_count(),
        "scheme_performance"   : clean_scheme_performance(),
        "investor_transactions": clean_investor_transactions(),
        "portfolio_holdings"   : clean_portfolio_holdings(),
        "benchmark_indices"    : clean_benchmark_indices(),
    }

    print(f"\n{DIVIDER}")
    print("  CLEANING SUMMARY")
    print(DIVIDER)
    print(f"   {'Dataset':<30} {'Rows':>10}")
    print(f"   {'-'*30}  {'-'*10}")
    for name, df in results.items():
        print(f"   {name:<30} {len(df):>10,}")
    print(f"\n✅ All 10 datasets cleaned → data/processed/\n")
