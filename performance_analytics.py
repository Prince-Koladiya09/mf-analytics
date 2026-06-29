

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
from scipy import stats
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────
BASE   = Path(__file__).resolve().parent
PROC   = BASE / "data" / "processed"
CHARTS = BASE / "reports" / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

RF_ANNUAL = 0.065          # Risk-free rate: RBI repo rate proxy 6.5%
RF_DAILY  = RF_ANNUAL / 252
DIVIDER   = "=" * 65

sns.set_theme(style="darkgrid", font_scale=1.05)

# ── Load data ─────────────────────────────────────────────────────────
print(f"\n{'█'*65}")
print("  DAY 4: PERFORMANCE ANALYTICS")
print(f"{'█'*65}\n")

nav   = pd.read_csv(PROC / "02_nav_history_clean.csv",  parse_dates=["date"])
fund  = pd.read_csv(PROC / "01_fund_master_clean.csv",  parse_dates=["launch_date"])
bench = pd.read_csv(PROC / "10_benchmark_indices_clean.csv", parse_dates=["date"])
perf_raw = pd.read_csv(PROC / "07_scheme_performance_clean.csv")

# NAV wide pivot (date × amfi_code)
nav_wide = nav.pivot(index="date", columns="amfi_code", values="nav").sort_index()

# Benchmark pivots
bench_wide = bench.pivot(index="date", columns="index_name", values="close_value").sort_index()
nifty50  = bench_wide["NIFTY50"].dropna()
nifty100 = bench_wide["NIFTY100"].dropna()

print(f"NAV matrix  : {nav_wide.shape[0]} days × {nav_wide.shape[1]} funds")
print(f"Benchmark   : {bench_wide.shape[0]} days, indices: {bench_wide.columns.tolist()}\n")


# ═══════════════════════════════════════════════════════════════════════
# 1. DAILY RETURNS
# ═══════════════════════════════════════════════════════════════════════
print(f"{DIVIDER}\n  STEP 1: Daily Returns\n{DIVIDER}")

returns = nav_wide.pct_change().dropna(how="all")

# Validation
desc = returns.stack().describe()
print(f"Return distribution (all funds, all days):")
print(f"  Count : {desc['count']:,.0f}")
print(f"  Mean  : {desc['mean']*100:.4f}%")
print(f"  Std   : {desc['std']*100:.4f}%")
print(f"  Min   : {desc['min']*100:.3f}%")
print(f"  Max   : {desc['max']*100:.3f}%")

# Flag extreme returns (>10% or <-10% in a single day)
extreme = (returns.abs() > 0.10).sum().sum()
print(f"  Extreme days (abs > 10%): {extreme}")
print("   Distribution looks reasonable — mean near 0, fat tails expected\n")

# Save daily returns
returns.to_csv(PROC / "daily_returns.csv")
print("   Saved → data/processed/daily_returns.csv")


# ═══════════════════════════════════════════════════════════════════════
# 2. CAGR TABLE
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{DIVIDER}\n  STEP 2: CAGR Computation\n{DIVIDER}")

def cagr(nav_series, years):
    """CAGR = (NAV_end / NAV_start)^(1/n) - 1"""
    end_date   = nav_series.dropna().index.max()
    start_date = end_date - pd.DateOffset(years=years)
    series     = nav_series.dropna()
    # Find closest available dates
    avail = series.index
    start_idx = avail.searchsorted(start_date)
    if start_idx >= len(avail):
        return np.nan
    nav_start = series.iloc[start_idx]
    nav_end   = series.iloc[-1]
    if nav_start <= 0:
        return np.nan
    return (nav_end / nav_start) ** (1 / years) - 1

cagr_rows = []
for code in nav_wide.columns:
    s = nav_wide[code].dropna()
    row = {"amfi_code": code}
    for yr in [1, 3, 5]:
        row[f"cagr_{yr}yr_pct"] = round(cagr(s, yr) * 100, 2)
    cagr_rows.append(row)

cagr_df = pd.DataFrame(cagr_rows).merge(
    fund[["amfi_code","scheme_name","fund_house","sub_category","plan","expense_ratio_pct"]],
    on="amfi_code", how="left"
)

print("CAGR Comparison Table (top 10 by 3yr CAGR):")
top_cagr = cagr_df.sort_values("cagr_3yr_pct", ascending=False)
display_cols = ["scheme_name","plan","cagr_1yr_pct","cagr_3yr_pct","cagr_5yr_pct"]
print(top_cagr[display_cols].head(10).to_string(index=False))
cagr_df.to_csv(PROC / "cagr_table.csv", index=False)
print("\n   Saved → data/processed/cagr_table.csv")


# ═══════════════════════════════════════════════════════════════════════
# 3. SHARPE RATIO
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{DIVIDER}\n  STEP 3: Sharpe Ratio\n{DIVIDER}")

def sharpe(ret_series):
    """(Rp - Rf) / Std(Rp) * sqrt(252)"""
    excess = ret_series.dropna() - RF_DAILY
    if excess.std() == 0:
        return np.nan
    return (excess.mean() / excess.std()) * np.sqrt(252)

sharpe_scores = {code: sharpe(returns[code]) for code in returns.columns}
sharpe_series = pd.Series(sharpe_scores, name="sharpe_ratio").sort_values(ascending=False)

print("Sharpe Ratio Ranking (top 10):")
for rank, (code, val) in enumerate(sharpe_series.head(10).items(), 1):
    name = fund.loc[fund["amfi_code"] == code, "scheme_name"].values
    name = name[0][:40] if len(name) else str(code)
    print(f"  {rank:>2}. {name:<42} {val:.4f}")


# ═══════════════════════════════════════════════════════════════════════
# 4. SORTINO RATIO
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{DIVIDER}\n  STEP 4: Sortino Ratio\n{DIVIDER}")

def sortino(ret_series):
    """(Rp - Rf) / Downside_Std * sqrt(252)"""
    r = ret_series.dropna()
    excess   = r - RF_DAILY
    downside = r[r < RF_DAILY] - RF_DAILY
    if len(downside) < 2 or downside.std() == 0:
        return np.nan
    return (excess.mean() / downside.std()) * np.sqrt(252)

sortino_scores = {code: sortino(returns[code]) for code in returns.columns}
sortino_series = pd.Series(sortino_scores, name="sortino_ratio").sort_values(ascending=False)

print("Sortino Ratio Ranking (top 10):")
for rank, (code, val) in enumerate(sortino_series.head(10).items(), 1):
    name = fund.loc[fund["amfi_code"] == code, "scheme_name"].values
    name = name[0][:40] if len(name) else str(code)
    print(f"  {rank:>2}. {name:<42} {val:.4f}")


# ═══════════════════════════════════════════════════════════════════════
# 5. ALPHA AND BETA (OLS regression vs Nifty 100)
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{DIVIDER}\n  STEP 5: Alpha & Beta (vs Nifty 100)\n{DIVIDER}")

# Nifty 100 daily returns
bench_ret = nifty100.pct_change().dropna()

ab_rows = []
for code in returns.columns:
    fund_ret = returns[code].dropna()
    # Align on common dates
    common = fund_ret.index.intersection(bench_ret.index)
    if len(common) < 60:
        ab_rows.append({"amfi_code": code, "alpha_annual": np.nan,
                        "beta": np.nan, "r_squared": np.nan})
        continue
    y = fund_ret.loc[common].values
    x = bench_ret.loc[common].values
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    ab_rows.append({
        "amfi_code"    : code,
        "alpha_annual" : round(intercept * 252 * 100, 4),  # annualised %
        "beta"         : round(slope, 4),
        "r_squared"    : round(r_value ** 2, 4),
        "p_value"      : round(p_value, 4),
        "intercept_daily": round(intercept * 100, 6),
    })

ab_df = pd.DataFrame(ab_rows).merge(
    fund[["amfi_code","scheme_name","fund_house","sub_category","plan"]],
    on="amfi_code", how="left"
)

print("Alpha & Beta Table (sorted by Alpha):")
print(ab_df[["scheme_name","plan","alpha_annual","beta","r_squared"]]
      .sort_values("alpha_annual", ascending=False)
      .head(10).to_string(index=False))

ab_df.to_csv(PROC / "alpha_beta.csv", index=False)
print("\n   Saved → data/processed/alpha_beta.csv")


# ═══════════════════════════════════════════════════════════════════════
# 6. MAXIMUM DRAWDOWN
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{DIVIDER}\n  STEP 6: Maximum Drawdown\n{DIVIDER}")

def max_drawdown(nav_series):
    """min(NAV / running_max - 1)"""
    s = nav_series.dropna()
    if len(s) < 2:
        return np.nan, None, None
    running_max = s.cummax()
    drawdown    = s / running_max - 1
    mdd_val     = drawdown.min()
    mdd_date    = drawdown.idxmin()
    # Peak before the drawdown
    peak_date   = s.loc[:mdd_date].idxmax()
    return mdd_val, peak_date, mdd_date

mdd_rows = []
for code in nav_wide.columns:
    mdd_val, peak_dt, trough_dt = max_drawdown(nav_wide[code])
    mdd_rows.append({
        "amfi_code"   : code,
        "max_drawdown_pct": round(mdd_val * 100, 2) if not np.isnan(mdd_val) else np.nan,
        "peak_date"   : str(peak_dt.date()) if peak_dt else None,
        "trough_date" : str(trough_dt.date()) if trough_dt else None,
        "days_to_trough": (trough_dt - peak_dt).days if (peak_dt and trough_dt) else None,
    })

mdd_df = pd.DataFrame(mdd_rows).merge(
    fund[["amfi_code","scheme_name","plan","sub_category"]],
    on="amfi_code", how="left"
)

print("Worst Drawdowns (top 10 worst):")
print(mdd_df[["scheme_name","plan","max_drawdown_pct","peak_date","trough_date","days_to_trough"]]
      .sort_values("max_drawdown_pct").head(10).to_string(index=False))


# ═══════════════════════════════════════════════════════════════════════
# 7. FUND SCORECARD (0–100)
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{DIVIDER}\n  STEP 7: Fund Scorecard (0-100)\n{DIVIDER}")

# Build master metrics table
metrics = (cagr_df[["amfi_code","scheme_name","fund_house","plan",
                     "sub_category","expense_ratio_pct","cagr_3yr_pct"]]
           .copy())
metrics["sharpe_ratio"]    = metrics["amfi_code"].map(sharpe_scores)
metrics["sortino_ratio"]   = metrics["amfi_code"].map(sortino_scores)
metrics["alpha_annual"]    = metrics["amfi_code"].map(ab_df.set_index("amfi_code")["alpha_annual"])
metrics["max_drawdown_pct"]= metrics["amfi_code"].map(mdd_df.set_index("amfi_code")["max_drawdown_pct"])
metrics = metrics.dropna(subset=["cagr_3yr_pct","sharpe_ratio","alpha_annual","max_drawdown_pct"])

def percentile_rank(series, ascending=True):
    """Rank 0–100; ascending=True means higher value = higher score."""
    ranked = series.rank(ascending=ascending, method="min")
    return ((ranked - 1) / (len(ranked) - 1) * 100).round(2)

metrics["rank_3yr_return"]  = percentile_rank(metrics["cagr_3yr_pct"],     ascending=True)
metrics["rank_sharpe"]      = percentile_rank(metrics["sharpe_ratio"],      ascending=True)
metrics["rank_alpha"]       = percentile_rank(metrics["alpha_annual"],      ascending=True)
metrics["rank_expense"]     = percentile_rank(metrics["expense_ratio_pct"], ascending=False)  # lower = better
metrics["rank_mdd"]         = percentile_rank(metrics["max_drawdown_pct"],  ascending=False)  # less negative = better

# Composite score
metrics["scorecard"] = (
    0.30 * metrics["rank_3yr_return"] +
    0.25 * metrics["rank_sharpe"]     +
    0.20 * metrics["rank_alpha"]      +
    0.15 * metrics["rank_expense"]    +
    0.10 * metrics["rank_mdd"]
).round(2)

scorecard = metrics.sort_values("scorecard", ascending=False).reset_index(drop=True)
scorecard.index += 1  # rank from 1

print("Fund Scorecard — Top 15:")
display_cols = ["scheme_name","plan","scorecard","cagr_3yr_pct",
                "sharpe_ratio","alpha_annual","expense_ratio_pct","max_drawdown_pct"]
print(scorecard[display_cols].head(15).to_string())

scorecard_out = scorecard.copy()
scorecard_out.index.name = "rank"
scorecard_out.to_csv(PROC / "fund_scorecard.csv")
print("\n   Saved → data/processed/fund_scorecard.csv")


# ═══════════════════════════════════════════════════════════════════════
# 8. BENCHMARK COMPARISON CHART + TRACKING ERROR
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{DIVIDER}\n  STEP 8: Benchmark Comparison Chart\n{DIVIDER}")

# Top 5 funds by scorecard
top5_codes = scorecard.head(5)["amfi_code"].tolist()
top5_names = scorecard.head(5)["scheme_name"].str[:30].tolist()

# 3-year window
start_3yr = nav_wide.index.max() - pd.DateOffset(years=3)
nav_3yr   = nav_wide.loc[start_3yr:, top5_codes].dropna(how="all")
n50_3yr   = nifty50.loc[start_3yr:].dropna()
n100_3yr  = nifty100.loc[start_3yr:].dropna()

# Rebase to 100
def rebase(series):
    return series / series.dropna().iloc[0] * 100

fig, axes = plt.subplots(2, 1, figsize=(14, 12),
                          gridspec_kw={"height_ratios": [3, 1.2]})

# ── Top panel: rebased NAV ────────────────────────────────────────────
colors = ["#00BFFF","#7FBA00","#FF6B6B","#FFD700","#C084FC"]
for i, (code, name) in enumerate(zip(top5_codes, top5_names)):
    s = rebase(nav_3yr[code].dropna())
    axes[0].plot(s.index, s.values, color=colors[i], linewidth=2,
                 label=f"{name} (Fund)", zorder=3)

axes[0].plot(rebase(n50_3yr).index,  rebase(n50_3yr).values,
             color="white", linewidth=2.5, linestyle="--", label="Nifty 50",  zorder=4)
axes[0].plot(rebase(n100_3yr).index, rebase(n100_3yr).values,
             color="silver", linewidth=2.5, linestyle=":",  label="Nifty 100", zorder=4)

axes[0].set_title("Top 5 Funds vs Nifty 50 & Nifty 100 (3-Year, Rebased to 100)",
                   fontsize=14, fontweight="bold", pad=12)
axes[0].set_ylabel("Index (Base = 100)")
axes[0].legend(fontsize=9, loc="upper left")
axes[0].yaxis.set_major_formatter(mtick.FormatStrFormatter("%.0f"))
axes[0].grid(True, alpha=0.3)

# ── Tracking error table ──────────────────────────────────────────────
te_rows = []
bench_ret_3yr = n100_3yr.pct_change().dropna()

for code, name in zip(top5_codes, top5_names):
    fund_ret_3yr = nav_3yr[code].pct_change().dropna()
    common = fund_ret_3yr.index.intersection(bench_ret_3yr.index)
    if len(common) < 30:
        te_rows.append({"Fund": name[:28], "Tracking Error %": np.nan,
                        "Excess Return %": np.nan})
        continue
    diff = fund_ret_3yr.loc[common] - bench_ret_3yr.loc[common]
    te   = diff.std() * np.sqrt(252) * 100
    xret = diff.mean() * 252 * 100
    te_rows.append({"Fund": name[:28], "Tracking Error %": round(te, 2),
                    "Excess Return % (ann)": round(xret, 2)})

te_df = pd.DataFrame(te_rows)
print("\nTracking Error vs Nifty 100 (annualised):")
print(te_df.to_string(index=False))

# ── Bottom panel: tracking error bar ─────────────────────────────────
axes[1].bar(te_df["Fund"], te_df["Tracking Error %"],
            color=colors[:len(te_df)], edgecolor="white", linewidth=1.5)
axes[1].axhline(y=te_df["Tracking Error %"].mean(), color="gold",
                linestyle="--", linewidth=1.5, label="Average TE")
axes[1].set_title("Tracking Error vs Nifty 100 (Annualised %)",
                   fontsize=12, fontweight="bold")
axes[1].set_ylabel("Tracking Error (%)")
axes[1].set_xticklabels(te_df["Fund"], rotation=20, ha="right", fontsize=9)
axes[1].legend(fontsize=9)
axes[1].grid(True, alpha=0.3, axis="y")
for bar_p, val in zip(axes[1].patches, te_df["Tracking Error %"]):
    if not np.isnan(val):
        axes[1].text(bar_p.get_x() + bar_p.get_width()/2,
                     bar_p.get_height() + 0.1, f"{val:.2f}%",
                     ha="center", va="bottom", fontsize=9)

plt.tight_layout(pad=2.5)
fig.patch.set_facecolor("#1a1a2e")
for ax in axes:
    ax.set_facecolor("#16213e")
    ax.tick_params(colors="white")
    ax.yaxis.label.set_color("white")
    ax.title.set_color("white")
    ax.xaxis.label.set_color("white")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444")

out_path = CHARTS / "16_benchmark_comparison.png"
fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"\n   Saved → reports/charts/16_benchmark_comparison.png")


# ═══════════════════════════════════════════════════════════════════════
# BONUS: Scorecard Bar Chart
# ═══════════════════════════════════════════════════════════════════════
print("\n  Generating scorecard chart...")

fig2, ax = plt.subplots(figsize=(13, 9))
top15 = scorecard.head(15).copy()
top15["label"] = top15["scheme_name"].str[:30] + " (" + top15["plan"].str[0] + ")"

bar_colors = plt.cm.RdYlGn(np.linspace(0.4, 0.9, len(top15)))[::-1]
bars = ax.barh(range(len(top15)), top15["scorecard"].values,
               color=bar_colors, edgecolor="white", linewidth=0.8)
ax.set_yticks(range(len(top15)))
ax.set_yticklabels(top15["label"].values, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("Composite Score (0–100)", fontsize=11)
ax.set_title("Fund Scorecard Rankings (Top 15)\n"
             "30% 3yr CAGR | 25% Sharpe | 20% Alpha | 15% Expense | 10% Max DD",
             fontsize=12, fontweight="bold", pad=10)
ax.axvline(50, color="gold", linestyle="--", alpha=0.7, label="Score = 50")
for bar_p, val in zip(bars, top15["scorecard"]):
    ax.text(bar_p.get_width() + 0.5, bar_p.get_y() + bar_p.get_height()/2,
            f"{val:.1f}", va="center", fontsize=9)
ax.legend(fontsize=9)
ax.set_xlim(0, 110)
plt.tight_layout()
fig2.savefig(CHARTS / "17_fund_scorecard.png", dpi=150, bbox_inches="tight")
plt.close()
print("   Saved → reports/charts/17_fund_scorecard.png")


# ═══════════════════════════════════════════════════════════════════════
# BONUS: Alpha vs Beta Scatter
# ═══════════════════════════════════════════════════════════════════════
print("  Generating alpha-beta scatter...")

ab_plot = ab_df.dropna(subset=["alpha_annual","beta"])
fig3, ax = plt.subplots(figsize=(12, 8))
sc = ax.scatter(ab_plot["beta"], ab_plot["alpha_annual"],
                c=ab_plot["alpha_annual"], cmap="RdYlGn",
                s=120, edgecolors="white", linewidth=0.8, zorder=3)
plt.colorbar(sc, ax=ax, label="Alpha (Annual %)")
ax.axhline(0, color="white", linestyle="--", linewidth=1, alpha=0.6, label="Alpha = 0")
ax.axvline(1, color="gold",  linestyle="--", linewidth=1, alpha=0.6, label="Beta = 1 (market)")
for _, row in ab_plot.iterrows():
    label = str(row["scheme_name"])[:18]
    ax.annotate(label, (row["beta"], row["alpha_annual"]),
                fontsize=7, alpha=0.8,
                xytext=(4, 4), textcoords="offset points")
ax.set_xlabel("Beta (Sensitivity to Nifty 100)", fontsize=11)
ax.set_ylabel("Annualised Alpha (%)", fontsize=11)
ax.set_title("Alpha vs Beta — All Funds (vs Nifty 100)", fontsize=13, fontweight="bold")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)
plt.tight_layout()
fig3.savefig(CHARTS / "18_alpha_beta_scatter.png", dpi=150, bbox_inches="tight")
plt.close()
print("   Saved → reports/charts/18_alpha_beta_scatter.png")


# ═══════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{DIVIDER}")
print("  PERFORMANCE ANALYTICS SUMMARY")
print(DIVIDER)
print(f"  Funds analysed          : {len(scorecard)}")
print(f"  Date range              : {nav_wide.index.min().date()} → {nav_wide.index.max().date()}")
print(f"  Risk-free rate (Rf)     : {RF_ANNUAL*100:.1f}% (RBI repo rate proxy)")
print(f"\n  Top Fund Overall        : {scorecard.iloc[0]['scheme_name'][:45]}")
print(f"  Score                   : {scorecard.iloc[0]['scorecard']:.1f}/100")
print(f"  3yr CAGR                : {scorecard.iloc[0]['cagr_3yr_pct']:.2f}%")
print(f"  Sharpe                  : {scorecard.iloc[0]['sharpe_ratio']:.4f}")
print(f"  Alpha (annual)          : {scorecard.iloc[0]['alpha_annual']:.4f}%")
print(f"  Max Drawdown            : {scorecard.iloc[0]['max_drawdown_pct']:.2f}%")
print(f"\n  CSVs exported:")
print(f"    data/processed/daily_returns.csv")
print(f"    data/processed/cagr_table.csv")
print(f"    data/processed/alpha_beta.csv")
print(f"    data/processed/fund_scorecard.csv")
print(f"\n  Charts exported:")
print(f"    reports/charts/16_benchmark_comparison.png")
print(f"    reports/charts/17_fund_scorecard.png")
print(f"    reports/charts/18_alpha_beta_scatter.png")
print(f"\n performance_analytics.py complete.\n")