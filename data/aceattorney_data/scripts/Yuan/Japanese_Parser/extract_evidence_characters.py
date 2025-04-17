import os
import re
import json
from bs4 import BeautifulSoup
import codecs # To handle specific encodings

# --- Configuration ---
RAW_HTML_DIR = os.path.join("data", "aceattorney_data", "generated", "raw")
OUTPUT_DIR = os.path.join("data", "aceattorney_data", "generated", "japanese_parsed")
ENGLISH_EVIDENCE_FILE = os.path.join("data", "aceattorney_data", "generated", "objects_parsed", "List_of_Evidence_in_Phoenix_Wright_Ace_Attorney.json")
ENGLISH_CHARACTERS_FILE = os.path.join("data", "aceattorney_data", "generated", "characters_parsed", "List_of_Profiles_in_Phoenix_Wright_Ace_Attorney.json")

# Files to process (adjust range if needed)
FILE_RANGE_START = 1
FILE_RANGE_END = 46 # Assuming word001.htm.html to word046.htm.html

# Regex patterns
EVIDENCE_PATTERN = re.compile(r"証拠品<<(.+?)>>") # Extracts name inside << >> after 証拠品
# Extracts base chapter name like "はじめての逆転" from "第１話『はじめての逆転』"
CHAPTER_TITLE_PATTERN = re.compile(r"『(.+?)』")
# Extracts character name before the ellipsis/color code (e.g., "成歩堂　龍一")
# Updated pattern to handle potential variations and ensure it captures the start
CHARACTER_NAME_PATTERN = re.compile(r"^\s*([^\s…（]+(?:\s+[^\s…（]+)*)")
# Regex to find and remove common control characters (tab, newline, carriage return)
CONTROL_CHARS_PATTERN = re.compile(r'[\t\n\r]')


# --- Helper Functions ---

def clean_chapter_title(raw_title):
    """Extracts the core chapter name from the raw title string."""
    match = CHAPTER_TITLE_PATTERN.search(raw_title)
    if match:
        # Further clean known suffixes if necessary
        title = match.group(1)
        # Remove specific trial/part markers
        title = re.sub(r'（前編）|（後編）|（その\d+）', '', title).strip()
        title = re.sub(r'第[１２３４５６７８９０]+回(?:法廷|探偵|裁判)', '', title).strip() # More robust removal
        # Handle potential extra spaces from removals
        title = re.sub(r'\s+', ' ', title).strip()
        return title
    # Fallback if pattern doesn't match - try removing common prefixes/suffixes
    raw_title = re.sub(r'^第\d+話\s*', '', raw_title).strip()
    raw_title = re.sub(r'\s*第[１２３４５６７８９０]+回(?:法廷|探偵|裁判).*$', '', raw_title).strip()
    raw_title = re.sub(r'（前編）|（後編）|（その\d+）', '', raw_title).strip()
    return raw_title # Return cleaned raw title as fallback

def get_character_name_from_cell(cell_text):
    """Extracts character name from the table cell text."""
    cleaned_text = cell_text.strip()
    match = CHARACTER_NAME_PATTERN.match(cleaned_text)
    if match:
        # Return the captured group, stripping any extra whitespace
        return match.group(1).strip()
    # Fallback: if no specific pattern matches, return the stripped text if it looks like a name
    if cleaned_text and '…' not in cleaned_text and '（' not in cleaned_text:
         return cleaned_text
    return None # Return None if no match or looks like description

def clean_string(text):
    """Removes control characters and extra whitespace."""
    if not text:
        return text
    # Remove control characters
    text = CONTROL_CHARS_PATTERN.sub('', text)
    # Strip leading/trailing whitespace and normalize internal whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- Main Logic ---

def main():
    print("Starting Japanese HTML parsing for evidence and characters...")

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- Data Structures ---
    # Key: Chapter Title, Value: Set of unique evidence names
    chapter_evidence = {}
    # Key: Chapter Title, Value: Set of unique character names
    chapter_characters = {}
    # Keep track of chapter titles in order
    chapter_order = []
    # Store raw titles to debug chapter cleaning
    raw_titles_processed = {}

    # --- Iterate through HTML files ---
    for i in range(FILE_RANGE_START, FILE_RANGE_END + 1):
        filename = f"word{i:03d}.htm.html"
        filepath = os.path.join(RAW_HTML_DIR, filename)

        if not os.path.exists(filepath):
            filename = f"word{i:03d}.html"
            filepath = os.path.join(RAW_HTML_DIR, filename)
        if not os.path.exists(filepath):
            print(f"Warning: File not found, skipping: {filepath}")
            continue

        print(f"Processing: {filepath}")
        html_content = None
        used_encoding = None

        # --- Try reading with different encodings ---
        try:
            # 1. Try UTF-8 first (standard for saved files)
            with codecs.open(filepath, 'r', encoding='utf-8', errors='strict') as f:
                html_content = f.read()
            used_encoding = 'utf-8'
            print(f"  Successfully read with UTF-8")
        except UnicodeDecodeError:
            print(f"  UTF-8 decoding failed. Trying Shift_JIS...")
            try:
                # 2. Try Shift_JIS (used in download script for specific URLs)
                with codecs.open(filepath, 'r', encoding='shift_jis', errors='replace') as f:
                    html_content = f.read()
                used_encoding = 'shift_jis'
                print(f"  Successfully read with Shift_JIS (used replace for errors)")
            except Exception as e_sjis:
                print(f"  Shift_JIS decoding also failed: {e_sjis}. Trying EUC-JP...")
                try:
                     # 3. Try EUC-JP as a last resort for these files
                     with codecs.open(filepath, 'r', encoding='euc-jp', errors='replace') as f:
                         html_content = f.read()
                     used_encoding = 'euc-jp'
                     print(f"  Successfully read with EUC-JP (used replace for errors)")
                except Exception as e_eucjp:
                    print(f"Error: Could not decode file {filepath} with UTF-8, Shift_JIS, or EUC-JP. Error: {e_eucjp}")
                    continue # Skip this file if all decodings fail
        except Exception as e_other:
             print(f"Error reading file {filepath}: {e_other}")
             continue # Skip file on other read errors

        # --- Process the successfully read content ---
        if html_content:
            try:
                soup = BeautifulSoup(html_content, 'html.parser')

                # --- Extract Chapter Title ---
                title_tag = soup.find('title')
                raw_chapter_title = title_tag.string.strip() if title_tag and title_tag.string else f"Unknown Chapter {i}"
                current_chapter = clean_chapter_title(raw_chapter_title)
                print(f"  Raw Title: '{raw_chapter_title}' -> Cleaned Chapter: '{current_chapter}' (Encoding: {used_encoding})")

                # Store for debugging chapter grouping
                if current_chapter not in raw_titles_processed:
                    raw_titles_processed[current_chapter] = []
                raw_titles_processed[current_chapter].append(raw_chapter_title)

                if current_chapter not in chapter_evidence:
                    chapter_evidence[current_chapter] = set()
                    chapter_characters[current_chapter] = set()
                    if current_chapter not in chapter_order:
                         chapter_order.append(current_chapter)

                # --- Extract Characters from Header Table ---
                header_tables = soup.find_all('table', border="0")
                if header_tables:
                    char_table = header_tables[0] # Assume first table is characters
                    rows = char_table.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        # Check if the first cell contains text likely to be a character name definition
                        if len(cells) > 0 and cells[0].find('font'):
                            cell_text = cells[0].get_text(strip=True)
                            char_name = get_character_name_from_cell(cell_text)
                            if char_name:
                                clean_char_name = clean_string(char_name) # Clean the name
                                if clean_char_name: # Add only if not empty after cleaning
                                    chapter_characters[current_chapter].add(clean_char_name)

                # --- Extract Evidence Mentions ---
                all_text = soup.get_text()
                found_evidence = EVIDENCE_PATTERN.findall(all_text)
                for evidence_name in found_evidence:
                    clean_evidence_name = clean_string(evidence_name) # Use new cleaning function
                    if clean_evidence_name: # Ensure it's not empty after cleaning
                        chapter_evidence[current_chapter].add(clean_evidence_name)

            except Exception as e_parse:
                print(f"Error parsing file {filepath} after reading with {used_encoding}: {e_parse}")

    # --- Debug: Print how chapters were grouped ---
    print("\n--- Chapter Grouping Debug ---")
    for chapter, titles in raw_titles_processed.items():
        print(f"Cleaned Chapter: '{chapter}'")
        for raw_title in titles:
            print(f"  - Raw: '{raw_title}'")
    print("----------------------------\n")


    # --- Load English Data (for reference, not used for matching yet) ---
    try:
        with open(ENGLISH_EVIDENCE_FILE, 'r', encoding='utf-8') as f:
            english_evidence_data = json.load(f)
        print(f"Loaded English evidence data from: {ENGLISH_EVIDENCE_FILE}")
    except Exception as e:
        print(f"Error loading English evidence file {ENGLISH_EVIDENCE_FILE}: {e}")
        english_evidence_data = []

    try:
        with open(ENGLISH_CHARACTERS_FILE, 'r', encoding='utf-8') as f:
            english_characters_data = json.load(f)
        print(f"Loaded English character data from: {ENGLISH_CHARACTERS_FILE}")
    except Exception as e:
        print(f"Error loading English characters file {ENGLISH_CHARACTERS_FILE}: {e}")
        english_characters_data = []


    # --- Format Output JSONs ---
    final_evidence_list = []
    for chapter_title in chapter_order:
        if chapter_title in chapter_evidence:
            evidence_items = []
            for jp_name in sorted(list(chapter_evidence[chapter_title])):
                # !! Placeholder: Matching and description translation needed !!
                # Find corresponding English entry based on jp_name (requires mapping)
                # For now, create a basic structure
                evidence_items.append({
                    "currentChapter": chapter_title, # Use Japanese chapter title for now
                    "name": jp_name,
                    "type": "PLACEHOLDER_TYPE",
                    "obtained": "PLACEHOLDER_OBTAINED",
                    "description1": "PLACEHOLDER_DESCRIPTION_1",
                    # Add description2 etc. if needed based on English structure
                })
            final_evidence_list.append({
                "chapter": chapter_title,
                "evidences": evidence_items
            })

    final_character_list = []
    for chapter_title in chapter_order:
         if chapter_title in chapter_characters:
            character_items = []
            for jp_name in sorted(list(chapter_characters[chapter_title])):
                # !! Placeholder: Matching and description translation needed !!
                character_items.append({
                    "currentChapter": chapter_title,
                    "name": jp_name,
                    "age": "PLACEHOLDER_AGE",
                    "gender": "PLACEHOLDER_GENDER",
                    "description1": "PLACEHOLDER_DESCRIPTION_1",
                     # Add description2 etc. if needed based on English structure
                })
            final_character_list.append({
                "chapter": chapter_title,
                "characters": character_items
            })

    # --- Write Output JSON Files ---
    evidence_output_path = os.path.join(OUTPUT_DIR, "Japanese_Evidence_List.json")
    characters_output_path = os.path.join(OUTPUT_DIR, "Japanese_Character_List.json")

    try:
        with open(evidence_output_path, 'w', encoding='utf-8') as f:
            json.dump(final_evidence_list, f, ensure_ascii=False, indent=2)
        print(f"Successfully wrote Japanese evidence list to: {evidence_output_path}")
    except Exception as e:
        print(f"Error writing evidence JSON: {e}")

    try:
        with open(characters_output_path, 'w', encoding='utf-8') as f:
            json.dump(final_character_list, f, ensure_ascii=False, indent=2)
        print(f"Successfully wrote Japanese character list to: {characters_output_path}")
    except Exception as e:
        print(f"Error writing characters JSON: {e}")

    print("Finished parsing.")

if __name__ == "__main__":
    main() 