import json
import os
import argparse
from datetime import datetime
from run_models_spatial import (
    parse_json, 
    build_prompt_prefix_suffix, 
    build_prompt, 
    get_output_dir,
    get_fnames
)

def test_prompts_generation():
    """Test prompt generation with the same logic as run_models_spatial.py"""
    
    # Configuration - mirroring the actual script
    MODEL = 'test-model'  # Dummy model name
    PROMPT = 'base'       # You can change this to test different prompts
    CONTEXT = None        # You can change this to 'full' or 'sum' to test context
    CASE = "ALL"          # You can change this to test specific cases
    NO_DESCRIPTION = False # Set to True to test without descriptions
    DATA = 'aceattorney'  # You can change this to 'danganronpa'
    LABEL = 'spatial'     # You can change this to test different labels or set to None
    
    print("=" * 60)
    print("PROMPT GENERATION TEST")
    print("=" * 60)
    print(f"Model: {MODEL}")
    print(f"Prompt: {PROMPT}")
    print(f"Context: {CONTEXT}")
    print(f"Case: {CASE}")
    print(f"No Description: {NO_DESCRIPTION}")
    print(f"Data: {DATA}")
    print(f"Label Filter: {LABEL}")
    print("-" * 60)
    
    # Set data directory (same logic as actual script)
    if DATA == 'aceattorney':
        data_dir = '../data/aceattorney_data/final'
    elif DATA == 'danganronpa':
        data_dir = '../data/danganronpa_data/final'
    else:
        print(f"Error: Unknown data type '{DATA}'")
        return
    
    # Create timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Get output directory (same logic as actual script)
    output_dir = get_output_dir(MODEL, PROMPT, CONTEXT, CASE, NO_DESCRIPTION, DATA, LABEL)
    test_output_dir = output_dir.replace('../output_spatial/', '../output_spatial/prompt_test/')
    
    # Create output directory
    if not os.path.exists(test_output_dir):
        os.makedirs(test_output_dir)
    
    print(f"Data directory: {data_dir}")
    print(f"Test output directory: {test_output_dir}")
    
    # Get file names (same logic as actual script)
    fnames = get_fnames(data_dir, test_output_dir, CASE, eval=True, verbose=True)
    
    if not fnames:
        print("No files found to process!")
        return
    
    # Load prompt prefix and suffix (same logic as actual script)
    try:
        PROMPT_PREFIX, PROMPT_SUFFIX = build_prompt_prefix_suffix(PROMPT)
        print(f"Successfully loaded prompt template: {PROMPT}")
    except Exception as e:
        print(f"Error loading prompt template: {e}")
        return
    
    print("-" * 60)
    
    total_prompts = 0
    total_files_processed = 0
    files_with_prompts = 0
    
    # Process each file (same logic as actual script)
    for fname in fnames:
        print(f"\nProcessing: {fname}")
        
        try:
            # Parse JSON with label filtering (same as actual script)
            turns, prev_context = parse_json(os.path.join(data_dir, fname), LABEL)
            
            if not turns:  # Skip cases with no turns (same as actual script)
                print(f"  - Skipped: No turns found (after label filtering)")
                continue
            
            print(f"  - Found {len(turns)} turns (after label filtering)")
            print(f"  - Previous context length: {len(prev_context)} characters")
            
            # Build prompts (same logic as actual script)
            prompts = build_prompt(turns, prev_context, PROMPT_PREFIX, PROMPT_SUFFIX, CONTEXT, NO_DESCRIPTION, MODEL)
            print(f"  - Generated {len(prompts)} prompts")
            
            if prompts:
                files_with_prompts += 1
                
                # Save each prompt to a separate file
                base_filename = fname.replace('.json', '')
                for i, prompt in enumerate(prompts):
                    prompt_filename = f"{base_filename}_turn_{i+1}.txt"
                    prompt_filepath = os.path.join(test_output_dir, prompt_filename)
                    
                    with open(prompt_filepath, 'w', encoding='utf-8') as f:
                        f.write(f"=== PROMPT FOR {fname} - TURN {i+1} ===\n")
                        f.write(f"Model: {MODEL}\n")
                        f.write(f"Prompt Type: {PROMPT}\n")
                        f.write(f"Context: {CONTEXT}\n")
                        f.write(f"Case: {CASE}\n")
                        f.write(f"No Description: {NO_DESCRIPTION}\n")
                        f.write(f"Data: {DATA}\n")
                        f.write(f"Label Filter: {LABEL}\n")
                        f.write(f"Timestamp: {timestamp}\n")
                        f.write("=" * 60 + "\n\n")
                        f.write(prompt)
                        f.write("\n\n" + "=" * 60 + "\n")
                        f.write(f"END OF PROMPT FOR TURN {i+1}\n")
                    
                    print(f"    - Saved: {prompt_filename}")
                
                total_prompts += len(prompts)
            
            total_files_processed += 1
            
        except Exception as e:
            print(f"  - Error processing {fname}: {e}")
            import traceback
            traceback.print_exc()
    
    # Save metadata (same as actual script)
    metadata_path = os.path.join(test_output_dir, 'test_metadata.json')
    with open(metadata_path, 'w') as file:
        json.dump({
            'model': MODEL,
            'prompt': PROMPT,
            'context': "none" if CONTEXT is None else CONTEXT,
            'case': CASE if CASE != "ALL" else "all",
            'no_description': NO_DESCRIPTION,
            'data': DATA,
            'label': LABEL if LABEL is not None else "none",
            'timestamp': timestamp,
            'total_files_found': len(fnames),
            'total_files_processed': total_files_processed,
            'files_with_prompts': files_with_prompts,
            'total_prompts_generated': total_prompts
        }, file, indent=2)
    
    print(f"\n" + "=" * 60)
    print(f"SUMMARY:")
    print(f"Total files found: {len(fnames)}")
    print(f"Total files processed: {total_files_processed}")
    print(f"Files with prompts: {files_with_prompts}")
    print(f"Total prompts generated: {total_prompts}")
    print(f"Prompts saved to: {test_output_dir}")
    print(f"Metadata saved to: {metadata_path}")
    print(f"=" * 60)

def test_different_configurations():
    """Test multiple configurations like the actual script would handle"""
    
    configurations = [
        {
            'name': 'spatial_no_context',
            'PROMPT': 'base',
            'CONTEXT': None,
            'NO_DESCRIPTION': False,
            'DATA': 'aceattorney',
            'LABEL': 'spatial'
        },
        {
            'name': 'spatial_full_context',
            'PROMPT': 'base',
            'CONTEXT': 'full',
            'NO_DESCRIPTION': False,
            'DATA': 'aceattorney',
            'LABEL': 'spatial'
        },
        {
            'name': 'all_turns_no_filter',
            'PROMPT': 'base',
            'CONTEXT': None,
            'NO_DESCRIPTION': False,
            'DATA': 'aceattorney',
            'LABEL': None
        }
    ]
    
    print("Testing multiple configurations...")
    for config in configurations:
        print(f"\n{'='*60}")
        print(f"Testing configuration: {config['name']}")
        print(f"{'='*60}")
        
        # You would modify test_prompts_generation to accept parameters
        # For now, just run the default configuration
        test_prompts_generation()
        break  # Remove this to test all configurations

if __name__ == "__main__":
    print("Spatial Prompt Testing Script")
    print("Mirrors the functionality of run_models_spatial.py")
    print("=" * 60)
    
    # Test with default configuration
    test_prompts_generation()
    
    # Uncomment to test multiple configurations
    # test_different_configurations() 