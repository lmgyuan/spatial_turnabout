import json
import os
import re
import spacy
from collections import defaultdict

# --- Configuration ---
JSONL_PATH = "../GS1/en/sc0_text_u.mdt.jsonl"
JSON_PATH = "../../final/1-1-1_The_First_Turnabout.json"
OUTPUT_PATH = "../mappings/sc0_to_1-1-1_mapping.json"
SIMILARITY_THRESHOLD = 0.75  # Threshold for spaCy similarity

# Load spaCy model (you may need to download this with: python -m spacy download en_core_web_md)
print("Loading spaCy model...")
nlp = spacy.load("en_core_web_md")

# --- Helper Functions ---
def normalize_text(text):
    """Clean and normalize text for better comparison"""
    if not text:
        return ""
    # Remove punctuation that might differ between versions
    text = re.sub(r'[.,!?;:/\(\)\[\]\{\}]', ' ', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip().lower()
    return text

def get_text_doc(text):
    """Get spaCy doc for a text after normalization"""
    return nlp(normalize_text(text))

def get_similarity(text1, text2):
    """Calculate semantic similarity between texts using spaCy"""
    if not text1 or not text2:
        return 0
    
    # For very short texts, fall back to substring checking
    if len(text1) < 10 or len(text2) < 10:
        norm_text1 = normalize_text(text1)
        norm_text2 = normalize_text(text2)
        if norm_text1 in norm_text2 or norm_text2 in norm_text1:
            return 0.9  # High similarity for substring matches
    
    # Process texts with spaCy
    doc1 = get_text_doc(text1)
    doc2 = get_text_doc(text2)
    
    # If either doc is empty after processing, return 0
    if not doc1 or not doc2:
        return 0
    
    # Return similarity score
    return doc1.similarity(doc2)

def find_best_match(target_text, candidates, threshold=SIMILARITY_THRESHOLD):
    """Find the best matching candidate for the target text"""
    best_match = None
    best_score = 0
    
    target_doc = get_text_doc(target_text)
    
    for candidate in candidates:
        candidate_text = candidate["text"]
        
        # Skip empty candidates
        if not candidate_text.strip():
            continue
        
        # Check similarity
        similarity = target_doc.similarity(get_text_doc(candidate_text))
        
        if similarity > best_score:
            best_score = similarity
            best_match = candidate
    
    return (best_match, best_score) if best_score >= threshold else (None, 0)

# --- Main Function ---
def main():
    print("Starting mapping process with spaCy...")
    
    # Load case JSON
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        case_data = json.load(f)
    
    # Load JSONL content
    jsonl_contents = []
    with open(JSONL_PATH, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if line.strip():
                try:
                    item = json.loads(line.strip())
                    content = item.get('content', '')
                    if content and content.strip():
                        jsonl_contents.append({
                            "id": i,
                            "content": content
                        })
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse line {i}: {line[:50]}...")
    
    print(f"Loaded {len(jsonl_contents)} content items from JSONL")
    
    # Extract all text segments from the case data
    all_text_segments = []
    
    # Process prevContext
    if "prevContext" in case_data and case_data["prevContext"]:
        all_text_segments.append({
            "text": case_data["prevContext"],
            "field_type": "prevContext",
            "turn_index": 0
        })
    
    # Process turn content
    for turn_idx, turn in enumerate(case_data.get("turns", []), 1):
        # Process newContext
        if "newContext" in turn and turn["newContext"]:
            all_text_segments.append({
                "text": turn["newContext"],
                "field_type": "newContext",
                "turn_index": turn_idx
            })
        
        # Process testimonies
        if "testimonies" in turn:
            for testimony_idx, testimony in enumerate(turn["testimonies"]):
                if "testimony" in testimony:
                    all_text_segments.append({
                        "text": testimony["testimony"],
                        "field_type": "testimony",
                        "turn_index": turn_idx,
                        "testimony_index": testimony_idx
                    })
    
    print(f"Extracted {len(all_text_segments)} text segments from case data")
    
    # Pre-process all text segments with spaCy for faster matching
    print("Processing text segments with spaCy...")
    for segment in all_text_segments:
        segment["doc"] = get_text_doc(segment["text"])
    
    # Create mappings
    mappings = []
    
    # Process sequentially for context segments and then testimonies separately
    context_segments = [s for s in all_text_segments if s["field_type"] != "testimony"]
    testimony_segments = [s for s in all_text_segments if s["field_type"] == "testimony"]
    
    # First pass: Sequential matching for context segments
    jsonl_index = 0
    for segment in context_segments:
        segment_text = segment["text"]
        segment_doc = segment["doc"]
        
        # Match multiple JSONL entries to this segment
        while jsonl_index < len(jsonl_contents):
            jsonl_item = jsonl_contents[jsonl_index]
            jsonl_text = jsonl_item["content"]
            jsonl_doc = get_text_doc(jsonl_text)
            
            # Check if this JSONL content belongs to the current segment
            similarity = segment_doc.similarity(jsonl_doc)
            
            if similarity >= SIMILARITY_THRESHOLD:
                # Good match, add it to mappings
                mappings.append({
                    "jsonl_id": jsonl_item["id"],
                    "jsonl_content": jsonl_text[:100] + ("..." if len(jsonl_text) > 100 else ""),
                    "case_turn_index": segment["turn_index"],
                    "case_field_type": segment["field_type"],
                    "match_ratio": round(similarity, 2)
                })
                
                # Move to next JSONL item
                jsonl_index += 1
                
                # If near the end of segment, move to next segment
                if jsonl_index < len(jsonl_contents):
                    next_item = jsonl_contents[jsonl_index]
                    next_doc = get_text_doc(next_item["content"])
                    next_similarity = segment_doc.similarity(next_doc)
                    
                    if next_similarity < SIMILARITY_THRESHOLD:
                        break
            else:
                # Poor match, move to next segment
                break
    
    # Second pass: Match remaining JSONL entries to testimonies
    mapped_ids = {m["jsonl_id"] for m in mappings}
    
    for jsonl_item in jsonl_contents:
        if jsonl_item["id"] in mapped_ids:
            continue  # Skip already mapped items
        
        jsonl_text = jsonl_item["content"]
        jsonl_doc = get_text_doc(jsonl_text)
        
        best_match = None
        best_score = 0
        
        # Find the best matching testimony
        for testimony in testimony_segments:
            similarity = jsonl_doc.similarity(testimony["doc"])
            
            if similarity >= SIMILARITY_THRESHOLD and similarity > best_score:
                best_score = similarity
                best_match = testimony
        
        # If we found a good match, record it
        if best_match:
            mappings.append({
                "jsonl_id": jsonl_item["id"],
                "jsonl_content": jsonl_text[:100] + ("..." if len(jsonl_text) > 100 else ""),
                "case_turn_index": best_match["turn_index"],
                "case_field_type": best_match["field_type"],
                "testimony_index": best_match.get("testimony_index", 0),
                "match_ratio": round(best_score, 2)
            })
            mapped_ids.add(jsonl_item["id"])
    
    # Sort mappings by JSONL ID
    mappings.sort(key=lambda x: x["jsonl_id"])
    
    # Organize mappings by turn and field type
    organized_mappings = defaultdict(lambda: defaultdict(list))
    for mapping in mappings:
        turn_idx = mapping["case_turn_index"]
        field_type = mapping["case_field_type"]
        organized_mappings[turn_idx][field_type].append(mapping)
    
    # Prepare output data
    output_data = {
        "total_jsonl_items": len(jsonl_contents),
        "matched_items": len(mappings),
        "match_rate": round(len(mappings) / len(jsonl_contents), 2) if jsonl_contents else 0,
        "mapping_by_turn": {str(k): dict(v) for k, v in organized_mappings.items()},
        "mappings": mappings
    }
    
    # Save the mapping to a file
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully mapped {len(mappings)} out of {len(jsonl_contents)} content items")
    print(f"Match rate: {output_data['match_rate'] * 100:.1f}%")
    print(f"Mapping saved to {OUTPUT_PATH}")
    
    # Print stats by field type
    content_types = {}
    for mapping in mappings:
        field_type = mapping["case_field_type"]
        content_types[field_type] = content_types.get(field_type, 0) + 1
    
    print("\nMatch distribution by field type:")
    for field_type, count in content_types.items():
        print(f"  {field_type}: {count} matches")
    
    # Show unmapped items
    unmapped_count = len(jsonl_contents) - len(mappings)
    if unmapped_count > 0:
        print(f"\n{unmapped_count} items could not be mapped")

if __name__ == "__main__":
    main()