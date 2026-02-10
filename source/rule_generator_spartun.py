import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path


class RuleGeneratorSpartun:
    """Generate per-question spatial rules for SPARTUN with caching.

    - Uses a generation prompt with {RULE_COUNT}, {story_text}, {question_text}
    - Calls the provided OpenAI-compatible client (same as runners)
    - Caches rules per (case_id, q_id, rule_count)
    """

    def __init__(self, prompt_file: Optional[str] = None, rule_count: int = 10, seed: int = 42, model_name: Optional[str] = None):
        # Resolve prompt file relative to this source directory by default
        if prompt_file is None:
            prompt_path = Path(__file__).resolve().parent / "prompts_spartun" / "rule_generation_improved_v2.json"
        else:
            p = Path(prompt_file)
            if not p.is_absolute():
                p = Path(__file__).resolve().parent / p
            prompt_path = p
        with open(str(prompt_path), 'r', encoding='utf-8') as f:
            self.prompt_template = json.load(f)
        self.prompt_file = str(prompt_path)
        self.rule_count = int(rule_count)
        self.seed = int(seed)
        self.cache_file: Optional[str] = None
        self.rules_cache: Dict[str, Any] = {}
        
        # Initialize client once for thread-safe reuse
        self.client = None
        self.client_name = None
        if model_name:
            from model_loader import load_model
            try:
                models_cfg = Path(__file__).resolve().parent / "models.json"
                self.client, self.client_name = load_model(model_name, config_path=str(models_cfg))
                print(f"[init] RuleGeneratorSpartun: Loaded client {self.client_name}")
            except Exception as e:
                print(f"[ERROR] Failed to load model {model_name} in RuleGeneratorSpartun.__init__: {e}")

    def set_cache_file(self, output_dir: str, model_name: str, prompt_name: str) -> None:
        safe_prompt = prompt_name.replace('/', '_') if isinstance(prompt_name, str) else str(prompt_name)
        self.cache_file = os.path.join(output_dir, f"rules_cache_{model_name}_{safe_prompt}.json")
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_file and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.rules_cache = json.load(f)
            except Exception:
                self.rules_cache = {}

    def _save_cache(self) -> None:
        if not self.cache_file:
            return
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.rules_cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _cache_key(self, case_id: str, q_id: int, rule_count: Optional[int] = None) -> str:
        count = int(rule_count) if rule_count is not None else self.rule_count
        return f"{case_id}_q{q_id}_r{count}"

    def get_cached_rules(self, case_id: str, q_id: int, rule_count: Optional[int] = None) -> Optional[List[str]]:
        key = self._cache_key(case_id, q_id, rule_count)
        if key in self.rules_cache:
            entry = self.rules_cache[key]
            rules = entry.get('rules', [])
            return self._sanitize_rules_list(rules, rule_count)
        return None

    def cache_rules(self, case_id: str, q_id: int, rules: List[str], rule_count: Optional[int] = None) -> None:
        if not rules:
            return
        key = self._cache_key(case_id, q_id, rule_count)
        sanitized = self._sanitize_rules_list(rules, rule_count)
        self.rules_cache[key] = {
            'rules': sanitized,
            'generated_at': datetime.now().isoformat(),
            'case_id': case_id,
            'q_id': q_id,
            'rule_count': int(rule_count) if rule_count is not None else self.rule_count
        }
        self._save_cache()

    def _sanitize_rules_list(self, rules: Any, rule_count: Optional[int]) -> List[str]:
        if not isinstance(rules, list):
            return []
        candidates: List[str] = []
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
            if clean.startswith('If') and ' then ' in clean:
                candidates.append(clean)
        count = int(rule_count) if rule_count is not None else self.rule_count
        return candidates[-count:] if len(candidates) >= count else candidates

    def _build_generation_prompt(self, case: Dict[str, Any], question: Dict[str, Any], rule_count: int) -> str:
        story_text = case.get('story_text', '')
        question_text = question.get('text', '')

        prefix = self.prompt_template['prefix']
        suffix = self.prompt_template['suffix']
        prefix = prefix.replace('{RULE_COUNT}', str(rule_count)).replace('{story_text}', story_text).replace('{question_text}', question_text)
        suffix = suffix.replace('{RULE_COUNT}', str(rule_count))
        return prefix + suffix

    def _parse_rules_from_response(self, response_text: str, rule_count: int) -> List[str]:
        # Extract lines strictly between <BEGIN_RULES> and <END_RULES> if present
        text = response_text.strip()
        try:
            import re
            block = text
            m = re.search(r'<BEGIN_RULES>([\s\S]*?)<END_RULES>', text)
            if m:
                block = m.group(1)
            lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
            rules = []
            for ln in lines:
                # Handle "Rule N: If ... then ..." format
                if ln.startswith('Rule ') and ':' in ln:
                    # Extract the part after "Rule N:"
                    rule_text = ln.split(':', 1)[1].strip()
                    if 'If' in rule_text and ' then ' in rule_text:
                        rules.append(rule_text)
                # Also handle plain "If ... then ..." format
                elif ln.startswith('If') and ' then ' in ln:
                    rules.append(ln)
            # Return last N
            return rules[-rule_count:] if len(rules) >= rule_count else rules
        except Exception:
            return []

    def generate_question_rules(self, case: Dict[str, Any], question: Dict[str, Any], model_name: str, case_id: str, q_id: int, rule_count: Optional[int] = None, logger=None) -> List[str]:
        """Generate rules for a specific question (per-question processing).
        
        Uses the client initialized in __init__ for thread-safe parallel processing.
        """
        count = int(rule_count) if rule_count is not None else self.rule_count
        cached = self.get_cached_rules(case_id, q_id, count)
        if cached is not None:
            print(f"[DEBUG] Using cached rules for {case_id} q{q_id}")
            return cached

        print(f"[DEBUG] Generating rules for {case_id} q{q_id}")
        
        # Use pre-initialized client
        if not self.client or not self.client_name:
            print(f"[ERROR] Client not initialized in RuleGeneratorSpartun")
            return []

        prompt = self._build_generation_prompt(case, question, count)
        try:
            response = self.client.chat.completions.create(
                model=self.client_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                seed=self.seed,
            )
            full_answer = response.choices[0].message.content
            
            if not full_answer:
                print(f"[WARNING] Rule generation returned empty content for {case_id} q{q_id}")
                return []
            
            rules = self._parse_rules_from_response(full_answer, count)
            
            if not rules:
                print(f"[WARNING] Rule parsing returned no rules for {case_id} q{q_id}")
                print(f"[DEBUG] Raw response was: {full_answer[:200]}...")
            
            # Log generation call if logger provided
            if logger and hasattr(logger, 'log_generation_call'):
                logger.log_generation_call(
                    case_id=case_id,
                    q_id=q_id,
                    generation_type='rules',
                    prompt_sent=prompt,
                    raw_response=full_answer,
                    parsed_items=rules,
                    count_requested=count,
                    count_parsed=len(rules)
                )
            
            self.cache_rules(case_id, q_id, rules, count)
            return rules
        except Exception as e:
            print(f"[ERROR] Rule generation API call failed for {case_id} q{q_id}: {e}")
            import traceback
            traceback.print_exc()
            return []


