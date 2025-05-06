"""
parse_transcript_segment.py

This script parses a range of raw HTML transcript files from the Ace Attorney Japanese game script,
extracts testimony and evidence presentation segments, and outputs a structured JSON file for use in
downstream NLP or game data pipelines.

What it does:
- Reads a specified range of HTML files (e.g., word113.htm.html to word117.htm.html) from the raw data directory.
- Extracts all text, identifies testimony lines and evidence presentation events using regular expressions.
- Segments the transcript into cross-examination "turns" with associated testimonies and evidence.
- Assembles a JSON object containing chapter, character, evidence, and turn/testimony data.
- Writes the output JSON to the specified output directory.

How to use:
1. Place the raw HTML files in the directory: data/aceattorney_data/generated/raw/
2. Adjust FILE_RANGE_START and FILE_RANGE_END to the desired file indices.
3. Optionally, change OUTPUT_FILENAME and OUTPUT_DIR as needed.
4. Run the script:
       python parse_transcript_segment.py
5. The parsed JSON will be written to the output directory.

Dependencies:
- BeautifulSoup4 (bs4)
- Python 3.x

Note: This script is tailored for the Japanese Ace Attorney script format and may require adaptation for other formats.
"""

import os
import re
import json
from bs4 import BeautifulSoup, NavigableString
import codecs

# --- Configuration ---
RAW_HTML_DIR = os.path.join("data", "aceattorney_data", "generated", "raw")
OUTPUT_DIR = os.path.join("data", "aceattorney_data", "generated", "japanese_parsed") # Or a different output dir if needed
OUTPUT_FILENAME = "parsed_segment_135_152.json"

# Files to process
FILE_RANGE_START = 135
FILE_RANGE_END = 152
currentChapter = "逆転のレシピ"

# Regex patterns
CHARACTER_PATTERN = re.compile(r"^(.*?)：") # Matches "成：" -> "成"
EVIDENCE_PATTERN = re.compile(r"<<(.+?)>>") # Extracts name inside << >>
TESTIMONY_START_PATTERN = re.compile(r"『(.*?)』") # Matches testimony lines like 『...』
PRESENT_EVIDENCE_PATTERN = re.compile(r"（「証言(\d+)」に「(.+?)」をつきつける）") # Parses the evidence presentation line

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
    name_tag = tag.find('font')
    if name_tag and name_tag.string:
        match = CHARACTER_PATTERN.match(name_tag.string.strip())
        if match:
            return match.group(1).strip()
    # Fallback if no font tag or pattern mismatch
    match = CHARACTER_PATTERN.match(tag.get_text(strip=True))
    if match:
        return match.group(1).strip()
    return None

# --- Main Parsing Logic ---
def main():
    all_characters = set()
    all_evidence = set()
    full_context = ""
    turns_data = []
    current_turn_testimonies = []
    last_speaker = None

    print(f"Starting parsing for files word{FILE_RANGE_START} to word{FILE_RANGE_END}...")

    # Initialize full_transcript before the loop
    full_transcript = ""

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
            # Extract all text content, including from any tags
            text_content = ""
            for string in soup.stripped_strings:
                text_content += string + "\n"
            full_transcript += text_content + "\n\n" # Append all extracted text to context

    # Find patterns of evidence presentation using regex
    evidence_pattern = re.compile(r'「([^」]+)」に「([^」]+)」をつきつける')
    # Convert the iterator to a list immediately
    evidence_matches = list(evidence_pattern.finditer(full_transcript))
    # Initialize list to store text segments
    text_segments = []
    last_end = 0

    # Iterate through matches to extract text segments
    for match in evidence_matches:
        # Get text from last match end to current match start
        segment = full_transcript[last_end:match.start()].strip()
        text_segments.append(segment)
        last_end = match.end()

    
    # Extract testimonies before each evidence presentation
    testimony_pattern = re.compile(r'『([^』]+)』（証言(\d+)）')
    
    # For each segment, find the last set of testimonies before the evidence presentation
    testimonies_before_matches = []
    for i, segment in enumerate(text_segments):
        testimonies = []
        current_testimony_set = []
        last_testimony_num = 0
        
        # Find all testimony matches in the segment
        for match in testimony_pattern.finditer(segment):
            testimony_text = match.group(1)
            testimony_num = int(match.group(2))
            
            # If we find a testimony #1, start a new set
            if testimony_num == 1 and current_testimony_set:
                testimonies = current_testimony_set.copy()
                current_testimony_set = []
            
            # If testimony numbers are sequential, add to current set
            if testimony_num == last_testimony_num + 1:
                current_testimony_set.append(testimony_text)
                last_testimony_num = testimony_num
            elif testimony_num == 1:
                current_testimony_set = [testimony_text]
                last_testimony_num = 1
        
        # Don't forget the last set if it exists
        if current_testimony_set:
            testimonies = current_testimony_set
            
        testimonies_before_matches.append(testimonies)


    # --- Assemble Final JSON ---
    print("\nAssembling final JSON...")

    # Create Character Objects (with placeholders)
    character_list = [
        {"currentChapter": currentChapter, "name": name, "age": "不明", "gender": "不明", "description1": ""}
        for name in sorted(list(all_characters))
    ]

    # Create Evidence Objects (with placeholders)
    evidence_list = [
        {"currentChapter": currentChapter, "name": name, "type": "不明", "obtained": "不明", "description1": ""}
        for name in sorted(list(all_evidence))
    ]

    # --- Write Output JSON ---
    output_filepath = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
    print("writing to: " + output_filepath)

    # Debug prints to check loop variables
    print(f"Number of evidence matches: {len(evidence_matches)}")
    print(f"Number of text segments: {len(text_segments)}")
    print(f"Number of testimony sets: {len(testimonies_before_matches)}")

    for i, evidence_match in enumerate(evidence_matches):
        print(f"\nProcessing evidence match {i+1}:")
        print(f"Evidence match groups: {evidence_match.groups()}")
        testimonies = []
        
        if i < len(testimonies_before_matches):
            print(f"Number of testimonies in this set: {len(testimonies_before_matches[i])}")
            print(f"testimonies_before_matches[i]: {testimonies_before_matches[i]}")
            
            for j in range(len(testimonies_before_matches[i])):
                try:
                    # Correctly extract the testimony number by removing non-digits
                    testimony_id_str = evidence_match.group(1)
                    # Remove non-digit characters to get the number
                    current_evidence_id_num_str = ''.join(filter(str.isdigit, testimony_id_str))
                    if not current_evidence_id_num_str:
                         print(f"Warning: Could not extract number from testimony ID '{testimony_id_str}'")
                         continue # Skip if no number found
                    current_evidence_id_num = int(current_evidence_id_num_str)

                    print(f"Processing testimony {j+1} with evidence ID number {current_evidence_id_num}")

                    testimony_obj = {
                        "testimony": testimonies_before_matches[i][j],
                        "person": "Gumshoe", # Placeholder - needs actual speaker detection
                        "present": []
                    }

                    # Add evidence to present array if this is the testimony it should be presented on
                    # Compare the loop index (j+1) with the extracted testimony number
                    if j+1 == current_evidence_id_num:
                        testimony_obj["present"] = [evidence_match.group(2)]

                        # Add source information for contradictions
                        testimony_obj["source"] = {
                            "evidence_span": "",  # Would need evidence description
                            "testimony_span": testimonies_before_matches[i][j],
                            "explanation": "",    # Would need contradiction explanation
                            "is_self_contained": "no",
                            "context_span": ""    # Would need surrounding context
                        }

                    testimonies.append(testimony_obj)
                    print(f"Added testimony object {j+1}")

                except Exception as e:
                    print(f"Error processing testimony {j+1}: {str(e)}")
                    # Optionally add more specific error handling or logging here
                    continue
            
            turn_data = {
                "category": "cross_examination", 
                "newContext": text_segments[i],
                "testimonies": testimonies
            }
            turns_data.append(turn_data)
            print(f"Added turn data for evidence match {i+1}")
        else:
            print(f"Warning: No testimony data found for evidence match {i+1}")
    
    output_data = {
        "currentChapter": currentChapter,
        "characters": character_list,
        "evidence": evidence_list,
        "turns": turns_data
    }


    os.makedirs(OUTPUT_DIR, exist_ok=True)
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\nSuccessfully wrote parsed data to: {output_filepath}")
    except Exception as e:
        print(f"\nError writing JSON file: {e}")

if __name__ == "__main__":
    main() 