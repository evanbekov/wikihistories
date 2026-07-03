#!/usr/bin/env python3
import pandas as pd
import pickle
import os
import sys
import argparse

def apply_rules(rules_path='data/categorisation/rules.csv', 
                assignments_path='data/interim/assignments.csv', 
                output_path='data/interim/assignments.csv', 
                fallback_category='Uncategorised'):
    print(f"Loading rules from {rules_path}...")
    rules_df = pd.read_csv(rules_path)
    print(f"Loaded {len(rules_df):,} rules.")
    
    print(f"Loading assignments from {assignments_path}...")
    assignments_df = pd.read_csv(assignments_path, dtype={'category': 'object'})
    
    # Ensure category column exists and is string type
    if 'category' not in assignments_df.columns:
        assignments_df['category'] = pd.Series(dtype='object')
    else:
        assignments_df['category'] = assignments_df['category'].astype('object')
        
    print("Loading class graph...")
    with open('data/interim/class_graph.pkl', 'rb') as f:
        data = pickle.load(f)
        graph = data['graph']
        
    # Helper to find next classes
    # Memoization to speed up repeated queries
    memo = {} # (orig_class, current_root) -> list of next classes
    
    def get_next_classes(orig_class, current_root):
        if orig_class == current_root:
            return [current_root]
            
        cache_key = (orig_class, current_root)
        if cache_key in memo:
            return memo[cache_key]
            
        node_memo = {}
        def dfs(node, visited):
            if node == current_root:
                return set()
                
            if node in node_memo:
                return node_memo[node]
                
            if node in visited:
                return set()
                
            visited.add(node)
            res = set()
            parents = graph.get(node, [])
            
            # If current_root is a direct parent, this node is the next step down on this path
            if current_root in parents:
                res.add(node)
                
            # We still check other parents because there might be multiple paths 
            # leading to different direct children of current_root
            for p in parents:
                if p != current_root:
                    res.update(dfs(p, visited))
                    
            visited.remove(node)
            node_memo[node] = res
            return res
            
        next_classes = dfs(orig_class, set())
        
        # Fallback: if no path found (shouldn't happen if graph is correct), just keep it at current_root
        if not next_classes:
            next_classes = {current_root}
            
        result = list(next_classes)
        memo[cache_key] = result
        return result

    total_pages_in_dataset = assignments_df['qid'].nunique()
    total_views_in_dataset = assignments_df.drop_duplicates(subset=['qid'])['views'].sum()

    print(f"Total unique pages in working dataset: {total_pages_in_dataset:,}")
    print(f"Total views in working dataset: {total_views_in_dataset:,}")
    
    # Apply rules in a single pass exactly as generated
    print("Applying rules in a single pass...")
    for idx, rule in rules_df.iterrows():
        class_id_str = str(rule['class_id']).strip()
        if not (class_id_str.startswith('Q') or class_id_str.startswith('C') or class_id_str.startswith('P')):
            continue
            
        is_class_rule = class_id_str.startswith('C')
        is_page_rule = class_id_str.startswith('P')
        class_id = int(class_id_str.replace('Q', '').replace('C', '').replace('P', ''))
        action = str(rule['action']).strip().lower()
        category = str(rule['category']).strip() if pd.notna(rule['category']) else None
        
        # Print progress every 200 rules
        if idx % 200 == 0 or idx == len(rules_df) - 1:
            print(f"Applying rule {idx}/{len(rules_df)}: {class_id_str} -> {action} {category if category else ''}", flush=True)
        
        if action == 'split' or action == 'auto-split':
            # Find rows to split (only unassigned pages)
            mask = (assignments_df['current_class'] == class_id) & (assignments_df['category'].isna()) & (assignments_df['is_class'] == is_class_rule) & (assignments_df['is_page'] == is_page_rule)
            rows_to_split = assignments_df[mask]
            
            if not rows_to_split.empty:
                # Map each unique orig_class to its next_classes
                unique_orig = rows_to_split['original_p31'].unique()
                orig_to_next = {orig: get_next_classes(orig, class_id) for orig in unique_orig}
                
                # Add next_classes column
                rows_to_split = rows_to_split.copy()
                rows_to_split['next_classes'] = rows_to_split['original_p31'].map(orig_to_next)
                
                # Explode next_classes
                exploded = rows_to_split.explode('next_classes')
                exploded['next_classes'] = exploded['next_classes'].astype('int64')
                
                # Separate into two cases:
                # 1. next_classes is class_id (meaning we split to the page itself)
                # 2. next_classes is not class_id
                self_split_mask = (exploded['next_classes'] == class_id)
                
                # For self-split:
                exploded.loc[self_split_mask, 'current_class'] = exploded.loc[self_split_mask, 'qid']
                exploded.loc[self_split_mask, 'is_page'] = True
                exploded.loc[self_split_mask, 'is_class'] = False
                
                # For normal split:
                exploded.loc[~self_split_mask, 'current_class'] = exploded.loc[~self_split_mask, 'next_classes']
                
                # Drop the temporary next_classes column
                exploded = exploded.drop(columns=['next_classes'])
                
                # Remove old rows and add new rows
                assignments_df = pd.concat([assignments_df[~mask], exploded], ignore_index=True)
                # Drop duplicates just in case a page reached the same next_class via multiple paths
                assignments_df = assignments_df.drop_duplicates(subset=['qid', 'current_class'])
                
        elif action == 'assign':
            if not category:
                continue
                
            # Find rows to assign
            mask = (assignments_df['current_class'] == class_id) & (assignments_df['category'].isna()) & (assignments_df['is_class'] == is_class_rule) & (assignments_df['is_page'] == is_page_rule)
            assigned_ids = assignments_df.loc[mask, 'qid'].unique()
            
            if len(assigned_ids) > 0:
                # Update category for these rows
                assignments_df.loc[mask, 'category'] = str(category)
                
                # Deduplicate: once a page is assigned, we drop all its unassigned alternative paths
                assigned_set = set(assigned_ids)
                all_assigned_mask = assignments_df['qid'].isin(assigned_set)
                unassigned_duplicates_mask = all_assigned_mask & assignments_df['category'].isna()
                
                assignments_df = assignments_df[~unassigned_duplicates_mask]
                
                # Deduplicate the assigned rows so we don't have multiple identical assignments
                assignments_df = assignments_df.drop_duplicates(subset=['qid', 'category'])

    print("\nCalculating final coverage on working dataset...")
    assigned_df = assignments_df[assignments_df['category'].notna()]
    unique_assigned = assigned_df.drop_duplicates(subset=['qid'])
    total_assigned_pages = len(unique_assigned)
    total_assigned_views = unique_assigned['views'].sum()
    
    pages_pct = (total_assigned_pages / total_pages_in_dataset * 100) if total_pages_in_dataset > 0 else 0
    views_pct = (total_assigned_views / total_views_in_dataset * 100) if total_views_in_dataset > 0 else 0
    
    print(f"Final coverage on working dataset: {total_assigned_pages:,} pages ({pages_pct:.2f}%), {total_assigned_views:,} views ({views_pct:.2f}%)")
    
    # Assign fallback_category to any remaining unassigned rows
    unassigned_mask = assignments_df['category'].isna()
    if unassigned_mask.any():
        unassigned_count = assignments_df.loc[unassigned_mask, 'qid'].nunique()
        print(f"Setting category '{fallback_category}' for {unassigned_count:,} pages that didn't match any rules.")
        assignments_df.loc[unassigned_mask, 'category'] = fallback_category

    print("\nSaving updated assignments...")
    assignments_df.to_csv(output_path, index=False)
    print(f"Saved {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply categorisation rules to assignments.")
    parser.add_argument("--filter-category", default=None, help="The target category to filter (e.g., Events).")
    parser.add_argument("--fallback-category", default="Uncategorised", help="Fallback category for unassigned rows (default: Uncategorised).")
    
    args = parser.parse_args()
    
    filter_category = args.filter_category
    if filter_category:
        cat_lower = filter_category.lower()
        singular = "event" if cat_lower == "events" else cat_lower
        rules_path = f"data/categorisation/{singular}_rules.csv"
        assignments_path = f"data/interim/assignments_{cat_lower}.csv"
        output_path = f"data/interim/assignments_{cat_lower}.csv"
    else:
        rules_path = "data/categorisation/rules.csv"
        assignments_path = "data/interim/assignments.csv"
        output_path = "data/interim/assignments.csv"
        
    apply_rules(rules_path=rules_path, 
                assignments_path=assignments_path, 
                output_path=output_path, 
                fallback_category=args.fallback_category)
