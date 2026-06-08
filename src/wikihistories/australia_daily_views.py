from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from wikihistories.project_summary import update_report_section


START_DATE = date(2017, 2, 9)
END_DATE = date(2026, 2, 28)
RAW_PAGEVIEWS_DIR = Path("data/raw/pageviews")
AUSTRALIA_PAGEVIEWS_DIR = Path("data/interim/australia/pageviews")
PROCESSED_DIR = Path("data/processed")
FIGURES_DIR = Path("outputs/figures")

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
class BuildManifest:
    start_date: str
    end_date: str
    expected_days: int
    files_found: int
    missing_dates: list[str]
    au_rows_read: int
    main_page_rows_excluded: int
    total_views: int
    unique_pages: int
    complete: bool

def iter_dates(start: date = START_DATE, end: date = END_DATE):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)

def expected_raw_paths(raw_dir: Path = RAW_PAGEVIEWS_DIR) -> list[Path]:
    return [raw_dir / f"{day.isoformat()}.tsv" for day in iter_dates()]

def read_australia_pageviews(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        sep="\t",
        names=TSV_COLUMNS,
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

def build_australia_daily_views(
    australia_pageviews_dir: Path = AUSTRALIA_PAGEVIEWS_DIR,
    output_csv: Path = PROCESSED_DIR / "australia_daily_views.csv",
    manifest_json: Path = PROCESSED_DIR / "australia_daily_views_manifest.json",
) -> tuple[pd.DataFrame, BuildManifest]:
    daily_totals: list[dict[str, object]] = []
    missing_dates: list[str] = []
    au_rows_read = 0
    main_page_rows_excluded = 0
    page_ids: set[int] = set()

    for day in iter_dates():
        path = australia_pageviews_dir / f"{day.isoformat()}.tsv"
        if not path.exists():
            missing_dates.append(day.isoformat())
            continue

        au = read_australia_pageviews(path)
        au_rows_read += len(au)

        main_page_mask = au["PageTitle"] == "Main_Page"
        main_page_rows_excluded += int(main_page_mask.sum())
        au = au[~main_page_mask]

        for page_id in au["PageID"]:
            if not pd.isna(page_id):
                page_ids.add(int(page_id))

        daily_totals.append(
            {
                "Date": day.isoformat(),
                "Views": int(au["Views"].sum()),
            }
        )

    result = pd.DataFrame(daily_totals).sort_values("Date")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_csv, index=False)

    manifest = BuildManifest(
        start_date=START_DATE.isoformat(),
        end_date=END_DATE.isoformat(),
        expected_days=len(list(iter_dates())),
        files_found=len(daily_totals),
        missing_dates=missing_dates,
        au_rows_read=au_rows_read,
        main_page_rows_excluded=main_page_rows_excluded,
        total_views=int(result["Views"].sum()) if not result.empty else 0,
        unique_pages=len(page_ids),
        complete=len(missing_dates) == 0,
    )

    manifest_json.parent.mkdir(parents=True, exist_ok=True)
    manifest_json.write_text(
        json.dumps(asdict(manifest), indent=2) + "\n",
        encoding="utf-8",
    )

    return result, manifest

def load_daily_views(path: Path = PROCESSED_DIR / "australia_daily_views.csv") -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["Date"])

def plot_australia_daily_views(
    daily_views: pd.DataFrame,
    output_png: Path = FIGURES_DIR / "australia_daily_views.png",
) -> Path:
    import matplotlib
    import matplotlib.dates as mdates

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 9))
    ax.plot(daily_views["Date"].values, daily_views["Views"].values, linewidth=2)

    ax.set_title("Total Wikipedia views per day (Australia)", size=26)
    ax.set_ylabel("Views", size=26)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.setp(ax.get_xticklabels(), ha="center")
    ax.spines[["top", "right"]].set_visible(False)
    plt.yticks(
        range(0, 3_500_001, 500_000),
        ["0", "0.5M", "1M", "1.5M", "2M", "2.5M", "3M", "3.5M"],
        size=22,
    )
    plt.xticks(size=22, rotation=45)
    plt.tight_layout()

    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, dpi=600)
    plt.close(fig)
    return output_png

def parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()

def format_int(value: int) -> str:
    return f"{value:,}"

def format_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    return parsed.strftime("%-d %B %Y")

def plural(value: int, singular: str, plural_word: str | None = None) -> str:
    word = singular if value == 1 else plural_word or f"{singular}s"
    return f"{format_int(value)} {word}"


def report_values_from_manifest(manifest: BuildManifest) -> dict[str, str]:
    missing_count = len(manifest.missing_dates)
    daily_average = round(manifest.total_views / manifest.files_found)
    missing_source_days_sentence = (
        "The source dataset used here covers the full requested date range."
        if manifest.complete
        else (
            "The source dataset used here is missing "
            f"{plural(missing_count, 'raw source day')}."
        )
    )

    return {
        "australia_pageview_rows": format_int(manifest.au_rows_read),
        "daily_average_views": format_int(daily_average),
        "expected_days": format_int(manifest.expected_days),
        "files_found": format_int(manifest.files_found),
        "figure": str(FIGURES_DIR / "australia_daily_views.png"),
        "total_views": format_int(manifest.total_views),
        "unique_pages": format_int(manifest.unique_pages),
        "missing_days_number": format_int(missing_count),
        "missing_days": ", ".join(format_date(date) for date in manifest.missing_dates),
    }


def update_australia_pageviews_report(
    manifest_json: Path = PROCESSED_DIR / "australia_daily_views_manifest.json",
) -> Path:
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    manifest = BuildManifest(**data)
    return update_report_section(
        "australia_pageviews",
        report_values_from_manifest(manifest),
    )
