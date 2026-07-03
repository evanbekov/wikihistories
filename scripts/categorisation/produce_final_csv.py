#!/usr/bin/env python3
import pandas as pd
import os
import argparse

def main(assignments_path='data/interim/assignments.csv', output_path='data/interim/categorised_pages.csv'):
    print(f"Loading assignments from {assignments_path}...")
    df = pd.read_csv(assignments_path)
    
    print("Aggregating categories per page...")
    # Group by qid to find the final category for each page
    # Since page_name and views are the same for the same qid, we can group by qid, page_name, and views
    
    # Let's define an aggregation function for category
    def aggregate_categories(series):
        # Drop NaNs and strip whitespace
        cats = series.dropna().astype(str).str.strip()
        # Filter out empty strings
        cats = cats[cats != '']
        if cats.empty:
            return None
        # Get unique categories in order of appearance
        unique_cats = []
        for cat in cats:
            if cat not in unique_cats:
                unique_cats.append(cat)
        return '; '.join(unique_cats)

    # Group by qid and aggregate
    aggregated = df.groupby('qid').agg({
        'page_name': 'first',
        'views': 'first',
        'category': aggregate_categories
    }).reset_index()
    
    # Sort by views descending
    aggregated = aggregated.sort_values(by='views', ascending=False)
    
    # Reorder columns
    aggregated = aggregated[['page_name', 'qid', 'views', 'category']]
    
    # Save to output_path
    os.makedirs('data/interim', exist_ok=True)
    aggregated.to_csv(output_path, index=False)
    
    print(f"Saved {len(aggregated):,} unique pages to {output_path}")
    
    # Print statistics
    total_pages = len(aggregated)
    categorised_pages = aggregated['category'].notna().sum()
    categorised_pct = (categorised_pages / total_pages * 100) if total_pages > 0 else 0
    
    print(f"Total unique pages: {total_pages:,}")
    print(f"Categorised pages: {categorised_pages:,} ({categorised_pct:.2f}%)")
    print(f"Uncategorised pages: {total_pages - categorised_pages:,} ({100 - categorised_pct:.2f}%)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Produce final aggregated CSV per page from assignments.")
    parser.add_argument("--filter-category", default=None, help="The target category to filter (e.g., Events).")
    
    args = parser.parse_args()
    
    filter_category = args.filter_category
    if filter_category:
        cat_lower = filter_category.lower()
        singular = "event" if cat_lower == "events" else cat_lower
        assignments_path = f"data/interim/assignments_{cat_lower}.csv"
        output_path = f"data/interim/categorised_{singular}_pages.csv"
    else:
        assignments_path = "data/interim/assignments.csv"
        output_path = "data/interim/categorised_pages.csv"
        
    main(assignments_path=assignments_path, output_path=output_path)
