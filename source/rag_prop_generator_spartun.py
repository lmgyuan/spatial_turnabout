import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from rag_spartun import SpartunRAG


class RagPropGeneratorSpartun:
    """Generate propositions from RAG-retrieved rules with caching keyed by (case_id, q_id, rules hash, prop_count)."""

    def __init__(self, prompt_file: Optional[str] = None, seed: int = 42, model_name: Optional[str] = None):
        if prompt_file is None:
            # Default to generic template with {PROP_COUNT}
            prompt_path = Path(__file__).resolve().parent / "prompts_spartun" / "rag_prop_generation_improved_v2.json"
        else:
            p = Path(prompt_file)
            if not p.is_absolute():
                p = Path(__file__).resolve().parent / p
            prompt_path = p
        with open(str(prompt_path), 'r', encoding='utf-8') as f:
            self.prompt_template = json.load(f)
        self.prompt_file = str(prompt_path)
        self.seed = int(seed)
        self.cache_file: Optional[str] = None
        self.props_cache: Dict[str, Any] = {}
        
        # Initialize client once for thread-safe reuse
        self.client = None
        self.client_name = None
        if model_name:
            from model_loader import load_model
            try:
                models_cfg = Path(__file__).resolve().parent / "models.json"
                self.client, self.client_name = load_model(model_name, config_path=str(models_cfg))
                print(f"[init] RagPropGeneratorSpartun: Loaded client {self.client_name}")
            except Exception as e:
                print(f"[ERROR] Failed to load model {model_name} in RagPropGeneratorSpartun.__init__: {e}")

    def set_cache_file(self, output_dir: str, model_name: str, prompt_name: str) -> None:
        safe_prompt = prompt_name.replace('/', '_') if isinstance(prompt_name, str) else str(prompt_name)
        self.cache_file = os.path.join(output_dir, f"rag_props_cache_{model_name}_{safe_prompt}.json")
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_file and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.props_cache = json.load(f)
            except Exception:
                self.props_cache = {}

    def _save_cache(self) -> None:
        if not self.cache_file:
            return
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.props_cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _rules_hash(self, rules: List[Tuple[str, float]]) -> str:
        lines = [r for r, _ in rules]
        key = "\n".join(sorted(lines))
        return str(hash(key))

    def _cache_key(self, case_id: str, q_id: int, rules_hash: str, prop_count: int) -> str:
        return f"{case_id}_q{q_id}_rag_{rules_hash}_p{int(prop_count)}"

    def get_cached_props(self, case_id: str, q_id: int, rules: List[Tuple[str, float]], prop_count: int):
        rh = self._rules_hash(rules)
        key = self._cache_key(case_id, q_id, rh, prop_count)
        if key in self.props_cache:
            return self.props_cache[key].get('props', [])
        return None

    def cache_props(self, case_id: str, q_id: int, rules: List[Tuple[str, float]], props: List[str], prop_count: int) -> None:
        if not props:
            return
        rh = self._rules_hash(rules)
        key = self._cache_key(case_id, q_id, rh, prop_count)
        self.props_cache[key] = {
            'props': props,
            'generated_at': datetime.now().isoformat(),
            'case_id': case_id,
            'q_id': q_id,
            'rules_hash': rh,
            'rules_count': len(rules),
            'prop_count': int(prop_count)
        }
        self._save_cache()

    def _build_generation_prompt(self, case: Dict[str, Any], question: Dict[str, Any], rules: List[Tuple[str, float]], prop_count: int) -> str:
        story_text = case.get('story_text', '')
        question_text = question.get('text', '')
        rules_text = "\n".join([r for r, _ in rules])
        prefix = self.prompt_template['prefix']
        suffix = self.prompt_template['suffix']
        prefix = (
            prefix
            .replace('{rag_rules}', rules_text)
            .replace('{story_text}', story_text)
            .replace('{question_text}', question_text)
            .replace('{PROP_COUNT}', str(prop_count))
        )
        suffix = suffix.replace('{PROP_COUNT}', str(prop_count))
        return prefix + suffix

    def _parse_props(self, response_text: str) -> List[str]:
        text = response_text.strip()
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        props: List[str] = []
        for ln in lines:
            if ln.startswith('Prop '):
                props.append(ln)
        return props

    def generate_question_props_from_rag(self, case: Dict[str, Any], question: Dict[str, Any], rules: List[Tuple[str, float]], model_name: str, case_id: str, q_id: int, prop_count: int = 10, logger=None) -> List[str]:
        """Generate propositions for a specific question from RAG-retrieved rules (per-question processing).
        
        Uses the client initialized in __init__ for thread-safe parallel processing.
        """
        cached = self.get_cached_props(case_id, q_id, rules, prop_count)
        if cached is not None:
            return cached
        
        print(f"[DEBUG] Generating RAG props for {case_id} q{q_id}")
        
        # Use pre-initialized client
        if not self.client or not self.client_name:
            print(f"[ERROR] Client not initialized in RagPropGeneratorSpartun")
            return []
        
        prompt = self._build_generation_prompt(case, question, rules, prop_count)
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
                print(f"[WARNING] RAG prop generation returned empty content for {case_id} q{q_id}")
                return []
            
            props = self._parse_props(full_answer)
            
            if not props:
                print(f"[WARNING] RAG prop parsing returned no props for {case_id} q{q_id}")
                print(f"[DEBUG] Raw response was: {full_answer[:200]}...")
            
            # Log generation call if logger provided
            if logger and hasattr(logger, 'log_generation_call'):
                logger.log_generation_call(
                    case_id=case_id,
                    q_id=q_id,
                    generation_type='rag_props',
                    prompt_sent=prompt,
                    raw_response=full_answer,
                    parsed_items=props,
                    count_requested=prop_count,
                    count_parsed=len(props)
                )
            
            self.cache_props(case_id, q_id, rules, props, prop_count)
            return props
        except Exception as e:
            print(f"[ERROR] RAG prop generation API call failed for {case_id} q{q_id}: {e}")
            import traceback
            traceback.print_exc()
            return []


