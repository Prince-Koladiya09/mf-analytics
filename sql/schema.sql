

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dim_fund (
    amfi_code           INTEGER     PRIMARY KEY,
    fund_house          TEXT        NOT NULL,
    scheme_name         TEXT        NOT NULL,
    category            TEXT,
    sub_category        TEXT,
    plan                TEXT,
    benchmark           TEXT,
    fund_manager        TEXT,
    risk_category       TEXT,
    sebi_category_code  TEXT,
    launch_date         TEXT,
    min_sip_amount      INTEGER,
    min_lumpsum_amount  INTEGER,
    expense_ratio_pct   REAL,
    exit_load_pct       REAL
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_id     TEXT    PRIMARY KEY,
    year        INTEGER NOT NULL,
    quarter     INTEGER NOT NULL,
    month       INTEGER NOT NULL,
    month_name  TEXT    NOT NULL,
    week        INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name    TEXT    NOT NULL,
    is_weekend  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS fact_nav (
    nav_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code   INTEGER NOT NULL REFERENCES dim_fund(amfi_code),
    date_id     TEXT    NOT NULL REFERENCES dim_date(date_id),
    nav         REAL    NOT NULL CHECK (nav > 0),
    UNIQUE (amfi_code, date_id)
);

CREATE TABLE IF NOT EXISTS fact_transactions (
    txn_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    investor_id         TEXT    NOT NULL,
    amfi_code           INTEGER NOT NULL REFERENCES dim_fund(amfi_code),
    date_id             TEXT    NOT NULL REFERENCES dim_date(date_id),
    transaction_type    TEXT    NOT NULL CHECK (transaction_type IN ('SIP','Lumpsum','Redemption')),
    amount_inr          INTEGER NOT NULL CHECK (amount_inr > 0),
    state               TEXT,
    city                TEXT,
    city_tier           TEXT,
    age_group           TEXT,
    gender              TEXT,
    annual_income_lakh  REAL,
    payment_mode        TEXT,
    kyc_status          TEXT
);

CREATE TABLE IF NOT EXISTS fact_performance (
    perf_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code           INTEGER NOT NULL REFERENCES dim_fund(amfi_code),
    return_1yr_pct      REAL,
    return_3yr_pct      REAL,
    return_5yr_pct      REAL,
    benchmark_3yr_pct   REAL,
    alpha               REAL,
    beta                REAL,
    sharpe_ratio        REAL,
    sortino_ratio       REAL,
    std_dev_ann_pct     REAL,
    max_drawdown_pct    REAL,
    aum_crore           INTEGER,
    expense_ratio_pct   REAL,
    morningstar_rating  INTEGER CHECK (morningstar_rating BETWEEN 1 AND 5),
    risk_grade          TEXT,
    expense_ratio_flag  TEXT DEFAULT 'OK'
);

CREATE TABLE IF NOT EXISTS fact_aum (
    aum_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date_id         TEXT    NOT NULL REFERENCES dim_date(date_id),
    fund_house      TEXT    NOT NULL,
    aum_lakh_crore  REAL,
    aum_crore       INTEGER,
    num_schemes     INTEGER,
    UNIQUE (date_id, fund_house)
);

CREATE TABLE IF NOT EXISTS fact_sip_inflows (
    sip_id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    date_id                     TEXT    NOT NULL REFERENCES dim_date(date_id),
    sip_inflow_crore            INTEGER,
    active_sip_accounts_crore   REAL,
    new_sip_accounts_lakh       REAL,
    sip_aum_lakh_crore          REAL,
    yoy_growth_pct              REAL
);

CREATE TABLE IF NOT EXISTS fact_category_inflows (
    cat_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date_id             TEXT    NOT NULL REFERENCES dim_date(date_id),
    category            TEXT    NOT NULL,
    net_inflow_crore    REAL
);

CREATE TABLE IF NOT EXISTS fact_portfolio_holdings (
    holding_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code           INTEGER NOT NULL REFERENCES dim_fund(amfi_code),
    date_id             TEXT    NOT NULL REFERENCES dim_date(date_id),
    stock_symbol        TEXT,
    stock_name          TEXT,
    sector              TEXT,
    weight_pct          REAL,
    market_value_cr     REAL,
    current_price_inr   REAL
);

CREATE TABLE IF NOT EXISTS fact_benchmark_indices (
    idx_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    date_id     TEXT    NOT NULL REFERENCES dim_date(date_id),
    index_name  TEXT    NOT NULL,
    close_value REAL    NOT NULL,
    UNIQUE (date_id, index_name)
);

CREATE INDEX IF NOT EXISTS idx_nav_date      ON fact_nav(date_id);
CREATE INDEX IF NOT EXISTS idx_nav_fund      ON fact_nav(amfi_code);
CREATE INDEX IF NOT EXISTS idx_txn_date      ON fact_transactions(date_id);
CREATE INDEX IF NOT EXISTS idx_txn_fund      ON fact_transactions(amfi_code);
CREATE INDEX IF NOT EXISTS idx_txn_type      ON fact_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_txn_state     ON fact_transactions(state);
CREATE INDEX IF NOT EXISTS idx_aum_date      ON fact_aum(date_id);
CREATE INDEX IF NOT EXISTS idx_bench_date    ON fact_benchmark_indices(date_id);
CREATE INDEX IF NOT EXISTS idx_bench_name    ON fact_benchmark_indices(index_name);
CREATE INDEX IF NOT EXISTS idx_holdings_fund ON fact_portfolio_holdings(amfi_code);