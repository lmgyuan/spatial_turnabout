import os
import json
from datetime import datetime


class ETSelector:
    """Select N evidence indices and N testimony indices per turn deterministically.

    - Deterministic LLM call (temperature=0, seed provided)
    - JSON-only output enforced and sanitized
    - Caching to avoid re-selection on reruns
    - Lightweight debug log accumulation
    """

    def __init__(self, prompt_file: str, n: int, seed: int = 42):
        with open(prompt_file, 'r', encoding='utf-8') as f:
            self.prompt_template = json.load(f)
        self.n = int(n)
        self.seed = int(seed)
        self.cache_file = None
        self.cache = {}
        self.log = []

    def set_cache_file(self, output_dir: str, model_name: str, prompt_name: str):
        safe_prompt = prompt_name.replace('/', '_') if isinstance(prompt_name, str) else str(prompt_name)
        self.cache_file = os.path.join(output_dir, f"et_cache_{model_name}_{safe_prompt}.json")
        self._load_cache()

    def _load_cache(self):
        if self.cache_file and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                print(f"[ET CACHE] Loaded {len(self.cache)} cached selections")
            except Exception as e:
                print(f"[ET CACHE] Failed to load cache: {e}")
                self.cache = {}
        else:
            self.cache = {}

    def _save_cache(self):
        if self.cache_file:
            try:
                os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self.cache, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[ET CACHE] Failed to save cache: {e}")

    def _key(self, case_name: str, turn_idx: int) -> str:
        return f"{case_name}_turn_{turn_idx}_et{self.n}"

    def get_cached(self, case_name: str, turn_idx: int):
        key = self._key(case_name, turn_idx)
        if key in self.cache:
            entry = self.cache[key]
            print(f"[ET CACHE HIT] {key} (generated {entry.get('generated_at', 'unknown')})")
            return entry.get('evidences', []), entry.get('testimonies', [])
        return None

    def _cache_put(self, case_name: str, turn_idx: int, evidences, testimonies):
        key = self._key(case_name, turn_idx)
        self.cache[key] = {
            'evidences': evidences,
            'testimonies': testimonies,
            'generated_at': datetime.now().isoformat(),
            'case_name': case_name,
            'turn_idx': turn_idx,
            'n': self.n
        }
        self._save_cache()

    def select(self, turn_data: dict, client, client_name: str, case_name: str = None, turn_idx: int = None):
        # Try cache first
        if case_name is not None and turn_idx is not None:
            cached = self.get_cached(case_name, turn_idx)
            if cached is not None:
                evidences, testimonies = cached
                self._log(turn_data, case_name, turn_idx, evidences, testimonies, "[CACHED]", "[CACHED]")
                return evidences, testimonies

        prompt = self._build_prompt(turn_data)

        # Deterministic call
        response = client.chat.completions.create(
            model=client_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            seed=self.seed
        )
        content = response.choices[0].message.content

        ev_idxs, ts_idxs = self._parse_and_sanitize(content, turn_data)

        if case_name is not None and turn_idx is not None:
            self._cache_put(case_name, turn_idx, ev_idxs, ts_idxs)

        self._log(turn_data, case_name, turn_idx, ev_idxs, ts_idxs, prompt, content)
        return ev_idxs, ts_idxs

    def _build_prompt(self, turn_data: dict) -> str:
        case_block = []
        # Story
        if 'summarizedContext' in turn_data and turn_data['summarizedContext']:
            case_block.append(f"Story:\n{turn_data['summarizedContext']}\n")
        # Characters
        case_block.append("Characters:\n")
        for i, ch in enumerate(turn_data.get('characters', [])):
            case_block.append(f"Character {i}\n")
            case_block.append(f"Name: {ch.get('name','')}\n")
            if 'description1' in ch:
                case_block.append(f"Description: {ch['description1']}\n")
        # Evidences
        case_block.append("Evidences:\n")
        for i, ev in enumerate(turn_data.get('evidences', [])):
            case_block.append(f"Evidence {i}\n")
            case_block.append(f"Name: {ev.get('name','')}\n")
            descriptions = [v for k, v in ev.items() if 'description' in k]
            if descriptions:
                case_block.append(f"Description: {' '.join(descriptions)}\n")
        # Testimonies
        case_block.append("Testimonies:\n")
        for i, t in enumerate(turn_data.get('testimonies', [])):
            case_block.append(f"Testimony {i}\n")
            case_block.append(f"Testimony: {t.get('testimony','')}\n")
            if 'person' in t:
                case_block.append(f"Person: {t['person']}\n")

        prefix = self.prompt_template["prefix"]
        suffix = self.prompt_template["suffix"].replace("{N}", str(self.n))
        return prefix + ''.join(case_block) + suffix

    def _parse_and_sanitize(self, content: str, turn_data: dict):
        # Expect a single JSON object on the last line; fallback to whole content
        data = None
        try:
            data = json.loads(content.strip().splitlines()[-1])
        except Exception:
            try:
                data = json.loads(content)
            except Exception:
                data = {"evidences": [], "testimonies": []}

        evidences = data.get('evidences', [])
        testimonies = data.get('testimonies', [])

        ev_count = len(turn_data.get('evidences', []))
        ts_count = len(turn_data.get('testimonies', []))

        def sanitize(idxs, max_count):
            out = []
            seen = set()
            for x in idxs:
                if isinstance(x, int) and 0 <= x < max_count and x not in seen:
                    seen.add(x)
                    out.append(x)
            # If more than N, keep last N
            if len(out) > self.n:
                out = out[-self.n:]
            return out

        evidences = sanitize(evidences, ev_count)
        testimonies = sanitize(testimonies, ts_count)
        return evidences, testimonies

    def _log(self, turn_data, case_name, turn_idx, ev_idxs, ts_idxs, prompt_sent, raw_response):
        self.log.append({
            'case_name': case_name,
            'turn_idx': turn_idx,
            'timestamp': datetime.now().isoformat(),
            'selected_evidences': ev_idxs,
            'selected_testimonies': ts_idxs,
            'prompt_sent_to_llm': prompt_sent,
            'raw_llm_response': raw_response
        })

    def save_log(self, output_dir: str, model_name: str, prompt_name: str):
        if not self.log:
            return
        filename = f"et_debug_log_{model_name}_{prompt_name}.txt"
        path = os.path.join(output_dir, filename)
        is_new = not os.path.exists(path)
        with open(path, 'a', encoding='utf-8') as f:
            if is_new:
                f.write("ET SELECTION DEBUG LOG\n")
                f.write("=" * 100 + "\n\n")
                f.write(f"Model: {model_name}\n")
                f.write(f"Prompt Template: {prompt_name}\n")
                f.write("=" * 100 + "\n\n")
            run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            f.write(f"RUN ID: {run_id}\n")
            for i, entry in enumerate(self.log):
                f.write("-" * 80 + "\n")
                f.write(f"Turn {i+1}: {entry['case_name']} (Turn {entry['turn_idx']})\n")
                f.write(f"Selected evidences: {entry['selected_evidences']}\n")
                f.write(f"Selected testimonies: {entry['selected_testimonies']}\n\n")


