#!/usr/bin/env python3
from __future__ import annotations

from wikihistories.australia_daily_views import (
    load_daily_views,
    plot_australia_daily_views,
    update_australia_pageviews_report,
)
from wikihistories.project_summary import render_readme


def main() -> None:
    output = plot_australia_daily_views(load_daily_views())
    print(f"Wrote {output}")
    update_australia_pageviews_report()
    render_readme()
    print("Updated report.json and README.md")

if __name__ == "__main__":
    main()
