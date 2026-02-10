#!/usr/bin/env python3
"""Simple Semantic RAG System"""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

class SimpleRAG:
    def __init__(self, rules_file="../Rules/RuleText5.txt", top_k=5):
        self.rules_file = rules_file
        self.top_k = top_k
        self.rules = []
        self.rule_embeddings = None
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        self._load_rules()
        self._embed_rules()
    
    def _load_rules(self):
        with open(self.rules_file, 'r', encoding='utf-8') as f:
            self.rules = [line.strip() for line in f if line.strip()]
    
    def _embed_rules(self):
        self.rule_embeddings = self.model.encode(self.rules, convert_to_tensor=False)
    
    def extract_case_context(self, case_data):
        context_parts = []
        
        if 'testimonies' in case_data:
            for testimony in case_data['testimonies']:
                context_parts.append(testimony.get('testimony', ''))
        
        if 'evidences' in case_data:
            for evidence in case_data['evidences']:
                for key, value in evidence.items():
                    if 'description' in key and isinstance(value, str):
                        context_parts.append(value)
        
        return ' '.join(context_parts)
    
    def retrieve_relevant_rules(self, case_context):
        context_embedding = self.model.encode([case_context], convert_to_tensor=False)
        similarities = cosine_similarity(context_embedding, self.rule_embeddings)[0]
        top_indices = np.argsort(similarities)[-self.top_k:][::-1]
        
        return [(self.rules[idx], float(similarities[idx])) for idx in top_indices]

def enhance_prompt_with_rag(prompt_prefix, case_data, top_k=5, return_rules_metadata=False):
    rag = SimpleRAG(top_k=top_k)
    case_context = rag.extract_case_context(case_data)
    relevant_rules = rag.retrieve_relevant_rules(case_context)
    
    rules_text = "\n".join(rule for rule, score in relevant_rules)
    enhanced_prompt = prompt_prefix.replace("{dynamic_rules}", rules_text)
    
    if return_rules_metadata:
        return enhanced_prompt, relevant_rules, top_k
    else:
        return enhanced_prompt

def log_rules_usage(case_name, turn_idx, rules_metadata, top_k, model, prompt, context, label, no_description, data, reasoning):
    """Log rules usage to a file in the Rules folder"""
    import os
    from datetime import datetime
    
    # Create filename using the same format as output directories
    filename_parts = [f"{model.split('/')[-1]}_prompt_{prompt}"]
    if context is not None:
        filename_parts.append(f"context_{context}")
    if no_description:
        filename_parts.append("desc_none")
    if data == 'danganronpa':
        filename_parts.append(f"data_{data}")
    if label is not None:
        filename_parts.append(f"label_{label}")
    if reasoning != 'none':
        filename_parts.append(f"reasoning_{reasoning}")
    
    filename = f"rag_rules_used_{'_'.join(filename_parts)}.txt"
    filepath = os.path.join("../Rules", filename)
    
    # Ensure Rules directory exists
    os.makedirs("../Rules", exist_ok=True)
    
    # Add header only if file doesn't exist
    write_header = not os.path.exists(filepath)
        
    # Write rules usage
    with open(filepath, 'a', encoding='utf-8') as f:
        if write_header:
            f.write(f"RAG RULES USAGE LOG\n")
            f.write(f"Model: {model} | Prompt: {prompt} | Context: {context} | Label: {label}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*120}\n\n")
        
        f.write(f"\n{'='*80}\n")
        f.write(f"Case: {case_name} | Turn: {turn_idx} | Top-K: {top_k}\n")
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*80}\n")
        
        for i, (rule, score) in enumerate(rules_metadata, 1):
            f.write(f"{i}. [Score: {score:.4f}] {rule}\n")
        f.write(f"\n")

 