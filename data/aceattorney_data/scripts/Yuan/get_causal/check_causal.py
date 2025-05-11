import json
import os
import time
import multiprocessing
from openai import OpenAI
import argparse
from dotenv import load_dotenv
from functools import partial

load_dotenv()

# --- Configuration ---
INPUT_DIR = "data/aceattorney_data/final"
OUTPUT_DIR = "data/aceattorney_data/final_with_causal"
MODEL = "gpt-4.1-mini-2025-04-14"
NUM_PROCESSES = 10  # Number of parallel processes to use

# Create a lock for API access to avoid rate limiting issues
api_lock = multiprocessing.Lock()

def get_openai_client():
    """Create a new OpenAI client for each process"""
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def check_causal_relationship(proposition, process_id=0):
    """
    Ask GPT-4 mini if a proposition contains a causal relationship
    
    Args:
        proposition: The proposition text to analyze
        process_id: ID of the process (for logging)
        
    Returns:
        bool: True if the proposition contains a causal relationship, False otherwise
    """
    # Create a new client for each process
    client = get_openai_client()
    
    try:
        prompt = (
            f"I have a proposition: \"{proposition}\"\n"
            "Does this proposition involve a causal relationship? "
            "Respond with a JSON object with an 'answer' field containing only 'Yes' or 'No'."
        )

        # Use the lock to avoid overwhelming the API
        with api_lock:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "You analyze propositions to determine if they involve causal relationships. "
                            "Here are some examples of causal relationships: "
                            "'if someone is holding something in their right hand, their free hand would be their left hand' does not involve a causal relationship. "
                            "'If someone's eardrum was ruptured, they wouldn't be able to hear with that ear.' does involve a causal relationship."
                            "Respond with a JSON object with an 'answer' field containing only 'Yes' or 'No'."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=20,
                response_format={"type": "json_object"}
            )
            # Small delay to avoid hitting rate limits
            time.sleep(0.2)

        # Parse the response
        content = response.choices[0].message.content
        try:
            # Try to parse as JSON first
            import json as _json
            data = _json.loads(content)
            # Check if there's an "answer" field
            if "answer" in data:
                answer = data["answer"].strip().lower()
            else:
                # Look for yes/no in any of the JSON values
                answer = str(data).lower()
        except Exception:
            # If JSON parsing fails, check the raw content
            answer = content.strip().lower()
        
        print(f"[Process {process_id}] Answer received: {answer}")
        return "yes" in answer
        
    except Exception as e:
        print(f"[Process {process_id}] Error checking causal relationship: {e}")
        time.sleep(2)  # Back off on error
        return False

def process_json_file(file_path, dry_run=False, process_id=0):
    """
    Process a single JSON file by checking propositions for causal relationships
    """
    print(f"[Process {process_id}] Processing {file_path}...")
    
    # Load the JSON file
    with open(file_path, 'r', encoding='utf-8') as f:
        case_data = json.load(f)
    
    stats = {
        "file_path": file_path,
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
            reasoning_step = reasoning_step.strip().lower()
            if not reasoning_step.startswith("prop"):
                continue
            
            print(f"[Process {process_id}] Turn {turn_idx} in {os.path.basename(file_path)}: {reasoning_step}")

            stats["props_processed"] += 1
            proposition = reasoning_step.split(":")[1].strip()
            
            # Check if the proposition contains a causal relationship
            is_causal = check_causal_relationship(proposition, process_id)
            
            if is_causal:
                stats["causal_props_found"] += 1
                
                # Initialize labels field if it doesn't exist
                if "labels" not in turn:
                    turn["labels"] = []
                
                # Add "causal" to labels if not already present
                if "causal" not in turn["labels"]:
                    turn["labels"].append("causal")
                    turn_modified = True
                    print(f"[Process {process_id}] Causal relationship found in turn {turn_idx}: {proposition}...")
            else:
                print(f"[Process {process_id}] No causal relationship found in turn {turn_idx}: {proposition}...")
            print(f"[Process {process_id}] --------------------------------")
        
        if turn_modified:
            stats["turns_modified"] += 1
    
    # Save the updated JSON file if not a dry run
    if not dry_run and stats["turns_modified"] > 0:
        output_path = os.path.join(OUTPUT_DIR, os.path.basename(file_path))
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, indent=2, ensure_ascii=False)
        print(f"[Process {process_id}] Saved updated file to {output_path}")
    
    return stats

def worker_process(file_path, dry_run, process_id):
    """Worker function for each process"""
    try:
        return process_json_file(file_path, dry_run, process_id)
    except Exception as e:
        print(f"[Process {process_id}] Error processing {file_path}: {e}")
        return {
            "file_path": file_path,
            "error": str(e),
            "turns_processed": 0,
            "props_processed": 0,
            "causal_props_found": 0,
            "turns_modified": 0
        }

def main():
    parser = argparse.ArgumentParser(description="Check for causal relationships in propositions")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes, just print what would be done")
    parser.add_argument("--file", type=str, help="Process only a specific file")
    parser.add_argument("--processes", type=int, default=NUM_PROCESSES, help="Number of parallel processes to use")
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
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
    
    print(f"Found {len(json_files)} files to process")
    print(f"Using {args.processes} parallel processes")
    
    # Process files in parallel
    with multiprocessing.Pool(processes=args.processes) as pool:
        # Create a list of (file_path, process_id) tuples for mapping
        # Pass dry_run directly in the tasks
        tasks = [(file_path, args.dry_run, i % args.processes) for i, file_path in enumerate(json_files)]
        
        # Execute the tasks in parallel - use worker_process directly instead of a partial
        results = pool.starmap(worker_process, tasks)
    
    # Combine statistics from all processes
    total_stats = {
        "files_processed": len(results),
        "total_turns_processed": sum(stats["turns_processed"] for stats in results),
        "total_props_processed": sum(stats["props_processed"] for stats in results),
        "total_causal_props": sum(stats["causal_props_found"] for stats in results),
        "total_turns_modified": sum(stats["turns_modified"] for stats in results)
    }
    
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
    multiprocessing.freeze_support()  # Required for Windows
    main()
