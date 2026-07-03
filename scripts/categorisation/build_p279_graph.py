#!/usr/bin/env python3
import pandas as pd
import pickle
from collections import defaultdict
import os

def build_graph():
    print("Loading p279.csv...")
    p279_df = pd.read_csv('data/categorisation/p279.csv')
    
    print("Building full directed graph (child -> parents)...")
    full_graph = defaultdict(list)
    for row in p279_df.itertuples(index=False):
        full_graph[row.subject_id].append(row.object_id)
        
    print(f"Full graph built with {len(full_graph):,} nodes having parents.")
    return full_graph, p279_df

def find_roots_and_subgraph(full_graph, p279_df):
    print("Precomputing paths to roots and extracting subgraph...")
    
    # We only care about classes that are actually used in our dataset
    p31 = pd.read_csv('data/categorisation/p31.csv')
    relevant_classes = set(p31['object_id'].unique())
    print(f"Found {len(relevant_classes):,} unique classes used in p31.")
    
    # Find P279-only pages on the fly (pages without P31 but with P279)
    views_df = pd.read_csv('data/processed/views.csv')
    target_ids = set(views_df['qid'].astype(int))
    pages_with_p31 = set(p31['subject_id'].unique())
    pages_without_p31 = target_ids - pages_with_p31
    
    p279_subjects = set(p279_df['subject_id'].unique())
    p279_classes = pages_without_p31 & p279_subjects
    
    if len(p279_classes) > 0:
        relevant_classes.update(p279_classes)
        print(f"Added {len(p279_classes):,} P279-only pages to relevant classes on the fly.")
    
    # Memoization cache for paths to roots
    roots_cache = {}
    
    # This will store ONLY the edges we actually traverse
    subgraph = defaultdict(list)
    
    def get_roots(node, visited):
        if node in roots_cache:
            return roots_cache[node]
            
        # If we've seen this node in the current path, we have a cycle
        if node in visited:
            return {node}
            
        parents = full_graph.get(node, [])
        
        # If no parents, this is a root
        if not parents:
            roots_cache[node] = {node}
            return {node}
            
        visited.add(node)
        node_roots = set()
        
        for parent in parents:
            # Add the edge to our subgraph
            if parent not in subgraph[node]:
                subgraph[node].append(parent)
                
            node_roots.update(get_roots(parent, visited))
            
        visited.remove(node)
        roots_cache[node] = node_roots
        return node_roots

    # Calculate roots for all relevant classes and build the subgraph simultaneously
    class_to_roots = {}
    total_classes = len(relevant_classes)
    for i, cls in enumerate(relevant_classes):
        if i > 0 and i % 5000 == 0:
            print(f"Processed {i}/{total_classes} classes...")
        class_to_roots[cls] = get_roots(cls, set())
        
    print("Finished precomputing roots and extracting subgraph.")
    
    all_roots = set()
    for roots in class_to_roots.values():
        all_roots.update(roots)
    print(f"Found {len(all_roots):,} unique root classes.")
    print(f"Subgraph contains {len(subgraph):,} nodes with parents (down from {len(full_graph):,}).")
    
    # Save the subgraph and the precomputed roots
    print("Saving subgraph and roots to disk...")
    os.makedirs('data/interim', exist_ok=True)
    with open('data/interim/class_graph.pkl', 'wb') as f:
        pickle.dump({
            'graph': dict(subgraph), # child -> list of parents (only for traversed paths)
            'class_to_roots': class_to_roots
        }, f)
    print("Saved to data/interim/class_graph.pkl")

if __name__ == "__main__":
    full_graph, p279_df = build_graph()
    find_roots_and_subgraph(full_graph, p279_df)
