"""
rag_spartun.py - Simple semantic RAG utility tailored for SPARTUN dataset

Behavior:
- Loads rules from ../Rules/RuleText5.txt
- Embeds rules once using SentenceTransformer('all-MiniLM-L6-v2')
- Extracts case context from story_text + question texts (no options)
- Retrieves top_k most similar rules via cosine similarity
- Replaces {dynamic_rules} in a prompt prefix per case

Logging:
- Does not write separate files. Returns metadata so callers can log via existing debug_logger.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class SpartunRAG:
    def __init__(self, rules_file: Optional[str] = None, top_k: int = 5, model_name: str = 'all-MiniLM-L6-v2') -> None:
        self.top_k = int(top_k)
        self.model = SentenceTransformer(model_name)
        if rules_file is None:
            rules_file = str(Path(__file__).resolve().parents[1] / 'Rules' / 'RuleText.txt')
        self.rules_file = rules_file
        self.rules: List[str] = self._load_rules(self.rules_file)
        self.rule_embeddings = self._embed_rules(self.rules)

    def _load_rules(self, rules_path: str) -> List[str]:
        with open(rules_path, 'r', encoding='utf-8') as f:
            return [ln.strip() for ln in f if ln.strip()]

    def _embed_rules(self, rules: List[str]):
        return self.model.encode(rules, convert_to_tensor=False)

    def extract_case_context(self, case: Dict[str, Any]) -> str:
        """Extract context from story + all question texts (legacy method)."""
        parts: List[str] = []
        story = case.get('story_text', '')
        if isinstance(story, str) and story:
            parts.append(story)
        # Add only question texts (avoid options to not leak answers)
        for q in case.get('questions', []) or []:
            text = q.get('text')
            if isinstance(text, str) and text:
                parts.append(text)
        return ' '.join(parts)
    
    def extract_question_context(self, case: Dict[str, Any], question: Dict[str, Any]) -> str:
        """Extract context from story + single question text (per-question processing)."""
        parts: List[str] = []
        story = case.get('story_text', '')
        if isinstance(story, str) and story:
            parts.append(story)
        # Add only the specific question text (avoid options to not leak answer)
        text = question.get('text')
        if isinstance(text, str) and text:
            parts.append(text)
        return ' '.join(parts)

    def retrieve_relevant_rules(self, case_context: str, top_k: Optional[int] = None) -> List[Tuple[str, float]]:
        """Retrieve rules based on context string."""
        k = int(top_k) if top_k is not None else self.top_k
        if not case_context:
            return []
        context_emb = self.model.encode([case_context], convert_to_tensor=False)
        sims = cosine_similarity(context_emb, self.rule_embeddings)[0]
        top_indices = np.argsort(sims)[-k:][::-1]
        return [(self.rules[i], float(sims[i])) for i in top_indices]
    
    def retrieve_rules_for_question(self, case: Dict[str, Any], question: Dict[str, Any], top_k: Optional[int] = None) -> List[Tuple[str, float]]:
        """Retrieve rules for a specific question (per-question processing)."""
        context = self.extract_question_context(case, question)
        return self.retrieve_relevant_rules(context, top_k=top_k)

    def enhance_prefix_with_rag(self, prefix: str, case: Dict[str, Any], top_k: Optional[int] = None, return_metadata: bool = False):
        """Enhance prefix with RAG rules for entire case (legacy method)."""
        context = self.extract_case_context(case)
        rules = self.retrieve_relevant_rules(context, top_k=top_k)
        rules_text = "\n".join(rule for rule, _ in rules)
        enhanced = prefix.replace('{dynamic_rules}', rules_text)
        if return_metadata:
            meta = {
                'used_top_k': int(top_k) if top_k is not None else self.top_k,
                'rules_metadata': rules,
            }
            return enhanced, meta
        return enhanced
    
    def enhance_prefix_with_rag_for_question(self, prefix: str, case: Dict[str, Any], question: Dict[str, Any], top_k: Optional[int] = None, return_metadata: bool = False):
        """Enhance prefix with RAG rules for a specific question (per-question processing)."""
        rules = self.retrieve_rules_for_question(case, question, top_k=top_k)
        rules_text = "\n".join(rule for rule, _ in rules)
        enhanced = prefix.replace('{dynamic_rules}', rules_text)
        if return_metadata:
            meta = {
                'used_top_k': int(top_k) if top_k is not None else self.top_k,
                'rules_metadata': rules,
            }
            return enhanced, meta
        return enhanced


