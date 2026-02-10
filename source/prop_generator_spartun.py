import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path


class PropGeneratorSpartun:
    """Generate per-question propositions for SPARTUN with caching.

    - Uses a generation prompt with {PROP_COUNT}, {story_text}, {question_text}
    - Calls the provided OpenAI-compatible client
    - Caches props per (case_id, q_id, prop_count)
    """

    def __init__(self, prompt_file: Optional[str] = None, prop_count: int = 10, seed: int = 42, model_name: Optional[str] = None):
        if prompt_file is None:
            prompt_path = Path(__file__).resolve().parent / "prompts_spartun" / "prop_generation_improved_v2.json"
        else:
            p = Path(prompt_file)
            if not p.is_absolute():
                p = Path(__file__).resolve().parent / p
            prompt_path = p
        with open(str(prompt_path), 'r', encoding='utf-8') as f:
            self.prompt_template = json.load(f)
        self.prompt_file = str(prompt_path)
        self.prop_count = int(prop_count)
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
                print(f"[init] PropGeneratorSpartun: Loaded client {self.client_name}")
            except Exception as e:
                print(f"[ERROR] Failed to load model {model_name} in PropGeneratorSpartun.__init__: {e}")

    def set_cache_file(self, output_dir: str, model_name: str, prompt_name: str) -> None:
        safe_prompt = prompt_name.replace('/', '_') if isinstance(prompt_name, str) else str(prompt_name)
        self.cache_file = os.path.join(output_dir, f"props_cache_{model_name}_{safe_prompt}.json")
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

    def _cache_key(self, case_id: str, q_id: int, prop_count: Optional[int] = None) -> str:
        count = int(prop_count) if prop_count is not None else self.prop_count
        return f"{case_id}_q{q_id}_p{count}"

    def get_cached_props(self, case_id: str, q_id: int, prop_count: Optional[int] = None) -> Optional[List[str]]:
        key = self._cache_key(case_id, q_id, prop_count)
        if key in self.props_cache:
            entry = self.props_cache[key]
            props = entry.get('props', [])
            return self._sanitize_props_list(props)
        return None

    def cache_props(self, case_id: str, q_id: int, props: List[str], prop_count: Optional[int] = None) -> None:
        if not props:
            return
        key = self._cache_key(case_id, q_id, prop_count)
        sanitized = self._sanitize_props_list(props)
        self.props_cache[key] = {
            'props': sanitized,
            'generated_at': datetime.now().isoformat(),
            'case_id': case_id,
            'q_id': q_id,
            'prop_count': int(prop_count) if prop_count is not None else self.prop_count
        }
        self._save_cache()

    def _sanitize_props_list(self, props: Any) -> List[str]:
        if not isinstance(props, list):
            return []
        out: List[str] = []
        for p in props:
            if isinstance(p, str):
                clean = p.strip()
                if clean:
                    out.append(clean)
        return out

    def _build_generation_prompt(self, case: Dict[str, Any], question: Dict[str, Any], prop_count: int) -> str:
        story_text = case.get('story_text', '')
        question_text = question.get('text', '')
        prefix = self.prompt_template['prefix']
        suffix = self.prompt_template['suffix']
        # Load general rules from repository Rules file
        try:
            rules_path = Path(__file__).resolve().parents[1] / 'Rules' / 'RuleText.txt'
            with open(str(rules_path), 'r', encoding='utf-8') as rf:
                general_rules = rf.read().strip()
        except Exception:
            general_rules = ""
        prefix = (
            prefix
            .replace('{PROP_COUNT}', str(prop_count))
            .replace('{story_text}', story_text)
            .replace('{question_text}', question_text)
            .replace('{general_rules}', general_rules)
        )
        suffix = suffix.replace('{PROP_COUNT}', str(prop_count))
        return prefix + suffix

    def _parse_props_from_response(self, response_text: str, prop_count: int) -> List[str]:
        text = response_text.strip()
        try:
            import re
            block = text
            m = re.search(r'<BEGIN_PROPS>([\s\S]*?)<END_PROPS>', text)
            if m:
                block = m.group(1)
            lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
            props: List[str] = []
            for ln in lines:
                if ln:
                    props.append(ln)
            return props[-prop_count:] if len(props) >= prop_count else props
        except Exception:
            return []

    def generate_question_props(self, case: Dict[str, Any], question: Dict[str, Any], model_name: str, case_id: str, q_id: int, prop_count: Optional[int] = None, logger=None) -> List[str]:
        """Generate propositions for a specific question (per-question processing).
        
        Uses the client initialized in __init__ for thread-safe parallel processing.
        """
        count = int(prop_count) if prop_count is not None else self.prop_count
        cached = self.get_cached_props(case_id, q_id, count)
        if cached is not None:
            return cached
        
        print(f"[DEBUG] Generating props for {case_id} q{q_id}")
        
        # Use pre-initialized client
        if not self.client or not self.client_name:
            print(f"[ERROR] Client not initialized in PropGeneratorSpartun")
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
                print(f"[WARNING] Prop generation returned empty content for {case_id} q{q_id}")
                return []
            
            props = self._parse_props_from_response(full_answer, count)
            
            if not props:
                print(f"[WARNING] Prop parsing returned no props for {case_id} q{q_id}")
                print(f"[DEBUG] Raw response was: {full_answer[:200]}...")
            
            # Log generation call if logger provided
            if logger and hasattr(logger, 'log_generation_call'):
                logger.log_generation_call(
                    case_id=case_id,
                    q_id=q_id,
                    generation_type='props',
                    prompt_sent=prompt,
                    raw_response=full_answer,
                    parsed_items=props,
                    count_requested=count,
                    count_parsed=len(props)
                )
            
            self.cache_props(case_id, q_id, props, count)
            return props
        except Exception as e:
            print(f"[ERROR] Prop generation API call failed for {case_id} q{q_id}: {e}")
            import traceback
            traceback.print_exc()
            return []


