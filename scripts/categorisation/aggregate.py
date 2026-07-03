#!/usr/bin/env python3
import pandas as pd
import os
import argparse

def main(filter_category=None):
    if filter_category:
        cat_lower = filter_category.lower()
        singular = "event" if cat_lower == "events" else cat_lower
        
        input_path = f"data/interim/categorised_{singular}_pages.csv"
        rules_path = f"data/categorisation/{cat_lower}_aggregation_rules.csv"
        label_rules_path = f"data/categorisation/{singular}_label_rules.csv"
        output_path = f"data/interim/categorised_{singular}_pages_labelled.csv"
        table_csv_path = f"outputs/tables/{singular}_category_distribution.csv"
    else:
        input_path = "data/interim/categorised_pages.csv"
        rules_path = "data/categorisation/aggregation_rules.csv"
        label_rules_path = "data/categorisation/label_rules.csv"
        output_path = "data/interim/categorised_pages_labelled.csv"
        table_csv_path = "outputs/tables/category_distribution.csv"

    print(f"Loading data from {input_path}...")
    if not os.path.exists(input_path):
        print(f"Error: {input_path} does not exist. Please run produce_final_csv.py first.")
        return
        
    df = pd.read_csv(input_path)
    print(f"Loaded {len(df):,} pages from {input_path}")
    
    print("Loading rules...")
    if not os.path.exists(rules_path):
        print(f"Error: Rules file {rules_path} is missing.")
        return
        
    agg_rules_df = pd.read_csv(rules_path)
    
    # Build mapping dictionaries
    # aggregation_rules maps label -> category
    agg_map = dict(zip(agg_rules_df['label'].str.strip(), agg_rules_df['category'].str.strip()))
    
    label_map = {}
    if label_rules_path and os.path.exists(label_rules_path):
        print(f"Loading label rules from {label_rules_path}...")
        label_rules_df = pd.read_csv(label_rules_path)
        label_map = dict(zip(label_rules_df['category'].str.strip(), label_rules_df['label'].str.strip()))
    else:
        print("Warning: Label rules file not found or not provided.")
        
    def map_category(cat_val):
        if pd.isna(cat_val):
            return "Uncategorised" if filter_category else cat_val
            
        part = str(cat_val).strip()
        if not part or (filter_category and part == 'Uncategorised'):
            return "Uncategorised" if filter_category else None
            
        # 1. Apply aggregation rules
        mapped = agg_map.get(part, part)
        
        # 2. Apply label rules
        final_label = label_map.get(mapped, mapped)
        
        return final_label
        
    print("Applying aggregation and label rules...")
    df['category'] = df['category'].apply(map_category)
    
    # Save the resulting dataframe in data/interim folder
    os.makedirs('data/interim', exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved resulting dataframe to {output_path}")
    
    # Generate distribution table
    counts = df['category'].value_counts(dropna=False)
    views_by_cat = df.groupby('category', dropna=False)['views'].sum()
    total_views = df['views'].sum()
    
    # Collect categorized and uncategorized rows
    rows_data = []
    uncategorised_row = None
    
    for cat, count in counts.items():
        pct_pages = (count / len(df)) * 100
        cat_views = views_by_cat.get(cat, 0)
        pct_views = (cat_views / total_views) * 100 if total_views > 0 else 0
        
        if pd.isna(cat) or cat == 'Uncategorised':
            if uncategorised_row:
                # Merge if we somehow have both NaN and 'Uncategorised'
                uncategorised_row['count'] += count
                uncategorised_row['pct_pages'] += pct_pages
                uncategorised_row['views'] += cat_views
                uncategorised_row['pct_views'] += pct_views
            else:
                uncategorised_row = {
                    'name': 'Uncategorised',
                    'count': count,
                    'pct_pages': pct_pages,
                    'views': cat_views,
                    'pct_views': pct_views
                }
        else:
            rows_data.append({
                'name': str(cat),
                'count': count,
                'pct_pages': pct_pages,
                'views': cat_views,
                'pct_views': pct_views
            })
            
    # Group rows with duplicate names (since different categories might map to the same label)
    grouped_rows = {}
    for r in rows_data:
        name = r['name']
        if name not in grouped_rows:
            grouped_rows[name] = {
                'name': name,
                'count': 0,
                'pct_pages': 0.0,
                'views': 0,
                'pct_views': 0.0
            }
        grouped_rows[name]['count'] += r['count']
        grouped_rows[name]['pct_pages'] += r['pct_pages']
        grouped_rows[name]['views'] += r['views']
        grouped_rows[name]['pct_views'] += r['pct_views']
        
    rows_data = list(grouped_rows.values())
    
    # Sort categorized rows
    # For events, sort by views descending. For main, sort by page count descending.
    if filter_category:
        rows_data = sorted(rows_data, key=lambda x: x['views'], reverse=True)
    else:
        rows_data = sorted(rows_data, key=lambda x: x['count'], reverse=True)
        
    total_categorised_pages = sum(r['count'] for r in rows_data)
    total_pct_pages = (total_categorised_pages / len(df)) * 100
    total_categorised_views = sum(r['views'] for r in rows_data)
    total_pct_views = (total_categorised_views / total_views) * 100 if total_views > 0 else 0
    
    # Save as CSV
    csv_rows = []
    for r in rows_data:
        csv_rows.append({
            'Category': r['name'],
            'Pages': r['count'],
            'Pages %': f"{r['pct_pages']:.2f}%",
            'Views': r['views'],
            'Views %': f"{r['pct_views']:.2f}%"
        })
    if uncategorised_row:
        csv_rows.append({
            'Category': uncategorised_row['name'],
            'Pages': uncategorised_row['count'],
            'Pages %': f"{uncategorised_row['pct_pages']:.2f}%",
            'Views': uncategorised_row['views'],
            'Views %': f"{uncategorised_row['pct_views']:.2f}%"
        })
    csv_rows.append({
        'Category': 'Total Categorised',
        'Pages': total_categorised_pages,
        'Pages %': f"{total_pct_pages:.2f}%",
        'Views': total_categorised_views,
        'Views %': f"{total_pct_views:.2f}%"
    })
    csv_df = pd.DataFrame(csv_rows)
    os.makedirs('outputs/tables', exist_ok=True)
    csv_df.to_csv(table_csv_path, index=False)
    print(f"Saved category distribution CSV to {table_csv_path}")
    
    # Print the table to console
    print("\n" + csv_df.to_string(index=False) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aggregate page categories using aggregation and label rules.")
    parser.add_argument("--filter-category", default=None, help="The target category to filter (e.g., Events).")
    
    args = parser.parse_args()
    main(filter_category=args.filter_category)
