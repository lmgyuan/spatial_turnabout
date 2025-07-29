import os
import json
from datetime import datetime

class DebugLogger:
    """General debug logger for LLM interactions across all prompt types"""
    
    def __init__(self):
        self.logs = []  # Store all LLM interactions for this run
        self.enabled = False  # Can be toggled on/off
    
    def enable(self):
        """Enable debug logging"""
        self.enabled = True
        print(f"[DEBUG] Debug logging enabled")
    
    def disable(self):
        """Disable debug logging"""
        self.enabled = False
        print(f"[DEBUG] Debug logging disabled")
    
    def log_llm_interaction(self, case_name, turn_idx, prompt_sent, raw_response, parsed_result, prompt_type=None):
        """Log a single LLM interaction"""
        if not self.enabled:
            return
        
        log_entry = {
            'case_name': case_name,
            'turn_idx': turn_idx,
            'timestamp': datetime.now().isoformat(),
            'prompt_type': prompt_type or 'unknown',
            'prompt_sent_to_llm': prompt_sent,
            'raw_llm_response': raw_response,
            'parsed_result': parsed_result
        }
        self.logs.append(log_entry)
    
    def save_debug_log(self, output_dir, model_name, prompt_name):
        """Save debug log to file with similar format to props debug log"""
        if not self.logs:
            return
            
        # Create filename similar to props debug log
        log_filename = f"debug_log_{model_name}_{prompt_name}.txt"
        log_path = os.path.join(output_dir, log_filename)
        
        # Check if this is a new file or append to existing
        is_new_file = not os.path.exists(log_path)
        current_run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        with open(log_path, 'a', encoding='utf-8') as f:
            if is_new_file:
                # Write header only for new files
                f.write("LLM DEBUG LOG\n")
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
            f.write(f"Turns processed in this run: {len(self.logs)}\n")
            f.write("=" * 100 + "\n\n")
            
            for i, entry in enumerate(self.logs):
                f.write(f"TURN {i+1}: {entry['case_name']} (Turn {entry['turn_idx']}) [RUN: {current_run_id}]\n")
                f.write("=" * 60 + "\n\n")
                
                # Prompt type
                f.write(f"PROMPT TYPE: {entry['prompt_type']}\n")
                f.write("-" * 20 + "\n\n")
                
                # LLM Input
                f.write("LLM INPUT (PROMPT SENT):\n")
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
                f.write("\n")
                
                f.write("\n" + "=" * 100 + "\n\n")
        
        print(f"Debug log {'created' if is_new_file else 'appended to'}: {log_path}")
        
        # Clear logs after saving to prevent memory buildup
        self.logs.clear()

# Global debug logger instance
debug_logger = DebugLogger()
