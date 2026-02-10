"""
run_spartun_parallel.py - Per-question parallel processing for SPARTUN

Processes one question at a time (similar to Turnabout architecture)
- Parallelizes across ALL questions from ALL cases
- Supports all pipelines: base, RAG, props, rules, gold_rules
- Output format compatible with evaluate_spartun.py

Usage:
  python run_spartun_parallel.py -m nebius-llama3.3-70b -p base --case 20
  python run_spartun_parallel.py -m nebius-llama3.3-70b -p gold_rules_improved --case ALL
"""

import os
import json
import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import concurrent.futures

from model_loader import load_model
from debug_logger_spartun import debug_logger_spartun
from rag_spartun import SpartunRAG
from rule_generator_spartun import RuleGeneratorSpartun
from prop_generator_spartun import PropGeneratorSpartun
from rag_prop_generator_spartun import RagPropGeneratorSpartun


def detect_pipeline(prompt_name: str, prefix: str) -> str:
    """Detect which pipeline to use based on prompt name and placeholders."""
    if prompt_name and "rules_generated" in prompt_name:
        return "rules_generated"
    if prompt_name and "gold_rules" in prompt_name:
        return "gold_rules"
    if prompt_name and ("rag" in prompt_name and "prop" in prompt_name) and ("{rag_generated_props}" in prefix):
        return "rag_prop"
    if prompt_name and "prop_generated" in prompt_name:
        return "prop_generated"
    if prompt_name and ("rag" in prompt_name) and ("{dynamic_rules}" in prefix):
        return "rag"
    return "default"


def parse_arguments():
    parser = argparse.ArgumentParser(description='Run SPARTUN per-question pipeline in parallel')
    parser.add_argument('-m', '--model', type=str, required=True, help='model name')
    parser.add_argument('-p', '--prompt', type=str, default='base', help='prompt template name under prompts_spartun/')
    parser.add_argument('--case', type=str, default='20', help='ALL or a number N to run the first N cases (default: 20)')
    parser.add_argument('--max_workers', type=int, default=20, help='Number of parallel workers (default: 20)')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing outputs')
    parser.add_argument('--debug_log_off', action='store_true')
    return parser


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_output_dir(model: str, prompt: str) -> str:
    out_dir = get_project_root() / "output_spurtun" / f"{model.split('/')[-1]}_prompt_{prompt}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(out_dir)


def load_prompt(prompt_arg: str) -> tuple[str, str]:
    path = Path(__file__).resolve().parent / "prompts_spartun" / f"{prompt_arg}.json"
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("prefix", ""), data.get("suffix", "")


def load_cases() -> List[Dict[str, Any]]:
    """Load SPARTUN cases from dataset."""
    data_path = get_project_root() / "data" / "SPARTUN" / "sample_spartun_with_rules_used.json"
    with open(data_path, 'r', encoding='utf-8') as f:
        full_data = json.load(f)
    
    cases = []
    for case in full_data["data"]:
        normalized = {
            "case_id": case["identifier"],
            "story_text": " ".join(case["story"]) if isinstance(case["story"], list) else case["story"],
            "questions": []
        }
        
        for q in case["questions"]:
            normalized_q = {
                "q_id": q["q_id"],
                "type": q.get("q_type", q.get("type", "YN")),
                "text": q.get("question", q.get("text", "")),
                "options": q.get("candidate_answers", q.get("options", [])),
                "gold": q.get("answer", q.get("gold", [])),
                "answer_type": q.get("answer_type", "single"),
                "rule_used": q.get("rule_used", []),
                "question_info": q.get("question_info", {})
            }
            normalized["questions"].append(normalized_q)
        
        cases.append(normalized)
    
    return cases


def build_single_question_block(question: Dict[str, Any]) -> str:
    """Build formatted block for a single question."""
    q_id = question.get("q_id")
    q_type = question.get("type")
    text = question.get("text")
    options = question.get("options", [])
    answer_type = question.get("answer_type", "single")
    
    return f"QID {q_id} | TYPE {q_type} | ANSWER_TYPE {answer_type}\n{text}\nOptions: {', '.join(options)}"


def build_prompt(prefix: str, suffix: str, case: Dict[str, Any], question: Dict[str, Any]) -> str:
    """Build prompt for a single question."""
    story_text = case.get("story_text", "")
    question_block = build_single_question_block(question)
    prompt = prefix.replace("{story_text}", story_text).replace("{question_block}", question_block)
    prompt = prompt + suffix
    return prompt


def select_indices(cases: List[Dict[str, Any]], case_arg: str) -> List[int]:
    """Select which cases to process."""
    n = len(cases)
    if case_arg == "ALL":
        return list(range(n))
    try:
        k = int(case_arg)
    except Exception:
        k = 20
    k = max(0, min(k, n))
    return list(range(k))


def get_json_answer(multiline_string: str) -> Dict[str, Any]:
    """Extract JSON answer from response (expects {"answer": ...})."""
    text = multiline_string.strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    
    # Try last few lines as one-line JSON
    for back in (1, 2, 3):
        if len(lines) >= back:
            candidate = lines[-back]
            if candidate.startswith('{') and candidate.endswith('}'):
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict) and 'answer' in obj:
                        return obj
                except json.JSONDecodeError:
                    pass
    
    # Find last object containing "answer"
    key = '"answer"'
    key_idx = text.rfind(key)
    if key_idx != -1:
        obj_start = text.rfind('{', 0, key_idx)
        if obj_start != -1:
            # Extract balanced braces
            brace_count = 0
            end_idx = None
            for i in range(obj_start, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            if end_idx:
                candidate = text[obj_start:end_idx]
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict) and 'answer' in obj:
                        return obj
                except json.JSONDecodeError:
                    pass
    
    return {}


def extract_gold_rules_for_question(question: Dict[str, Any]) -> List[str]:
    """Extract gold rules for a single question."""
    try:
        rule_used = question.get("rule_used", [])
        if not isinstance(rule_used, list):
            return []
        
        rules = []
        for rule in rule_used:
            if not isinstance(rule, str):
                continue
            rule_clean = " ".join(rule.split())
            if rule_clean:
                rules.append(rule_clean)
        
        return rules
    except Exception:
        return []


def process_single_question(
    case_id: str,
    case_data: Dict[str, Any],
    question: Dict[str, Any],
    prefix: str,
    suffix: str,
    client,
    client_name: str,
    model_name: str,
    pipeline: str,
    prompt_name: str,
    output_dir: str,
    debug_enabled: bool,
    rag_instance: Optional[SpartunRAG],
    rule_gen: Optional[RuleGeneratorSpartun],
    prop_gen: Optional[PropGeneratorSpartun],
    rag_prop_gen: Optional[RagPropGeneratorSpartun]
) -> Dict[str, Any]:
    """Process a single question with appropriate pipeline."""
    try:
        q_id = question["q_id"]
        used_prefix = prefix
        
        # Apply pipeline-specific enhancements to prefix
        if pipeline == "gold_rules" and "{gold_rules}" in used_prefix:
            gold_rules_list = extract_gold_rules_for_question(question)
            gold_rules_text = "\n".join(gold_rules_list) if gold_rules_list else "No gold rules available for this question."
            used_prefix = used_prefix.replace("{gold_rules}", gold_rules_text)
        
        elif pipeline == "rag" and "{dynamic_rules}" in used_prefix and rag_instance:
            top_k = None
            try:
                import re
                m = re.search(r"_t(\d+)", prompt_name)
                if m:
                    top_k = int(m.group(1))
            except Exception:
                pass
            
            used_prefix = rag_instance.enhance_prefix_with_rag_for_question(
                used_prefix, case_data, question, top_k=top_k
            )
        
        elif pipeline == "rag_prop" and "{rag_generated_props}" in used_prefix and rag_instance and rag_prop_gen:
            top_k = None
            prop_count = 10
            try:
                import re
                m = re.search(r"_t(\d+)", prompt_name)
                if m:
                    top_k = int(m.group(1))
                pm = re.search(r"_p(\d+)", prompt_name)
                if pm:
                    prop_count = int(pm.group(1))
            except Exception:
                pass
            
            rules = rag_instance.retrieve_rules_for_question(case_data, question, top_k=top_k)
            props = rag_prop_gen.generate_question_props_from_rag(
                case_data, question, rules, model_name, case_id, q_id, prop_count, logger=debug_logger_spartun
            )
            props_text = "\n".join(props) if props else "No specific propositions generated."
            used_prefix = used_prefix.replace("{rag_generated_props}", props_text)
        
        elif pipeline == "rules_generated" and "{generated_rules}" in used_prefix and rule_gen:
            rule_count = 10
            try:
                import re
                m = re.search(r"_r(\d+)", prompt_name)
                if m:
                    rule_count = int(m.group(1))
            except Exception:
                pass
            
            rules_list = rule_gen.generate_question_rules(
                case_data, question, model_name, case_id, q_id, rule_count, logger=debug_logger_spartun
            )
            rules_text = "\n".join(rules_list) if rules_list else "No rules generated."
            used_prefix = used_prefix.replace("{generated_rules}", rules_text)
        
        elif pipeline == "prop_generated" and "{generated_props}" in used_prefix and prop_gen:
            prop_count = 10
            try:
                import re
                m = re.search(r"_p(\d+)", prompt_name)
                if m:
                    prop_count = int(m.group(1))
            except Exception:
                pass
            
            props_list = prop_gen.generate_question_props(
                case_data, question, model_name, case_id, q_id, prop_count, logger=debug_logger_spartun
            )
            props_text = "\n".join(props_list) if props_list else "No specific propositions generated."
            used_prefix = used_prefix.replace("{generated_props}", props_text)
        
        # Build final prompt
        prompt = build_prompt(used_prefix, suffix, case_data, question)
        
        # Call LLM
        response = client.chat.completions.create(
            model=client_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            seed=42
        )
        
        full_answer = response.choices[0].message.content or ""
        
        # Get COT if available
        try:
            cot = response.choices[0].message.reasoning_content
            if cot is not None:
                full_answer_with_cot = cot + "\n\n" + full_answer
            else:
                cot = ""
                full_answer_with_cot = full_answer
        except Exception:
            cot = ""
            full_answer_with_cot = full_answer
        
        # Parse answer
        answer_json = get_json_answer(full_answer)
        
        # Log if debugging enabled
        if debug_enabled:
            debug_logger_spartun.log_llm_interaction(
                case_id, q_id, prompt, full_answer_with_cot, answer_json, pipeline
            )
        
        return {
            'case_id': case_id,
            'q_id': q_id,
            'answer': answer_json.get('answer', ''),
            'full_response': full_answer,
            'cot': cot,
            'has_error': not answer_json
        }
        
    except Exception as e:
        print(f"Error processing {case_id} question {question['q_id']}: {str(e)}")
        return {
            'case_id': case_id,
            'q_id': question['q_id'],
            'answer': '',
            'full_response': '',
            'cot': '',
            'has_error': True
        }


def run_per_question_parallel(
    cases: List[Dict[str, Any]],
    case_indices: List[int],
    prefix: str,
    suffix: str,
    client,
    client_name: str,
    model_name: str,
    pipeline: str,
    prompt_name: str,
    output_dir: str,
    max_workers: int,
    overwrite: bool,
    debug_enabled: bool
) -> None:
    """Process all questions across all cases in parallel."""
    
    # Inject all_rules placeholder if needed
    if "{all_rules}" in prefix:
        rules_path = get_project_root() / "Rules" / "RuleText.txt"
        try:
            with open(rules_path, 'r', encoding='utf-8') as rf:
                rules_text = rf.read().strip()
            prefix = prefix.replace("{all_rules}", rules_text)
        except Exception as e:
            print(f"[WARNING] Failed to load rules from {rules_path}: {e}")
    
    # Initialize pipeline-specific generators BEFORE parallel processing (thread-safe)
    print(f"[init] Initializing pipeline generators for: {pipeline}")
    rag_instance = None
    if pipeline in ["rag", "rag_prop"]:
        rag_instance = SpartunRAG()
    
    rule_gen = None
    if pipeline == "rules_generated":
        rule_gen = RuleGeneratorSpartun(model_name=model_name)
        try:
            rule_gen.set_cache_file(output_dir, client_name.split('/')[-1], prompt_name)
        except Exception:
            pass
    
    prop_gen = None
    if pipeline == "prop_generated":
        prop_gen = PropGeneratorSpartun(model_name=model_name)
        try:
            prop_gen.set_cache_file(output_dir, client_name.split('/')[-1], prompt_name)
        except Exception:
            pass
    
    rag_prop_gen = None
    if pipeline == "rag_prop":
        rag_prop_gen = RagPropGeneratorSpartun(model_name=model_name)
        try:
            rag_prop_gen.set_cache_file(output_dir, client_name.split('/')[-1], prompt_name)
        except Exception:
            pass
    
    # Collect all (case, question) pairs to process
    tasks = []
    for case_idx in case_indices:
        case = cases[case_idx]
        case_id = case["case_id"]
        
        # Check if output already exists (unless overwrite)
        out_file = Path(output_dir) / f"{case_id}.jsonl"
        if out_file.exists() and not overwrite:
            print(f"[skip] Case {case_id} already exists")
            continue
        
        # Add all questions from this case to task list
        for question in case["questions"]:
            tasks.append({
                'case_id': case_id,
                'case_data': case,
                'question': question
            })
    
    if not tasks:
        print("[info] No tasks to process (all outputs exist, use --overwrite to rerun)")
        return
    
    print(f"[info] Processing {len(tasks)} questions from {len(case_indices)} cases with {max_workers} workers")
    
    # Process all questions in parallel
    results = []
    completed_count = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(
                process_single_question,
                task['case_id'],
                task['case_data'],
                task['question'],
                prefix,
                suffix,
                client,
                client_name,
                model_name,
                pipeline,
                prompt_name,
                output_dir,
                debug_enabled,
                rag_instance,
                rule_gen,
                prop_gen,
                rag_prop_gen
            ): task
            for task in tasks
        }
        
        for future in concurrent.futures.as_completed(future_to_task):
            result = future.result()
            results.append(result)
            completed_count += 1
            
            if completed_count % 10 == 0 or completed_count == len(tasks):
                print(f"[progress] Completed {completed_count}/{len(tasks)} questions")
    
    # Group results by case and save
    print("[info] Aggregating results and saving...")
    results_by_case = {}
    for result in results:
        case_id = result['case_id']
        if case_id not in results_by_case:
            results_by_case[case_id] = []
        results_by_case[case_id].append(result)
    
    # Save results for each case
    for case_id, case_results in results_by_case.items():
        case_results.sort(key=lambda x: x['q_id'])
        
        # Format as array of answers (compatible with evaluate_spartun.py)
        answers_array = [
            {
                "q_id": r['q_id'],
                "answer": r['answer']
            }
            for r in case_results
        ]
        
        answer_json = {"answers": answers_array}
        out_base = Path(output_dir) / f"{case_id}"
        
        # Write .jsonl file
        with open(str(out_base) + '.jsonl', 'w', encoding='utf-8') as f:
            f.write(json.dumps(answer_json, ensure_ascii=False) + "\n")
        
        # Write detailed outputs file
        outputs_data = {
            "case_id": case_id,
            "answers": answers_array,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "processing_mode": "per_question",
                "pipeline": pipeline,
                "total_questions": len(answers_array),
                "errors": sum(1 for r in case_results if r['has_error'])
            },
            "detailed_responses": [
                {
                    "q_id": r['q_id'],
                    "answer": r['answer'],
                    "full_response": r['full_response'],
                    "cot": r['cot']
                }
                for r in case_results
            ]
        }
        
        with open(str(out_base) + '_outputs.json', 'w', encoding='utf-8') as f:
            json.dump(outputs_data, f, indent=2, ensure_ascii=False)
    
    print(f"[done] Saved outputs for {len(results_by_case)} cases to {output_dir}")


def main():
    parser = parse_arguments()
    args = parser.parse_args()
    
    model = args.model
    prompt_name = args.prompt
    case_arg = args.case
    max_workers = args.max_workers
    overwrite = args.overwrite
    debug_enabled = not args.debug_log_off
    
    # Load components
    print(f"[init] Loading model: {model}")
    models_cfg_path = Path(__file__).resolve().parent / "models.json"
    client, client_name = load_model(model, config_path=str(models_cfg_path))
    
    print(f"[init] Loading prompt: {prompt_name}")
    prefix, suffix = load_prompt(prompt_name)
    
    print(f"[init] Loading cases")
    cases = load_cases()
    case_indices = select_indices(cases, case_arg)
    
    print(f"[init] Output directory")
    output_dir = get_output_dir(model, prompt_name)
    
    # Detect pipeline
    pipeline = detect_pipeline(prompt_name, prefix)
    print(f"[pipeline] Selected: {pipeline}")
    
    # Configure debug logging
    if debug_enabled:
        debug_logger_spartun.enable()
    else:
        debug_logger_spartun.disable()
    
    # Save metadata
    with open(os.path.join(output_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
        json.dump({
            'model': model,
            'prompt': prompt_name,
            'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'runner': 'run_spartun_parallel',
            'pipeline': pipeline,
            'max_workers': max_workers
        }, f, indent=2)
    
    print(f"[config] Model: {model}")
    print(f"[config] Prompt: {prompt_name}")
    print(f"[config] Cases: {len(case_indices)} out of {len(cases)}")
    print(f"[config] Max workers: {max_workers}")
    print(f"[config] Overwrite: {overwrite}")
    print(f"[config] Debug logging: {debug_enabled}")
    
    # Run processing
    run_per_question_parallel(
        cases, case_indices, prefix, suffix,
        client, client_name, model, pipeline, prompt_name, output_dir,
        max_workers, overwrite, debug_enabled
    )
    
    # Save debug log if enabled
    if debug_enabled:
        debug_logger_spartun.save_debug_log(output_dir, model.split("/")[-1], prompt_name)
    
    print("[complete] SPARTUN per-question processing finished")


if __name__ == "__main__":
    main()
