"""Australian click-through impact for the Wikipedia Climate change article.

Wikimedia's monthly *clickstream* dumps record, for every (source -> target)
navigation on English Wikipedia, how many times readers followed that link.
On its own the clickstream is global and monthly; the daily *country pageviews*
dataset tells us how many times each page was viewed from Australia on each day.
Combining them yields a daily estimate of how many Australian readers reached
the Climate change article from each linking source:

    au_clicks(source, day) = clicks(source, month)
                             * au_views(source, day) / global_views(source, month)

where ``clicks / global_views`` is the source's monthly click-through rate to
Climate change and ``au_views`` scales it to Australian traffic on the day.

The module has two stages, each with a thin script under ``scripts``:

* :func:`download_clicks` fetches the monthly dumps and filters them to the
  climate-related subset stored in ``data/clicks`` (``download_clickstream.py``).
* the panel builder (added alongside this docstring) turns clicks plus raw
  daily pageviews into the single ``data/processed/climate_au_daily.csv`` that
  the figures read (``build_clickstream_impact.py``).
"""

from __future__ import annotations

import csv
import re
import urllib.request
from pathlib import Path

import pandas as pd

CLICKS_DIR = Path("data/clicks")
RAW_CLICKSTREAM_DIR = Path("data/raw/clickstream")
RAW_PAGEVIEWS_DIR = Path("data/raw/pageviews")
PROCESSED_DIR = Path("data/processed")
PANEL_CSV = PROCESSED_DIR / "climate_au_daily.csv"
CLICKSTREAM_BASE_URL = "https://dumps.wikimedia.org/other/clickstream"

CLICKS_COLUMNS = ["source", "page", "type", "count"]
PAGEVIEW_COLUMNS = [
    "Country",
    "CountryCode",
    "Project",
    "PageID",
    "PageTitle",
    "WikidataID",
    "Views",
]
PANEL_COLUMNS = ["date", "pageid", "title", "au_views", "au_count"]

PROJECT = "en.wikipedia"
COUNTRY = "Australia"

# Destination-title variants folded into the canonical Climate change article
# so their inbound clicks are counted together.
PAGES_TO_COMBINE = [
    "Climate_change",
    "Global_warming",
    "Climate_change_(general_concept)",
    "Climate_variability_and_change",
    "Global_warming_disambiguation_page",
    "Global_warming_(disambiguation)",
]

# Wikipedia's Main Page is excluded as a source.
FILTERED_SOURCES = ["Main_Page"]

# We keep any navigation whose destination page title mentions climate change
# or warming; the build stage narrows these to the canonical Climate change
# article via its merged title variants.
TARGET_KEYWORDS = ("climate_change", "warming")
_TARGET_PATTERN = "|".join(re.escape(keyword) for keyword in TARGET_KEYWORDS)

# Clickstream coverage committed to the repository (English Wikipedia dumps
# begin in 2017-11).
FIRST_MONTH = "2017-11"
LAST_MONTH = "2026-02"


def month_range(start: str = FIRST_MONTH, end: str = LAST_MONTH) -> list[str]:
    """List ``YYYY-MM`` strings from ``start`` through ``end`` inclusive."""
    return [period.strftime("%Y-%m") for period in pd.period_range(start, end, freq="M")]


# ---------------------------------------------------------------------------
# Stage 1: download monthly clickstream dumps -> data/clicks
# ---------------------------------------------------------------------------
def download_month(
    month: str,
    clicks_dir: Path = CLICKS_DIR,
    raw_dir: Path = RAW_CLICKSTREAM_DIR,
    keep_archive: bool = False,
) -> tuple[int, bool]:
    """Fetch one month's dump, filter to climate pages, write ``{month}.csv``.

    Returns ``(rows_written, downloaded)``. An already-present output CSV is
    left untouched and reported as ``(0, False)``.
    """
    out_csv = clicks_dir / f"{month}.csv"
    if out_csv.exists():
        return 0, False

    archive = raw_dir / f"clickstream-enwiki-{month}.tsv.gz"
    if not archive.exists():
        raw_dir.mkdir(parents=True, exist_ok=True)
        url = f"{CLICKSTREAM_BASE_URL}/{month}/{archive.name}"
        urllib.request.urlretrieve(url, archive)

    dump = pd.read_csv(
        archive,
        sep="\t",
        names=CLICKS_COLUMNS,
        header=None,
        quoting=csv.QUOTE_NONE,  # page titles contain literal double quotes
    )
    climate = dump[dump["page"].str.contains(_TARGET_PATTERN, case=False, na=False)]

    clicks_dir.mkdir(parents=True, exist_ok=True)
    climate.to_csv(out_csv, index=False)

    if not keep_archive:
        archive.unlink()
    return len(climate), True


def download_clicks(
    months: list[str] | None = None,
    clicks_dir: Path = CLICKS_DIR,
    raw_dir: Path = RAW_CLICKSTREAM_DIR,
    keep_archive: bool = False,
) -> list[Path]:
    """Download and filter every month in ``months`` (default: full coverage)."""
    written: list[Path] = []
    for month in months or month_range():
        rows, downloaded = download_month(
            month, clicks_dir=clicks_dir, raw_dir=raw_dir, keep_archive=keep_archive
        )
        if downloaded:
            print(f"{month}: {rows:,} climate rows -> {clicks_dir / f'{month}.csv'}")
        else:
            print(f"{month}: already present, skipped")
        written.append(clicks_dir / f"{month}.csv")
    return written


# ---------------------------------------------------------------------------
# Stage 2: clicks + daily pageviews -> data/processed/climate_au_daily.csv
# ---------------------------------------------------------------------------
def available_months(clicks_dir: Path = CLICKS_DIR) -> list[str]:
    """Months (``YYYY-MM``) for which a clicks file exists, in order."""
    return sorted(path.stem for path in clicks_dir.glob("*.csv"))


def month_clicks(month: str, clicks_dir: Path = CLICKS_DIR) -> pd.Series:
    """Clicks landing on Climate change per source page for one month.

    Navigation between the merged climate variants is dropped; every remaining
    variant is treated as the same destination so their inbound clicks combine.
    Indexed by source title, valued by summed click count.
    """
    clicks = pd.read_csv(clicks_dir / f"{month}.csv")
    clicks = clicks[clicks["type"] != "external"]
    internal = clicks["page"].isin(PAGES_TO_COMBINE) & clicks["source"].isin(PAGES_TO_COMBINE)
    clicks = clicks[~internal & clicks["page"].isin(PAGES_TO_COMBINE)]
    clicks = clicks[~clicks["source"].isin(FILTERED_SOURCES)]
    return clicks.groupby("source")["count"].sum()


def _read_pageviews(path: Path, columns: list[str]) -> pd.DataFrame:
    """English-Wikipedia rows of one daily TSV, keeping ``columns``."""
    day = pd.read_csv(
        path,
        sep="\t",
        names=PAGEVIEW_COLUMNS,
        header=None,
        quoting=csv.QUOTE_NONE,  # page titles contain literal double quotes
        usecols=["Project", *columns],
        dtype={"Country": "string", "Project": "string", "PageTitle": "string"},
    )
    return day[day["Project"] == PROJECT].drop(columns="Project")


def _title_to_pageid(month: str, source_titles: set[str], raw_dir: Path) -> pd.Series:
    """Map each source title to the page id it accrued the most views under.

    A clickstream source is a title string; the pageviews are keyed by page id,
    and one page may appear under several title spellings. Each title resolves
    to its dominant page id so renames and redirects collapse onto one page.
    """
    frames = []
    for path in sorted(raw_dir.glob(f"{month}-*.tsv")):
        views = _read_pageviews(path, ["PageID", "PageTitle", "Views"])
        views = views[views["PageTitle"].isin(source_titles)]
        if not views.empty:
            frames.append(views.groupby(["PageID", "PageTitle"], as_index=False)["Views"].sum())
    if not frames:
        return pd.Series(dtype="int64")
    by_title = pd.concat(frames, ignore_index=True).groupby(
        ["PageID", "PageTitle"], as_index=False
    )["Views"].sum()
    return (
        by_title.sort_values("Views")
        .drop_duplicates("PageTitle", keep="last")
        .set_index("PageTitle")["PageID"]
    )


def build_month(
    month: str,
    clicks_dir: Path = CLICKS_DIR,
    raw_dir: Path = RAW_PAGEVIEWS_DIR,
) -> pd.DataFrame:
    """Daily Australian click estimates for one month (long, pageid-keyed).

    For each source page: efficiency is its monthly click-through rate to
    Climate change (clicks / global views), and the day's estimate is that rate
    times the page's Australian views that day. Global and Australian views are
    summed per page id across every title spelling, so pages that were renamed
    mid-history keep a single identity.
    """
    clicks = month_clicks(month, clicks_dir)
    if clicks.empty:
        return pd.DataFrame(columns=PANEL_COLUMNS)

    source_titles = set(clicks.index)
    title_to_pageid = _title_to_pageid(month, source_titles, raw_dir)
    if title_to_pageid.empty:
        return pd.DataFrame(columns=PANEL_COLUMNS)

    # Clicks (by source title) collapsed onto the pages they resolve to.
    counts = clicks.rename_axis("PageTitle").reset_index(name="count")
    counts["PageID"] = counts["PageTitle"].map(title_to_pageid)
    counts = counts.dropna(subset=["PageID"])
    counts["PageID"] = counts["PageID"].astype("int64")
    count_by_pageid = counts.groupby("PageID")["count"].sum()
    pageids = set(count_by_pageid.index)

    # Second pass, now keyed by page id so every title spelling is captured:
    # global views (all countries) for the denominator, Australian views by day.
    title_frames: list[pd.DataFrame] = []
    au_frames: list[pd.DataFrame] = []
    for path in sorted(raw_dir.glob(f"{month}-*.tsv")):
        views = _read_pageviews(path, ["Country", "PageID", "PageTitle", "Views"])
        views = views[views["PageID"].isin(pageids)]
        if views.empty:
            continue
        title_frames.append(views.groupby(["PageID", "PageTitle"], as_index=False)["Views"].sum())
        au = views[views["Country"] == COUNTRY]
        if not au.empty:
            au = au.groupby("PageID", as_index=False)["Views"].sum()
            au["date"] = path.stem
            au_frames.append(au)

    if not title_frames or not au_frames:
        return pd.DataFrame(columns=PANEL_COLUMNS)

    by_title = pd.concat(title_frames, ignore_index=True).groupby(
        ["PageID", "PageTitle"], as_index=False
    )["Views"].sum()
    global_views = by_title.groupby("PageID")["Views"].sum()
    pageid_title = (
        by_title.sort_values("Views").drop_duplicates("PageID", keep="last")
        .set_index("PageID")["PageTitle"]
    )

    efficiency = count_by_pageid / global_views.reindex(count_by_pageid.index)
    efficiency = efficiency[efficiency.notna() & (global_views.reindex(efficiency.index) > 0)]

    au_daily = pd.concat(au_frames, ignore_index=True)
    au_daily = au_daily[au_daily["PageID"].isin(efficiency.index)].copy()
    au_daily["au_count"] = au_daily["PageID"].map(efficiency) * au_daily["Views"]
    au_daily["title"] = au_daily["PageID"].map(pageid_title)
    return au_daily.rename(columns={"PageID": "pageid", "Views": "au_views"})[PANEL_COLUMNS]


def build_panel(
    clicks_dir: Path = CLICKS_DIR,
    raw_dir: Path = RAW_PAGEVIEWS_DIR,
    out_csv: Path = PANEL_CSV,
) -> pd.DataFrame:
    """Build every month and write the combined daily panel CSV."""
    frames: list[pd.DataFrame] = []
    months = available_months(clicks_dir)
    for index, month in enumerate(months, start=1):
        part = build_month(month, clicks_dir, raw_dir)
        if not part.empty:
            frames.append(part)
        print(f"{month}: {len(part):,} rows  [{index}/{len(months)}]", flush=True)

    panel = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(columns=PANEL_COLUMNS)
    )
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(out_csv, index=False)
    return panel
