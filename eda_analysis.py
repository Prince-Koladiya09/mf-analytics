import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────
BASE   = Path(__file__).resolve().parent
PROC   = BASE / "data" / "processed"
CHARTS = BASE / "reports" / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

# ── Style ─────────────────────────────────────────────────────────────
sns.set_theme(style="darkgrid", palette="muted", font_scale=1.1)
PLOTLY_TEMPLATE = "plotly_dark"
COLORS = px.colors.qualitative.Set2

print("Loading data...")

# ── Load all datasets ─────────────────────────────────────────────────
nav     = pd.read_csv(PROC / "02_nav_history_clean.csv",         parse_dates=["date"])
fund    = pd.read_csv(PROC / "01_fund_master_clean.csv",         parse_dates=["launch_date"])
aum     = pd.read_csv(PROC / "03_aum_by_fund_house_clean.csv",   parse_dates=["date"])
sip     = pd.read_csv(PROC / "04_monthly_sip_inflows_clean.csv", parse_dates=["month"])
cat     = pd.read_csv(PROC / "05_category_inflows_clean.csv",    parse_dates=["month"])
folio   = pd.read_csv(PROC / "06_industry_folio_count_clean.csv",parse_dates=["month"])
perf    = pd.read_csv(PROC / "07_scheme_performance_clean.csv")
txn     = pd.read_csv(PROC / "08_investor_transactions_clean.csv",parse_dates=["transaction_date"])
hold    = pd.read_csv(PROC / "09_portfolio_holdings_clean.csv")

# merge nav with fund master for scheme names
nav_m = nav.merge(fund[["amfi_code","scheme_name","fund_house","sub_category","plan"]], on="amfi_code", how="left")

print(" Data loaded. Generating charts...\n")

# ═══════════════════════════════════════════════════════════════════════
# CHART 1 — NAV Trend: all 40 schemes 2022–2026 (Plotly)
# ═══════════════════════════════════════════════════════════════════════
print("Chart 1: NAV trend analysis...")

# Use direct plans only to reduce clutter (20 lines instead of 40)
direct = fund[fund["plan"] == "Direct"]["amfi_code"].tolist()
nav_d  = nav_m[nav_m["amfi_code"].isin(direct)].copy()

fig = go.Figure()
for code, grp in nav_d.groupby("amfi_code"):
    name = grp["scheme_name"].iloc[0][:35]
    fig.add_trace(go.Scatter(
        x=grp["date"], y=grp["nav"],
        mode="lines", name=name,
        line=dict(width=1.2),
        hovertemplate=f"<b>{name}</b><br>Date: %{{x|%d %b %Y}}<br>NAV: ₹%{{y:.2f}}<extra></extra>"
    ))

# Highlight 2023 bull run
fig.add_vrect(x0="2023-03-01", x1="2023-12-31",
              fillcolor="rgba(0,255,100,0.07)", line_width=0,
              annotation_text="2023 Bull Run", annotation_position="top left",
              annotation=dict(font_size=11, font_color="lightgreen"))

# Highlight 2024 correction
fig.add_vrect(x0="2024-06-01", x1="2024-10-31",
              fillcolor="rgba(255,80,80,0.07)", line_width=0,
              annotation_text="2024 Correction", annotation_position="top left",
              annotation=dict(font_size=11, font_color="salmon"))

fig.update_layout(
    title=dict(text="Daily NAV Trend — All Direct Funds (2022–2026)", font_size=18),
    xaxis_title="Date", yaxis_title="NAV (₹)",
    template=PLOTLY_TEMPLATE, height=550,
    legend=dict(font_size=8, x=1.01, y=1),
    hovermode="x unified"
)
fig.write_image(str(CHARTS / "01_nav_trend.png"), width=1400, height=550, scale=1.5)
print(" 01_nav_trend.png")


# ═══════════════════════════════════════════════════════════════════════
# CHART 2 — AUM Growth Grouped Bar by Fund House (Seaborn)
# ═══════════════════════════════════════════════════════════════════════
print("Chart 2: AUM growth bar chart...")

aum["year"] = aum["date"].dt.year
aum_annual  = aum.groupby(["fund_house","year"])["aum_lakh_crore"].mean().reset_index()
top_fh      = aum_annual.groupby("fund_house")["aum_lakh_crore"].mean().nlargest(8).index
aum_top     = aum_annual[aum_annual["fund_house"].isin(top_fh)]

fig2, ax = plt.subplots(figsize=(14, 7))
bar_data = aum_top.pivot(index="fund_house", columns="year", values="aum_lakh_crore").fillna(0)
bar_data.plot(kind="bar", ax=ax, width=0.75,
              color=["#4C72B0","#55A868","#C44E52","#8172B2"])

# Highlight SBI bar
for patch in ax.patches:
    if patch.get_height() > 10:
        patch.set_edgecolor("gold")
        patch.set_linewidth(2.5)

ax.set_title("AUM by Fund House per Year (Top 8 AMCs)", fontsize=16, fontweight="bold", pad=15)
ax.set_xlabel("Fund House", fontsize=12)
ax.set_ylabel("AUM (₹ Lakh Crore)", fontsize=12)
ax.set_xticklabels([l.get_text().replace(" Mutual Fund","").replace(" Asset Management","")
                    for l in ax.get_xticklabels()], rotation=30, ha="right")
ax.legend(title="Year", fontsize=10)
ax.annotate("SBI dominance\n₹12.5L Cr (2025)",
            xy=(0, bar_data.loc["SBI Mutual Fund"].max() if "SBI Mutual Fund" in bar_data.index else 12),
            xytext=(0.5, 13), fontsize=10, color="gold",
            arrowprops=dict(arrowstyle="->", color="gold"))
plt.tight_layout()
fig2.savefig(CHARTS / "02_aum_growth.png", dpi=150, bbox_inches="tight")
plt.close()
print("    02_aum_growth.png")


# ═══════════════════════════════════════════════════════════════════════
# CHART 3 — SIP Inflow Time-Series with Annotation (Plotly)
# ═══════════════════════════════════════════════════════════════════════
print("Chart 3: SIP inflow time-series...")

fig3 = go.Figure()
fig3.add_trace(go.Scatter(
    x=sip["month"], y=sip["sip_inflow_crore"],
    mode="lines+markers",
    line=dict(color="#00BFFF", width=2.5),
    marker=dict(size=5),
    fill="tozeroy", fillcolor="rgba(0,191,255,0.12)",
    name="SIP Inflow",
    hovertemplate="<b>%{x|%b %Y}</b><br>Inflow: ₹%{y:,} Cr<extra></extra>"
))

# Annotate all-time high
ath_row = sip.loc[sip["sip_inflow_crore"].idxmax()]
fig3.add_annotation(
    x=ath_row["month"], y=ath_row["sip_inflow_crore"],
    text=f"<b>ATH ₹{ath_row['sip_inflow_crore']:,} Cr</b><br>{ath_row['month'].strftime('%b %Y')}",
    showarrow=True, arrowhead=2, arrowcolor="gold",
    font=dict(color="gold", size=12),
    bgcolor="rgba(0,0,0,0.6)", bordercolor="gold", borderwidth=1,
    ax=60, ay=-50
)

# Add YoY growth on secondary axis
fig3.add_trace(go.Bar(
    x=sip["month"], y=sip["yoy_growth_pct"],
    name="YoY Growth %", yaxis="y2",
    marker_color="rgba(255,165,0,0.35)",
    hovertemplate="YoY: %{y:.1f}%<extra></extra>"
))

fig3.update_layout(
    title=dict(text="Monthly SIP Inflows (Jan 2022 – Dec 2025)", font_size=18),
    xaxis_title="Month", yaxis_title="SIP Inflow (₹ Crore)",
    yaxis2=dict(title="YoY Growth (%)", overlaying="y", side="right", showgrid=False),
    template=PLOTLY_TEMPLATE, height=500,
    legend=dict(x=0.01, y=0.99),
    hovermode="x unified"
)
fig3.write_image(str(CHARTS / "03_sip_inflows.png"), width=1400, height=500, scale=1.5)
print("    03_sip_inflows.png")


# ═══════════════════════════════════════════════════════════════════════
# CHART 4 — Category Inflow Heatmap (Seaborn)
# ═══════════════════════════════════════════════════════════════════════
print("Chart 4: Category inflow heatmap...")

cat["month_label"] = cat["month"].dt.strftime("%b %Y")
cat["month_num"]   = cat["month"].dt.to_period("M")
pivot = cat.pivot_table(index="category", columns="month_label",
                        values="net_inflow_crore", aggfunc="sum")
# Sort columns chronologically
ordered_cols = cat.sort_values("month")[["month_label"]].drop_duplicates()["month_label"].tolist()
pivot = pivot.reindex(columns=[c for c in ordered_cols if c in pivot.columns])

fig4, ax = plt.subplots(figsize=(18, 6))
sns.heatmap(pivot, ax=ax, cmap="RdYlGn", center=0,
            linewidths=0.3, linecolor="gray",
            cbar_kws={"label": "Net Inflow (₹ Crore)", "shrink": 0.8},
            fmt=".0f", annot=False)
ax.set_title("Category Net Inflow Heatmap (Monthly)", fontsize=15, fontweight="bold", pad=12)
ax.set_xlabel("Month", fontsize=11)
ax.set_ylabel("Fund Category", fontsize=11)
ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=9)
plt.tight_layout()
fig4.savefig(CHARTS / "04_category_heatmap.png", dpi=150, bbox_inches="tight")
plt.close()
print("    04_category_heatmap.png")


# ═══════════════════════════════════════════════════════════════════════
# CHART 5a — Investor Demographics: Age Group Pie
# CHART 5b — SIP Amount Box Plot by Age Group
# CHART 5c — Gender Split
# ═══════════════════════════════════════════════════════════════════════
print("Chart 5: Investor demographics...")

fig5, axes = plt.subplots(1, 3, figsize=(18, 6))

# 5a — Age pie
age_counts = txn["age_group"].value_counts()
axes[0].pie(age_counts, labels=age_counts.index, autopct="%1.1f%%",
            colors=sns.color_palette("Set2", len(age_counts)),
            startangle=140, pctdistance=0.8,
            wedgeprops=dict(linewidth=1.5, edgecolor="white"))
axes[0].set_title("Investor Age Group Distribution", fontsize=13, fontweight="bold")

# 5b — Box plot SIP amount by age
sip_txn = txn[txn["transaction_type"] == "SIP"]
age_order = sorted(txn["age_group"].dropna().unique())
sns.boxplot(data=sip_txn, x="age_group", y="amount_inr",
            order=age_order, palette="Set2", ax=axes[1],
            showfliers=False, linewidth=1.5)
axes[1].set_title("SIP Amount by Age Group", fontsize=13, fontweight="bold")
axes[1].set_xlabel("Age Group")
axes[1].set_ylabel("SIP Amount (₹)")
axes[1].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x:,.0f}"))

# 5c — Gender pie
gender_counts = txn["gender"].value_counts()
axes[2].pie(gender_counts, labels=gender_counts.index, autopct="%1.1f%%",
            colors=["#4C72B0","#DD8452","#55A868"],
            startangle=90,
            wedgeprops=dict(linewidth=1.5, edgecolor="white"))
axes[2].set_title("Investor Gender Split", fontsize=13, fontweight="bold")

plt.suptitle("Investor Demographics Analysis", fontsize=15, fontweight="bold", y=1.02)
plt.tight_layout()
fig5.savefig(CHARTS / "05_investor_demographics.png", dpi=150, bbox_inches="tight")
plt.close()
print("    05_investor_demographics.png")


# ═══════════════════════════════════════════════════════════════════════
# CHART 6a — SIP Amount by State (horizontal bar)
# CHART 6b — T30 vs B30 Pie
# ═══════════════════════════════════════════════════════════════════════
print("Chart 6: Geographic distribution...")

fig6, axes = plt.subplots(1, 2, figsize=(18, 8))

# 6a — State bar
state_sip = (txn.groupby("state")["amount_inr"].sum()
               .sort_values(ascending=True).tail(15))
colors_bar = ["#C44E52" if v == state_sip.max() else "#4C72B0" for v in state_sip]
axes[0].barh(state_sip.index, state_sip.values / 1e7, color=colors_bar, edgecolor="white")
axes[0].set_title("Total SIP Amount by State (Top 15)", fontsize=13, fontweight="bold")
axes[0].set_xlabel("Total SIP Amount (₹ Crore)")
axes[0].xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x:.0f}Cr"))
for i, (val, name) in enumerate(zip(state_sip.values, state_sip.index)):
    axes[0].text(val / 1e7 + 0.5, i, f"₹{val/1e7:.0f}Cr", va="center", fontsize=8)

# 6b — T30 vs B30 pie
tier_counts = txn.groupby("city_tier")["amount_inr"].sum()
axes[1].pie(tier_counts, labels=tier_counts.index, autopct="%1.1f%%",
            colors=["#2196F3","#FF9800"], startangle=120,
            wedgeprops=dict(linewidth=2, edgecolor="white"),
            textprops=dict(fontsize=13))
axes[1].set_title("Investment Distribution: T30 vs B30 Cities", fontsize=13, fontweight="bold")

plt.tight_layout()
fig6.savefig(CHARTS / "06_geographic_distribution.png", dpi=150, bbox_inches="tight")
plt.close()
print("    06_geographic_distribution.png")


# ═══════════════════════════════════════════════════════════════════════
# CHART 7 — Folio Count Growth with Milestones (Plotly)
# ═══════════════════════════════════════════════════════════════════════
print("Chart 7: Folio count growth...")

fig7 = go.Figure()
fig7.add_trace(go.Scatter(
    x=folio["month"], y=folio["total_folios_crore"],
    mode="lines+markers",
    line=dict(color="#7FBA00", width=3),
    marker=dict(size=6, symbol="circle"),
    fill="tozeroy", fillcolor="rgba(127,186,0,0.1)",
    name="Total Folios",
    hovertemplate="<b>%{x|%b %Y}</b><br>Total Folios: %{y:.2f} Cr<extra></extra>"
))

# Sub-category lines
for col, color, label in [
    ("equity_folios_crore", "#00BFFF", "Equity"),
    ("debt_folios_crore",   "#FF6B6B", "Debt"),
    ("hybrid_folios_crore", "#FFD700", "Hybrid"),
]:
    fig7.add_trace(go.Scatter(
        x=folio["month"], y=folio[col],
        mode="lines", name=label,
        line=dict(color=color, width=1.5, dash="dot"),
        hovertemplate=f"{label}: %{{y:.2f}} Cr<extra></extra>"
    ))

# Milestones
milestones = [
    (folio["month"].iloc[0],  folio["total_folios_crore"].iloc[0],  "Start: 13.26 Cr"),
    (folio["month"].iloc[-1], folio["total_folios_crore"].iloc[-1], f"End: {folio['total_folios_crore'].iloc[-1]:.2f} Cr"),
]
for x, y, text in milestones:
    fig7.add_annotation(x=x, y=y, text=f"<b>{text}</b>",
                        showarrow=True, arrowhead=2, arrowcolor="gold",
                        font=dict(color="gold", size=11),
                        bgcolor="rgba(0,0,0,0.5)", bordercolor="gold")

fig7.update_layout(
    title=dict(text="Folio Count Growth (Jan 2022 – Dec 2025)", font_size=18),
    xaxis_title="Month", yaxis_title="Folios (Crore)",
    template=PLOTLY_TEMPLATE, height=500,
    hovermode="x unified"
)
fig7.write_image(str(CHARTS / "07_folio_growth.png"), width=1400, height=500, scale=1.5)
print("    07_folio_growth.png")


# ═══════════════════════════════════════════════════════════════════════
# CHART 8 — NAV Return Correlation Matrix (Seaborn)
# ═══════════════════════════════════════════════════════════════════════
print("Chart 8: NAV return correlation matrix...")

# Select 10 schemes (direct plans)
top10 = fund[fund["plan"] == "Direct"].head(10)["amfi_code"].tolist()
nav_pivot = (nav[nav["amfi_code"].isin(top10)]
             .pivot(index="date", columns="amfi_code", values="nav")
             .dropna())
returns = nav_pivot.pct_change().dropna()

# Short names for labels
label_map = {row["amfi_code"]: row["scheme_name"][:20].replace("Fund","").strip()
             for _, row in fund[fund["amfi_code"].isin(top10)].iterrows()}
returns.columns = [label_map.get(c, str(c)) for c in returns.columns]

corr = returns.corr()

fig8, ax = plt.subplots(figsize=(12, 9))
mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
sns.heatmap(corr, ax=ax, annot=True, fmt=".2f", cmap="coolwarm",
            center=0, vmin=-1, vmax=1,
            linewidths=0.5, linecolor="gray",
            cbar_kws={"label": "Pearson Correlation", "shrink": 0.8},
            annot_kws={"size": 9})
ax.set_title("Daily Return Correlation Matrix (10 Selected Funds)", fontsize=14, fontweight="bold", pad=12)
ax.set_xticklabels(ax.get_xticklabels(), rotation=40, ha="right", fontsize=9)
ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=9)
plt.tight_layout()
fig8.savefig(CHARTS / "08_correlation_matrix.png", dpi=150, bbox_inches="tight")
plt.close()
print("    08_correlation_matrix.png")


# ═══════════════════════════════════════════════════════════════════════
# CHART 9 — Sector Allocation Donut (Plotly)
# ═══════════════════════════════════════════════════════════════════════
print("Chart 9: Sector allocation donut...")

equity_codes = fund[fund["category"] == "Equity"]["amfi_code"].tolist()
hold_eq = hold[hold["amfi_code"].isin(equity_codes)]
sector_wt = hold_eq.groupby("sector")["weight_pct"].sum().sort_values(ascending=False)

fig9 = go.Figure(go.Pie(
    labels=sector_wt.index,
    values=sector_wt.values,
    hole=0.48,
    textinfo="label+percent",
    textfont_size=11,
    marker=dict(
        colors=px.colors.qualitative.Plotly,
        line=dict(color="white", width=2)
    ),
    hovertemplate="<b>%{label}</b><br>Weight: %{value:.1f}%<br>Share: %{percent}<extra></extra>"
))
fig9.add_annotation(
    text="Sector<br>Allocation", x=0.5, y=0.5,
    font_size=14, showarrow=False, font_color="white"
)
fig9.update_layout(
    title=dict(text="Aggregate Sector Allocation — All Equity Funds", font_size=18),
    template=PLOTLY_TEMPLATE, height=550,
    legend=dict(font_size=10, x=1.02)
)
fig9.write_image(str(CHARTS / "09_sector_donut.png"), width=1200, height=550, scale=1.5)
print("    09_sector_donut.png")


# ═══════════════════════════════════════════════════════════════════════
# CHART 10 — Performance Scatter: Sharpe vs Return (Plotly)
# ═══════════════════════════════════════════════════════════════════════
print("Chart 10: Performance scatter (bonus)...")

perf_m = perf.merge(fund[["amfi_code","fund_house","sub_category"]], on="amfi_code", how="left")
fig10 = px.scatter(
    perf_m, x="return_3yr_pct", y="sharpe_ratio",
    size="aum_crore", color="sub_category",
    hover_name="scheme_name",
    hover_data={"expense_ratio_pct": True, "aum_crore": True},
    labels={"return_3yr_pct": "3-Year CAGR (%)", "sharpe_ratio": "Sharpe Ratio",
            "sub_category": "Sub-Category"},
    title="Risk-Adjusted Return: Sharpe Ratio vs 3-Year CAGR",
    template=PLOTLY_TEMPLATE, height=520,
    color_discrete_sequence=COLORS,
    size_max=45
)
fig10.add_hline(y=1.0, line_dash="dash", line_color="gold",
                annotation_text="Sharpe = 1.0 (good threshold)",
                annotation_position="bottom right")
fig10.write_image(str(CHARTS / "10_performance_scatter.png"), width=1300, height=520, scale=1.5)
print("    10_performance_scatter.png")


# ═══════════════════════════════════════════════════════════════════════
# CHART 11 — Expense Ratio Distribution (Seaborn)
# ═══════════════════════════════════════════════════════════════════════
print("Chart 11: Expense ratio distribution...")

fig11, axes = plt.subplots(1, 2, figsize=(14, 6))

# KDE plot
for plan, color in [("Direct","#00BFFF"), ("Regular","#FF6B6B")]:
    data = perf_m[perf_m["plan"] == plan]["expense_ratio_pct"].dropna()
    sns.kdeplot(data, ax=axes[0], fill=True, alpha=0.4, color=color, label=plan, linewidth=2)
axes[0].axvline(1.0, color="gold", linestyle="--", label="1% threshold")
axes[0].set_title("Expense Ratio Distribution: Direct vs Regular", fontsize=13, fontweight="bold")
axes[0].set_xlabel("Expense Ratio (%)")
axes[0].set_ylabel("Density")
axes[0].legend()

# Box by sub_category
sns.boxplot(data=perf_m, x="expense_ratio_pct", y="sub_category",
            palette="Set2", ax=axes[1], linewidth=1.5, showfliers=True,
            flierprops=dict(marker="o", markersize=4, alpha=0.5))
axes[1].axvline(1.0, color="gold", linestyle="--", label="1% threshold")
axes[1].set_title("Expense Ratio by Sub-Category", fontsize=13, fontweight="bold")
axes[1].set_xlabel("Expense Ratio (%)")
axes[1].set_ylabel("")
axes[1].legend()
plt.tight_layout()
fig11.savefig(CHARTS / "11_expense_ratio.png", dpi=150, bbox_inches="tight")
plt.close()
print("    11_expense_ratio.png")


# ═══════════════════════════════════════════════════════════════════════
# CHART 12 — Transaction Type Monthly Volume (Plotly stacked bar)
# ═══════════════════════════════════════════════════════════════════════
print("Chart 12: Transaction volume...")

txn["month"] = txn["transaction_date"].dt.to_period("M").dt.to_timestamp()
txn_m = txn.groupby(["month","transaction_type"])["amount_inr"].sum().reset_index()
txn_m["amount_cr"] = txn_m["amount_inr"] / 1e7

fig12 = px.bar(txn_m, x="month", y="amount_cr", color="transaction_type",
               barmode="stack",
               labels={"amount_cr": "Amount (₹ Crore)", "month": "Month",
                       "transaction_type": "Type"},
               title="Monthly Transaction Volume by Type (SIP / Lumpsum / Redemption)",
               template=PLOTLY_TEMPLATE, height=480,
               color_discrete_map={"SIP":"#00BFFF","Lumpsum":"#7FBA00","Redemption":"#FF6B6B"})
fig12.write_image(str(CHARTS / "12_txn_volume.png"), width=1300, height=480, scale=1.5)
print("    12_txn_volume.png")


# ═══════════════════════════════════════════════════════════════════════
# CHART 13 — Top 10 Holdings Bar (Seaborn)
# ═══════════════════════════════════════════════════════════════════════
print("Chart 13: Top holdings...")

top_stocks = (hold.groupby(["stock_name","sector"])
              .agg(total_mv=("market_value_cr","sum"),
                   num_funds=("amfi_code","nunique"))
              .reset_index()
              .sort_values("total_mv", ascending=False).head(10))

fig13, ax = plt.subplots(figsize=(13, 7))
bars = sns.barplot(data=top_stocks, x="total_mv", y="stock_name",
                   hue="sector", dodge=False, palette="tab10", ax=ax, legend=True)
ax.set_title("Top 10 Stocks by Market Value Across All Funds", fontsize=14, fontweight="bold")
ax.set_xlabel("Total Market Value (₹ Crore)")
ax.set_ylabel("")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x:,.0f}Cr"))
for bar, (_, row) in zip(ax.patches, top_stocks.iterrows()):
    ax.text(bar.get_width() + 50, bar.get_y() + bar.get_height()/2,
            f"{row['num_funds']} funds", va="center", fontsize=9)
plt.tight_layout()
fig13.savefig(CHARTS / "13_top_holdings.png", dpi=150, bbox_inches="tight")
plt.close()
print("    13_top_holdings.png")


# ═══════════════════════════════════════════════════════════════════════
# CHART 14 — Morningstar Rating Distribution (Seaborn)
# ═══════════════════════════════════════════════════════════════════════
print("Chart 14: Morningstar ratings...")

fig14, axes = plt.subplots(1, 2, figsize=(14, 6))

# Count of ratings
rating_counts = perf["morningstar_rating"].value_counts().sort_index()
star_colors   = ["#C44E52","#DD8452","#CCB974","#55A868","#4C72B0"]
axes[0].bar(rating_counts.index, rating_counts.values,
            color=star_colors, edgecolor="white", linewidth=1.5)
axes[0].set_title("Morningstar Rating Distribution", fontsize=13, fontweight="bold")
axes[0].set_xlabel("Stars ⭐")
axes[0].set_ylabel("Number of Funds")
axes[0].set_xticks(rating_counts.index)

# Return by rating
sns.boxplot(data=perf, x="morningstar_rating", y="return_3yr_pct",
            palette=star_colors, ax=axes[1], linewidth=1.5, showfliers=False)
axes[1].set_title("3-Year Return by Morningstar Rating", fontsize=13, fontweight="bold")
axes[1].set_xlabel("Stars ⭐")
axes[1].set_ylabel("3-Year CAGR (%)")
plt.tight_layout()
fig14.savefig(CHARTS / "14_morningstar_ratings.png", dpi=150, bbox_inches="tight")
plt.close()
print("    14_morningstar_ratings.png")


# ═══════════════════════════════════════════════════════════════════════
# CHART 15 — SIP Inflow vs Folio Growth Dual-Axis (Plotly)
# ═══════════════════════════════════════════════════════════════════════
print("Chart 15: SIP vs Folio dual-axis...")

sip_f   = sip[["month","sip_inflow_crore"]].copy()
folio_f = folio[["month","total_folios_crore"]].copy()
combined = pd.merge(sip_f, folio_f, on="month", how="inner")

fig15 = make_subplots(specs=[[{"secondary_y": True}]])
fig15.add_trace(go.Bar(x=combined["month"], y=combined["sip_inflow_crore"],
                        name="SIP Inflow (₹ Cr)", marker_color="rgba(0,191,255,0.6)"),
                secondary_y=False)
fig15.add_trace(go.Scatter(x=combined["month"], y=combined["total_folios_crore"],
                            mode="lines+markers", name="Total Folios (Cr)",
                            line=dict(color="#FFD700", width=3)),
                secondary_y=True)
fig15.update_layout(
    title=dict(text="SIP Inflows vs Folio Count Growth", font_size=18),
    template=PLOTLY_TEMPLATE, height=500,
    hovermode="x unified",
    legend=dict(x=0.01, y=0.99)
)
fig15.update_yaxes(title_text="SIP Inflow (₹ Crore)", secondary_y=False)
fig15.update_yaxes(title_text="Total Folios (Crore)", secondary_y=True)
fig15.write_image(str(CHARTS / "15_sip_vs_folio.png"), width=1300, height=500, scale=1.5)
print("    15_sip_vs_folio.png")


print(f"\n{'='*60}")
print(f"  ALL 15 CHARTS SAVED → reports/charts/")
print(f"{'='*60}")
charts = sorted(CHARTS.glob("*.png"))
for c in charts:
    size_kb = c.stat().st_size / 1024
    print(f"  {c.name:<40} {size_kb:>6.0f} KB")
print(f"\n  Total: {len(charts)} charts")