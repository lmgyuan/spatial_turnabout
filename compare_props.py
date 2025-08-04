#!/usr/bin/env python3
"""
=============================================================================
compare_props.py - Compare Generated Props with Original Props
=============================================================================

This script compares AI-generated spatial reasoning props from cache files
with original props from the aceattorney dataset. It creates comparison
text files for manual review.

FUNCTIONALITY:
- Reads original props from data/aceattorney_data/final/*.json
- Reads generated props from output_spatial cache files
- Filters only spatial-labeled turns
- Creates side-by-side comparison text files
- Handles both props_cache_*.json and rag_props_cache_*.json

OUTPUT:
- One prop_comparison.txt file per experiment directory
- Shows original vs generated props for each case/turn
- Uses "MISSING DATA" placeholders for unmatched entries

USAGE:
    python compare_props.py

=============================================================================
"""

import json
import os
import glob
import re
from typing import Dict, List, Tuple, Optional

def extract_original_props(reasoning_list: List[str]) -> List[str]:
    """Extract prop statements from reasoning array"""
    props = []
    for item in reasoning_list:
        if item.strip().startswith("Prop "):
            # Remove "Prop X: " prefix and keep the actual prop
            prop_text = re.sub(r'^Prop \d+:\s*', '', item.strip())
            props.append(prop_text)
    return props

def parse_original_data(file_path: str) -> Dict[str, List[str]]:
    """Parse original data file and extract spatial turns with their props"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return {}
    
    case_name = os.path.basename(file_path).replace('.json', '')
    spatial_turns = {}
    turn_idx = 0
    
    for turn in data.get("turns", []):
        # Skip turns without noPresent flag or with noPresent=True
        if turn.get("noPresent", True):
            continue
            
        # Check if turn has spatial label
        turn_labels = turn.get("labels", [])
        has_spatial = False
        
        if isinstance(turn_labels, list) and "spatial" in turn_labels:
            has_spatial = True
        elif isinstance(turn_labels, str) and turn_labels == "spatial":
            has_spatial = True
            
        if not has_spatial:
            continue
            
        # Extract props from reasoning
        reasoning = turn.get("reasoning", [])
        props = extract_original_props(reasoning)
        
        # Store with case_name_turn_idx format to match cache keys
        key = f"{case_name}_turn_{turn_idx}"
        spatial_turns[key] = props
        turn_idx += 1
    
    return spatial_turns

def load_all_original_data() -> Dict[str, List[str]]:
    """Load all original data from aceattorney_data/final/"""
    data_dir = "data/aceattorney_data/final"
    all_original_props = {}
    
    if not os.path.exists(data_dir):
        print(f"Warning: {data_dir} not found")
        return {}
        
    json_files = glob.glob(os.path.join(data_dir, "*.json"))
    print(f"Found {len(json_files)} original data files")
    
    for file_path in json_files:
        case_props = parse_original_data(file_path)
        all_original_props.update(case_props)
        
    print(f"Loaded original props for {len(all_original_props)} spatial turns")
    return all_original_props

def parse_cache_key(cache_key: str) -> Tuple[str, int]:
    """Parse cache key to extract case name and turn index"""
    # Format: "1-3-6_Turnabout_Samurai_turn_0" or "1-3-6_Turnabout_Samurai_turn_0_rag_123456"
    parts = cache_key.split('_turn_')
    if len(parts) != 2:
        return cache_key, 0
    
    case_name = parts[0]
    try:
        # Handle both formats: "0" and "0_rag_123456"
        turn_part = parts[1].split('_')[0]  # Take only the turn number before any additional suffixes
        turn_idx = int(turn_part)
    except (ValueError, IndexError):
        turn_idx = 0
        
    return case_name, turn_idx

def load_cache_file(cache_path: str) -> Dict[str, List[str]]:
    """Load props from a cache file"""
    try:
        with open(cache_path, 'r', encoding='utf-8') as file:
            cache_data = json.load(file)
    except Exception as e:
        print(f"Error reading cache file {cache_path}: {e}")
        return {}
        
    cache_props = {}
    for key, entry in cache_data.items():
        props = entry.get("props", [])
        # Normalize the key to match original data format
        case_name, turn_idx = parse_cache_key(key)
        normalized_key = f"{case_name}_turn_{turn_idx}"
        cache_props[normalized_key] = props
        
    return cache_props

def find_cache_files(output_dir: str) -> List[str]:
    """Find all cache files in output_spatial directory"""
    cache_files = []
    
    # Find props_cache_*.json files
    props_cache_pattern = os.path.join(output_dir, "*prop*", "props_cache_*.json")
    cache_files.extend(glob.glob(props_cache_pattern))
    
    # Find rag_props_cache_*.json files  
    rag_props_cache_pattern = os.path.join(output_dir, "*prop*", "rag_props_cache_*.json")
    cache_files.extend(glob.glob(rag_props_cache_pattern))
    
    return cache_files

def create_comparison_text(original_props: Dict[str, List[str]], 
                          generated_props: Dict[str, List[str]], 
                          experiment_name: str) -> str:
    """Create comparison text for manual review"""
    
    text_lines = []
    text_lines.append("=" * 80)
    text_lines.append(f"PROP COMPARISON: {experiment_name}")
    text_lines.append("=" * 80)
    text_lines.append("")
    
    # Get all unique keys from both datasets
    all_keys = set(original_props.keys()) | set(generated_props.keys())
    
    # Sort keys for consistent output
    sorted_keys = sorted(all_keys)
    
    comparison_count = 0
    for key in sorted_keys:
        # Parse the normalized key format: "case_name_turn_X"
        parts = key.rsplit('_turn_', 1)
        if len(parts) == 2:
            case_name = parts[0]
            turn_idx = parts[1]
        else:
            case_name = key
            turn_idx = "0"
        
        text_lines.append(f"Case: {case_name}, Turn: {turn_idx}")
        text_lines.append("-" * 60)
        
        # Original props
        text_lines.append("ORIGINAL PROPS:")
        orig_props = original_props.get(key, [])
        if orig_props:
            for i, prop in enumerate(orig_props, 1):
                text_lines.append(f"  {i}. {prop}")
        else:
            text_lines.append("  MISSING DATA")
        
        text_lines.append("")
        
        # Generated props
        text_lines.append("GENERATED PROPS:")
        gen_props = generated_props.get(key, [])
        if gen_props:
            for i, prop in enumerate(gen_props, 1):
                text_lines.append(f"  {i}. {prop}")
        else:
            text_lines.append("  MISSING DATA")
            
        text_lines.append("")
        text_lines.append("=" * 60)
        text_lines.append("")
        comparison_count += 1
    
    # Add summary
    text_lines.append(f"SUMMARY:")
    text_lines.append(f"Total comparisons: {comparison_count}")
    text_lines.append(f"Original data entries: {len(original_props)}")
    text_lines.append(f"Generated data entries: {len(generated_props)}")
    text_lines.append("")
    
    return "\n".join(text_lines)

def process_experiment_directory(exp_dir: str, original_props: Dict[str, List[str]]):
    """Process a single experiment directory"""
    exp_name = os.path.basename(exp_dir)
    print(f"Processing experiment: {exp_name}")
    
    # Find cache files in this directory
    cache_files = []
    for cache_pattern in ["props_cache_*.json", "rag_props_cache_*.json"]:
        cache_files.extend(glob.glob(os.path.join(exp_dir, cache_pattern)))
    
    if not cache_files:
        print(f"  No cache files found in {exp_dir}")
        return
        
    # Load all cache data for this experiment
    all_generated_props = {}
    for cache_file in cache_files:
        cache_name = os.path.basename(cache_file)
        print(f"  Loading cache: {cache_name}")
        cache_props = load_cache_file(cache_file)
        all_generated_props.update(cache_props)
    
    print(f"  Loaded {len(all_generated_props)} generated prop entries")
    
    # Create comparison text
    comparison_text = create_comparison_text(original_props, all_generated_props, exp_name)
    
    # Write comparison file
    output_file = os.path.join(exp_dir, "prop_comparison.txt")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(comparison_text)
        print(f"  Created: {output_file}")
    except Exception as e:
        print(f"  Error writing {output_file}: {e}")

def main():
    """Main function to compare props across all experiments"""
    print("Starting prop comparison script...")
    
    # Load all original data
    print("\n1. Loading original data...")
    original_props = load_all_original_data()
    
    if not original_props:
        print("No original data found. Exiting.")
        return
    
    # Find all experiment directories with prop caches
    output_spatial_dir = "output_spatial"
    if not os.path.exists(output_spatial_dir):
        print(f"Error: {output_spatial_dir} directory not found")
        return
        
    print(f"\n2. Finding experiment directories...")
    exp_dirs = []
    for item in os.listdir(output_spatial_dir):
        item_path = os.path.join(output_spatial_dir, item)
        if os.path.isdir(item_path) and "prop" in item:
            exp_dirs.append(item_path)
    
    print(f"Found {len(exp_dirs)} prop experiment directories")
    
    # Process each experiment directory
    print(f"\n3. Processing experiments...")
    for exp_dir in sorted(exp_dirs):
        process_experiment_directory(exp_dir, original_props)
    
    print(f"\nComparison complete! Check prop_comparison.txt files in each experiment directory.")

if __name__ == "__main__":
    main()
