#!/usr/bin/env python3
from __future__ import annotations

from wikihistories.australia_daily_views import build_australia_daily_views
from wikihistories.australia_daily_views import update_australia_pageviews_report
from wikihistories.project_summary import render_readme

def main() -> None:
    daily_views, manifest = build_australia_daily_views()
    print(f"Wrote {len(daily_views)} daily totals")
    print(f"Total views: {manifest.total_views:,}")
    print(f"Unique pages: {manifest.unique_pages:,}")
    print(f"Complete date range: {manifest.complete}")
    if manifest.missing_dates:
        print(f"Warning: missing {len(manifest.missing_dates)} dates")
        print("Missing dates: " + ", ".join(manifest.missing_dates))
    update_australia_pageviews_report()
    render_readme()
    print("Updated report.json and README.md")

if __name__ == "__main__":
    main()
