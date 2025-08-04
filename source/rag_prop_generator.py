import os
import json
from datetime import datetime

class RagPropGenerator:
    def __init__(self, prompt_file="prompts/rag_prop_generation_improved.json"):
        # Load prop generation prompt template
        with open(prompt_file, 'r', encoding='utf-8') as f:
            self.prompt_template = json.load(f)
        
        self.prompt_file = prompt_file  # Store for debugging
        
        self.props_log = []  # Store generated props for logging
        self.cache_file = None  # Will be set when output_dir is known
        self.props_cache = {}  # In-memory cache
    
    def set_cache_file(self, output_dir, model_name, prompt_name):
        """Set the cache file path and load existing cache"""
        self.cache_file = os.path.join(output_dir, f"rag_props_cache_{model_name}_{prompt_name}.json")
        self.load_cache()
    
    def load_cache(self):
        """Load existing props cache from file"""
        if self.cache_file and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.props_cache = json.load(f)
                print(f"[RAG PROPS CACHE] Loaded {len(self.props_cache)} cached rag-prop entries")
            except Exception as e:
                print(f"[RAG PROPS CACHE] Failed to load cache: {e}")
                self.props_cache = {}
        else:
            self.props_cache = {}
    
    def save_cache(self):
        """Save props cache to file"""
        if self.cache_file:
            try:
                os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self.props_cache, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[RAG PROPS CACHE] Failed to save cache: {e}")
    
    def get_cache_key(self, case_name, turn_idx, rag_rules_hash):
        """Generate cache key for a specific case, turn, and RAG rules"""
        return f"{case_name}_turn_{turn_idx}_rag_{rag_rules_hash}"
    
    def get_rag_rules_hash(self, rag_rules):
        """Generate a hash of the RAG rules for cache consistency"""
        rules_text = "\n".join(sorted([rule for rule, score in rag_rules]))
        return str(hash(rules_text))
    
    def get_cached_props(self, case_name, turn_idx, rag_rules):
        """Get cached props for a specific case, turn, and RAG rules"""
        rag_rules_hash = self.get_rag_rules_hash(rag_rules)
        cache_key = self.get_cache_key(case_name, turn_idx, rag_rules_hash)
        if cache_key in self.props_cache:
            cached_entry = self.props_cache[cache_key]
            print(f"[RAG PROPS CACHE HIT] Using cached rag-props for {case_name}_turn_{turn_idx} (generated {cached_entry.get('generated_at', 'unknown')})")
            return cached_entry.get('props', [])
        return None
    
    def cache_props(self, case_name, turn_idx, rag_rules, props):
        """Cache props for a specific case, turn, and RAG rules"""
        # Don't cache empty props
        if not props:
            print(f"[RAG PROPS CACHE] Skipping cache for {case_name}_turn_{turn_idx} - no props to cache")
            return
        
        rag_rules_hash = self.get_rag_rules_hash(rag_rules)
        cache_key = self.get_cache_key(case_name, turn_idx, rag_rules_hash)
        self.props_cache[cache_key] = {
            'props': props,
            'generated_at': datetime.now().isoformat(),
            'case_name': case_name,
            'turn_idx': turn_idx,
            'rag_rules_hash': rag_rules_hash,
            'rag_rules_count': len(rag_rules)
        }
        print(f"[RAG PROPS CACHE] Cached {len(props)} rag-props for {case_name}_turn_{turn_idx}")
        # Save cache immediately to persist across runs
        self.save_cache()
    
    def generate_turn_props_from_rag_rules(self, turn_data, rag_rules, client, client_name, case_name=None, turn_idx=None):
        """Generate turn-specific propositions using RAG-retrieved rules with caching"""
        # Debug: Show which turn we're processing
        evidence_names = [ev.get('name', 'Unknown') for ev in turn_data.get('evidences', [])]
        print(f"[RAG PROPS DEBUG] Generating rag-props for turn {turn_idx}, evidences: {evidence_names[:3]}, rag_rules: {len(rag_rules)}")
        
        # Try to get from cache first
        if case_name is not None and turn_idx is not None:
            cached_props = self.get_cached_props(case_name, turn_idx, rag_rules)
            if cached_props is not None:
                # Still log for debugging purposes, but don't re-generate
                self._log_props(cached_props, turn_data, case_name, turn_idx, "[CACHED] Rag-props retrieved from cache", "[CACHED] Rag-props retrieved from cache", rag_rules)
                return cached_props
        
        # Generate new props via API
        print(f"[RAG PROPS CACHE MISS] Generating new rag-props for {case_name}_turn_{turn_idx}")
        prompt = self._build_rag_prop_prompt(turn_data, rag_rules)
        
        # Use same LLM calling logic as run_models_spatial.py
        response = client.chat.completions.create(
            model=client_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        
        full_answer = response.choices[0].message.content
        props = self._parse_props(full_answer)
        
        # Cache the successful generation
        if case_name is not None and turn_idx is not None:
            self.cache_props(case_name, turn_idx, rag_rules, props)
        
        # Enhanced logging with full prompt and response
        self._log_props(props, turn_data, case_name, turn_idx, prompt, full_answer, rag_rules)
        
        return props
    
    def _build_rag_prop_prompt(self, turn_data, rag_rules):
        # Use ONLY the RAG-retrieved rules instead of all rules
        rules_text = "\n".join([rule for rule, score in rag_rules]) if rag_rules else "No relevant rules available"
        
        # Build the same rich context as the main prompt
        case_data = ""
        
        # Add story context (summarized context when using --context sum)
        if 'summarizedContext' in turn_data and turn_data['summarizedContext']:
            case_data += f"Story:\n{turn_data['summarizedContext']}\n"
        
        # Add characters with descriptions (same format as main prompt)
        if 'characters' in turn_data:
            case_data += "Characters:\n"
            for i, character in enumerate(turn_data['characters']):
                case_data += f"Character {i}\n"
                case_data += f"Name: {character['name']}\n"
                if 'description1' in character:
                    case_data += f"Description: {character['description1']}\n"
        
        # Add evidences with full descriptions (same format as main prompt)
        if 'evidences' in turn_data:
            case_data += "Evidences:\n"
            for i, evidence in enumerate(turn_data['evidences']):
                case_data += f"Evidence {i}\n"
                case_data += f"Name: {evidence['name']}\n"
                # Join all description fields like the main prompt
                descriptions = []
                for key in evidence.keys():
                    if 'description' in key:
                        descriptions.append(evidence[key])
                if descriptions:
                    case_data += f"Description: {' '.join(descriptions)}\n"
        
        # Add testimonies with person and context (same format as main prompt)
        if 'testimonies' in turn_data:
            case_data += "Testimonies:\n"
            for i, testimony in enumerate(turn_data['testimonies']):
                case_data += f"Testimony {i}\n"
                case_data += f"Testimony: {testimony['testimony']}\n"
                if 'person' in testimony:
                    case_data += f"Person: {testimony['person']}\n"
        
        # Use prefix/suffix structure like other prompts, but with RAG rules
        prefix = self.prompt_template["prefix"].replace("{rag_rules}", rules_text)
        suffix = self.prompt_template["suffix"]
        
        prompt = prefix + case_data + suffix
        return prompt
    
    def _parse_props(self, response):
        lines = response.strip().split('\n')
        props = []
        for line in lines:
            if line.strip() and ('Prop' in line or line.strip()[0].isdigit()):
                # Clean up the line to extract just the proposition
                clean_prop = line.strip()
                if ':' in clean_prop:
                    clean_prop = clean_prop.split(':', 1)[1].strip()
                props.append(clean_prop)
        
        # Return all props generated by the LLM (no artificial limits)
        return props
    
    def _log_props(self, props, turn_data, case_name, turn_idx, prompt_sent, raw_response, rag_rules):
        """Log generated rag-props for analysis"""
        log_entry = {
            'case_name': case_name,
            'turn_idx': turn_idx,
            'timestamp': datetime.now().isoformat(),
            'prompt_sent_to_llm': prompt_sent,
            'raw_llm_response': raw_response,
            'parsed_props': props,
            'rag_rules_used': [{"rule": rule, "score": float(score)} for rule, score in rag_rules],
            'rag_rules_count': len(rag_rules),
            'turn_data': {
                'testimonies': [t['testimony'] for t in turn_data['testimonies']],
                'evidences': [e['name'] for e in turn_data['evidences']]
            }
        }
        self.props_log.append(log_entry)
    
    def save_props_log(self, output_dir, model_name, prompt_name):
        """Save generated rag-props log to file for debugging with append mode and run tracking"""
        if not self.props_log:
            return
            
        # Create filename similar to other output files
        log_filename = f"rag_props_debug_log_{model_name}_{prompt_name}.txt"
        log_path = os.path.join(output_dir, log_filename)
        
        # Check if this is a new file or append to existing
        is_new_file = not os.path.exists(log_path)
        current_run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        with open(log_path, 'a', encoding='utf-8') as f:  # Changed from 'w' to 'a' for append mode
            if is_new_file:
                # Write header only for new files
                f.write("RAG + PROP GENERATION DEBUG LOG\n")
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
            f.write(f"Turns processed in this run: {len(self.props_log)}\n")
            f.write("=" * 100 + "\n\n")
            
            for i, entry in enumerate(self.props_log):
                f.write(f"TURN {i+1}: {entry['case_name']} (Turn {entry['turn_idx']}) [RUN: {current_run_id}]\n")
                f.write("=" * 60 + "\n\n")
                
                # Input context
                f.write("TURN CONTEXT:\n")
                f.write("-" * 20 + "\n")
                f.write("Testimonies:\n")
                for j, testimony in enumerate(entry['turn_data']['testimonies']):
                    f.write(f"  {j}: {testimony}\n")
                f.write("\nEvidences:\n")
                for j, evidence in enumerate(entry['turn_data']['evidences']):
                    f.write(f"  {j}: {evidence}\n")
                f.write("\n")
                
                # RAG Rules Used
                f.write("RAG RULES USED:\n")
                f.write("-" * 20 + "\n")
                f.write(f"Total rules: {entry['rag_rules_count']}\n")
                for j, rag_rule in enumerate(entry['rag_rules_used']):
                    f.write(f"  {j+1}: (score: {rag_rule['score']:.4f}) {rag_rule['rule']}\n")
                f.write("\n")
                
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
                f.write("PARSED RAG-PROPOSITIONS:\n")
                f.write("-" * 30 + "\n")
                for j, prop in enumerate(entry['parsed_props']):
                    f.write(f"  {j+1}: {prop}\n")
                
                f.write("\n" + "=" * 100 + "\n\n")
        
        print(f"Rag-props debug log {'created' if is_new_file else 'appended to'}: {log_path}") 
