#!/usr/bin/env python3
import pandas as pd
import pickle
import numpy as np
import os
import argparse

def initialise_assignments(output_path='data/interim/assignments.csv', 
                           filter_from=None, 
                           filter_category=None):
    print("Loading data...")
    views_df = pd.read_csv('data/processed/views.csv')
    p31_df = pd.read_csv('data/categorisation/p31.csv')
    p279_df = pd.read_csv('data/categorisation/p279.csv')
    
    # Handle category filtering to mimic the web interface's sub-task initialization
    if filter_from and filter_category:
        print(f"Filtering QIDs from {filter_from} where category is '{filter_category}'...")
        ref_df = pd.read_csv(filter_from, dtype={'category': str})
        target_qids = set(ref_df.loc[ref_df['category'] == filter_category, 'qid'].dropna().astype(int).unique())
        print(f"Found {len(target_qids):,} QIDs matching '{filter_category}'. filtering input pages...")
        views_df['qid'] = views_df['qid'].astype(int)
        views_df = views_df[views_df['qid'].isin(target_qids)].copy()
        print(f"Filtered pages count: {len(views_df):,}")

    # Find P279-only pages on the fly (pages without P31 but with P279)
    print("Finding P279-only pages on the fly...")
    pages_with_p31 = set(p31_df['subject_id'].unique())
    target_ids = set(views_df['qid'].astype(int))
    pages_without_p31 = target_ids - pages_with_p31
    
    p279_subjects = set(p279_df['subject_id'].unique())
    p279_only_set = pages_without_p31 & p279_subjects
    print(f"Found {len(p279_only_set):,} P279-only pages in targeted subset.")
    
    with open('data/interim/class_graph.pkl', 'rb') as f:
        data = pickle.load(f)
        class_to_roots = data['class_to_roots']

    print("Mapping pages to their P31 classes...")
    # A page might have multiple P31 classes. We group them.
    views_df['qid'] = views_df['qid'].astype(int)
    
    # Merge views with p31 to get the initial classes for each page
    merged_df = pd.merge(
        views_df, 
        p31_df, 
        left_on='qid', 
        right_on='subject_id', 
        how='left'
    )
    
    print("Mapping P31 classes to their roots...")
    assignments = []
    no_class_count = 0
    
    for row in merged_df.itertuples(index=False):
        page_id = row.qid
        p31_class = row.object_id
        
        if pd.isna(p31_class):
            if page_id in p279_only_set:
                roots = class_to_roots.get(page_id, {page_id})
                for root in roots:
                    assignments.append({
                        'page_name': row.page_name,
                        'qid': page_id,
                        'views': row.views,
                        'original_p31': page_id,
                        'current_class': root,
                        'is_class': True,
                        'is_page': False
                    })
            else:
                assignments.append({
                    'page_name': row.page_name,
                    'qid': page_id,
                    'views': row.views,
                    'original_p31': page_id,
                    'current_class': page_id,
                    'is_class': False,
                    'is_page': True
                })
                no_class_count += 1
        else:
            p31_class = int(p31_class)
            roots = class_to_roots.get(p31_class, {p31_class})
            
            for root in roots:
                assignments.append({
                    'page_name': row.page_name,
                    'qid': page_id,
                    'views': row.views,
                    'original_p31': p31_class,
                    'current_class': root,
                    'is_class': False,
                    'is_page': False
                })
                
    assignments_df = pd.DataFrame(assignments)
    
    # Drop duplicates just in case
    assignments_df = assignments_df.drop_duplicates(subset=['qid', 'current_class'])
    
    print(f"Created {len(assignments_df):,} assignments.")
    print(f"Pages with no P31 class: {no_class_count:,}")
    
    # Save the initial frontier
    os.makedirs('data/interim', exist_ok=True)
    assignments_df.sort_values(by=['views'], ascending=[False], inplace=True)
    assignments_df.to_csv(output_path, index=False)
    print(f"Saved initial assignments to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize page-class assignments.")
    parser.add_argument("--filter-category", default=None, help="The target category to filter.")
    
    args = parser.parse_args()
    
    filter_category = args.filter_category
    if filter_category:
        cat_lower = filter_category.lower()
        output_path = f"data/interim/assignments_{cat_lower}.csv"
        filter_from = "data/interim/assignments.csv"
    else:
        output_path = "data/interim/assignments.csv"
        filter_from = None
        
    initialise_assignments(output_path=output_path, 
                           filter_from=filter_from, 
                           filter_category=filter_category)
