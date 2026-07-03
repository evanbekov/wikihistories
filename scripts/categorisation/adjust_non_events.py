import os
import re
import argparse
import pandas as pd

def parse_args():
    parser = argparse.ArgumentParser(description="Post-process distribution tables to remove Non-Events from events and move them to their appropriate main categories.")
    parser.add_argument('--main-csv', default='outputs/tables/category_distribution.csv', help='Path to main category distribution CSV')
    parser.add_argument('--event-csv', default='outputs/tables/event_category_distribution.csv', help='Path to event category distribution CSV')
    return parser.parse_args()

def main():
    args = parse_args()
    
    print("Post-processing category distributions...")
    
    # 1. Load the category distribution CSVs
    if not os.path.exists(args.main_csv):
        print(f"Error: Main category distribution file {args.main_csv} not found.")
        return
    if not os.path.exists(args.event_csv):
        print(f"Error: Event category distribution file {args.event_csv} not found.")
        return
        
    main_df = pd.read_csv(args.main_csv)
    event_df = pd.read_csv(args.event_csv)
    
    # Parse Non-Events from event_df
    # Category,Pages,Pages %,Views,Views %
    non_event_rows = []
    remaining_event_rows = []
    uncategorised_event_row = None
    
    for _, row in event_df.iterrows():
        cat_name = str(row['Category']).strip()
        if cat_name == 'Total Categorised':
            continue
        if cat_name == 'Uncategorised':
            uncategorised_event_row = row.to_dict()
            continue
            
        match = re.match(r'^Non-Events \(([^)]+)\)$', cat_name)
        if match:
            # Determine mapped main category
            main_cat = match.group(1).strip()
            non_event_rows.append({
                'original_name': cat_name,
                'target_main_category': main_cat,
                'pages': int(row['Pages']),
                'views': int(row['Views'])
            })
        else:
            remaining_event_rows.append({
                'name': cat_name,
                'count': int(row['Pages']),
                'views': int(row['Views'])
            })
            
    if not non_event_rows:
        print("No 'Non-Events (X)' categories found in event category distribution. Nothing to do.")
        return
        
    print(f"Found {len(non_event_rows)} Non-Events categories to move:")
    for nr in non_event_rows:
        print(f"  - {nr['original_name']} ({nr['pages']} pages, {nr['views']:,} views) -> moves to main category '{nr['target_main_category']}'")
        
    # 2. Adjust main_df
    # Let's convert main_df to a dictionary of category -> {pages, views}
    main_categories = {}
    total_row = None
    uncategorised_main_row = None
    
    for _, row in main_df.iterrows():
        cat_name = str(row['Category']).strip()
        if cat_name == 'Total Categorised':
            total_row = row.to_dict()
            continue
        if cat_name == 'Uncategorised':
            uncategorised_main_row = {
                'pages': int(row['Pages']),
                'views': int(row['Views'])
            }
            continue
            
        main_categories[cat_name] = {
            'pages': int(row['Pages']),
            'views': int(row['Views'])
        }
        
    # Subtract Non-Events from 'Events' in main categories, and add to their target category
    total_moved_pages = 0
    total_moved_views = 0
    for nr in non_event_rows:
        pages_to_move = nr['pages']
        views_to_move = nr['views']
        target = nr['target_main_category']
        
        # Add to target
        if target in main_categories:
            main_categories[target]['pages'] += pages_to_move
            main_categories[target]['views'] += views_to_move
        else:
            # Fallback if target category doesn't exist for some reason
            main_categories[target] = {
                'pages': pages_to_move,
                'views': views_to_move
            }
            
        total_moved_pages += pages_to_move
        total_moved_views += views_to_move
        
    if 'Events' in main_categories:
        main_categories['Events']['pages'] -= total_moved_pages
        main_categories['Events']['views'] -= total_moved_views
    else:
        print("Warning: 'Events' category not found in main category distribution table.")
        
    # Recompute total denominators (Total Categorised row remains the same!)
    total_pages_main = int(total_row['Pages']) if total_row else sum(c['pages'] for c in main_categories.values()) + uncategorised_main_row['pages']
    total_views_main = int(total_row['Views']) if total_row else sum(c['views'] for c in main_categories.values()) + uncategorised_main_row['views']
    
    # Rebuild main table rows
    adjusted_main_rows = []
    for cat_name, data in main_categories.items():
        pct_pages = (data['pages'] / total_pages_main) * 100 if total_pages_main > 0 else 0
        pct_views = (data['views'] / total_views_main) * 100 if total_views_main > 0 else 0
        adjusted_main_rows.append({
            'name': cat_name,
            'count': data['pages'],
            'pct_pages': pct_pages,
            'views': data['views'],
            'pct_views': pct_views
        })
        
    # Sort adjusted_main_rows by page count descending (as in the original table)
    adjusted_main_rows = sorted(adjusted_main_rows, key=lambda x: x['count'], reverse=True)
    
    # Save adjusted main category distribution to CSV
    new_main_csv_rows = []
    for r in adjusted_main_rows:
        new_main_csv_rows.append({
            'Category': r['name'],
            'Pages': r['count'],
            'Pages %': f"{r['pct_pages']:.2f}%",
            'Views': r['views'],
            'Views %': f"{r['pct_views']:.2f}%"
        })
    if uncategorised_main_row:
        u_pct_pages = (uncategorised_main_row['pages'] / total_pages_main) * 100 if total_pages_main > 0 else 0
        u_pct_views = (uncategorised_main_row['views'] / total_views_main) * 100 if total_views_main > 0 else 0
        new_main_csv_rows.append({
            'Category': 'Uncategorised',
            'Pages': uncategorised_main_row['pages'],
            'Pages %': f"{u_pct_pages:.2f}%",
            'Views': uncategorised_main_row['views'],
            'Views %': f"{u_pct_views:.2f}%"
        })
    new_main_csv_rows.append({
        'Category': 'Total Categorised',
        'Pages': total_pages_main,
        'Pages %': '100.00%',
        'Views': total_views_main,
        'Views %': '100.00%'
    })
    
    pd.DataFrame(new_main_csv_rows).to_csv(args.main_csv, index=False)
    print(f"Saved adjusted main category distribution CSV to {args.main_csv}")
    
    # 3. Adjust event_df
    # Recompute total denominators for events table (subtracting moved Non-Events)
    new_total_pages_event = sum(r['count'] for r in remaining_event_rows)
    new_total_views_event = sum(r['views'] for r in remaining_event_rows)
    if uncategorised_event_row:
        new_total_pages_event += int(uncategorised_event_row['Pages'])
        new_total_views_event += int(uncategorised_event_row['Views'])
        
    adjusted_event_rows = []
    for r in remaining_event_rows:
        pct_pages = (r['count'] / new_total_pages_event) * 100 if new_total_pages_event > 0 else 0
        pct_views = (r['views'] / new_total_views_event) * 100 if new_total_views_event > 0 else 0
        adjusted_event_rows.append({
            'name': r['name'],
            'count': r['count'],
            'pct_pages': pct_pages,
            'views': r['views'],
            'pct_views': pct_views
        })
        
    # Sort remaining event categories by views count descending (as in original table)
    adjusted_event_rows = sorted(adjusted_event_rows, key=lambda x: x['views'], reverse=True)
    
    # Save adjusted event category distribution to CSV
    new_event_csv_rows = []
    for r in adjusted_event_rows:
        new_event_csv_rows.append({
            'Category': r['name'],
            'Pages': r['count'],
            'Pages %': f"{r['pct_pages']:.2f}%",
            'Views': r['views'],
            'Views %': f"{r['pct_views']:.2f}%"
        })
    if uncategorised_event_row:
        ue_pct_pages = (int(uncategorised_event_row['Pages']) / new_total_pages_event) * 100 if new_total_pages_event > 0 else 0
        ue_pct_views = (int(uncategorised_event_row['Views']) / new_total_views_event) * 100 if new_total_views_event > 0 else 0
        new_event_csv_rows.append({
            'Category': 'Uncategorised',
            'Pages': int(uncategorised_event_row['Pages']),
            'Pages %': f"{ue_pct_pages:.2f}%",
            'Views': int(uncategorised_event_row['Views']),
            'Views %': f"{ue_pct_views:.2f}%"
        })
    total_categorised_pages_event = sum(r['count'] for r in adjusted_event_rows)
    total_pct_pages_event = (total_categorised_pages_event / new_total_pages_event) * 100 if new_total_pages_event > 0 else 0
    total_categorised_views_event = sum(r['views'] for r in adjusted_event_rows)
    total_pct_views_event = (total_categorised_views_event / new_total_views_event) * 100 if new_total_views_event > 0 else 0
    new_event_csv_rows.append({
        'Category': 'Total Categorised',
        'Pages': total_categorised_pages_event,
        'Pages %': f"{total_pct_pages_event:.2f}%",
        'Views': total_categorised_views_event,
        'Views %': f"{total_pct_views_event:.2f}%"
    })
    
    pd.DataFrame(new_event_csv_rows).to_csv(args.event_csv, index=False)
    print(f"Saved adjusted event category distribution CSV to {args.event_csv}")
    
    print("Post-processing complete!")

if __name__ == '__main__':
    main()
