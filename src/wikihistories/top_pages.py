from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

RAW_PAGEVIEWS_DIR = Path("data/raw/pageviews")
TABLES_DIR = Path("outputs/tables")
FIGURES_DIR = Path("outputs/figures")

DEFAULT_PALETTE = [
    "#7F3C8D", "#11A579", "#3969AC", "#F2B701", "#E73F74",
    "#80BA5A", "#E68310", "#008695", "#CF1C90", "#A5AA99",
]

# Per-country pageview TSVs share the same column layout everywhere in this
# project (see wikihistories.australia_daily_views.TSV_COLUMNS).
TSV_COLUMNS = [
    "Country",
    "CountryCode",
    "Project",
    "PageID",
    "PageTitle",
    "WikidataID",
    "Views",
]


@dataclass(frozen=True)
class TopPagesSpec:
    """A single top-pages query."""

    country_code: str
    start_date: date
    end_date: date
    output_csv: Path
    title: str = ""
    figure_stem: str = ""
    highlight_titles: tuple[str, ...] = ()
    highlight_cmap: str = ""
    legend_loc: str = "upper right"
    legend_bbox: tuple[float, float] | None = None


def iter_dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def read_country_pageviews(path: Path, country_code: str) -> pd.DataFrame:
    """Read one raw daily TSV and keep English Wikipedia rows for a country."""
    frame = pd.read_csv(
        path,
        sep="\t",
        names=TSV_COLUMNS,
        header=None,
        quoting=csv.QUOTE_NONE,
        usecols=["CountryCode", "Project", "PageTitle", "Views"],
        dtype={
            "CountryCode": "string",
            "Project": "string",
            "PageTitle": "string",
            "Views": "int64",
        },
    )
    mask = (
        (frame["CountryCode"] == country_code)
        & (frame["Project"] == "en.wikipedia")
        & (frame["PageTitle"] != "Main_Page")
    )
    return frame.loc[mask, ["PageTitle", "Views"]]


def collect_daily_views(
    spec: TopPagesSpec,
    raw_dir: Path = RAW_PAGEVIEWS_DIR,
) -> tuple[pd.DataFrame, list[date]]:
    """Read each day in the range into a long (Date, PageTitle, Views) frame."""
    frames: list[pd.DataFrame] = []
    days: list[date] = []
    missing: list[str] = []

    for day in iter_dates(spec.start_date, spec.end_date):
        path = raw_dir / f"{day.isoformat()}.tsv"
        if not path.exists():
            missing.append(day.isoformat())
            continue
        days.append(day)
        frame = read_country_pageviews(path, spec.country_code)
        frame = frame.assign(Date=pd.Timestamp(day))
        frames.append(frame)

    if missing:
        raise FileNotFoundError(
            f"Missing raw pageview files for {spec.country_code}: "
            + ", ".join(missing)
        )
    if not days:
        raise ValueError("No days in range")

    return pd.concat(frames, ignore_index=True), days


def compute_top_pages(
    spec: TopPagesSpec,
    top_n: int = 10,
    raw_dir: Path = RAW_PAGEVIEWS_DIR,
    daily: pd.DataFrame | None = None,
    days: list[date] | None = None,
) -> pd.DataFrame:
    """Compute the top-N pages by average daily views over the date range."""
    if daily is None or days is None:
        daily, days = collect_daily_views(spec, raw_dir=raw_dir)

    totals = daily.groupby("PageTitle")["Views"].sum().sort_values(ascending=False)
    ranked = totals.head(top_n)

    rows = [
        {
            "Rank": rank,
            "Article title": title.replace("_", " "),
            "Average daily views": round(int(total) / len(days)),
        }
        for rank, (title, total) in enumerate(ranked.items(), start=1)
    ]
    return pd.DataFrame(rows, columns=["Rank", "Article title", "Average daily views"])


def plot_top_pages(
    spec: TopPagesSpec,
    title: str,
    stem: str,
    top_n: int = 10,
    daily: pd.DataFrame | None = None,
    days: list[date] | None = None,
    figures_dir: Path = FIGURES_DIR,
) -> Path:
    """Plot daily views vs date for the top-N pages, one line per page."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    if daily is None or days is None:
        daily, days = collect_daily_views(spec)

    totals = daily.groupby("PageTitle")["Views"].sum().sort_values(ascending=False)
    top_titles = list(totals.head(top_n).index)

    date_index = pd.DatetimeIndex([pd.Timestamp(d) for d in days])
    pivot = (
        daily[daily["PageTitle"].isin(top_titles)]
        .pivot_table(index="PageTitle", columns="Date", values="Views", fill_value=0)
        .reindex(index=top_titles, columns=date_index, fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(10, 8))

    # Optionally highlight a chosen set of pages in a colour family and mute the
    # rest (grey, semi-transparent) so the highlighted lines stand out.
    highlighted = [t for t in top_titles if t.replace("_", " ") in spec.highlight_titles]
    highlight_colors: dict[str, tuple] = {}
    if highlighted and spec.highlight_cmap:
        family = plt.get_cmap(spec.highlight_cmap)
        shades = np.linspace(0.9, 0.5, len(highlighted))
        highlight_colors = {t: family(s) for t, s in zip(highlighted, shades)}

    for i, page_title in enumerate(top_titles):
        series = pivot.loc[page_title].to_numpy()
        label = page_title.replace("_", " ")
        if highlight_colors:
            if page_title in highlight_colors:
                ax.plot(
                    date_index, series, marker="o", markersize=5, linewidth=2.5,
                    color=highlight_colors[page_title], label=label, zorder=3,
                )
            else:
                ax.plot(
                    date_index, series, linewidth=1.5, color="#888888",
                    alpha=0.3, label=label, zorder=1,
                )
        else:
            ax.plot(
                date_index, series, marker="o", markersize=4, linewidth=2,
                color=DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)], label=label,
            )

    def k_formatter(x, _pos) -> str:
        if abs(x) >= 1000:
            return f"{x * 1e-3:g}K"
        return f"{x:g}"

    ax.set_title(title, size=18, pad=15)
    ax.set_ylabel("Daily views", size=20)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(k_formatter))
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.tick_params(axis="x", labelsize=16, rotation=45)
    ax.tick_params(axis="y", labelsize=16)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(
        loc=spec.legend_loc,
        bbox_to_anchor=spec.legend_bbox,
        fontsize=12,
        frameon=False
    )
    fig.tight_layout()

    figures_dir.mkdir(parents=True, exist_ok=True)
    png_path = figures_dir / f"{stem}.png"
    fig.savefig(png_path, dpi=600)
    fig.savefig(figures_dir / f"{stem}.pdf")
    plt.close(fig)
    return png_path


def write_top_pages(
    spec: TopPagesSpec, top_n: int = 10, make_plot: bool = False
) -> pd.DataFrame:
    daily, days = collect_daily_views(spec)
    table = compute_top_pages(spec, top_n=top_n, daily=daily, days=days)
    spec.output_csv.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(spec.output_csv, index=False)
    if make_plot:
        plot_top_pages(
            spec,
            title=spec.title,
            stem=spec.figure_stem,
            top_n=top_n,
            daily=daily,
            days=days,
        )
    return table
