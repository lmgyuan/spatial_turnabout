import json
import os
import copy
from collections import defaultdict

# --- Configuration ---
MAPPING_PATH = "./sc0_to_1-1-1_mapping.json"
TEMPLATE_JSON_PATH = "../../final/1-1-1_The_First_Turnabout.json"
OUTPUT_DIR = "../constructed_json"

def construct_multilingual_json(lang_code, jsonl_path=None):
    """
    Construct a JSON file in the target language using the mapping and template
    
    Args:
        lang_code: Language code (e.g., 'en', 'jp', 'fr')
        jsonl_path: Path to the JSONL file for the language (if None, constructs path)
    """
    if jsonl_path is None:
        jsonl_path = f"../GS1/{lang_code}/sc0_text_u.mdt.jsonl"
    
    output_path = f"{OUTPUT_DIR}/1-1-1_The_First_Turnabout_{lang_code}.json"
    
    print(f"Constructing {lang_code} version from {jsonl_path}")
    print(f"Output will be saved to {output_path}")
    
    # Load template JSON
    with open(TEMPLATE_JSON_PATH, 'r', encoding='utf-8') as f:
        template_data = json.load(f)
    
    # Create a deep copy to avoid modifying the original
    new_json = copy.deepcopy(template_data)
    
    # Load the mapping
    with open(MAPPING_PATH, 'r', encoding='utf-8') as f:
        mapping_data = json.load(f)
    
    # Load JSONL contents
    jsonl_contents = load_jsonl_contents(jsonl_path)
    print(f"Loaded {len(jsonl_contents)} content items from JSONL")
    
    # Organize mappings for easier lookup
    content_segments = organize_mappings(mapping_data["mappings"])
    
    # Replace content in the JSON structure
    replace_content(new_json, content_segments, jsonl_contents)
    
    # Write the output file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(new_json, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully created {lang_code} version at: {output_path}")
    
    # Return stats about what was replaced
    stats = {
        "language": lang_code,
        "total_jsonl_items": len(jsonl_contents),
        "segments_replaced": count_replacements(content_segments)
    }
    return stats

def load_jsonl_contents(path):
    """Load all content entries from the JSONL file into a list by position"""
    contents = {}
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if line.strip():
                try:
                    item = json.loads(line.strip())
                    content = item.get('content', '')
                    if content and content.strip():
                        contents[i] = content
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse line {i}: {line[:50]}...")
    return contents

def organize_mappings(mappings):
    """
    Organize mappings into a structure that makes it easy to replace content
    Returns a dict with keys for each segment type (prevContext, newContext, testimony)
    """
    segments = defaultdict(list)
    
    # Group by top-level prevContext (turn_index 0)
    top_prevcontext = []
    
    # Group by turn and field type
    turn_segments = defaultdict(lambda: defaultdict(list))
    
    # First pass - group by location
    for mapping in mappings:
        jsonl_id = mapping["jsonl_id"]
        turn_idx = mapping["case_turn_index"]
        field_type = mapping["case_field_type"]
        
        # Handle top-level prevContext specially
        if turn_idx == 0 and field_type == "prevContext":
            top_prevcontext.append((jsonl_id, mapping))
        elif field_type == "testimony":
            testimony_idx = mapping.get("testimony_index", 0)
            turn_segments[turn_idx][f"testimony_{testimony_idx}"].append((jsonl_id, mapping))
        else:
            turn_segments[turn_idx][field_type].append((jsonl_id, mapping))
    
    # Second pass - sort each group by JSONL ID for proper sequence
    if top_prevcontext:
        segments["top_prevcontext"] = [m for _, m in sorted(top_prevcontext)]
    
    for turn_idx in turn_segments:
        for field_type in turn_segments[turn_idx]:
            sorted_items = sorted(turn_segments[turn_idx][field_type])
            location_key = f"turn_{turn_idx}_{field_type}"
            segments[location_key] = [m for _, m in sorted_items]
    
    return segments

def replace_content(json_data, content_segments, jsonl_contents):
    """Replace content in the JSON structure using the mapping and JSONL content"""
    # Replace top-level prevContext if it exists
    if "top_prevcontext" in content_segments and "prevContext" in json_data:
        jsonl_ids = [m["jsonl_id"] for m in content_segments["top_prevcontext"]]
        text_parts = [jsonl_contents[j_id] for j_id in jsonl_ids if j_id in jsonl_contents]
        if text_parts:
            json_data["prevContext"] = " ".join(text_parts)
            print(f"Replaced top-level prevContext with {len(text_parts)} fragments")
    
    # Replace turn-specific content
    for turn_idx, turn in enumerate(json_data.get("turns", []), 1):
        # Replace newContext
        newcontext_key = f"turn_{turn_idx}_newContext"
        if newcontext_key in content_segments and "newContext" in turn:
            jsonl_ids = [m["jsonl_id"] for m in content_segments[newcontext_key]]
            text_parts = [jsonl_contents[j_id] for j_id in jsonl_ids if j_id in jsonl_contents]
            if text_parts:
                turn["newContext"] = " ".join(text_parts)
                print(f"Replaced newContext in turn {turn_idx} with {len(text_parts)} fragments")
        
        # Replace prevContext if it exists (less common)
        prevcontext_key = f"turn_{turn_idx}_prevContext"
        if prevcontext_key in content_segments and "prevContext" in turn:
            jsonl_ids = [m["jsonl_id"] for m in content_segments[prevcontext_key]]
            text_parts = [jsonl_contents[j_id] for j_id in jsonl_ids if j_id in jsonl_contents]
            if text_parts:
                turn["prevContext"] = " ".join(text_parts)
                print(f"Replaced prevContext in turn {turn_idx} with {len(text_parts)} fragments")
        
        # Replace testimonies
        if "testimonies" in turn:
            for testimony_idx, testimony in enumerate(turn["testimonies"]):
                testimony_key = f"turn_{turn_idx}_testimony_{testimony_idx}"
                if testimony_key in content_segments and "testimony" in testimony:
                    jsonl_ids = [m["jsonl_id"] for m in content_segments[testimony_key]]
                    text_parts = [jsonl_contents[j_id] for j_id in jsonl_ids if j_id in jsonl_contents]
                    if text_parts:
                        testimony["testimony"] = " ".join(text_parts)
                        print(f"Replaced testimony {testimony_idx} in turn {turn_idx} with {len(text_parts)} fragments")

def count_replacements(content_segments):
    """Count how many segments were replaced in the JSON"""
    return sum(len(segments) for segments in content_segments.values())

def main():
    print("Multilingual JSON Construction Tool")
    print("===================================")
    
    # Process English version as a test/reference
    en_stats = construct_multilingual_json('en')
    print(f"\nSuccessfully processed English version.")
    print(f"Replaced {en_stats['segments_replaced']} content segments with " + 
          f"{en_stats['total_jsonl_items']} JSONL items.\n")
    
    # List available language codes (you would customize this based on your files)
    available_langs = ['en']  # Add other language codes as needed
    for lang in available_langs[1:]:  # Skip English which we already processed
        try:
            jsonl_path = f"../GS1/{lang}/sc0_text_u.mdt.jsonl"
            if os.path.exists(jsonl_path):
                stats = construct_multilingual_json(lang)
                print(f"\nSuccessfully processed {lang} version.")
                print(f"Replaced {stats['segments_replaced']} content segments with " + 
                      f"{stats['total_jsonl_items']} JSONL items.\n")
            else:
                print(f"Skipping {lang} - JSONL file not found at: {jsonl_path}")
        except Exception as e:
            print(f"Error processing {lang}: {e}")
    
    print("\nAll language versions processed.")

if __name__ == "__main__":
    main()
