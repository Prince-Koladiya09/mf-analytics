# Mutual Fund Analytics Project

End-to-end analytics pipeline for Indian mutual fund data using AMFI/mfapi.in sources.

## Folder Structure

```
mf_analytics/
|
|-- data/
|   |-- raw/                                   # 10 original CSVs + live NAV fetches
|   |-- processed/
|       |-- 01_fund_master_clean.csv
|       |-- 02_nav_history_clean.csv           # 64,320 rows (ffilled weekends)
|       |-- 03_aum_by_fund_house_clean.csv
|       |-- 04_monthly_sip_inflows_clean.csv
|       |-- 05_category_inflows_clean.csv
|       |-- 06_industry_folio_count_clean.csv
|       |-- 07_scheme_performance_clean.csv
|       |-- 08_investor_transactions_clean.csv
|       |-- 09_portfolio_holdings_clean.csv
|       |-- 10_benchmark_indices_clean.csv
|       |-- data_quality_summary.csv
|       |-- daily_returns.csv                  # Day 4: daily returns all 40 funds
|       |-- cagr_table.csv                     # Day 4: 1yr / 3yr / 5yr CAGR
|       |-- alpha_beta.csv                     # Day 4: OLS alpha and beta vs Nifty 100
|       |-- fund_scorecard.csv                 # Day 4: composite 0-100 score
|
|-- notebooks/
|   |-- EDA_Analysis.ipynb                     # Day 3: 15 charts + 10 EDA findings
|   |-- Performance_Analytics.ipynb            # Day 4: returns, CAGR, Sharpe, Alpha, Scorecard
|
|-- sql/
|   |-- schema.sql                             # SQLite star schema DDL
|   |-- queries.sql                            # 10 analytical SQL queries
|
|-- dashboard/                                 # Day 5+
|
|-- reports/
|   |-- data_dictionary.md
|   |-- charts/
|       |-- 01_nav_trend.png
|       |-- 02_aum_growth.png
|       |-- 03_sip_inflows.png
|       |-- 04_category_heatmap.png
|       |-- 05_investor_demographics.png
|       |-- 06_geographic_distribution.png
|       |-- 07_folio_growth.png
|       |-- 08_correlation_matrix.png
|       |-- 09_sector_donut.png
|       |-- 10_performance_scatter.png
|       |-- 11_expense_ratio.png
|       |-- 12_txn_volume.png
|       |-- 13_top_holdings.png
|       |-- 14_morningstar_ratings.png
|       |-- 15_sip_vs_folio.png
|       |-- 16_benchmark_comparison.png        # Day 4: top 5 vs Nifty 50 + Nifty 100
|       |-- 17_fund_scorecard.png              # Day 4: composite scorecard bar chart
|       |-- 18_alpha_beta_scatter.png          # Day 4: alpha vs beta scatter
|
|-- data_ingestion.py                          # Day 1
|-- live_nav_fetch.py                          # Day 1
|-- data_cleaning.py                           # Day 2
|-- db_loader.py                               # Day 2
|-- eda_analysis.py                            # Day 3
|-- generate_notebook.py                       # Day 3
|-- performance_analytics.py                   # Day 4
|-- generate_performance_notebook.py           # Day 4
|-- bluestock_mf.db                            # SQLite DB (star schema, 9 tables)
|-- requirements.txt
|-- README.md
```

---

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/mf-analytics.git
cd mf-analytics

python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate      # Mac / Linux

pip install -r requirements.txt
```

---

## How to Run (in order)

### Day 1 - Data Ingestion
```bash
python data_ingestion.py      # load + inspect all 10 CSVs, validate AMFI codes
python live_nav_fetch.py      # fetch live NAV from mfapi.in (needs internet)
```

### Day 2 - Cleaning + Database
```bash
python data_cleaning.py       # clean all 10 CSVs to data/processed/
python db_loader.py           # build bluestock_mf.db, verify row counts
```

### Day 3 - EDA + Charts
```bash
python eda_analysis.py              # generate 15 chart PNGs to reports/charts/
python generate_notebook.py         # build notebooks/EDA_Analysis.ipynb
jupyter notebook                    # open EDA_Analysis.ipynb interactively
```

### Day 4 - Performance Analytics
```bash
python performance_analytics.py             # compute all metrics + export CSVs + 3 charts
python generate_performance_notebook.py     # build notebooks/Performance_Analytics.ipynb
jupyter notebook                            # open Performance_Analytics.ipynb
```

---

## Metrics Computed (Day 4)

| Metric | Formula | Notes |
|--------|---------|-------|
| Daily Return | NAV_t / NAV_t-1 - 1 | Validated: mean 0.045%, std 0.87% |
| CAGR | (NAV_end / NAV_start)^(1/n) - 1 | 1yr, 3yr, 5yr lookback |
| Sharpe Ratio | (Rp - Rf) / Std x sqrt(252) | Rf = 6.5% |
| Sortino Ratio | (Rp - Rf) / Downside_Std x sqrt(252) | Downside days only |
| Alpha | OLS intercept x 252 (annualised %) | vs Nifty 100 |
| Beta | OLS slope vs Nifty 100 | scipy.stats.linregress |
| Max Drawdown | min(NAV / running_max - 1) | Peak + trough dates recorded |
| Scorecard | 30% CAGR + 25% Sharpe + 20% Alpha + 15% ER + 10% MDD | 0-100 scale |

---

## Key Results (Day 4)

**Top Fund by Scorecard:** ICICI Pru Midcap Fund - Regular (84.7/100)
- 3yr CAGR: 31.78%
- Sharpe: 0.883
- Alpha: 29.26% annualised
- Max Drawdown: -18.19%

**Best Sharpe Ratio:** Mirae Asset Large Cap Fund (1.068)
**Highest Alpha:** SBI Small Cap Fund (30.34% annualised)
**Lowest Max Drawdown:** Mirae Asset Large Cap Fund (-11.27%)

---

## Datasets (10 CSVs)

| File | Rows | Description |
|------|------|-------------|
| 01_fund_master_clean.csv | 40 | Scheme metadata |
| 02_nav_history_clean.csv | 64,320 | Daily NAV (ffilled) |
| 03_aum_by_fund_house_clean.csv | 90 | Quarterly AUM |
| 04_monthly_sip_inflows_clean.csv | 48 | SIP inflow stats |
| 05_category_inflows_clean.csv | 144 | Monthly category inflows |
| 06_industry_folio_count_clean.csv | 21 | Quarterly folios |
| 07_scheme_performance_clean.csv | 40 | Returns + risk metrics |
| 08_investor_transactions_clean.csv | 32,778 | Buy/sell/SIP records |
| 09_portfolio_holdings_clean.csv | 322 | Stock-level holdings |
| 10_benchmark_indices_clean.csv | 8,050 | Nifty50/100/etc daily |

---

## Commit History

| Day | Commit Message | Deliverables |
|-----|---------------|--------------|
| 1 | Day 1: Data ingestion complete | data_ingestion.py, live_nav_fetch.py |
| 2 | Day 2: Cleaned data + SQLite DB loaded | data_cleaning.py, db_loader.py, schema.sql, queries.sql, bluestock_mf.db |
| 3 | Day 3: EDA complete - 15 charts + notebook | eda_analysis.py, EDA_Analysis.ipynb, 15 PNGs |
| 4 | Day 4: Performance analytics complete | performance_analytics.py, Performance_Analytics.ipynb, fund_scorecard.csv, alpha_beta.csv, 3 PNGs |