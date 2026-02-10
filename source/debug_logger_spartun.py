import os
import json
from datetime import datetime

class DebugLoggerSpartun:
    """Extended debug logger for SPARTUN with generation call tracking"""
    
    def __init__(self):
        self.logs = []  # Store all LLM interactions for this run
        self.enabled = False  # Can be toggled on/off
    
    def enable(self):
        """Enable debug logging"""
        self.enabled = True
        print(f"[DEBUG] Debug logging enabled (SPARTUN)")
    
    def disable(self):
        """Disable debug logging"""
        self.enabled = False
        print(f"[DEBUG] Debug logging disabled (SPARTUN)")
    
    def log_llm_interaction(self, case_name, turn_idx, prompt_sent, raw_response, parsed_result, prompt_type=None):
        """Log a final answer LLM interaction"""
        if not self.enabled:
            return
        
        log_entry = {
            'log_type': 'answer',
            'case_name': case_name,
            'turn_idx': turn_idx,
            'timestamp': datetime.now().isoformat(),
            'prompt_type': prompt_type or 'unknown',
            'prompt_sent_to_llm': prompt_sent,
            'raw_llm_response': raw_response,
            'parsed_result': parsed_result
        }
        self.logs.append(log_entry)
    
    def log_generation_call(self, case_id, q_id, generation_type, prompt_sent, raw_response, parsed_items, count_requested, count_parsed):
        """Log an intermediate generation call (rules/props)
        
        Args:
            case_id: Case identifier
            q_id: Question ID
            generation_type: 'rules', 'props', or 'rag_props'
            prompt_sent: The generation prompt sent to LLM
            raw_response: Raw LLM response
            parsed_items: List of parsed rules/props
            count_requested: Number requested (e.g., 10)
            count_parsed: Number actually parsed
        """
        if not self.enabled:
            return
        
        log_entry = {
            'log_type': 'generation',
            'case_id': case_id,
            'q_id': q_id,
            'timestamp': datetime.now().isoformat(),
            'generation_type': generation_type,
            'count_requested': count_requested,
            'count_parsed': count_parsed,
            'prompt_sent_to_llm': prompt_sent,
            'raw_llm_response': raw_response,
            'parsed_items': parsed_items
        }
        self.logs.append(log_entry)
    
    def save_debug_log(self, output_dir, model_name, prompt_name):
        """Save debug log to file with interleaved generation and answer calls"""
        if not self.logs:
            return
            
        # Create filename
        log_filename = f"debug_log_{model_name}_{prompt_name}.txt"
        log_path = os.path.join(output_dir, log_filename)
        
        # Check if this is a new file or append to existing
        is_new_file = not os.path.exists(log_path)
        current_run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Sort logs by case+question first, then generation before answer, then timestamp
        # This ensures generation and answer calls for the same question are grouped together
        sorted_logs = sorted(self.logs, key=lambda x: (
            f"{x.get('case_id', x.get('case_name'))}_q{x.get('q_id', x.get('turn_idx'))}",  # Group by case+question
            0 if x['log_type'] == 'generation' else 1,  # Generation calls before answer calls
            x['timestamp']  # Then by timestamp within the same type
        ))
        
        with open(log_path, 'a', encoding='utf-8') as f:
            if is_new_file:
                # Write header only for new files
                f.write("LLM DEBUG LOG (SPARTUN EXTENDED)\n")
                f.write("=" * 100 + "\n\n")
                f.write(f"Model: {model_name}\n")
                f.write(f"Prompt Template: {prompt_name}\n")
                f.write("=" * 100 + "\n\n")
            else:
                # Add separator for new run in existing file
                f.write("\n" + "=" * 100 + "\n")
                f.write("NEW RUN STARTED\n")
                f.write("=" * 100 + "\n\n")
            
            # Add run-specific header
            f.write(f"RUN ID: {current_run_id}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Count generation and answer calls
            gen_calls = sum(1 for log in sorted_logs if log['log_type'] == 'generation')
            answer_calls = sum(1 for log in sorted_logs if log['log_type'] == 'answer')
            f.write(f"Generation calls: {gen_calls}\n")
            f.write(f"Answer calls: {answer_calls}\n")
            f.write(f"Total interactions: {len(sorted_logs)}\n")
            f.write("=" * 100 + "\n\n")
            
            # Group logs by case/question for better organization
            current_case_q = None
            interaction_num = 0
            
            for entry in sorted_logs:
                if entry['log_type'] == 'generation':
                    case_q_key = f"{entry['case_id']}_q{entry['q_id']}"
                    
                    # New case/question header if needed
                    if case_q_key != current_case_q:
                        if current_case_q is not None:
                            f.write("\n" + "=" * 100 + "\n\n")
                        current_case_q = case_q_key
                        f.write(f"CASE: {entry['case_id']} | QUESTION: {entry['q_id']}\n")
                        f.write("=" * 100 + "\n\n")
                        interaction_num = 0
                    
                    interaction_num += 1
                    f.write(f"[{interaction_num}] GENERATION CALL: {entry['generation_type'].upper()}\n")
                    f.write("-" * 60 + "\n\n")
                    
                    # Generation metadata
                    f.write(f"Requested Count: {entry['count_requested']}\n")
                    f.write(f"Parsed Count: {entry['count_parsed']}\n")
                    if entry['count_requested'] != entry['count_parsed']:
                        f.write(f"⚠️  MISMATCH: Expected {entry['count_requested']}, got {entry['count_parsed']}\n")
                    f.write("\n")
                    
                    # Generation prompt
                    f.write("GENERATION PROMPT:\n")
                    f.write("-" * 30 + "\n")
                    f.write(entry['prompt_sent_to_llm'])
                    f.write("\n\n")
                    
                    # LLM response
                    f.write("LLM RESPONSE:\n")
                    f.write("-" * 30 + "\n")
                    f.write(entry['raw_llm_response'])
                    f.write("\n\n")
                    
                    # Parsed items
                    f.write(f"PARSED {entry['generation_type'].upper()} ({entry['count_parsed']}):\n")
                    f.write("-" * 30 + "\n")
                    for i, item in enumerate(entry['parsed_items'], 1):
                        f.write(f"{i}. {item}\n")
                    f.write("\n")
                
                elif entry['log_type'] == 'answer':
                    case_q_key = f"{entry['case_name']}_q{entry['turn_idx']}"
                    
                    # New case/question header if needed
                    if case_q_key != current_case_q:
                        if current_case_q is not None:
                            f.write("\n" + "=" * 100 + "\n\n")
                        current_case_q = case_q_key
                        f.write(f"CASE: {entry['case_name']} | QUESTION: {entry['turn_idx']}\n")
                        f.write("=" * 100 + "\n\n")
                        interaction_num = 0
                    
                    interaction_num += 1
                    f.write(f"[{interaction_num}] FINAL ANSWER CALL\n")
                    f.write("-" * 60 + "\n\n")
                    
                    # Prompt type
                    f.write(f"PROMPT TYPE: {entry['prompt_type']}\n")
                    f.write("\n")
                    
                    # LLM Input
                    f.write("LLM INPUT (FINAL PROMPT):\n")
                    f.write("-" * 30 + "\n")
                    f.write(entry['prompt_sent_to_llm'])
                    f.write("\n\n")
                    
                    # LLM Output
                    f.write("LLM OUTPUT (RAW RESPONSE):\n")
                    f.write("-" * 30 + "\n")
                    f.write(entry['raw_llm_response'])
                    f.write("\n\n")
                    
                    # Parsed Results
                    f.write("PARSED RESULT:\n")
                    f.write("-" * 20 + "\n")
                    if isinstance(entry['parsed_result'], dict):
                        f.write(json.dumps(entry['parsed_result'], indent=2))
                    else:
                        f.write(str(entry['parsed_result']))
                    f.write("\n\n")
            
            f.write("\n" + "=" * 100 + "\n")
        
        print(f"Debug log {'created' if is_new_file else 'appended to'}: {log_path}")
        
        # Also save JSON version for programmatic analysis
        self._save_json_log(output_dir, model_name, prompt_name, sorted_logs)
        
        # Clear logs after saving to prevent memory buildup
        self.logs.clear()
    
    def _save_json_log(self, output_dir, model_name, prompt_name, sorted_logs):
        """Save structured JSON log for programmatic analysis"""
        if not sorted_logs:
            return
        
        # Create filename
        json_filename = f"debug_log_{model_name}_{prompt_name}.json"
        json_path = os.path.join(output_dir, json_filename)
        
        # Build metadata
        gen_calls = sum(1 for log in sorted_logs if log['log_type'] == 'generation')
        answer_calls = sum(1 for log in sorted_logs if log['log_type'] == 'answer')
        
        # Group interactions by case+question
        questions_map = {}
        for entry in sorted_logs:
            if entry['log_type'] == 'generation':
                key = f"{entry['case_id']}_q{entry['q_id']}"
                if key not in questions_map:
                    questions_map[key] = {
                        'case_id': entry['case_id'],
                        'question_id': entry['q_id'],
                        'generation_calls': [],
                        'answer_call': None
                    }
                
                # Add generation call
                questions_map[key]['generation_calls'].append({
                    'generation_type': entry['generation_type'],
                    'timestamp': entry['timestamp'],
                    'requested_count': entry['count_requested'],
                    'parsed_count': entry['count_parsed'],
                    'has_mismatch': entry['count_requested'] != entry['count_parsed'],
                    'prompt': entry['prompt_sent_to_llm'],
                    'raw_response': entry['raw_llm_response'],
                    'parsed_items': entry['parsed_items']
                })
            
            elif entry['log_type'] == 'answer':
                key = f"{entry['case_name']}_q{entry['turn_idx']}"
                if key not in questions_map:
                    questions_map[key] = {
                        'case_id': entry['case_name'],
                        'question_id': entry['turn_idx'],
                        'generation_calls': [],
                        'answer_call': None
                    }
                
                # Add answer call
                questions_map[key]['answer_call'] = {
                    'timestamp': entry['timestamp'],
                    'prompt_type': entry['prompt_type'],
                    'prompt': entry['prompt_sent_to_llm'],
                    'raw_response': entry['raw_llm_response'],
                    'parsed_result': entry['parsed_result']
                }
        
        # Convert to list maintaining the sorted order
        questions_list = []
        seen_keys = set()
        for entry in sorted_logs:
            if entry['log_type'] == 'generation':
                key = f"{entry['case_id']}_q{entry['q_id']}"
            else:
                key = f"{entry['case_name']}_q{entry['turn_idx']}"
            
            if key not in seen_keys:
                questions_list.append(questions_map[key])
                seen_keys.add(key)
        
        # Build final structure
        json_data = {
            'metadata': {
                'run_id': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'model': model_name,
                'prompt_template': prompt_name,
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'stats': {
                    'total_generation_calls': gen_calls,
                    'total_answer_calls': answer_calls,
                    'total_interactions': len(sorted_logs),
                    'total_questions': len(questions_list)
                }
            },
            'questions': questions_list
        }
        
        # Write JSON file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print(f"JSON debug log saved: {json_path}")

# Global debug logger instance for SPARTUN
debug_logger_spartun = DebugLoggerSpartun()

