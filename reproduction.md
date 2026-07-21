# Reproducing The Australia Pageviews Result

## Setup

Create an environment and install the project:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

Download the daily Wikimedia country-project-page TSV files from the
[historical release](https://analytics.wikimedia.org/published/datasets/country_project_page_historical/)
and the
[current release](https://analytics.wikimedia.org/published/datasets/country_project_page/).
Place the files for 2017-02-09 through 2026-02-28 in:

```text
data/raw/pageviews/
```

## Run

### 1. Extract and Build Pageviews

Extract the Australia-only pageview files:

```bash
.venv/bin/python scripts/extract_australia_pageviews.py
```

Build the daily totals:

```bash
.venv/bin/python scripts/build_australia_daily_views.py
```

Compute project-specific statistics:

```bash
.venv/bin/python scripts/compute_project_stats.py
```

Create the figure:

```bash
.venv/bin/python scripts/plot_australia_daily_views.py
```

### 2. Categorise Pages

To apply the categorisation rules and map each unique page to its respective category:

First, aggregate unique pages across all daily files to get their views and QIDs:

```bash
.venv/bin/python scripts/aggregate_pages.py
```

Build the subclass hierarchy graph from `data/categorisation/p279.csv`:

```bash
.venv/bin/python scripts/categorisation/build_p279_graph.py
```

Initialise page-class assignments using `data/categorisation/p31.csv` and the built graph:

```bash
.venv/bin/python scripts/categorisation/init_assignments.py
```

Apply the categorisation rules from `data/categorisation/rules.csv`:

```bash
.venv/bin/python scripts/categorisation/apply_rules.py
```

Produce the intermediate categorised pages CSV file:

```bash
.venv/bin/python scripts/categorisation/produce_final_csv.py
```

Apply aggregation and label rules to simplify categories and produce the final category distribution table:

```bash
.venv/bin/python scripts/categorisation/aggregate.py
```

### 3. Sub-categorise Event Pages

To apply the event-specific sub-categorisation rules to pages categorised as `Events` at the first step, run:

Initialise assignments specifically for Event pages:

```bash
.venv/bin/python scripts/categorisation/init_assignments.py --filter-category Events
```

Apply the sub-categorisation rules:

```bash
.venv/bin/python scripts/categorisation/apply_rules.py --filter-category Events
```

Produce the intermediate categorised event pages CSV file:

```bash
.venv/bin/python scripts/categorisation/produce_final_csv.py --filter-category Events
```

Apply event-specific aggregation and label rules to simplify event sub-categories and produce the event category distribution table:

```bash
.venv/bin/python scripts/categorisation/aggregate.py --filter-category Events
```

### 4. Adjust Non-Events

To finalise the distributions by removing "Non-Events" sub-categories from the event table and moving their counts and views to their appropriate main categories in the main category distribution table, run:

```bash
.venv/bin/python scripts/categorisation/adjust_non_events.py
```

### 5. Build Category Plots

To generate the category distribution treemap plots (standalone non-event categories, event categories, and combined category plots) from the final tables, run:

```bash
.venv/bin/python scripts/categorisation/build_plots.py
```

### 6. Plot Event Timelines

Each event category is defined by a page list in
`data/poi/{bushfires,cyclones,earthquakes,climate}.csv`, giving each page's
`page_id` and display `name`. Build the per-event daily-view CSVs by scanning
the Australia-only pageview TSVs and summing the views of the listed page IDs.
Matching on the page ID captures a page's full history even across renames:

```bash
.venv/bin/python scripts/build_event_views.py
```

Then generate the per-event pageview timeline figures (bushfire, cyclone and
earthquake small-multiple grids, plus the standalone climate-change timeline):

```bash
.venv/bin/python scripts/plot_event_timelines.py
```

### 7. Top Pages by Country and Date Range

Compute the 10 most viewed English Wikipedia pages for a set of country/date-range
queries (Australia and the UK) directly from the raw `data/raw/pageviews/` TSVs.
This writes one ranked CSV per query and one daily views-vs-date figure per query,
highlighting the bushfire pages (Australia, Dec 2019 – Jan 2020) and the cyclone
pages (Australia, Mar 2025):

```bash
.venv/bin/python scripts/compute_top_pages.py
```

### 8. Clickstream Impact

Estimate how many Australian readers reached the Climate change article from
each linking page, and plot the share over time. The estimate combines
Wikimedia's monthly *clickstream* dumps (global source → target click counts on
English Wikipedia) with the daily `data/raw/pageviews/` TSVs already downloaded
in Setup:

    au_clicks(source, day) = clicks(source, month)
                             * au_views(source, day) / global_views(source, month)

First, download the monthly clickstream dumps and filter each to the
climate-related destination pages. This writes one small CSV per month to
`data/clicks/`:

```bash
.venv/bin/python scripts/download_clickstream.py
```

Build the daily Australian impact panel by combining the clicks with the raw
daily pageviews. This scans every `data/raw/pageviews/` TSV once (a few
minutes) and writes a single CSV; it is run once, after which the figure reads
only that CSV:

```bash
.venv/bin/python scripts/build_clickstream_impact.py
```

Then plot the small-multiple figure of each top source's share of Australian
clicks to Climate change:

```bash
.venv/bin/python scripts/plot_clickstream_shares.py
```

## Outputs

- `data/interim/australia/pageviews/`: Australia-only daily pageview TSVs.
- `data/processed/australia_daily_views.csv`: daily total views.
- `data/processed/australia_daily_views_manifest.json`: dataset build metadata.
- `data/processed/project_stats.json`: project-specific page and view statistics.
- `data/processed/views.csv`: aggregated unique pages with views and QIDs.
- `data/interim/class_graph.pkl`: precomputed subclass hierarchy graph.
- `data/interim/assignments.csv`: intermediate state of page-category assignments.
- `outputs/figures/australia_daily_views.png`: rendered figure.
- `outputs/figures/non_event_categories.png` / `outputs/figures/non_event_categories.pdf`: standalone non-event categories treemap.
- `outputs/figures/event_categories.png` / `outputs/figures/event_categories.pdf`: standalone event categories treemap.
- `outputs/figures/combined_categories.png` / `outputs/figures/combined_categories.pdf`: combined category distribution treemap with connection lines.
- `data/interim/categorised_pages.csv`: intermediate categorised pages mapping.
- `data/interim/categorised_pages_labelled.csv`: final categorised pages with aggregation and label rules applied.
- `data/interim/assignments_events.csv`: intermediate state of event page assignments.
- `data/interim/categorised_event_pages.csv`: intermediate categorised event pages mapping.
- `data/interim/categorised_event_pages_labelled.csv`: final categorised event pages with event-specific aggregation and label rules applied.
- `outputs/tables/category_distribution.csv`: final category distribution table (CSV format).
- `outputs/tables/event_category_distribution.csv`: final event category distribution table (CSV format).
- `data/poi/{bushfires,cyclones,earthquakes,climate}.csv`: page lists (`page_id`, `name`) that define each event category.
- `data/processed/event_views/{bushfires,cyclones,earthquakes,climate}.csv`: daily views for the selected event pages, built from the Australia TSVs by matching page IDs.
- `outputs/figures/bushfire.png` / `.pdf`: bushfire event pageview timelines (small-multiple grid).
- `outputs/figures/cyclone.png` / `.pdf`: cyclone event pageview timelines (small-multiple grid).
- `outputs/figures/earthquake.png` / `.pdf`: earthquake event pageview timelines (small-multiple grid).
- `outputs/figures/climate.png` / `.pdf`: standalone climate-change pageview timeline.
- `outputs/tables/top_pages_australia_2025-03-04_2025-03-09.csv`: 10 most viewed pages in Australia, 4–9 Mar 2025 (Rank, Article title, Average daily views).
- `outputs/tables/top_pages_australia_2019-12-30_2020-01-09.csv`: 10 most viewed pages in Australia, 30 Dec 2019 – 9 Jan 2020.
- `outputs/tables/top_pages_uk_2025-03-04_2025-03-09.csv`: 10 most viewed pages in the UK, 4–9 Mar 2025.
- `outputs/figures/top_pages_cyclone.png` / `.pdf`: daily views-vs-date for the Australia 4–9 Mar 2025 top pages (cyclone pages highlighted).
- `outputs/figures/top_pages_bushfire.png` / `.pdf`: daily views-vs-date for the Australia 30 Dec 2019 – 9 Jan 2020 top pages (bushfire pages highlighted).
- `outputs/figures/top_pages_uk.png` / `.pdf`: daily views-vs-date for the UK 4–9 Mar 2025 top pages.
- `data/clicks/{YYYY-MM}.csv`: monthly clickstream rows landing on climate-related pages (`source`, `page`, `type`, `count`), filtered from the Wikimedia enwiki dumps.
- `data/processed/climate_au_daily.csv`: daily Australian click-impact panel for Climate change (`date`, `pageid`, `title`, `au_views`, `au_count`).
- `outputs/figures/clickstream_climate_shares.png` / `.pdf`: small multiples of each top source's share of estimated Australian clicks to Climate change.
