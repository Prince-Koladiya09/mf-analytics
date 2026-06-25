# Mutual Fund Analytics Project

End-to-end analytics pipeline for Indian mutual fund data using AMFI/mfapi.in sources.

## Project Structure

```
mf_analytics/
├── data/
│   ├── raw/                        # Original 10 CSVs + live NAV fetches
│   └── processed/                  # 10 cleaned CSVs + quality summary
├── notebooks/                      # Jupyter EDA notebooks (Day 3+)
├── sql/
│   ├── schema.sql                  # SQLite star schema DDL
│   └── queries.sql                 # 10 analytical SQL queries
├── dashboard/                      # Plotly / Dash dashboard (Day 3+)
├── reports/
│   └── data_dictionary.md          # Full column-level documentation
├── data_ingestion.py               # Day 1: Load & validate all 10 CSVs
├── live_nav_fetch.py               # Day 1: Live NAV from mfapi.in
├── data_cleaning.py                # Day 2: Clean all 10 datasets
├── db_loader.py                    # Day 2: Load SQLite DB via SQLAlchemy
├── bluestock_mf.db                 # SQLite database (5.58 MB)
└── requirements.txt
```

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/mf-analytics.git
cd mf-analytics
```

### 2. Create and activate virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

---

## How to Run

### Day 1 — Data Ingestion
```bash
python data_ingestion.py
```
Loads all 10 raw CSVs, prints shape / dtypes / head, checks for anomalies,
validates AMFI codes across files, saves a quality summary to `data/processed/`.

```bash
python live_nav_fetch.py
```
Fetches live NAV for 6 bluechip schemes from mfapi.in and saves to `data/raw/`.
Requires internet access to mfapi.in.

---

### Day 2 — Cleaning + Database
```bash
python data_cleaning.py
```
Cleans all 10 datasets — parses dates, forward-fills NAV, standardises enums,
validates ranges. Saves 10 clean CSVs to `data/processed/`.

```bash
python db_loader.py
```
Creates `bluestock_mf.db`, builds the star schema from `sql/schema.sql`,
loads all cleaned data, and verifies row counts match source CSVs.

---

### Run SQL Queries
Open any SQLite client (DB Browser, DBeaver, or the Python snippet below)
and point it at `bluestock_mf.db`. All 10 queries are in `sql/queries.sql`.

Quick way to run from terminal:
```bash
python - << 'EOF'
import sqlite3, pandas as pd
db = sqlite3.connect("bluestock_mf.db")

# Example: Top 5 funds by AUM
df = pd.read_sql("""
    SELECT f.scheme_name, f.plan, p.aum_crore, p.return_3yr_pct
    FROM fact_performance p
    JOIN dim_fund f USING(amfi_code)
    ORDER BY p.aum_crore DESC LIMIT 5
""", db)
print(df)
db.close()
EOF
```

---

## Datasets (10 CSVs)

| # | Raw File | Clean File | Rows (clean) | Description |
|---|----------|------------|--------------|-------------|
| 1 | fund_master | 01_fund_master_clean.csv | 40 | Scheme metadata, categories, risk |
| 2 | nav_history | 02_nav_history_clean.csv | 64,320 | Daily NAV (ffilled for holidays) |
| 3 | aum_by_fund_house | 03_aum_by_fund_house_clean.csv | 90 | Quarterly AUM per fund house |
| 4 | monthly_sip_inflows | 04_monthly_sip_inflows_clean.csv | 48 | Industry SIP inflow stats |
| 5 | category_inflows | 05_category_inflows_clean.csv | 144 | Monthly net inflows by category |
| 6 | industry_folio_count | 06_industry_folio_count_clean.csv | 21 | Quarterly folio counts |
| 7 | scheme_performance | 07_scheme_performance_clean.csv | 40 | Returns, alpha, beta, Sharpe |
| 8 | investor_transactions | 08_investor_transactions_clean.csv | 32,778 | Investor buy/sell/SIP records |
| 9 | portfolio_holdings | 09_portfolio_holdings_clean.csv | 322 | Stock-level holdings per scheme |
| 10 | benchmark_indices | 10_benchmark_indices_clean.csv | 8,050 | NIFTY50, SENSEX, etc. daily close |

---

## Database Schema (bluestock_mf.db)

Star schema with 2 dimension tables and 8 fact tables:

```
dim_fund ──────────────────────────────────────────────────┐
dim_date ──┬── fact_nav                                    │
           ├── fact_transactions ──────────────────────────┤
           ├── fact_performance ───────────────────────────┤
           ├── fact_aum                                    │
           ├── fact_sip_inflows                            │
           ├── fact_category_inflows                       │
           ├── fact_portfolio_holdings ─────────────────────┘
           └── fact_benchmark_indices
```

---

## Live NAV Schemes

| AMFI Code | Scheme |
|-----------|--------|
| 125497 | HDFC Top 100 Direct |
| 119551 | SBI Bluechip Direct |
| 120503 | ICICI Bluechip Direct |
| 118632 | Nippon Large Cap Direct |
| 119092 | Axis Bluechip Direct |
| 120841 | Kotak Bluechip Direct |

---

## Commit History

| Day | Commit Message | What was done |
|-----|---------------|---------------|
| 1 | Day 1: Data ingestion complete | Loaded 10 CSVs, AMFI validation, live NAV fetch |
| 2 | Day 2: Cleaned data + SQLite DB loaded | Cleaned all CSVs, built star schema, loaded DB, 10 SQL queries |
