"""Per-event Wikipedia pageview timelines for Australian climate events.

Reproduces the small-multiple timeline figures (bushfires, cyclones,
earthquakes) and the standalone climate-change timeline. Each figure is built
from a CSV of daily views for a set of event pages stored under
``data/processed/event_views/``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

EVENT_VIEWS_DIR = Path("data/processed/event_views")
FIGURES_DIR = Path("outputs/figures")

LINE_COLOR = "#1f77b4"
EVENT_LINE_COLOR = "#333333"

START_DATE = "2018-01-01"
# The climate figure spans a fixed window so it keeps its familiar 2019 start
# even though, matched by page ID, the article's first Australian views now
# fall later in 2019.
CLIMATE_START = "2019-01-01"


# ---------------------------------------------------------------------------
# Timeline construction
# ---------------------------------------------------------------------------
def get_timeline(
    df: pd.DataFrame,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int | None = None,
    sort: str = "max",
    fields: tuple[str, str, str] = ("date", "page_name", "views"),
    priority: object = None,
) -> tuple[np.ndarray, pd.DatetimeIndex, dict[str, int]]:
    """Pivot a long (date, page, views) frame into a dense per-page matrix.

    Returns the views matrix (one row per page), the full daily date index, and
    a mapping of page name to its row. Pages are sorted by peak (``max``) or
    cumulative (``total``) views; ``priority`` pins named pages to the top.
    """
    date_col, page_col, views_col = fields
    df[date_col] = pd.to_datetime(df[date_col])

    start = df[date_col].min() if start_date is None else pd.to_datetime(start_date)
    end = df[date_col].max() if end_date is None else pd.to_datetime(end_date)

    df = df[(df[date_col] >= start) & (df[date_col] <= end)]

    all_dates = pd.date_range(start=start, end=end, freq="D")
    pivot = df.pivot_table(
        index=page_col, columns=date_col, values=views_col, fill_value=0
    )
    pivot = pivot.reindex(columns=all_dates, fill_value=0)

    if sort == "max":
        pivot["Sorting"] = pivot.max(axis=1)
    elif sort == "total":
        pivot["Sorting"] = pivot.sum(axis=1)
    pivot = pivot.sort_values(by="Sorting", ascending=False).drop(columns="Sorting")

    if priority is not None:
        priority_list = (
            list(priority)
            if isinstance(priority, (list, tuple, set, pd.Index))
            else [priority]
        )
        priority_existing = [p for p in priority_list if p in pivot.index]
        if priority_existing:
            priority_set = set(priority_existing)
            new_index = priority_existing + [
                i for i in pivot.index if i not in priority_set
            ]
            pivot = pivot.reindex(new_index)

    if limit is not None:
        pivot = pivot.head(limit)

    views = pivot.to_numpy()
    titles = {name: i for i, name in enumerate(pivot.index.tolist())}
    return views, pivot.columns, titles


# ---------------------------------------------------------------------------
# Axis styling helpers
# ---------------------------------------------------------------------------
def add_event(ax, event_date) -> None:
    """Mark an event: a shaded span for a (start, end) window, else a dashed line."""
    if isinstance(event_date, (list, tuple)) and len(event_date) == 2:
        start_date = pd.to_datetime(event_date[0])
        end_date = pd.to_datetime(event_date[1])
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        ax.axvspan(
            start_date,
            end_date,
            facecolor=EVENT_LINE_COLOR,
            alpha=0.15,
            edgecolor="none",
            linewidth=0,
            antialiased=False,
        )
        return

    ax.axvline(
        pd.to_datetime(event_date), color=EVENT_LINE_COLOR, linestyle="--", alpha=0.5
    )


def add_title(ax, name: str) -> None:
    """Draw a bold page title on a fixed white panel in the top-right corner."""
    from matplotlib.patches import FancyBboxPatch

    x, y = 0.98, 1
    box_w, box_h = 0.9, 0.085  # axes fraction

    panel = FancyBboxPatch(
        (x - box_w, y - box_h),
        box_w,
        box_h,
        transform=ax.transAxes,
        boxstyle="round,pad=0.01,rounding_size=0.01",
        facecolor="white",
        edgecolor="none",
        alpha=0.85,
        zorder=100,
        clip_on=False,
    )
    ax.add_patch(panel)
    ax.text(
        x,
        y,
        name,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=12,
        fontweight="bold",
        zorder=101,
    )


def k_formatter(x, pos) -> str:
    if abs(x) >= 500:
        return f"{x * 1e-3:g}K"
    return f"{x:g}"


def polish(ax) -> None:
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    ax.spines[["top", "right"]].set_visible(False)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(k_formatter))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="x", rotation=45)


# ---------------------------------------------------------------------------
# Page-name normalisation per event type
# ---------------------------------------------------------------------------
def parse_bushfires(df: pd.DataFrame) -> pd.DataFrame:
    df["page_name"] = df["page_name"].replace(
        "2019–20 Australian bushfire season", "Black Summer"
    )
    df = df[~df["page_name"].str.endswith("Australian bushfire season")]
    renames = {
        "1967 Tasmanian fires": "Tasmania, 1967",
        "1994 eastern seaboard fires": "Eastern Seaboard, 1994",
        "2003 Canberra bushfires": "Canberra, 2003",
        "2013 New South Wales bushfires": "New South Wales, 2013",
        "Black Summer": "Black Summer, 2019–20",
        "2023 Wanneroo bushfire": "Wanneroo, 2023",
        "Ash Wednesday bushfires": "Ash Wednesday, 1983",
        "Black Christmas bushfires": "Black Christmas, 2001",
        "Black Friday bushfires": "Black Friday, 1939",
        "Black Saturday bushfires": "Black Saturday, 2009",
        "Black Thursday bushfires": "Black Thursday, 1851",
        "2021 Wooroloo bushfire": "Wooroloo, 2021",
        "2015 Sampson Flat bushfires": "Sampson Flat, 2015",
    }
    for old, new in renames.items():
        df["page_name"] = df["page_name"].replace(old, new)
    return df


def parse_cyclones(df: pd.DataFrame) -> pd.DataFrame:
    df["page_name"] = df["page_name"].str.replace("Cyclone ", "")
    years = {
        "Tracy": "1974",
        "Yasi": "2011",
        "Alfred": "2025",
        "Mahina": "1899",
        "Debbie": "2017",
        "Wanda": "1974",
        "Harold": "2020",
        "Larry": "2006",
        "Alby": "1978",
        "Marcia": "2015",
        "Jasper": "2023",
        "Freddy": "2023",
        "Gabrielle": "2023",
        "Marcus": "2018",
        "Oswald": "2013",
        "Ilsa": "2023",
    }
    for name, year in years.items():
        df["page_name"] = df["page_name"].replace(name, f"{name}, {year}")
    return df


def parse_earthquakes(df: pd.DataFrame) -> pd.DataFrame:
    renames = {
        "1989 Newcastle earthquake": "Newcastle, 1989",
        "2021 Mansfield earthquake": "Mansfield, 2021",
        "2012 Gippsland earthquake": "Gippsland, 2012",
        "1968 Meckering earthquake": "Meckering, 1968",
        "1954 Adelaide earthquake": "Adelaide, 1954",
        "1961 New South Wales earthquake": "New South Wales, 1961",
        "2004 Tasman Sea earthquake": "Tasman Sea, 2004",
    }
    for old, new in renames.items():
        df["page_name"] = df["page_name"].replace(old, new)
    return df


PARSERS = {
    "bushfires": parse_bushfires,
    "cyclones": parse_cyclones,
    "earthquakes": parse_earthquakes,
}


def load_event_views(
    name: str,
    priority: object = None,
    limit: int = 12,
    views_dir: Path = EVENT_VIEWS_DIR,
) -> tuple[np.ndarray, pd.DatetimeIndex, dict[str, int]]:
    """Load an event views CSV, normalise page names, and build its timeline."""
    df = pd.read_csv(views_dir / f"{name}.csv")
    parser = PARSERS.get(name)
    if parser is not None:
        df = parser(df)
    return get_timeline(df, start_date=START_DATE, limit=limit, sort="max", priority=priority)


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def _save(fig, stem: str, figures_dir: Path) -> Path:
    figures_dir.mkdir(parents=True, exist_ok=True)
    png_path = figures_dir / f"{stem}.png"
    fig.savefig(png_path, dpi=600)
    fig.savefig(figures_dir / f"{stem}.pdf")
    return png_path


def plot_event_grid(
    views: np.ndarray,
    dates: pd.DatetimeIndex,
    titles: dict[str, int],
    stem: str,
    event=None,
    limits: list[int] | None = None,
    columns: int = 4,
    figures_dir: Path = FIGURES_DIR,
) -> Path:
    """Small-multiple grid: one per-page daily-views timeline per subplot."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = list(titles)
    rows = (len(names) - 1) // columns + 1
    fig, axes = plt.subplots(
        rows, columns, figsize=(columns * 3, rows * 2), sharex=True
    )
    axes = axes.flatten()

    i = -1
    for i, title in enumerate(names):
        ax = axes[i]
        ax.plot(dates, views[i], color=LINE_COLOR, linewidth=1.5)

        if event:
            add_event(ax, event)
        add_title(ax, title)
        polish(ax)

        if limits:
            band = i // columns
            ax.set_ylim(0, limits[band] if band < len(limits) else limits[-1])

        if i % columns != 0:
            ax.set_yticklabels([])

        for text in ax.texts:
            if text.get_weight() == "bold":
                text.set_fontsize(10)

    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout()
    output = _save(fig, stem, figures_dir)
    plt.close(fig)
    return output


def plot_climate(
    views: np.ndarray,
    dates: pd.DatetimeIndex,
    stem: str = "climate",
    figures_dir: Path = FIGURES_DIR,
) -> Path:
    """Standalone climate-change timeline with annotated peaks."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    black_summer = ["2019-10-14", "2020-02-14"]
    election_debate = "2022-04-20"

    fig = plt.figure(figsize=(10, 6))
    ax = plt.gca()
    ax.plot(dates, views[0, :], color=LINE_COLOR, linewidth=3)

    add_event(ax, black_summer)
    add_event(ax, election_debate)
    add_title(ax, "Climate Change")
    polish(ax)

    plt.xticks(size=16)
    plt.yticks(size=16)
    plt.ylim(0, 15000)
    for text in ax.texts:
        if text.get_weight() == "bold":
            text.set_fontsize(20)

    plt.text(pd.to_datetime("2020-03-14"), 13000, "Black Summer", fontsize=14)
    plt.text(
        pd.to_datetime("2022-05-20"), 13000, "Federal Election Debate", fontsize=14
    )

    output = _save(fig, stem, figures_dir)
    plt.close(fig)
    return output


# Grid figures: (csv name, output stem, event marker, y-axis band limits, columns, page limit, priority)
GRID_FIGURES = [
    ("bushfires", "bushfire", ["2019-10-14", "2020-02-14"], [28000, 6000, 2000], 4, 12, None),
    ("cyclones", "cyclone", "2025-02-21", [16000, 6000, 3000], 4, 12, "Alfred, 2025"),
    ("earthquakes", "earthquake", "2021-09-22", [20000, 4000], 3, 6, "Mansfield, 2021"),
]


def build_all(figures_dir: Path = FIGURES_DIR) -> list[Path]:
    outputs: list[Path] = []
    for name, stem, event, limits, columns, limit, priority in GRID_FIGURES:
        views, dates, titles = load_event_views(name, priority=priority, limit=limit)
        outputs.append(
            plot_event_grid(
                views, dates, titles, stem,
                event=event, limits=limits, columns=columns, figures_dir=figures_dir,
            )
        )

    climate_df = pd.read_csv(EVENT_VIEWS_DIR / "climate.csv")
    views, dates, _ = get_timeline(climate_df, start_date=CLIMATE_START)
    outputs.append(plot_climate(views, dates, figures_dir=figures_dir))
    return outputs
