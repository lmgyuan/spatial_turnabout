#!/usr/bin/env python3
"""
Extract Clean Propositions Script
Processes prop_debug files and creates clean, concise versions for AI analysis
"""

import os
import re
from pathlib import Path

def extract_clean_props():
    """Extract clean propositions from prop_debug files"""
    
    # Define the three model directories (relative to source directory)
    model_dirs = [
        "../output_spatial/nebius-llama3.3-70b_prompt_prop_generated_explicit_context_sum_label_spatial",
        "../output_spatial/nebius-qwen-32b_prompt_prop_generated_explicit_context_sum_label_spatial", 
        "../output_spatial/nebius-qwen3-32b_prompt_prop_generated_explicit_context_sum_label_spatial"
    ]
    
    # Read ALL spatial reasoning rules from the official RuleText3.txt file
    try:
        with open('../Rules/RuleText3.txt', 'r', encoding='utf-8') as f:
            rule_lines = f.readlines()
        
        spatial_rules = "SPATIAL REASONING RULES:\n"
        for i, rule_line in enumerate(rule_lines, 1):
            rule_text = rule_line.strip()
            if rule_text:  # Skip empty lines
                spatial_rules += f"{i}. {rule_text}\n"
                
    except FileNotFoundError:
        print("Warning: Rules/RuleText3.txt not found, using fallback rules")
        spatial_rules = """SPATIAL REASONING RULES:
1. If XXX is above YYY then YYY is below XXX
2. If XXX is below YYY then YYY is above XXX
3. If XXX is to the left of YYY then YYY is to the right of XXX
4. If XXX is to the right of YYY then YYY is to the left of XXX
... (fallback - full rules not loaded)"""

    for model_dir in model_dirs:
        if not os.path.exists(model_dir):
            print(f"Directory not found: {model_dir}")
            continue
            
        # Find the prop_debug file in this directory
        debug_files = [f for f in os.listdir(model_dir) if f.startswith("props_debug_log_")]
        if not debug_files:
            print(f"No prop_debug file found in {model_dir}")
            continue
            
        debug_file = debug_files[0]
        debug_path = os.path.join(model_dir, debug_file)
        
        # Extract model name from the directory path more carefully
        dir_parts = model_dir.split("/")
        model_part = dir_parts[-1]  # Get the last part which contains the model directory name
        if "llama3.3-70b" in model_part:
            model_name = "Llama3.3-70B"
        elif "qwen3-32b" in model_part:
            model_name = "Qwen3-32B"
        elif "qwen-32b" in model_part:
            model_name = "Qwen-32B"
        else:
            model_name = "Unknown"
        
        print(f"Processing {model_name}...")
        
        try:
            with open(debug_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extract all turns and their propositions
            turn_sections = re.split(r'TURN \d+:', content)[1:]  # Skip header
            print(f"Found {len(turn_sections)} turn sections")
            
            # Collect all cases with their information for proper sorting
            all_cases = []
            
            for section in turn_sections:
                # Extract turn information with turn numbers
                turn_match = re.search(r'(\d+-\d+-\d+_[\w\s,]+?)\s*\(Turn (\d+)\)', section)
                if not turn_match:
                    continue
                    
                case_name = turn_match.group(1).strip()
                turn_number = int(turn_match.group(2))
                
                # Extract case ID for proper sorting (e.g., "1-2-4" from "1-2-4_Turnabout_Sisters")
                case_id_match = re.match(r'(\d+)-(\d+)-(\d+)', case_name)
                if case_id_match:
                    case_sort_key = (int(case_id_match.group(1)), int(case_id_match.group(2)), 
                                   int(case_id_match.group(3)), turn_number)
                else:
                    case_sort_key = (999, 999, 999, turn_number)  # Fallback for non-standard formats
                
                # Extract propositions using updated regex patterns for the new format
                props = []
                
                # First, try to find the section after "Generate all 15 relevant propositions:"
                prop_section_match = re.search(r'Generate all 15 relevant propositions:\s*\n\n(.*?)(?=PARSED PROPOSITIONS:|$)', section, re.DOTALL)
                if not prop_section_match:
                    # Fallback: try the original pattern in case some files still use it
                    prop_section_match = re.search(r'Generate all relevant propositions:\s*\n\n(.*?)(?=PARSED PROPOSITIONS:|$)', section, re.DOTALL)
                    if prop_section_match:
                        print(f"    Found prop section using fallback pattern")
                else:
                    print(f"    Found prop section using new pattern")
                
                if prop_section_match:
                    prop_section = prop_section_match.group(1)
                    
                    # Remove <think> tags and content inside them
                    prop_section = re.sub(r'<think>.*?</think>', '', prop_section, flags=re.DOTALL)
                    
                    # Extract individual propositions - try multiple patterns
                    # Pattern 1: Standard "Prop X:" format
                    prop_matches = re.findall(r'Prop (\d+):\s*(.+?)(?=\nProp \d+:|$)', prop_section, re.DOTALL)
                    
                    # If no matches with standard pattern, try alternative patterns
                    if not prop_matches:
                        # Pattern 2: Look for numbered propositions without "Prop" prefix
                        prop_matches = re.findall(r'^(\d+)\.\s*(.+?)(?=\n\d+\.|$)', prop_section, re.MULTILINE | re.DOTALL)
                    
                    # If still no matches, try to find any lines that look like propositions
                    if not prop_matches:
                        # Pattern 3: Lines that start with "If" and contain spatial reasoning
                        potential_props = re.findall(r'^(If .+?)(?=\n|$)', prop_section, re.MULTILINE)
                        prop_matches = [(str(i+1), prop) for i, prop in enumerate(potential_props) if len(prop) > 20]
                    
                    for prop_num, prop_text in prop_matches:
                        # Clean up the proposition text
                        prop_clean = re.sub(r'\s+', ' ', prop_text.strip())
                        # Remove any remaining think tags or markdown
                        prop_clean = re.sub(r'<[^>]+>', '', prop_clean)
                        prop_clean = re.sub(r'\*+', '', prop_clean)
                        
                        # Filter out template text and invalid propositions
                        if (prop_clean and 
                            not prop_clean.startswith('[') and 
                            'Your first proposition' not in prop_clean and
                            'etc.' not in prop_clean and
                            'Do not use markdown' not in prop_clean and
                            len(prop_clean) > 20):  # Must be substantial
                                                         props.append(prop_clean)
                if not props:
                    parsed_section_match = re.search(r'PARSED PROPOSITIONS:\s*\n-+\s*\n(.*?)(?=\n=+|$)', section, re.DOTALL)
                    if parsed_section_match:
                        print(f"    Found parsed propositions section")
                        parsed_section = parsed_section_match.group(1)
                        # Extract numbered propositions from parsed section
                        parsed_matches = re.findall(r'^\s*(\d+):\s*(.+?)(?=\n\s*\d+:|$)', parsed_section, re.MULTILINE | re.DOTALL)
                        for prop_num, prop_text in parsed_matches:
                            prop_clean = re.sub(r'\s+', ' ', prop_text.strip())
                            if prop_clean and len(prop_clean) > 20:
                                props.append(prop_clean)
                
                if not prop_section_match:
                    print(f"    No prop section found for {case_name} turn {turn_number}")
                
                if props:
                    print(f"  Extracted {len(props)} props from {case_name} turn {turn_number}")
                    all_cases.append({
                        'case_name': case_name,
                        'turn_number': turn_number,
                        'sort_key': case_sort_key,
                        'props': props
                    })
                else:
                    print(f"  No props found for {case_name} turn {turn_number}")
            
            # Sort cases by case ID and turn number
            all_cases.sort(key=lambda x: x['sort_key'])
            
            clean_content = f"""SPATIAL REASONING PROPOSITIONS - {model_name.upper()}
=================================================================

DESCRIPTION:
This file contains spatial reasoning propositions generated by the {model_name} model for legal case analysis. These propositions are logical statements that can be used to identify contradictions in testimonies and evidence by applying spatial reasoning rules.

{spatial_rules}

=================================================================
EXTRACTED PROPOSITIONS BY CASE
=================================================================

"""
            
            # Write out the sorted cases
            for case_info in all_cases:
                # Extract case ID and clean case name
                case_id_match = re.match(r'(\d+-\d+-\d+)_(.+)', case_info['case_name'])
                if case_id_match:
                    case_id = case_id_match.group(1)
                    case_title = case_id_match.group(2).replace('_', ' ')
                else:
                    case_id = "Unknown"
                    case_title = case_info['case_name']
                
                case_header = f"CASE {case_id}: {case_title} (Turn {case_info['turn_number']})"
                clean_content += f"\n{case_header}\n"
                clean_content += "-" * len(case_header) + "\n"
                for j, prop in enumerate(case_info['props'], 1):
                    clean_content += f"Prop {j}: {prop}\n"
                clean_content += "\n"
            
            # Save the clean file
            safe_model_name = model_name.lower().replace('-', '_').replace('.', '_').replace(' ', '_')
            output_filename = f"clean_propositions_{safe_model_name}.txt"
            output_path = os.path.join(model_dir, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(clean_content)
            
            print(f"✓ Created clean propositions file: {output_path}")
            
        except Exception as e:
            print(f"Error processing {model_dir}: {str(e)}")

def main():
    """Main function"""
    print("Extracting Clean Propositions from Debug Files...")
    print("=" * 60)
    
    try:
        extract_clean_props()
        print("\n✓ All clean proposition files generated successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 