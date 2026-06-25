import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent
PROC_DIR = BASE_DIR / "data" / "processed"
SQL_DIR  = BASE_DIR / "sql"
DB_PATH  = BASE_DIR / "bluestock_mf.db"

DIVIDER = "=" * 70


# ─────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────
def get_engine():
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))
    return engine


# ─────────────────────────────────────────────────────────────────────
# Create schema from schema.sql
# ─────────────────────────────────────────────────────────────────────
def create_schema(engine):
    print(f"\n{DIVIDER}\n  Creating schema from sql/schema.sql\n{DIVIDER}")
    schema_sql = (SQL_DIR / "schema.sql").read_text(encoding="utf-8")
    raw_stmts = schema_sql.split(";")
    statements = []
    for s in raw_stmts:
        cleaned = s.strip()
        if not cleaned:
            continue
        non_comment = [l for l in cleaned.splitlines()
                       if l.strip() and not l.strip().startswith("--")]
        if non_comment:
            statements.append(cleaned)
    with engine.connect() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
        conn.commit()
    print(f"    Schema created  ({len(statements)} statements executed)")


# ─────────────────────────────────────────────────────────────────────
# Build dim_date calendar
# ─────────────────────────────────────────────────────────────────────
def build_dim_date(engine):
    print(f"\n{DIVIDER}\n  Building dim_date\n{DIVIDER}")

    # Span covers all data: 2022-01-01 to 2026-12-31
    dates = pd.date_range("2022-01-01", "2026-12-31", freq="D")
    month_names = {1:"January",2:"February",3:"March",4:"April",5:"May",
                   6:"June",7:"July",8:"August",9:"September",
                   10:"October",11:"November",12:"December"}
    day_names   = {0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",
                   4:"Friday",5:"Saturday",6:"Sunday"}

    df = pd.DataFrame({
        "date_id"    : dates.strftime("%Y-%m-%d"),
        "year"       : dates.year,
        "quarter"    : dates.quarter,
        "month"      : dates.month,
        "month_name" : dates.month.map(month_names),
        "week"       : dates.isocalendar().week.values,
        "day_of_week": dates.dayofweek,
        "day_name"   : dates.dayofweek.map(day_names),
        "is_weekend" : (dates.dayofweek >= 5).astype(int),
    })

    df.to_sql("dim_date", engine, if_exists="replace", index=False)
    print(f"    dim_date loaded  ({len(df):,} rows)")
    return df


# ─────────────────────────────────────────────────────────────────────
# Load helper
# ─────────────────────────────────────────────────────────────────────
def load_table(df: pd.DataFrame, table: str, engine, if_exists="replace"):
    df.to_sql(table, engine, if_exists=if_exists, index=False)
    with engine.connect() as conn:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    print(f"    {table:<35} {count:>10,} rows")
    return count


# ─────────────────────────────────────────────────────────────────────
# Load dim_fund
# ─────────────────────────────────────────────────────────────────────
def load_dim_fund(engine) -> int:
    print(f"\n{DIVIDER}\n  Loading dim_fund\n{DIVIDER}")
    df = pd.read_csv(PROC_DIR / "01_fund_master_clean.csv", parse_dates=["launch_date"])
    df["launch_date"] = df["launch_date"].dt.strftime("%Y-%m-%d")
    return load_table(df, "dim_fund", engine)


# ─────────────────────────────────────────────────────────────────────
# Load fact_nav
# ─────────────────────────────────────────────────────────────────────
def load_fact_nav(engine) -> int:
    print(f"\n{DIVIDER}\n  Loading fact_nav\n{DIVIDER}")
    df = pd.read_csv(PROC_DIR / "02_nav_history_clean.csv", parse_dates=["date"])
    df["date_id"] = df["date"].dt.strftime("%Y-%m-%d")
    df = df[["amfi_code", "date_id", "nav"]].rename(columns={"nav": "nav"})
    return load_table(df, "fact_nav", engine)


# ─────────────────────────────────────────────────────────────────────
# Load fact_transactions
# ─────────────────────────────────────────────────────────────────────
def load_fact_transactions(engine) -> int:
    print(f"\n{DIVIDER}\n  Loading fact_transactions\n{DIVIDER}")
    df = pd.read_csv(PROC_DIR / "08_investor_transactions_clean.csv",
                     parse_dates=["transaction_date"])
    df["date_id"] = df["transaction_date"].dt.strftime("%Y-%m-%d")
    df = df.drop(columns=["transaction_date"])
    df = df.rename(columns={"investor_id": "investor_id"})
    return load_table(df, "fact_transactions", engine)


# ─────────────────────────────────────────────────────────────────────
# Load fact_performance
# ─────────────────────────────────────────────────────────────────────
def load_fact_performance(engine) -> int:
    print(f"\n{DIVIDER}\n  Loading fact_performance\n{DIVIDER}")
    df = pd.read_csv(PROC_DIR / "07_scheme_performance_clean.csv")
    keep = ["amfi_code","return_1yr_pct","return_3yr_pct","return_5yr_pct",
            "benchmark_3yr_pct","alpha","beta","sharpe_ratio","sortino_ratio",
            "std_dev_ann_pct","max_drawdown_pct","aum_crore","expense_ratio_pct",
            "morningstar_rating","risk_grade","expense_ratio_flag"]
    df = df[keep]
    return load_table(df, "fact_performance", engine)


# ─────────────────────────────────────────────────────────────────────
# Load fact_aum
# ─────────────────────────────────────────────────────────────────────
def load_fact_aum(engine) -> int:
    print(f"\n{DIVIDER}\n  Loading fact_aum\n{DIVIDER}")
    df = pd.read_csv(PROC_DIR / "03_aum_by_fund_house_clean.csv", parse_dates=["date"])
    df["date_id"] = df["date"].dt.strftime("%Y-%m-%d")
    df = df.drop(columns=["date"])
    return load_table(df, "fact_aum", engine)


# ─────────────────────────────────────────────────────────────────────
# Load supplementary tables
# ─────────────────────────────────────────────────────────────────────
def load_supplementary(engine):
    print(f"\n{DIVIDER}\n  Loading supplementary tables\n{DIVIDER}")

    # SIP inflows
    df = pd.read_csv(PROC_DIR / "04_monthly_sip_inflows_clean.csv", parse_dates=["month"])
    df["date_id"] = df["month"].dt.strftime("%Y-%m-%d")
    df = df.drop(columns=["month"])
    load_table(df, "fact_sip_inflows", engine)

    # Category inflows
    df = pd.read_csv(PROC_DIR / "05_category_inflows_clean.csv", parse_dates=["month"])
    df["date_id"] = df["month"].dt.strftime("%Y-%m-%d")
    df = df.drop(columns=["month"])
    load_table(df, "fact_category_inflows", engine)

    # Portfolio holdings
    df = pd.read_csv(PROC_DIR / "09_portfolio_holdings_clean.csv", parse_dates=["portfolio_date"])
    df["date_id"] = df["portfolio_date"].dt.strftime("%Y-%m-%d")
    df = df.drop(columns=["portfolio_date"])
    load_table(df, "fact_portfolio_holdings", engine)

    # Benchmark indices
    df = pd.read_csv(PROC_DIR / "10_benchmark_indices_clean.csv", parse_dates=["date"])
    df["date_id"] = df["date"].dt.strftime("%Y-%m-%d")
    df = df.drop(columns=["date"])
    load_table(df, "fact_benchmark_indices", engine)


# ─────────────────────────────────────────────────────────────────────
# Verify row counts against source CSVs
# ─────────────────────────────────────────────────────────────────────
def verify_counts(engine):
    print(f"\n{DIVIDER}\n  ROW COUNT VERIFICATION\n{DIVIDER}")

    checks = {
        "dim_fund"               : ("01_fund_master_clean.csv",           None),
        "fact_nav"               : ("02_nav_history_clean.csv",           None),
        "fact_aum"               : ("03_aum_by_fund_house_clean.csv",     None),
        "fact_sip_inflows"       : ("04_monthly_sip_inflows_clean.csv",   None),
        "fact_category_inflows"  : ("05_category_inflows_clean.csv",      None),
        "fact_performance"       : ("07_scheme_performance_clean.csv",    None),
        "fact_transactions"      : ("08_investor_transactions_clean.csv", None),
        "fact_portfolio_holdings": ("09_portfolio_holdings_clean.csv",    None),
        "fact_benchmark_indices" : ("10_benchmark_indices_clean.csv",     None),
    }

    print(f"{'Table':<35} {'CSV rows':>10}  {'DB rows':>10}  {'Match':>6}")
    print(f"{'-'*35}  {'-'*10}  {'-'*10}  {'-'*6}")
    all_match = True
    with engine.connect() as conn:
        for table, (fname, _) in checks.items():
            csv_rows = len(pd.read_csv(PROC_DIR / fname))
            db_rows  = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            match    = "✅" if csv_rows == db_rows else "❌"
            if csv_rows != db_rows:
                all_match = False
            print(f"   {table:<35} {csv_rows:>10,}  {db_rows:>10,}  {match:>6}")

    if all_match:
        print("\n    All row counts match source CSVs")
    else:
        print("\n    Some counts differ — check for FK constraint drops")

    # DB file size
    size_mb = DB_PATH.stat().st_size / 1024 / 1024
    print(f"\n    Database size: {size_mb:.2f} MB  →  {DB_PATH.name}")


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "█" * 70)
    print("  DAY 2: SQLite DB LOADER")
    print("█" * 70)

    # Drop existing DB for clean reload
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"\n   🗑  Removed existing {DB_PATH.name}")

    engine = get_engine()
    create_schema(engine)
    build_dim_date(engine)
    load_dim_fund(engine)
    load_fact_nav(engine)
    load_fact_transactions(engine)
    load_fact_performance(engine)
    load_fact_aum(engine)
    load_supplementary(engine)
    verify_counts(engine)

    print(f"\n bluestock_mf.db ready.\n")