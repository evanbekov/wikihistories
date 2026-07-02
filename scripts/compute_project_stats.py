#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

from wikihistories.australia_daily_views import (
    AUSTRALIA_PAGEVIEWS_DIR,
    PROCESSED_DIR,
    START_DATE,
    END_DATE,
    iter_dates,
    update_australia_pageviews_report,
)
from wikihistories.project_summary import render_readme

def main() -> None:
    project_views: dict[str, int] = {}
    project_pages: dict[str, set[int]] = {}

    print("Computing project statistics across all daily files...", flush=True)

    for day in iter_dates():
        path = AUSTRALIA_PAGEVIEWS_DIR / f"{day.isoformat()}.tsv"
        if not path.exists():
            continue

        df = pd.read_csv(
            path,
            sep="\t",
            names=["Country", "CountryCode", "Project", "PageID", "PageTitle", "WikidataID", "Views"],
            header=None,
            quoting=csv.QUOTE_NONE,
            usecols=["Project", "PageID", "PageTitle", "Views"],
            dtype={
                "Project": "string",
                "PageID": "Int64",
                "PageTitle": "string",
                "Views": "int64",
            },
        )

        # Exclude Main_Page
        df = df[df["PageTitle"] != "Main_Page"]

        for proj, grp in df.groupby("Project"):
            proj_str = str(proj)
            
            # Sum views
            views_sum = int(grp["Views"].sum())
            project_views[proj_str] = project_views.get(proj_str, 0) + views_sum

            # Accumulate unique page IDs (excluding NaNs)
            if proj_str not in project_pages:
                project_pages[proj_str] = set()
            valid_page_ids = grp["PageID"].dropna().astype(int)
            project_pages[proj_str].update(valid_page_ids)

    # Calculate overall totals
    total_views = sum(project_views.values())
    
    # Calculate unique page IDs per project
    project_page_counts = {proj: len(pages) for proj, pages in project_pages.items()}
    total_unique_pages = sum(project_page_counts.values())

    print(f"\nTotal Views: {total_views:,}")
    print(f"Total Unique Pages (sum of per-project uniques): {total_unique_pages:,}")

    # Compute percentages formatted as string to 1 decimal place
    en_pages_pct = f"{(project_page_counts.get('en.wikipedia', 0) / total_unique_pages) * 100:.1f}"
    zh_pages_pct = f"{(project_page_counts.get('zh.wikipedia', 0) / total_unique_pages) * 100:.1f}"
    
    en_views_pct = f"{(project_views.get('en.wikipedia', 0) / total_views) * 100:.1f}"
    zh_views_pct = f"{(project_views.get('zh.wikipedia', 0) / total_views) * 100:.1f}"

    stats_data = {
        "en_pages_pct": en_pages_pct,
        "zh_pages_pct": zh_pages_pct,
        "en_views_pct": en_views_pct,
        "zh_views_pct": zh_views_pct,
    }

    print("\nComputed Statistics:")
    print(json.dumps(stats_data, indent=2))

    # Save to data/processed/project_stats.json
    stats_json = PROCESSED_DIR / "project_stats.json"
    stats_json.parent.mkdir(parents=True, exist_ok=True)
    stats_json.write_text(json.dumps(stats_data, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved stats to {stats_json}")

    # Update report.json and README.md
    update_australia_pageviews_report()
    render_readme()
    print("Updated report.json and README.md successfully!")

if __name__ == "__main__":
    main()
