#!/usr/bin/env python3
"""
Script to extract and analyze spatial reasoning rule usage from CoT responses.
Analyzes output files to determine which rules are being used based on a provided rule file.
"""

import json
import os
import re
import argparse
from collections import defaultdict, Counter
from pathlib import Path

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Analyze spatial reasoning rule usage in model outputs')
    parser.add_argument('--rule_file', '-r', type=str, required=True,
                        help='Path to rule text file (e.g., ../Rules/RuleText4.txt)')
    parser.add_argument('--input_dir', '-i', type=str, required=True,
                        help='Directory containing model output JSON files')
    parser.add_argument('--output_file', '-o', type=str, default=None,
                        help='Output analysis file (default: auto-generated from input directory name)')
    return parser.parse_args()

def load_rules_from_file(rule_file_path):
    """Load spatial reasoning rules from a text file."""
    rules = []
    
    if not os.path.exists(rule_file_path):
        raise FileNotFoundError(f"Rule file not found: {rule_file_path}")
    
    print(f"Loading rules from: {rule_file_path}")
    
    with open(rule_file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Look for lines that start with "If"
            if line.startswith('If '):
                rules.append(line)
            else:
                # Warn about unexpected format but continue
                if line:  # Only warn for non-empty lines
                    print(f"Warning: Line {line_num} doesn't start with 'If': {line[:50]}...")
    
    print(f"Loaded {len(rules)} rules from {rule_file_path}")
    return rules

def create_rule_patterns(spatial_rules):
    """Create various patterns to match rule usage in CoT text."""
    patterns = {}
    
    for i, rule in enumerate(spatial_rules):
        rule_id = f"rule_{i+1:02d}"
        
        # Extract key concepts from each rule for flexible matching
        key_concepts = extract_key_concepts(rule)
        
        # Create exact match pattern (quoted rule)
        exact_pattern = re.escape(rule)
        
        # Create flexible patterns for partial matches
        flexible_patterns = create_flexible_patterns(rule, key_concepts)
        
        patterns[rule_id] = {
            "full_text": rule,
            "exact_pattern": exact_pattern,
            "key_concepts": key_concepts,
            "flexible_patterns": flexible_patterns
        }
    
    return patterns

def extract_key_concepts(rule):
    """Extract key spatial concepts from a rule."""
    concepts = []
    
    # Define concept mapping
    concept_map = {
        "see|view|visible|sight": "visibility",
        "between|blocking|blocks": "blocking", 
        "room|different room|same room": "room_separation",
        "facing|back to": "orientation",
        "above|below|up|down": "vertical",
        "left|right|direction": "direction",
        "move|travel|goes": "movement",
        "shot|bullet|trajectory": "trajectory",
        "hit|falls|fall": "impact",
        "taller|shorter|wider|narrower|larger|smaller": "size",
        "location|time": "temporal_spatial",
        "locked|open|passed through": "accessibility",
        "wall|separated": "separation",
        "reach|touch|close|far|range": "distance",
        "aligned|vertically|horizontally": "alignment",
        "middle|edge|corner|boundary": "positioning"
    }
    
    rule_lower = rule.lower()
    for pattern, concept in concept_map.items():
        if re.search(pattern, rule_lower):
            concepts.append(concept)
    
    return concepts

def create_flexible_patterns(rule, key_concepts):
    """Create flexible regex patterns for rule matching."""
    patterns = []
    
    # Extract core spatial relationships
    if "see" in rule.lower() and "between" in rule.lower():
        patterns.append(r"(?:cannot|can\'?t)\s+see.*between")
        patterns.append(r"between.*(?:cannot|can\'?t)\s+see")
        
    if "blocks" in rule.lower() and "view" in rule.lower():
        patterns.append(r"blocks?\s+(?:the\s+)?view")
        patterns.append(r"view.*blocked")
        
    if "same room" in rule.lower():
        patterns.append(r"same\s+room.*(?:can\s+)?potentially\s+see")
        patterns.append(r"potentially\s+see.*same\s+room")
        
    if "different room" in rule.lower():
        patterns.append(r"different\s+room.*cannot\s+see")
        patterns.append(r"cannot\s+see.*different\s+room")
        
    # Add more patterns based on rule content
    if "facing" in rule.lower():
        patterns.append(r"facing.*can\s+see")
        
    if "back to" in rule.lower():
        patterns.append(r"back\s+to.*cannot\s+see")
    
    return patterns

def find_rule_mentions(cot_text, rule_patterns):
    """Find which rules are mentioned in the CoT text."""
    mentioned_rules = []
    
    # Clean the text for better matching
    cot_clean = clean_text(cot_text)
    
    for rule_id, pattern_data in rule_patterns.items():
        rule_mentioned = False
        match_types = []
        
        # Check for exact quotes of the rule
        if re.search(pattern_data["exact_pattern"], cot_text, re.IGNORECASE):
            rule_mentioned = True
            match_types.append("exact_quote")
        
        # Check for flexible patterns
        for pattern in pattern_data["flexible_patterns"]:
            if re.search(pattern, cot_clean, re.IGNORECASE):
                rule_mentioned = True
                match_types.append("concept_match")
                break
        
        # Check for explicit rule references
        rule_ref_patterns = [
            rf"rule.*{rule_id.split('_')[1]}",
            r"according\s+to\s+(?:the\s+)?rule",
            r"applying\s+(?:the\s+)?rule",
            r"using\s+(?:the\s+)?rule",
            r"this\s+rule",
            r"rule.*applies?",
            r"spatial\s+reasoning\s+rule"
        ]
        
        for ref_pattern in rule_ref_patterns:
            if re.search(ref_pattern, cot_clean, re.IGNORECASE):
                # If rule reference found, check if our rule concepts are nearby
                nearby_text = get_nearby_text(cot_clean, ref_pattern, 100)
                if any(concept in nearby_text.lower() for concept in pattern_data["key_concepts"]):
                    rule_mentioned = True
                    match_types.append("explicit_reference")
                    break
        
        if rule_mentioned:
            mentioned_rules.append({
                "rule_id": rule_id,
                "rule_text": pattern_data["full_text"],
                "match_types": match_types,
                "concepts": pattern_data["key_concepts"]
            })
    
    return mentioned_rules

def clean_text(text):
    """Clean text for better pattern matching."""
    # Remove escape sequences and normalize whitespace
    text = text.replace('\\n', ' ').replace('\\u', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_nearby_text(text, pattern, window_size):
    """Get text around a matched pattern."""
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        start = max(0, match.start() - window_size)
        end = min(len(text), match.end() + window_size)
        return text[start:end]
    return ""

def generate_report(all_rule_usage, turn_results, case_summaries, rule_patterns, spatial_rules, total_turns, output_file, rule_file_path, input_dir):
    """Generate comprehensive analysis report."""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("SPATIAL REASONING RULE USAGE ANALYSIS\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Rule file: {rule_file_path}\n")
        f.write(f"Input directory: {input_dir}\n")
        f.write(f"Total cases analyzed: {len(case_summaries)}\n")
        f.write(f"Total turns analyzed: {total_turns}\n")
        f.write(f"Total spatial reasoning rules: {len(spatial_rules)}\n\n")
        
        # Summary statistics
        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 20 + "\n")
        rules_used = len([r for r in all_rule_usage.keys() if all_rule_usage[r]])
        rules_never_used = len(spatial_rules) - rules_used
        f.write(f"Rules used at least once: {rules_used}/{len(spatial_rules)} ({rules_used/len(spatial_rules)*100:.1f}%)\n")
        f.write(f"Rules never used: {rules_never_used}\n")
        
        # Turn-level statistics
        turns_with_rules = len([t for t in turn_results if t["num_rules_used"] > 0])
        turns_without_rules = total_turns - turns_with_rules
        f.write(f"Turns using spatial rules: {turns_with_rules}/{total_turns} ({turns_with_rules/total_turns*100:.1f}%)\n")
        f.write(f"Turns with no rule usage: {turns_without_rules}\n")
        
        # Average rules per turn
        avg_rules_per_turn = sum(t["num_rules_used"] for t in turn_results) / total_turns if total_turns > 0 else 0
        f.write(f"Average rules per turn: {avg_rules_per_turn:.2f}\n\n")
        
        # Rule usage frequency
        f.write("RULE USAGE FREQUENCY\n")
        f.write("-" * 25 + "\n")
        usage_counter = Counter()
        for rule_id, usages in all_rule_usage.items():
            usage_counter[rule_id] = len(usages)
        
        f.write("Most frequently used rules:\n")
        for rule_id, count in usage_counter.most_common(10):
            rule_text = rule_patterns[rule_id]["full_text"]
            f.write(f"  {rule_id}: {count} times - {rule_text[:80]}...\n")
        
        f.write(f"\nNever used rules:\n")
        for i, rule in enumerate(spatial_rules):
            rule_id = f"rule_{i+1:02d}"
            if rule_id not in usage_counter:
                f.write(f"  {rule_id}: {rule[:80]}...\n")
        
        # Detailed rule analysis
        f.write(f"\n\nDETAILED RULE USAGE ANALYSIS\n")
        f.write("-" * 35 + "\n")
        
        for i, rule in enumerate(spatial_rules):
            rule_id = f"rule_{i+1:02d}"
            usages = all_rule_usage.get(rule_id, [])
            
            f.write(f"\n{rule_id.upper()}: {rule}\n")
            f.write(f"Usage count: {len(usages)} turns\n")
            
            if usages:
                # Cases and turns where used
                cases_used = set(u["case"] for u in usages)
                f.write(f"Used in {len(cases_used)} cases: {', '.join(sorted(cases_used)[:3])}")
                if len(cases_used) > 3:
                    f.write(f" (and {len(cases_used)-3} more)")
                f.write("\n")
                
                # Example turns
                example_turns = [u["turn_id"] for u in usages[:3]]
                f.write(f"Example turns: {', '.join(example_turns)}\n")
                
                # Match types
                match_types = Counter()
                for usage in usages:
                    for match_type in usage["match_types"]:
                        match_types[match_type] += 1
                f.write(f"Match types: {dict(match_types)}\n")
            else:
                f.write("Never used in any turn.\n")
        
        # Turn-by-turn analysis (top cases)
        f.write(f"\n\nTURN-BY-TURN ANALYSIS\n")
        f.write("-" * 25 + "\n")
        
        # Show turns with most rule usage
        top_turns = sorted(turn_results, key=lambda x: x["num_rules_used"], reverse=True)[:20]
        f.write("Top 20 turns by rule usage:\n")
        for turn in top_turns:
            f.write(f"\n{turn['turn_id']}:\n")
            f.write(f"  Rules used: {turn['num_rules_used']}\n")
            if turn["rules_used"]:
                f.write(f"  Rule IDs: {', '.join(turn['rules_used'])}\n")
        
        # Case-level summary
        f.write(f"\n\nCASE-LEVEL SUMMARY\n")
        f.write("-" * 20 + "\n")
        
        # Sort cases by unique rules used
        sorted_cases = sorted(case_summaries, key=lambda x: x["num_unique_rules"], reverse=True)
        for case in sorted_cases:
            f.write(f"\n{case['case']}:\n")
            f.write(f"  Turns: {case['num_turns']}\n")
            f.write(f"  Unique rules used: {case['num_unique_rules']}\n")
            if case["unique_rules_used"]:
                f.write(f"  Rules: {', '.join(case['unique_rules_used'][:5])}")
                if len(case["unique_rules_used"]) > 5:
                    f.write(f" (and {len(case['unique_rules_used'])-5} more)")
                f.write("\n")
        
        f.write(f"\n\nANALYSIS COMPLETE\n")
        f.write(f"Report generated from {len(case_summaries)} cases and {total_turns} turns\n")
        f.write(f"Total rule mentions found: {sum(len(usages) for usages in all_rule_usage.values())}\n")

def analyze_directory(input_dir, spatial_rules):
    """Analyze all output files in the directory."""
    input_path = Path(input_dir)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Directory not found: {input_dir}")
    
    # Initialize tracking variables
    all_rule_usage = defaultdict(list)
    turn_results = []
    case_summaries = []
    rule_patterns = create_rule_patterns(spatial_rules)
    
    # Process all output files
    output_files = list(input_path.glob("*_outputs.json"))
    print(f"Found {len(output_files)} output files to analyze...")
    
    if not output_files:
        print(f"Warning: No *_outputs.json files found in {input_dir}")
        return all_rule_usage, turn_results, case_summaries, rule_patterns, 0
    
    total_turns = 0
    
    for file_path in output_files:
        case_name = file_path.stem.replace("_outputs", "")
        print(f"Processing: {case_name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            case_turn_count = len(data)
            case_rules_used = set()
            
            # Process each turn in the case
            for turn_data in data:
                turn_id = f"{case_name}_turn_{turn_data.get('idx', 0)}"
                cot_text = turn_data.get("cot", "")
                
                # Find mentioned rules in this turn
                mentioned_rules = find_rule_mentions(cot_text, rule_patterns)
                
                # Track rule usage for this specific turn
                turn_rule_ids = set()
                for rule_info in mentioned_rules:
                    rule_id = rule_info["rule_id"]
                    turn_rule_ids.add(rule_id)
                    case_rules_used.add(rule_id)
                    
                    all_rule_usage[rule_id].append({
                        "case": case_name,
                        "turn": turn_data.get("idx", 0),
                        "turn_id": turn_id,
                        "match_types": rule_info["match_types"],
                        "concepts": rule_info["concepts"]
                    })
                
                # Store turn-level results
                turn_results.append({
                    "turn_id": turn_id,
                    "case": case_name,
                    "turn_idx": turn_data.get("idx", 0),
                    "rules_used": list(turn_rule_ids),
                    "num_rules_used": len(turn_rule_ids),
                    "mentioned_rules": mentioned_rules
                })
                
                total_turns += 1
            
            # Store case-level summary
            case_summaries.append({
                "case": case_name,
                "num_turns": case_turn_count,
                "unique_rules_used": list(case_rules_used),
                "num_unique_rules": len(case_rules_used)
            })
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue
    
    return all_rule_usage, turn_results, case_summaries, rule_patterns, total_turns

def main():
    """Main function to run the rule usage analysis."""
    args = parse_arguments()
    
    # Auto-generate output filename if not provided
    if args.output_file is None:
        # Extract directory name and add suffix
        input_dir_name = Path(args.input_dir).name
        args.output_file = f"{input_dir_name}_rules_analysis.txt"
    
    print(f"Loading rules from: {args.rule_file}")
    print(f"Analyzing files in: {args.input_dir}")
    print(f"Output will be saved to: {args.output_file}")
    
    # Load spatial reasoning rules from file
    try:
        rules = load_rules_from_file(args.rule_file)
        print(f"Loaded {len(rules)} rules")
    except Exception as e:
        print(f"Error loading rules: {e}")
        return
    
    # Analyze rule usage in model outputs
    try:
        all_rule_usage, turn_results, case_summaries, rule_patterns, total_turns = analyze_directory(args.input_dir, rules)
        
        if total_turns == 0:
            print("Error: No turns found to analyze.")
            return
        
        # Generate the report
        generate_report(
            all_rule_usage, turn_results, case_summaries, rule_patterns, rules, 
            total_turns, args.output_file, args.rule_file, args.input_dir
        )
        
        print(f"\n✓ Analysis complete!")
        print(f"✓ Report saved to: {args.output_file}")
        print(f"✓ Analyzed {len(case_summaries)} cases with {total_turns} total turns")
        print(f"✓ Found {sum(len(usages) for usages in all_rule_usage.values())} rule mentions")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        return

if __name__ == "__main__":
    main() 