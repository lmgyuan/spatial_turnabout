import os
import json
from datetime import datetime


class RuleGenerator:
    """Generate per-turn spatial reasoning rules with caching and deterministic seeding.

    Mirrors PropGenerator structure but produces rules instead of propositions.
    """

    def __init__(self, prompt_file="prompts/rule_generation_r10_improved_v2.json", rule_count=10, seed=42):
        # Load rule generation prompt template
        with open(prompt_file, 'r', encoding='utf-8') as f:
            self.prompt_template = json.load(f)

        self.prompt_file = prompt_file
        self.rule_count = int(rule_count)
        self.seed = int(seed)

        self.rules_log = []  # Store generated rules for logging
        self.cache_file = None  # Will be set when output_dir is known
        self.rules_cache = {}  # In-memory cache

    def set_cache_file(self, output_dir, model_name, prompt_name):
        """Set the cache file path and load existing cache"""
        safe_prompt = prompt_name.replace('/', '_') if isinstance(prompt_name, str) else str(prompt_name)
        self.cache_file = os.path.join(output_dir, f"rules_cache_{model_name}_{safe_prompt}.json")
        self.load_cache()

    def load_cache(self):
        """Load existing rules cache from file"""
        if self.cache_file and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.rules_cache = json.load(f)
                print(f"[RULES CACHE] Loaded {len(self.rules_cache)} cached rule entries")
            except Exception as e:
                print(f"[RULES CACHE] Failed to load cache: {e}")
                self.rules_cache = {}
        else:
            self.rules_cache = {}

    def save_cache(self):
        """Save rules cache to file"""
        if self.cache_file:
            try:
                os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self.rules_cache, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[RULES CACHE] Failed to save cache: {e}")

    def get_cache_key(self, case_name, turn_idx, rule_count=None):
        """Generate cache key for a specific case, turn, and rule count"""
        count = self.rule_count if rule_count is None else int(rule_count)
        return f"{case_name}_turn_{turn_idx}_r{count}"

    def get_cached_rules(self, case_name, turn_idx, rule_count=None):
        """Get cached rules for a specific case/turn and rule count"""
        cache_key = self.get_cache_key(case_name, turn_idx, rule_count)
        if cache_key in self.rules_cache:
            cached_entry = self.rules_cache[cache_key]
            print(f"[RULES CACHE HIT] Using cached rules for {cache_key} (generated {cached_entry.get('generated_at', 'unknown')})")
            raw_rules = cached_entry.get('rules', [])
            # Sanitize cached rules to avoid leaking any non-rule content
            count = int(rule_count if rule_count is not None else self.rule_count)
            return self._sanitize_rules_list(raw_rules, count)
        return None

    def cache_rules(self, case_name, turn_idx, rules, rule_count=None):
        """Cache rules for a specific case/turn and rule count"""
        if not rules:
            print(f"[RULES CACHE] Skipping cache for {case_name}_turn_{turn_idx} - no rules to cache")
            return
        cache_key = self.get_cache_key(case_name, turn_idx, rule_count)
        # Sanitize before storing
        count = int(rule_count if rule_count is not None else self.rule_count)
        sanitized = self._sanitize_rules_list(rules, count)
        self.rules_cache[cache_key] = {
            'rules': sanitized,
            'generated_at': datetime.now().isoformat(),
            'case_name': case_name,
            'turn_idx': turn_idx,
            'rule_count': count
        }
        print(f"[RULES CACHE] Cached {len(rules)} rules for {cache_key}")
        self.save_cache()

    def generate_turn_rules(self, turn_data, client, client_name, case_name=None, turn_idx=None, rule_count=None):
        """Generate turn-specific rules with caching and deterministic seeding"""
        count = int(rule_count if rule_count is not None else self.rule_count)

        # Try to get from cache first
        if case_name is not None and turn_idx is not None:
            cached_rules = self.get_cached_rules(case_name, turn_idx, count)
            if cached_rules is not None:
                self._log_rules(cached_rules, turn_data, case_name, turn_idx, "[CACHED] Rules retrieved from cache", "[CACHED] Rules retrieved from cache")
                return cached_rules

        # Build prompt from template and turn data
        prompt = self._build_rule_prompt(turn_data, count)

        # Call LLM deterministically
        response = client.chat.completions.create(
            model=client_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            seed=self.seed
        )

        full_answer = response.choices[0].message.content
        rules = self._parse_rules(full_answer, count)

        if case_name is not None and turn_idx is not None:
            self.cache_rules(case_name, turn_idx, rules, count)

        # Enhanced logging with full prompt and response
        self._log_rules(rules, turn_data, case_name, turn_idx, prompt, full_answer)
        return rules

    def _build_rule_prompt(self, turn_data, rule_count):
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
                descriptions = []
                for key in evidence.keys():
                    if 'description' in key:
                        descriptions.append(evidence[key])
                if descriptions:
                    case_data += f"Description: {' '.join(descriptions)}\n"

        # Add testimonies with person
        if 'testimonies' in turn_data:
            case_data += "Testimonies:\n"
            for i, testimony in enumerate(turn_data['testimonies']):
                case_data += f"Testimony {i}\n"
                case_data += f"Testimony: {testimony['testimony']}\n"
                if 'person' in testimony:
                    case_data += f"Person: {testimony['person']}\n"

        # Use prefix/suffix structure
        prefix = self.prompt_template["prefix"]
        suffix = self.prompt_template["suffix"].replace("{RULE_COUNT}", str(rule_count))
        prompt = prefix + case_data + suffix
        return prompt

    def _parse_rules(self, response, rule_count):
        """Parse only rule-like lines and keep the last N that start with 'If'."""
        lines = response.splitlines()
        candidates = []
        for line in lines:
            if not line:
                continue
            clean = line.strip()
            if not clean:
                continue
            # Trim a leading "Rule X:" prefix if present
            if ':' in clean:
                prefix = clean.split(':', 1)[0].strip().lower()
                if prefix.startswith('rule'):
                    clean = clean.split(':', 1)[1].strip()
            # Keep only lines that look like actual rules
            if clean.startswith('If'):
                candidates.append(clean)
        if not candidates:
            return []
        # Take the last rule_count entries
        count = int(rule_count)
        return candidates[-count:] if len(candidates) >= count else candidates

    def _sanitize_rules_list(self, rules, rule_count):
        """Sanitize a list of rules: keep only lines starting with 'If', return last N."""
        if not isinstance(rules, list):
            return []
        candidates = []
        for r in rules:
            if not isinstance(r, str):
                continue
            clean = r.strip()
            if not clean:
                continue
            # Trim a leading "Rule X:" prefix if present
            if ':' in clean:
                prefix = clean.split(':', 1)[0].strip().lower()
                if prefix.startswith('rule'):
                    clean = clean.split(':', 1)[1].strip()
            if clean.startswith('If'):
                candidates.append(clean)
        if not candidates:
            return []
        count = int(rule_count)
        return candidates[-count:] if len(candidates) >= count else candidates

    def _log_rules(self, rules, turn_data, case_name, turn_idx, prompt_sent, raw_response):
        log_entry = {
            'case_name': case_name,
            'turn_idx': turn_idx,
            'timestamp': datetime.now().isoformat(),
            'prompt_sent_to_llm': prompt_sent,
            'raw_llm_response': raw_response,
            'parsed_rules': rules,
            'turn_data': {
                'testimonies': [t['testimony'] for t in turn_data.get('testimonies', [])],
                'evidences': [e['name'] for e in turn_data.get('evidences', [])]
            }
        }
        self.rules_log.append(log_entry)

    def save_rules_log(self, output_dir, model_name, prompt_name):
        if not self.rules_log:
            return

        log_filename = f"rules_debug_log_{model_name}_{prompt_name}.txt"
        log_path = os.path.join(output_dir, log_filename)
        is_new_file = not os.path.exists(log_path)
        current_run_id = datetime.now().strftime('%Y%m%d_%H%M%S')

        with open(log_path, 'a', encoding='utf-8') as f:
            if is_new_file:
                f.write("RULE GENERATION DEBUG LOG\n")
                f.write("=" * 100 + "\n\n")
                f.write(f"Model: {model_name}\n")
                f.write(f"Prompt Template: {prompt_name}\n")
                f.write("=" * 100 + "\n\n")
            else:
                f.write("\n" + "=" * 100 + "\n")
                f.write("NEW RUN STARTED\n")
                f.write("=" * 100 + "\n\n")

            f.write(f"RUN ID: {current_run_id}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Turns processed in this run: {len(self.rules_log)}\n")
            f.write("=" * 100 + "\n\n")

            for i, entry in enumerate(self.rules_log):
                f.write(f"TURN {i+1}: {entry['case_name']} (Turn {entry['turn_idx']}) [RUN: {current_run_id}]\n")
                f.write("=" * 60 + "\n\n")

                f.write("TURN CONTEXT:\n")
                f.write("-" * 20 + "\n")
                f.write("Testimonies:\n")
                for j, testimony in enumerate(entry['turn_data']['testimonies']):
                    f.write(f"  {j}: {testimony}\n")
                f.write("\nEvidences:\n")
                for j, evidence in enumerate(entry['turn_data']['evidences']):
                    f.write(f"  {j}: {evidence}\n")
                f.write("\n")

                f.write("LLM INPUT (PROMPT SENT):\n")
                f.write("-" * 30 + "\n")
                f.write(entry['prompt_sent_to_llm'])
                f.write("\n\n")

                f.write("LLM OUTPUT (RAW RESPONSE):\n")
                f.write("-" * 30 + "\n")
                f.write(entry['raw_llm_response'])
                f.write("\n\n")

                f.write("PARSED RULES:\n")
                f.write("-" * 25 + "\n")
                for j, rule in enumerate(entry['parsed_rules']):
                    f.write(f"  {j+1}: {rule}\n")
                f.write("\n" + "=" * 100 + "\n\n")


