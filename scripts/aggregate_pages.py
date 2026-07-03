#!/usr/bin/env python3
import csv
import os
import pandas as pd
from pathlib import Path
from collections import defaultdict
from wikihistories.australia_daily_views import AUSTRALIA_PAGEVIEWS_DIR, iter_dates

def main():
    print("Aggregating pageviews across all daily files...", flush=True)
    
    # Dictionary to store: qid -> {page_name -> views}
    # We will aggregate views per (qid, page_name)
    page_stats = defaultdict(int)
    # Also keep track of pages with no Wikidata ID or invalid Wikidata ID
    no_qid_views = 0
    no_qid_count = set()
    
    dates = list(iter_dates())
    total_dates = len(dates)
    
    for idx, day in enumerate(dates, 1):
        path = AUSTRALIA_PAGEVIEWS_DIR / f"{day.isoformat()}.tsv"
        if not path.exists():
            continue
            
        if idx % 200 == 0 or idx == 1 or idx == total_dates:
            print(f"Processing day {idx}/{total_dates}: {day.isoformat()}...", flush=True)
            
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
            for row in reader:
                if len(row) < 7:
                    continue
                # Columns: Country, CountryCode, Project, PageID, PageTitle, WikidataID, Views
                page_title = row[4]
                wikidata_id = row[5]
                try:
                    views = int(row[6])
                except ValueError:
                    continue
                
                if page_title == "Main_Page":
                    continue
                    
                if not wikidata_id or not wikidata_id.startswith("Q"):
                    no_qid_views += views
                    no_qid_count.add(page_title)
                    continue
                    
                try:
                    qid = int(wikidata_id[1:])
                except ValueError:
                    no_qid_views += views
                    no_qid_count.add(page_title)
                    continue
                
                page_stats[(qid, page_title)] += views

    print(f"Finished reading files. Aggregating results...", flush=True)
    print(f"Total pages without QID: {len(no_qid_count):,}")
    print(f"Total views of pages without QID: {no_qid_views:,}")
    
    # Now, for each QID, we might have multiple page titles (e.g. from different language wikis, or renames).
    # We will select the page title with the highest views for each QID, and sum all views for that QID.
    qid_to_titles = defaultdict(list)
    for (qid, title), views in page_stats.items():
        qid_to_titles[qid].append((title, views))
        
    final_rows = []
    for qid, titles_views in qid_to_titles.items():
        # Sum views across all titles for this QID
        total_views = sum(v for t, v in titles_views)
        # Find the most viewed title
        best_title = max(titles_views, key=lambda x: x[1])[0]
        final_rows.append({
            'page_name': best_title,
            'views': total_views,
            'qid': qid
        })
        
    df = pd.DataFrame(final_rows)
    df = df.sort_values(by='views', ascending=False)
    
    os.makedirs('data/processed', exist_ok=True)
    output_path = 'data/processed/views.csv'
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df):,} unique pages to {output_path}")
    print(f"Total views of pages with QID: {df['views'].sum():,}")

if __name__ == "__main__":
    main()
