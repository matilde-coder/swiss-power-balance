"""Run every analysis query, save the results as CSV and draw the README charts."""

from __future__ import annotations

from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "swiss_power.duckdb"
SQL_DIR = ROOT / "sql"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"

# Colour palette (validated for colour-vision deficiencies, light background)
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
IMPORT_RED, EXPORT_BLUE = "#e34948", "#2a78d6"
COUNTRY_COLORS = {"DE": BLUE, "FR": ORANGE, "AT": AQUA, "IT": YELLOW}
COUNTRY_NAMES = {"DE": "Germany", "FR": "France", "AT": "Austria", "IT": "Italy"}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 10,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "axes.titlesize": 13,
    "axes.titleweight": "semibold",
    "axes.titlelocation": "left",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": INK_2,
    "ytick.labelcolor": INK_2,
    "ytick.left": False,
    "legend.frameon": False,
    "legend.labelcolor": INK_2,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "savefig.facecolor": SURFACE,
})


def run_queries() -> dict[str, pd.DataFrame]:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    RESULTS_DIR.mkdir(exist_ok=True)
    results = {}
    for path in sorted(SQL_DIR.glob("[0-9][0-9]_*.sql")):
        if path.name.startswith("00_"):
            continue  # view definitions, created by the loader
        df = con.execute(path.read_text()).df()
        df.to_csv(RESULTS_DIR / f"{path.stem}.csv", index=False)
        results[path.stem[3:]] = df
        print(f"[ok] {path.name}: {len(df)} rows")
    con.close()
    return results


def subtitle(ax, text: str) -> None:
    ax.text(0, 1.02, text, transform=ax.transAxes, color=INK_2, fontsize=9.5, va="bottom")


def source(fig, y: float = -0.02) -> None:
    fig.text(0.01, y, "Source: Swissgrid, Energy Overview Switzerland (15-minute data)",
             color=MUTED, fontsize=8, ha="left")


def save(fig, name: str) -> None:
    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.png")
    plt.close(fig)
    print(f"[ok] figures/{name}.png")


def chart_monthly_balance(df: pd.DataFrame) -> None:
    df = df.copy()
    df["date"] = pd.to_datetime(dict(year=df.year, month=df.month, day=1))
    colors = [IMPORT_RED if v > 0 else EXPORT_BLUE for v in df.net_import_gwh]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.bar(df.date, df.net_import_gwh, width=24, color=colors, edgecolor=SURFACE, linewidth=0.5)
    ax.axhline(0, color=AXIS, linewidth=1)
    ax.set_title("Switzerland imports in winter and exports in summer", pad=24)
    subtitle(ax, "Monthly net imports, GWh  (above zero = net import, below = net export)")
    ax.annotate("Winter 2021/22: all six months\nabove 1 TWh of net imports", xy=(pd.Timestamp("2021-10-01"), 1400),
                xytext=(pd.Timestamp("2021-08-01"), 1500), color=INK_2, fontsize=8.5, ha="right", va="center")
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=IMPORT_RED),
                       plt.Rectangle((0, 0), 1, 1, color=EXPORT_BLUE)],
              labels=["Net import", "Net export"], loc="lower left", ncols=2)
    ax.set_ylabel("GWh")
    source(fig)
    save(fig, "01_monthly_balance")


def chart_winter_share(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(df.winter, df.import_share_pct, width=0.55,
                  color=[IMPORT_RED if v > 0 else EXPORT_BLUE for v in df.import_share_pct])
    ax.axhline(0, color=AXIS, linewidth=1)
    for bar, v in zip(bars, df.import_share_pct):
        ax.text(bar.get_x() + bar.get_width() / 2, v + (0.8 if v >= 0 else -0.8), f"{v:+.1f}%",
                ha="center", va="bottom" if v >= 0 else "top", color=INK, fontsize=9.5)
    ax.set_title("Winter import dependency swings widely from year to year", pad=24)
    subtitle(ax, "Net imports as a share of consumption, October to March")
    ax.set_ylim(min(df.import_share_pct.min() - 4, -2), df.import_share_pct.max() + 4)
    ax.set_yticks([])
    ax.grid(False)
    ax.tick_params(axis="x", length=0)
    source(fig)
    save(fig, "02_winter_import_share")


def chart_flows_by_country(df: pd.DataFrame) -> None:
    wide = df.pivot(index="winter", columns="country", values="net_import_twh")
    fig, ax = plt.subplots(figsize=(8, 4.6))
    x = range(len(wide.index))
    for country in ["DE", "FR", "AT", "IT"]:
        y = wide[country]
        ax.plot(x, y, color=COUNTRY_COLORS[country], linewidth=2, marker="o", markersize=6,
                markeredgecolor=SURFACE, markeredgewidth=1.5, label=COUNTRY_NAMES[country])
        ax.text(len(x) - 1 + 0.12, y.iloc[-1], COUNTRY_NAMES[country], color=INK_2, va="center", fontsize=9.5)
    ax.axhline(0, color=AXIS, linewidth=1)
    ax.set_xticks(list(x), wide.index)
    ax.set_xlim(-0.2, len(x) - 1 + 0.7)
    ax.set_ylabel("TWh")
    ax.set_title("France has replaced Germany as the main winter supplier", pad=24)
    subtitle(ax, "Net imports per neighbour, October to March, TWh  (negative = Switzerland exports)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.1), ncols=4)
    source(fig, y=-0.08)
    save(fig, "03_flows_by_country")


def chart_daily_profile(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.6))
    styles = {
        ("winter", "weekday"): (BLUE, "-", "Winter weekday"),
        ("winter", "weekend"): (BLUE, "--", "Winter weekend"),
        ("summer", "weekday"): (ORANGE, "-", "Summer weekday"),
        ("summer", "weekend"): (ORANGE, "--", "Summer weekend"),
    }
    for (half, day), (color, ls, label) in styles.items():
        d = df[(df.half_year == half) & (df.day_type == day)]
        ax.plot(d.hour, d.avg_demand_mw / 1000, color=color, linestyle=ls, linewidth=2, label=label)
        ax.text(23.4, d.avg_demand_mw.iloc[-1] / 1000, label, color=INK_2, va="center", fontsize=9)
    ax.set_xticks(range(0, 24, 3), [f"{h:02d}:00" for h in range(0, 24, 3)])
    ax.set_xlim(0, 27)
    ax.set_ylabel("GW")
    ax.set_title("Winter weekday demand peaks mid-morning and early evening", pad=24)
    subtitle(ax, "Average end-user demand by hour of day (local time), 2020-2025, GW")
    ax.legend(loc="lower right", bbox_to_anchor=(0.86, 0), ncols=2, fontsize=9)
    source(fig)
    save(fig, "04_daily_load_profile")


def chart_cantons(df: pd.DataFrame, year: int) -> None:
    df = df.sort_values("winter")
    fig, ax = plt.subplots(figsize=(8, 6))
    y = range(len(df))
    ax.hlines(y, df.winter, df.summer, color=GRID, linewidth=2, zorder=1)
    ax.scatter(df.winter, y, color=BLUE, s=55, zorder=3, label="Winter (Oct-Mar)",
               edgecolor=SURFACE, linewidth=1.5)
    ax.scatter(df.summer, y, color=ORANGE, s=55, zorder=3, label="Summer (Apr-Sep)",
               edgecolor=SURFACE, linewidth=1.5)
    ax.axvline(1, color=INK_2, linewidth=1, linestyle=":")
    ax.text(1.05, len(df) - 0.4, "self-sufficient", color=INK_2, fontsize=8.5, va="center")
    ax.set_yticks(list(y), df.region)
    ax.set_xscale("log")
    ax.set_xticks([0.05, 0.1, 0.25, 0.5, 1, 2, 4], ["0.05", "0.1", "0.25", "0.5", "1", "2", "4"])
    ax.minorticks_off()
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Production / consumption (log scale)")
    n_winter = int((df.winter > 1).sum())
    ax.set_title(f"Only {n_winter} of {len(df)} canton groups produce more than they use in winter", pad=24)
    subtitle(ax, f"Ratio of production to consumption, {year}")
    ax.legend(loc="lower right")
    source(fig)
    save(fig, "06_canton_self_sufficiency")


def main() -> None:
    r = run_queries()
    con = duckdb.connect(str(DB_PATH), read_only=True)
    latest_full_year = con.execute(
        "SELECT max(year) FROM (SELECT year FROM grid GROUP BY year HAVING count(DISTINCT month) = 12)"
    ).fetchone()[0]
    con.close()
    chart_monthly_balance(r["monthly_balance"])
    chart_winter_share(r["winter_import_share"])
    chart_flows_by_country(r["flows_by_country"])
    chart_daily_profile(r["daily_load_profile"])
    chart_cantons(r["canton_self_sufficiency"], latest_full_year)


if __name__ == "__main__":
    main()
