import json
import os
import time
from openai import OpenAI
from tqdm import tqdm
import argparse
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
INPUT_DIR = "data/aceattorney_data/final"
OUTPUT_DIR = "stats/causal/updated_cases"
MODEL = "gpt-4o"

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))  # Explicitly use the environment variable

def check_causal_relationship(proposition):
    """
    Ask GPT-4o if a proposition contains a causal relationship
    
    Args:
        proposition: The proposition text to analyze
        
    Returns:
        bool: True if the proposition contains a causal relationship, False otherwise
    """
    try:
        # Construct the prompt
        prompt = f"I have a proposition: \"{proposition}\"\nDoes this proposition involve causal relationship? Answer only with 'Yes' or 'No'."
        
        # Make API call to OpenAI
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You analyze propositions to determine if they involve causal relationships. Causal relationships show how one event, action, or state leads to or causes another. Keywords like 'because', 'therefore', 'as a result', 'due to', 'leads to', 'causes', etc. often indicate causality."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Lower temperature for more deterministic outputs
            max_tokens=10     # We only need a short response
        )
        
        # Extract and process the response
        answer = response.choices[0].message.content.strip().lower()
        return "yes" in answer
        
    except Exception as e:
        print(f"Error checking causal relationship: {e}")
        # Wait a bit in case of rate limiting
        time.sleep(2)
        return False

def process_json_file(file_path, dry_run=False):
    """
    Process a single JSON file by checking propositions for causal relationships
    
    Args:
        file_path: Path to the JSON file to process
        dry_run: If True, don't save changes, just print what would be done
        
    Returns:
        dict: Statistics about the processing
    """
    print(f"Processing {file_path}...")
    
    # Load the JSON file
    with open(file_path, 'r', encoding='utf-8') as f:
        case_data = json.load(f)
    
    stats = {
        "turns_processed": 0,
        "props_processed": 0,
        "causal_props_found": 0,
        "turns_modified": 0
    }
    
    # Process each turn in the case
    for turn_idx, turn in enumerate(case_data.get("turns", [])):
        # Skip turns without reasoning
        if "reasoning" not in turn:
            continue
        
        turn_modified = False
        stats["turns_processed"] += 1
        
        # Process each step in the reasoning
        for reasoning_step in turn["reasoning"]:
            # Skip reasoning steps without a proposition
            if "Prop" not in reasoning_step:
                continue
            
            stats["props_processed"] += 1
            proposition = reasoning_step["Prop"]
            
            # Check if the proposition contains a causal relationship
            is_causal = check_causal_relationship(proposition)
            
            if is_causal:
                stats["causal_props_found"] += 1
                
                # Initialize labels field if it doesn't exist
                if "labels" not in turn:
                    turn["labels"] = []
                
                # Add "causal" to labels if not already present
                if "causal" not in turn["labels"]:
                    turn["labels"].append("causal")
                    turn_modified = True
                    print(f"  Causal relationship found in turn {turn_idx}: {proposition[:100]}...")
        
        if turn_modified:
            stats["turns_modified"] += 1
    
    # Save the updated JSON file if not a dry run
    if not dry_run and stats["turns_modified"] > 0:
        output_path = os.path.join(OUTPUT_DIR, os.path.basename(file_path))
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, indent=2, ensure_ascii=False)
        print(f"  Saved updated file to {output_path}")
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="Check for causal relationships in propositions")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes, just print what would be done")
    parser.add_argument("--file", type=str, help="Process only a specific file")
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    total_stats = {
        "files_processed": 0,
        "total_turns_processed": 0,
        "total_props_processed": 0,
        "total_causal_props": 0,
        "total_turns_modified": 0
    }
    
    # Get list of JSON files to process
    if args.file:
        # Process only the specified file
        file_path = args.file
        if not os.path.exists(file_path):
            file_path = os.path.join(INPUT_DIR, args.file)
        json_files = [file_path] if os.path.exists(file_path) else []
    else:
        # Process all JSON files in the input directory
        json_files = [
            os.path.join(INPUT_DIR, filename)
            for filename in os.listdir(INPUT_DIR)
            if filename.endswith(".json") and not filename.startswith("_")
        ]
    
    # Process each JSON file with a progress bar
    for file_path in tqdm(json_files, desc="Processing files"):
        try:
            stats = process_json_file(file_path, args.dry_run)
            
            # Update total statistics
            total_stats["files_processed"] += 1
            total_stats["total_turns_processed"] += stats["turns_processed"]
            total_stats["total_props_processed"] += stats["props_processed"]
            total_stats["total_causal_props"] += stats["causal_props_found"]
            total_stats["total_turns_modified"] += stats["turns_modified"]
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Print summary statistics
    print("\nProcessing complete!")
    print(f"Files processed: {total_stats['files_processed']}")
    print(f"Total turns processed: {total_stats['total_turns_processed']}")
    print(f"Total propositions analyzed: {total_stats['total_props_processed']}")
    print(f"Total causal propositions found: {total_stats['total_causal_props']}")
    print(f"Total turns modified: {total_stats['total_turns_modified']}")
    
    if args.dry_run:
        print("\nThis was a dry run. No files were modified.")

if __name__ == "__main__":
    main()
