"""Small multiples of the daily Australian click share to Climate change.

Reads the panel built by :mod:`wikihistories.clickstream_impact`
(``data/processed/climate_au_daily.csv``) and draws one panel per top source,
each showing the share of estimated Australian clicks to the Climate change
article that arrived via that source, smoothed over a 28-day window.

The share is a ratio of smoothed quantities — a rolling mean of the source's
``au_count`` over a rolling mean of the daily total — which stays stable even
on days when few sources register, unlike smoothing the raw daily ratio.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from wikihistories.project_summary import REPORT, update_report_section

PANEL_CSV = Path("data/processed/climate_au_daily.csv")
FIGURES_DIR = Path("outputs/figures")
TABLES_DIR = Path("outputs/tables")
FIGURE_STEM = "clickstream_climate_shares"
RANKING_CSV = TABLES_DIR / "clickstream_top_sources.csv"

TOP_N = 5  # panels in the figure
RANKING_N = 10  # rows in the top-sources table
SMOOTH_DAYS = 28  # centred moving-average window

# Categorical series colours (one per panel) plus chart chrome.
SERIES = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7"]
CONTEXT = "#c3c2b7"  # gray line: cumulative share of the top sources
GRID = "#e1e0d9"
INK = "#0b0b0b"


def load_panel(path: Path = PANEL_CSV) -> pd.DataFrame:
    panel = pd.read_csv(path)
    panel["date"] = pd.to_datetime(panel["date"])
    return panel


def rank_sources(panel: pd.DataFrame) -> pd.DataFrame:
    """All source pages ranked by cumulative ``au_count``, with click share (%).

    ``share_pct`` is each page's estimated Australian clicks to Climate change as
    a percentage of the estimated total across every source over the study
    period. Titles are the page's most recent spelling, spaces restored.
    """
    latest_title = (
        panel.sort_values("date").drop_duplicates("pageid", keep="last")
        .set_index("pageid")["title"]
    )
    ranked = (
        panel.groupby("pageid")["au_count"].sum()
        .sort_values(ascending=False).rename("au_count").reset_index()
    )
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    ranked["title"] = ranked["pageid"].map(latest_title).str.replace("_", " ", regex=False)
    ranked["share_pct"] = 100 * ranked["au_count"] / ranked["au_count"].sum()
    return ranked[["rank", "pageid", "title", "au_count", "share_pct"]]


def write_top_sources_table(
    ranked: pd.DataFrame,
    out_csv: Path = RANKING_CSV,
    n: int = RANKING_N,
) -> Path:
    """Write the top ``n`` sources by click share to a CSV table."""
    table = ranked.head(n).rename(
        columns={
            "rank": "Rank",
            "pageid": "Page ID",
            "title": "Article title",
            "au_count": "Estimated AU clicks",
            "share_pct": "Share of clicks (%)",
        }
    )
    table["Estimated AU clicks"] = table["Estimated AU clicks"].round().astype(int)
    table["Share of clicks (%)"] = table["Share of clicks (%)"].round(2)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out_csv, index=False)
    return out_csv


def update_clickstream_report(ranked: pd.DataFrame, report_path: Path = REPORT) -> Path:
    """Store the top-3 sources' rounded click shares in report.json."""
    values = {
        f"top{row.rank}_share": f"{row.share_pct:.0f}"
        for row in ranked.head(3).itertuples()
    }
    return update_report_section("clickstream", values, report_path)


def smoothed_share(
    panel: pd.DataFrame,
    pageids: list[int],
    window: int = SMOOTH_DAYS,
) -> pd.DataFrame:
    """Smoothed daily click share per page id.

    Days in a month the panel covers but on which a source did not register are
    treated as zero; days in months absent from the panel stay NaN so the lines
    break rather than interpolating across gaps.
    """
    days = pd.date_range(panel["date"].min(), panel["date"].max(), freq="D")
    months = set(panel["date"].dt.strftime("%Y-%m"))
    covered = pd.Series(pd.Index(days.strftime("%Y-%m")).isin(months), index=days)

    total = panel.groupby("date")["au_count"].sum().reindex(days)
    total[covered] = total[covered].fillna(0.0)

    observed = (
        panel[panel["pageid"].isin(pageids)]
        .pivot_table(index="date", columns="pageid", values="au_count", aggfunc="sum")
        .reindex(days)
        .reindex(columns=pageids)
    )
    observed[covered] = observed[covered].fillna(0.0)

    roll = dict(window=window, center=True, min_periods=window // 2)
    return observed.rolling(**roll).mean().div(total.rolling(**roll).mean(), axis=0)


def plot_small_multiples(
    share: pd.DataFrame,
    labels: dict[int, str],
    stem: str = FIGURE_STEM,
    figures_dir: Path = FIGURES_DIR,
) -> Path:
    """One stacked panel per source; the cumulative top-source share sits behind."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    pageids = list(share.columns)
    fig, axes = plt.subplots(
        len(pageids), 1, figsize=(11, 2.1 * len(pageids)), sharex=True, sharey=True
    )

    cumulative = share.sum(axis=1, min_count=1)
    ymax = max(share.max().max(), cumulative.max()) * 100
    for ax, pageid, color in zip(axes, pageids, SERIES):
        ax.plot(share.index, cumulative * 100, color=CONTEXT, linewidth=1.5, alpha=0.6, zorder=1)
        ax.plot(share.index, share[pageid] * 100, color=color, linewidth=2.5, zorder=3)

        ax.text(
            0.99, 0.92, labels[pageid], transform=ax.transAxes,
            ha="right", va="top", fontsize=14, fontweight="bold", color=INK,
        )
        ax.set_ylim(0, ymax * 1.08)
        ax.set_xlim(share.index[0] - pd.Timedelta(days=30), share.index[-1])
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.tick_params(axis="x", labelsize=16, labelcolor="#000")
        ax.tick_params(axis="y", labelsize=12, labelcolor="#000")
        ax.grid(axis="y", color=GRID, linewidth=0.7)
        ax.set_axisbelow(True)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.spines[["top", "right"]].set_visible(False)

    axes[len(axes) // 2].set_ylabel(
        "Share of clicks to Climate Change article (%)", size=18, color="black"
    )
    fig.tight_layout(h_pad=2.5)

    figures_dir.mkdir(parents=True, exist_ok=True)
    png_path = figures_dir / f"{stem}.png"
    fig.savefig(png_path, dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(figures_dir / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return png_path


def build_all(
    panel_csv: Path = PANEL_CSV,
    figures_dir: Path = FIGURES_DIR,
    table_csv: Path = RANKING_CSV,
    report_path: Path = REPORT,
) -> Path:
    """Rank sources, write the top-sources table, update report.json, plot."""
    panel = load_panel(panel_csv)
    ranked = rank_sources(panel)
    write_top_sources_table(ranked, table_csv)
    update_clickstream_report(ranked, report_path)

    labels = dict(zip(ranked["pageid"].head(TOP_N), ranked["title"].head(TOP_N)))
    share = smoothed_share(panel, list(labels))
    return plot_small_multiples(share, labels, figures_dir=figures_dir)
