# Mutual Fund Analytics Project

End-to-end analytics pipeline for Indian mutual fund data using AMFI/mfapi.in sources.

## Project Structure

```
mf_analytics/
├── data/
│   ├── raw/           # Original CSVs + live NAV fetches
│   └── processed/     # Cleaned, merged, validated outputs
├── notebooks/         # Jupyter EDA notebooks
├── sql/               # SQL queries and schema
├── dashboard/         # Plotly / Dash dashboard code
├── reports/           # Generated reports
├── data_ingestion.py  # Day 1: Load & validate all 10 CSVs
├── live_nav_fetch.py  # Day 1: Live NAV from mfapi.in
└── requirements.txt
```

## Datasets (10 CSVs)

| # | File | Rows | Description |
|---|------|------|-------------|
| 1 | fund_master | 40 | Scheme metadata, categories, risk |
| 2 | nav_history | 46,000 | Daily NAV 2022–2025 |
| 3 | aum_by_fund_house | 90 | Quarterly AUM per fund house |
| 4 | monthly_sip_inflows | 48 | Industry SIP inflow stats |
| 5 | category_inflows | 144 | Monthly net inflows by category |
| 6 | industry_folio_count | 21 | Quarterly folio counts |
| 7 | scheme_performance | 40 | Returns, alpha, beta, Sharpe |
| 8 | investor_transactions | 32,778 | Investor buy/sell/SIP records |
| 9 | portfolio_holdings | 322 | Stock-level holdings per scheme |
| 10 | benchmark_indices | 8,050 | NIFTY50, SENSEX, etc. daily close |

## Live NAV Schemes

| AMFI Code | Scheme |
|-----------|--------|
| 125497 | HDFC Top 100 Direct |
| 119551 | SBI Bluechip Direct |
| 120503 | ICICI Bluechip Direct |
| 118632 | Nippon Large Cap Direct |
| 119092 | Axis Bluechip Direct |
| 120841 | Kotak Bluechip Direct |

## Setup

```bash
pip install -r requirements.txt
python data_ingestion.py
python live_nav_fetch.py
```

## Day 1 Commit
Data ingestion, validation, AMFI code cross-check, live NAV fetch scaffold.
