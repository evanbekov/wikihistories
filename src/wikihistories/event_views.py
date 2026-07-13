"""Build per-event daily pageview CSVs from the Australia TSVs.

Each event category (bushfires, cyclones, earthquakes, climate) is defined by a
list of Wikipedia pages in ``data/poi/{name}.csv`` giving each page's ``page_id``
and display ``name``. This module scans the Australia-only daily TSVs, sums the
views of the listed pages by day (matched on page ID, which stays constant when
a page is renamed), and writes them to ``data/processed/event_views/{name}.csv``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from wikihistories.australia_daily_views import (
    AUSTRALIA_PAGEVIEWS_DIR,
    iter_dates,
    read_australia_pageviews,
)

POI_DIR = Path("data/poi")
EVENT_VIEWS_DIR = Path("data/processed/event_views")

EVENT_CATEGORIES = ["bushfires", "cyclones", "earthquakes", "climate"]


def load_page_ids(csv_path: Path) -> dict[int, str]:
    """Map each page_id to its display name."""
    pages = pd.read_csv(csv_path)
    return dict(zip(pages["page_id"].astype("int64"), pages["name"].astype("object")))


def build_event_views(
    name: str,
    australia_pageviews_dir: Path = AUSTRALIA_PAGEVIEWS_DIR,
    poi_dir: Path = POI_DIR,
    output_dir: Path = EVENT_VIEWS_DIR,
) -> Path:
    """Build the ``{name}.csv`` daily-views file for one event category."""
    id_to_name = load_page_ids(poi_dir / f"{name}.csv")
    target_ids = set(id_to_name)

    frames: list[pd.DataFrame] = []
    for day in iter_dates():
        path = australia_pageviews_dir / f"{day.isoformat()}.tsv"
        if not path.exists():
            continue

        au = read_australia_pageviews(path)
        matched = au[au["PageID"].isin(target_ids)]
        if matched.empty:
            continue

        frames.append(
            pd.DataFrame(
                {
                    "page_name": matched["PageID"].map(id_to_name).astype("object"),
                    "date": day.isoformat(),
                    "views": matched["Views"].to_numpy(),
                }
            )
        )

    if frames:
        combined = pd.concat(frames, ignore_index=True)
        result = (
            combined.groupby(["page_name", "date"], as_index=False)["views"]
            .sum()
            .sort_values(["page_name", "date"])
            .reset_index(drop=True)
        )
    else:
        result = pd.DataFrame(columns=["page_name", "date", "views"])

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{name}.csv"
    result.to_csv(output_path, index=False)
    return output_path


def build_all_event_views() -> list[Path]:
    return [build_event_views(name) for name in EVENT_CATEGORIES]
