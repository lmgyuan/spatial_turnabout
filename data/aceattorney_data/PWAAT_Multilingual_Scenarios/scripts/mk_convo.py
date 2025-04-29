import json
import os
import re

# --- Configuration ---
INPUT_JSON_DIR = "../../final"
OUTPUT_JSON_DIR = "../conversations"
DEFAULT_SPEAKER = "Narration"

def extract_conversations(text):
    """
    Extract conversations from text by splitting on colons.
    Returns a list of (speaker, content) tuples.
    """
    if not text:
        return []
    
    conversations = []
    # Split text into sentences using periods, question marks, exclamation points
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    for sentence in sentences:
        if not sentence.strip():
            continue
            
        # Check if the sentence contains a colon for speaker identification
        if ":" in sentence:
            # Split on the first colon to separate speaker from content
            parts = sentence.split(":", 1)
            if len(parts) == 2:
                speaker = parts[0].strip()
                content = parts[1].strip()
                
                # Skip empty content
                if not content:
                    continue
                    
                # Add quotes if they're not already there
                if not (content.startswith('"') and content.endswith('"')):
                    # But only add quotes if it looks like dialogue
                    if not content.startswith('(') and not content.startswith('['):
                        content = content
                
                conversations.append({"speaker": speaker, "content": content})
            else:
                # Handle odd cases with just a colon
                conversations.append({"speaker": DEFAULT_SPEAKER, "content": sentence})
        else:
            # No speaker identified, treat as narration
            conversations.append({"speaker": DEFAULT_SPEAKER, "content": sentence})
    
    return conversations

def process_testimonies(testimonies):
    """Process testimony sections which have a different structure"""
    all_testimony_conversations = []
    
    for testimony in testimonies:
        if "testimony" in testimony:
            testimony_text = testimony["testimony"]
            testimony_conversations = extract_conversations(testimony_text)
            
            # Add a system message indicating this is testimony
            if testimony_conversations:
                all_testimony_conversations.append({
                    "speaker": "System", 
                    "content": "TESTIMONY BEGIN"
                })
                all_testimony_conversations.extend(testimony_conversations)
                all_testimony_conversations.append({
                    "speaker": "System", 
                    "content": "TESTIMONY END"
                })
    
    return all_testimony_conversations

def turn_to_conversations(turn):
    """Convert a turn's content to conversations"""
    conversations = []
    
    # Process prevContext if present
    if "prevContext" in turn and turn["prevContext"]:
        prev_conversations = extract_conversations(turn["prevContext"])
        conversations.extend(prev_conversations)
    
    # Process newContext
    if "newContext" in turn and turn["newContext"]:
        new_conversations = extract_conversations(turn["newContext"])
        conversations.extend(new_conversations)
    
    # Process testimonies if present
    if "testimonies" in turn:
        testimony_conversations = process_testimonies(turn["testimonies"])
        conversations.extend(testimony_conversations)
    
    return conversations

def convert_json_to_conversation(input_json_path, output_json_path):
    """Convert a case JSON file to conversation format"""
    print(f"Converting {input_json_path} to conversation format...")
    
    with open(input_json_path, 'r', encoding='utf-8') as f:
        case_data = json.load(f)
    
    # Initialize conversation structure
    conversation_data = {
        "currentChapter": case_data.get("currentChapter", "Unknown Chapter"),
        "conversations": []
    }
    
    # Process top-level prevContext if it exists
    if "prevContext" in case_data and case_data["prevContext"]:
        prev_conversations = extract_conversations(case_data["prevContext"])
        conversation_data["conversations"].extend(prev_conversations)
    
    # Process each turn
    for turn in case_data.get("turns", []):
        turn_conversations = turn_to_conversations(turn)
        conversation_data["conversations"].extend(turn_conversations)
    
    # Write the output file
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(conversation_data, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully created conversation file at: {output_json_path}")
    print(f"Total conversation entries: {len(conversation_data['conversations'])}")
    
    return conversation_data

def process_all_case_files():
    """Process all JSON case files in the input directory"""
    if not os.path.exists(INPUT_JSON_DIR):
        print(f"Input directory {INPUT_JSON_DIR} does not exist!")
        return
    
    os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)
    
    # Get all JSON files in the input directory
    json_files = [f for f in os.listdir(INPUT_JSON_DIR) if f.endswith('.json')]
    
    if not json_files:
        print(f"No JSON files found in {INPUT_JSON_DIR}")
        return
    
    print(f"Found {len(json_files)} JSON files to process")
    
    for json_file in json_files:
        input_path = os.path.join(INPUT_JSON_DIR, json_file)
        
        # Generate output filename by replacing or adding "_conversation" before the extension
        base_name, ext = os.path.splitext(json_file)
        output_file = f"{base_name}_conversation{ext}"
        output_path = os.path.join(OUTPUT_JSON_DIR, output_file)
        
        try:
            convert_json_to_conversation(input_path, output_path)
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    
    print("\nAll files processed.")

def main():
    print("Ace Attorney Conversation Converter")
    print("===================================")
    
    # Check if specific file was provided as argument
    import sys
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        input_path = os.path.join(INPUT_JSON_DIR, input_file) if not os.path.isabs(input_file) else input_file
        
        if not os.path.exists(input_path):
            print(f"Input file {input_path} does not exist!")
            return
        
        # Generate output filename
        base_name, ext = os.path.splitext(os.path.basename(input_path))
        output_file = f"{base_name}_conversation{ext}"
        output_path = os.path.join(OUTPUT_JSON_DIR, output_file)
        
        convert_json_to_conversation(input_path, output_path)
    else:
        # Process all files
        process_all_case_files()

if __name__ == "__main__":
    main()
