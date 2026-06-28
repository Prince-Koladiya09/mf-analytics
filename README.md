# Mutual Fund Analytics Project

End-to-end analytics pipeline for Indian mutual fund data using AMFI/mfapi.in sources.

## Folder Structure

```
mf_analytics/
├── data/
│   ├── raw/                              # 10 original CSVs + live NAV fetches
│   └── processed/                        # 10 cleaned CSVs + quality summary
│       ├── 01_fund_master_clean.csv
│       ├── 02_nav_history_clean.csv      # 64,320 rows (ffilled weekends)
│       ├── 03_aum_by_fund_house_clean.csv
│       ├── 04_monthly_sip_inflows_clean.csv
│       ├── 05_category_inflows_clean.csv
│       ├── 06_industry_folio_count_clean.csv
│       ├── 07_scheme_performance_clean.csv
│       ├── 08_investor_transactions_clean.csv
│       ├── 09_portfolio_holdings_clean.csv
│       ├── 10_benchmark_indices_clean.csv
│       └── data_quality_summary.csv
│
├── notebooks/
│   └── EDA_Analysis.ipynb                # Day 3: 15 charts + 10 EDA findings
│
├── sql/
│   ├── schema.sql                        # SQLite star schema DDL
│   └── queries.sql                       # 10 analytical SQL queries
│
├── dashboard/                            # Day 4+
│
├── reports/
│   ├── data_dictionary.md                # Full column-level documentation
│   └── charts/                           # 15 exported PNG charts
│       ├── 01_nav_trend.png
│       ├── 02_aum_growth.png
│       ├── 03_sip_inflows.png
│       ├── 04_category_heatmap.png
│       ├── 05_investor_demographics.png
│       ├── 06_geographic_distribution.png
│       ├── 07_folio_growth.png
│       ├── 08_correlation_matrix.png
│       ├── 09_sector_donut.png
│       ├── 10_performance_scatter.png
│       ├── 11_expense_ratio.png
│       ├── 12_txn_volume.png
│       ├── 13_top_holdings.png
│       ├── 14_morningstar_ratings.png
│       └── 15_sip_vs_folio.png
│
├── data_ingestion.py                     # Day 1: Load & validate all 10 CSVs
├── live_nav_fetch.py                     # Day 1: Live NAV from mfapi.in
├── data_cleaning.py                      # Day 2: Clean all 10 datasets
├── db_loader.py                          # Day 2: Load SQLite DB via SQLAlchemy
├── eda_analysis.py                       # Day 3: Generate all 15 chart PNGs
├── generate_notebook.py                  # Day 3: Build EDA_Analysis.ipynb
├── bluestock_mf.db                       # SQLite database (star schema, 9 tables)
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

### Day 1 - Data Ingestion
```bash
python data_ingestion.py      # inspect all 10 CSVs, validate AMFI codes
python live_nav_fetch.py      # fetch live NAV (needs internet)
```

### Day 2 - Cleaning + Database
```bash
python data_cleaning.py       # clean all 10 CSVs → data/processed/
python db_loader.py           # build bluestock_mf.db, verify row counts
```

### Day 3 - EDA + Charts
```bash
python eda_analysis.py        # generate all 15 chart PNGs → reports/charts/
python generate_notebook.py   # build notebooks/EDA_Analysis.ipynb
jupyter notebook               # open and run EDA_Analysis.ipynb interactively
```

---

## Datasets (10 CSVs)

| File | Rows (clean) | Description |
|------|--------------|-------------|
| 01_fund_master_clean.csv | 40 | Scheme metadata, categories, risk |
| 02_nav_history_clean.csv | 64,320 | Daily NAV (ffilled for holidays) |
| 03_aum_by_fund_house_clean.csv | 90 | Quarterly AUM per fund house |
| 04_monthly_sip_inflows_clean.csv | 48 | Industry SIP inflow stats |
| 05_category_inflows_clean.csv | 144 | Monthly net inflows by category |
| 06_industry_folio_count_clean.csv | 21 | Quarterly folio counts |
| 07_scheme_performance_clean.csv | 40 | Returns, alpha, beta, Sharpe |
| 08_investor_transactions_clean.csv | 32,778 | Investor buy/sell/SIP records |
| 09_portfolio_holdings_clean.csv | 322 | Stock-level holdings per scheme |
| 10_benchmark_indices_clean.csv | 8,050 | NIFTY50, SENSEX daily close |

---

## Database Schema (bluestock_mf.db)

Star schema with 2 dimension tables and 8 fact tables:
- dim_fund, dim_date
- fact_nav, fact_transactions, fact_performance, fact_aum
- fact_sip_inflows, fact_category_inflows, fact_portfolio_holdings, fact_benchmark_indices

---

## EDA Charts (15 total)

| Chart | Tool | Key Insight |
|-------|------|-------------|
| 01_nav_trend | Plotly | 2023 bull run +34%, 2024 correction |
| 02_aum_growth | Seaborn | SBI Rs.12.5L Cr dominance (gold border) |
| 03_sip_inflows | Plotly | ATH Rs.31,002 Cr (Dec 2025) annotated |
| 04_category_heatmap | Seaborn | Large Cap consistently positive |
| 05_investor_demographics | Seaborn | 36-45 age group highest SIP ticket |
| 06_geographic_distribution | Seaborn | T30 cities = 82% of investment value |
| 07_folio_growth | Plotly | 13.26 Cr to 26.12 Cr in 4 years |
| 08_correlation_matrix | Seaborn | Large-cap correlation r = 0.82-0.97 |
| 09_sector_donut | Plotly | Banking = 28% of equity weight |
| 10_performance_scatter | Plotly | Sharpe greater than 1 at 14-18% CAGR |
| 11_expense_ratio | Seaborn | Direct plans 53% cheaper than Regular |
| 12_txn_volume | Plotly | SIP dominates monthly volumes |
| 13_top_holdings | Seaborn | Axis Bank No.1 stock by market value |
| 14_morningstar_ratings | Seaborn | 5-star funds deliver highest returns |
| 15_sip_vs_folio | Plotly | SIP inflows and folios growing in tandem |

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

| Day | Commit Message | Deliverables |
|-----|---------------|--------------|
| 1 | Day 1: Data ingestion complete | data_ingestion.py, live_nav_fetch.py, requirements.txt |
| 2 | Day 2: Cleaned data + SQLite DB loaded | data_cleaning.py, db_loader.py, schema.sql, queries.sql, bluestock_mf.db, data_dictionary.md |
| 3 | Day 3: EDA complete - 15 charts + notebook | eda_analysis.py, generate_notebook.py, EDA_Analysis.ipynb, 15 PNG charts |