-- Q1: Top 5 funds by AUM (from fact_performance)
-- Business: Identify the largest schemes by assets under management.
SELECT
    f.fund_house,
    f.scheme_name,
    f.category,
    f.plan,
    p.aum_crore,
    p.morningstar_rating,
    p.return_3yr_pct
FROM fact_performance p
JOIN dim_fund f USING (amfi_code)
ORDER BY p.aum_crore DESC
LIMIT 5;


-- Q2: Average NAV per month (across all Large Cap Direct funds)
-- Business: Track monthly average price level for the Large Cap Direct universe.
SELECT
    d.year,
    d.month,
    d.month_name,
    ROUND(AVG(n.nav), 2)            AS avg_nav,
    ROUND(MIN(n.nav), 2)            AS min_nav,
    ROUND(MAX(n.nav), 2)            AS max_nav,
    COUNT(DISTINCT n.amfi_code)     AS num_funds
FROM fact_nav n
JOIN dim_date d ON n.date_id = d.date_id
JOIN dim_fund f ON n.amfi_code = f.amfi_code
WHERE f.sub_category = 'Large Cap'
  AND f.plan = 'Direct'
  AND d.is_weekend = 0
GROUP BY d.year, d.month
ORDER BY d.year, d.month;


-- Q3: SIP inflow YoY growth (monthly)
-- Business: Measure the year-on-year growth rate of SIP inflows.
SELECT
    d.year,
    d.month_name,
    s.sip_inflow_crore,
    s.active_sip_accounts_crore,
    ROUND(s.yoy_growth_pct, 2)      AS yoy_growth_pct,
    s.sip_aum_lakh_crore
FROM fact_sip_inflows s
JOIN dim_date d ON s.date_id = d.date_id
ORDER BY d.year, d.month;


-- Q4: Transactions by state - total invested, unique investors
-- Business: Geographical distribution of mutual fund investments.
SELECT
    state,
    COUNT(*)                        AS total_transactions,
    COUNT(DISTINCT investor_id)     AS unique_investors,
    SUM(amount_inr)                 AS total_invested_inr,
    ROUND(AVG(amount_inr), 0)       AS avg_transaction_inr,
    SUM(CASE WHEN transaction_type = 'SIP'        THEN 1 ELSE 0 END) AS sip_count,
    SUM(CASE WHEN transaction_type = 'Lumpsum'    THEN 1 ELSE 0 END) AS lumpsum_count,
    SUM(CASE WHEN transaction_type = 'Redemption' THEN 1 ELSE 0 END) AS redemption_count
FROM fact_transactions
GROUP BY state
ORDER BY total_invested_inr DESC;


-- Q5: Funds with expense_ratio < 1% (low-cost options)
-- Business: Identify cost-efficient funds for investor recommendations.
SELECT
    f.fund_house,
    f.scheme_name,
    f.sub_category,
    f.plan,
    p.expense_ratio_pct,
    p.return_3yr_pct,
    p.sharpe_ratio,
    p.morningstar_rating
FROM fact_performance p
JOIN dim_fund f USING (amfi_code)
WHERE p.expense_ratio_pct < 1.0
ORDER BY p.expense_ratio_pct ASC;


-- Q6: NAV growth (%) for each fund - start to latest date
-- Business: Absolute NAV appreciation since dataset start.
WITH first_nav AS (
    SELECT amfi_code, nav AS nav_start
    FROM fact_nav
    WHERE date_id = (SELECT MIN(date_id) FROM fact_nav)
),
last_nav AS (
    SELECT amfi_code, nav AS nav_end
    FROM fact_nav
    WHERE date_id = (SELECT MAX(date_id) FROM fact_nav)
)
SELECT
    f.fund_house,
    f.scheme_name,
    f.sub_category,
    ROUND(fn.nav_start, 2)                                          AS nav_start,
    ROUND(ln.nav_end,   2)                                          AS nav_end,
    ROUND((ln.nav_end - fn.nav_start) / fn.nav_start * 100, 2)     AS growth_pct
FROM first_nav fn
JOIN last_nav  ln USING (amfi_code)
JOIN dim_fund   f USING (amfi_code)
ORDER BY growth_pct DESC;


-- Q7: Alpha vs Benchmark - funds that beat the index
-- Business: Identify active funds generating positive alpha.
SELECT
    f.fund_house,
    f.scheme_name,
    f.plan,
    p.return_3yr_pct,
    p.benchmark_3yr_pct,
    ROUND(p.return_3yr_pct - p.benchmark_3yr_pct, 2)   AS excess_return_pct,
    p.alpha,
    p.beta,
    p.sharpe_ratio,
    p.morningstar_rating
FROM fact_performance p
JOIN dim_fund f USING (amfi_code)
WHERE f.category = 'Equity'
ORDER BY excess_return_pct DESC;


-- Q8: Monthly net inflows by category (2024)
-- Business: Understand where investor money is flowing by fund category.
SELECT
    d.month_name,
    ci.category,
    ROUND(ci.net_inflow_crore, 0)   AS net_inflow_crore
FROM fact_category_inflows ci
JOIN dim_date d ON ci.date_id = d.date_id
WHERE d.year = 2024
ORDER BY d.month, net_inflow_crore DESC;


-- Q9: Investor profile - age group vs transaction type
-- Business: Understand demographic preferences for SIP vs Lumpsum.
SELECT
    age_group,
    transaction_type,
    COUNT(*)                            AS txn_count,
    SUM(amount_inr)                     AS total_amount_inr,
    ROUND(AVG(amount_inr), 0)           AS avg_amount_inr,
    ROUND(AVG(annual_income_lakh), 1)   AS avg_annual_income_lakh
FROM fact_transactions
GROUP BY age_group, transaction_type
ORDER BY age_group, transaction_type;


-- Q10: Top 10 stocks held across all schemes by total market value
-- Business: Identify the most widely held stocks in the MF universe.
SELECT
    ph.stock_symbol,
    ph.stock_name,
    ph.sector,
    COUNT(DISTINCT ph.amfi_code)        AS num_funds_holding,
    ROUND(SUM(ph.weight_pct), 2)        AS total_weight_pct,
    ROUND(AVG(ph.weight_pct), 2)        AS avg_weight_pct,
    ROUND(SUM(ph.market_value_cr), 2)   AS total_market_value_cr
FROM fact_portfolio_holdings ph
GROUP BY ph.stock_symbol, ph.stock_name, ph.sector
ORDER BY total_market_value_cr DESC
LIMIT 10;