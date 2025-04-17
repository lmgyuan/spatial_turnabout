import os
import re
import json
from bs4 import BeautifulSoup, NavigableString
import codecs

# --- Configuration ---
RAW_HTML_DIR = os.path.join("data", "aceattorney_data", "generated", "raw")
OUTPUT_DIR = os.path.join("data", "aceattorney_data", "generated", "japanese_parsed") # Or a different output dir if needed
OUTPUT_FILENAME = "parsed_segment_113_117.json"

# Files to process
FILE_RANGE_START = 113
FILE_RANGE_END = 117

# Regex patterns
CHARACTER_PATTERN = re.compile(r"^(.*?)：") # Matches "成：" -> "成"
EVIDENCE_PATTERN = re.compile(r"<<(.+?)>>") # Extracts name inside << >>
TESTIMONY_START_PATTERN = re.compile(r"『(.*?)』") # Matches testimony lines like 『...』
PRESENT_EVIDENCE_PATTERN = re.compile(r"（「証言(\d+)」に「(.+?)」をつきつける）") # Parses the evidence presentation line
# Pattern to identify rows that are likely just formatting or empty
EMPTY_ROW_PATTERN = re.compile(r"^\s*\(?\s*（?\s*\)?$") # Matches empty or whitespace-only, potentially with stray parens
# Pattern to identify testimony start/end markers which should not end a block
TESTIMONY_MARKER_PATTERN = re.compile(r"～証言(?:開始|終了)～")

# --- Helper Functions ---
def clean_string(text):
    """Removes control characters and extra whitespace."""
    if not text:
        return text
    text = re.sub(r'[\t\n\r]+', ' ', text) # Replace control chars with space
    text = re.sub(r'\s+', ' ', text).strip() # Normalize whitespace
    return text

def get_character_name(tag):
    """Extracts character name from a tag, handling potential font tags."""
    # Prioritize font tag within the cell
    name_tag = tag.find('font', recursive=False) # Look only for direct children
    if name_tag and name_tag.string:
        match = CHARACTER_PATTERN.match(name_tag.string.strip())
        if match:
            return match.group(1).strip()

    # Fallback to cell's direct text content if no font tag or pattern mismatch
    # Combine direct text nodes, ignoring deeper tags unless necessary
    cell_text = ''.join(t for t in tag.find_all(string=True, recursive=False)).strip()
    if cell_text:
        match = CHARACTER_PATTERN.match(cell_text)
        if match:
            return match.group(1).strip()

    # Final fallback: get all text, might be less accurate
    full_text = tag.get_text(strip=True)
    if full_text:
        match = CHARACTER_PATTERN.match(full_text)
        if match:
            return match.group(1).strip()
    return None

# --- Main Parsing Logic ---
def main():
    all_characters = set()
    all_evidence = set()
    full_context_parts = [] # Collect parts for cleaner context
    turns_data = []
    current_turn_testimonies = [] # Stores ALL testimonies for the current turn object
    active_testimony_block = [] # Temporarily holds statements for the block being parsed
    last_speaker = None
    # Stores info about the most recently completed block added to current_turn_testimonies
    last_completed_block_info = None # {'start_index': int, 'length': int}

    print(f"Starting parsing for files word{FILE_RANGE_START} to word{FILE_RANGE_END}...")

    for i in range(FILE_RANGE_START, FILE_RANGE_END + 1):
        filename = f"word{i:03d}.htm.html"
        filepath = os.path.join(RAW_HTML_DIR, filename)

        if not os.path.exists(filepath):
            # Try without .html suffix if the first attempt failed (less likely now)
            filename = f"word{i:03d}.htm"
            filepath = os.path.join(RAW_HTML_DIR, filename)
            if not os.path.exists(filepath):
                print(f"Warning: File not found, skipping: {filename}")
                continue

        print(f"Processing: {filepath}")
        html_content = None
        used_encoding = None

        # --- Read File with Encoding Fallback ---
        try:
            with codecs.open(filepath, 'r', encoding='utf-8', errors='strict') as f:
                html_content = f.read()
            used_encoding = 'utf-8'
        except UnicodeDecodeError:
            try:
                with codecs.open(filepath, 'r', encoding='shift_jis', errors='replace') as f:
                    html_content = f.read()
                used_encoding = 'shift_jis'
            except Exception:
                 try:
                     with codecs.open(filepath, 'r', encoding='euc-jp', errors='replace') as f:
                         html_content = f.read()
                     used_encoding = 'euc-jp'
                 except Exception as e_read:
                     print(f"Error: Could not decode file {filepath}. Error: {e_read}")
                     continue
        except Exception as e_other:
            print(f"Error reading file {filepath}: {e_other}")
            continue

        # --- Parse HTML ---
        if html_content:
            soup = BeautifulSoup(html_content, 'html.parser')
            # Attempt to get cleaner context by joining text from relevant tags
            context_parts = [clean_string(tag.get_text()) for tag in soup.find_all(['p', 'font', 'td'])] # Adjust tags as needed
            full_context_parts.extend(filter(None, context_parts))

            script_table = soup.find('table')
            if not script_table:
                print(f"Warning: Could not find main script table in {filename}")
                continue

            rows = script_table.find_all('tr', recursive=False)

            for row_idx, row in enumerate(rows):
                cells = row.find_all('td', recursive=False)
                if len(cells) < 2: continue # Skip rows without at least two cells

                speaker_cell = cells[0]
                dialogue_cell = cells[1]
                dialogue_text_raw = dialogue_cell.get_text()
                dialogue_text_clean = clean_string(dialogue_text_raw)

                # Add non-empty cleaned text to context
                if dialogue_text_clean:
                    full_context_parts.append(dialogue_text_clean)

                # --- 1. Check for Evidence Presentation Line ---
                present_match = PRESENT_EVIDENCE_PATTERN.search(dialogue_text_raw)
                if present_match:
                    testimony_index = int(present_match.group(1)) - 1 # 0-based
                    evidence_name = clean_string(present_match.group(2))
                    print(f"  >>> Found Evidence Presentation: '{evidence_name}' for testimony index {testimony_index} (relative to last block)")
                    all_evidence.add(evidence_name)

                    if last_completed_block_info:
                        start = last_completed_block_info['start_index']
                        length = last_completed_block_info['length']
                        target_abs_index = start + testimony_index

                        if 0 <= testimony_index < length and target_abs_index < len(current_turn_testimonies):
                            target_testimony = current_turn_testimonies[target_abs_index]
                            target_testimony.setdefault("present", []).append(evidence_name)
                            target_testimony["source"] = {
                                "evidence_span": f"'{evidence_name}'", # Placeholder
                                "testimony_span": target_testimony['testimony'],
                                "explanation": "Contradiction detected.", # Placeholder
                                "is_self_contained": "unknown", "context_span": "",
                                "difficulty": "unknown", "labels": []
                            }
                            print(f"      Applied to testimony: [{target_testimony['person']}] {target_testimony['testimony']}")
                        else:
                            print(f"      Warning: Invalid testimony index {testimony_index} or block info for applying evidence.")
                    else:
                        print("      Warning: Found evidence presentation but no preceding testimony block info recorded.")
                    continue # This line is processed

                # --- 2. Check for Testimony Start/Continuation ---
                speaker = get_character_name(speaker_cell)
                is_testimony_line = False
                testimony_match = None

                if speaker:
                    last_speaker = speaker
                    all_characters.add(speaker)
                    testimony_match = TESTIMONY_START_PATTERN.match(dialogue_text_clean)
                    if testimony_match:
                        is_testimony_line = True
                        testimony_text = clean_string(testimony_match.group(1))
                        active_testimony_block.append({"person": speaker, "testimony": testimony_text}) # Init present later if needed
                        print(f"  Found testimony: [{speaker}] {testimony_text}")

                elif last_speaker and dialogue_text_clean and active_testimony_block:
                    # Continuation line
                    active_testimony_block[-1]["testimony"] += " " + dialogue_text_clean
                    print(f"    Appended continuation: {dialogue_text_clean}")
                    is_testimony_line = True

                # --- 3. Check for End of Testimony Block ---
                # A block ends if this line is NOT testimony, NOT the presentation line (already handled),
                # NOT an empty/formatting row, and NOT a testimony start/end marker, AND a block was active.
                is_formatting_or_marker = (EMPTY_ROW_PATTERN.match(dialogue_text_raw.strip()) or
                                           TESTIMONY_MARKER_PATTERN.search(dialogue_text_raw))

                if not is_testimony_line and not is_formatting_or_marker and active_testimony_block:
                    print(f"  End of testimony block detected (size {len(active_testimony_block)}). Finalizing.")
                    # Record info about the block being added
                    block_start_index = len(current_turn_testimonies)
                    block_length = len(active_testimony_block)
                    last_completed_block_info = {'start_index': block_start_index, 'length': block_length}

                    # Move the completed block
                    current_turn_testimonies.extend(active_testimony_block)
                    active_testimony_block = [] # Clear for the next block

                # --- 4. General Evidence Mention Check (can happen anywhere) ---
                found_evidence = EVIDENCE_PATTERN.findall(row.get_text())
                for ev in found_evidence:
                    all_evidence.add(clean_string(ev))

            # Add any remaining testimony block at the end of the file processing
            if active_testimony_block:
                print(f"  End of file reached. Finalizing remaining {len(active_testimony_block)} statements.")
                block_start_index = len(current_turn_testimonies)
                block_length = len(active_testimony_block)
                last_completed_block_info = {'start_index': block_start_index, 'length': block_length}
                current_turn_testimonies.extend(active_testimony_block)
                active_testimony_block = []


    # --- Assemble Final JSON ---
    print("\nAssembling final JSON...")
    final_context = "\n".join(full_context_parts) # Join collected context

    character_list = [
        {"currentChapter": "蘇る逆転 - 第5話", "name": name, "age": "不明", "gender": "不明", "description1": ""}
        for name in sorted(list(all_characters))
    ]

    evidence_list = [
        {"currentChapter": "蘇る逆転 - 第5話", "name": name, "type": "不明", "obtained": "不明", "description1": ""}
        for name in sorted(list(all_evidence))
    ]

    # Ensure all testimony objects have at least an empty 'present' list
    for testimony in current_turn_testimonies:
        testimony.setdefault("present", [])

    turn = {
        "category": "cross_examination",
        "newContext": final_context, # Use assembled context
        "testimonies": current_turn_testimonies,
        "noPresent": not any(t.get("present") for t in current_turn_testimonies),
        "summarizedContext": "証人の証言に対する尋問。", # Placeholder
        "difficulty": "unknown", "labels": [], "reasoning": []
    }
    turns_data.append(turn)

    output_data = {
        "previousContext": "",
        "characters": character_list,
        "evidences": evidence_list,
        "turns": turns_data
    }

    # --- Write Output JSON ---
    output_filepath = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\nSuccessfully wrote parsed data to: {output_filepath}")
    except Exception as e:
        print(f"\nError writing JSON file: {e}")

if __name__ == "__main__":
    main() 