"""
evaluate_spartun.py - Evaluation for SPARTUN base pipeline

Reads predictions from ../output_spurtun/<model>_prompt_<prompt>/
Compares against golds in data/SPARTUN/spartun_200.json
Writes report to ../eval_spurtun/<run_name>_report.json
"""

import os
import json
import argparse
from typing import Any, Dict, List
from pathlib import Path


def parse_arguments():
    parser = argparse.ArgumentParser(description='Evaluate SPARTUN base pipeline output')
    parser.add_argument('-m', '--model', type=str, required=True, help='model name')
    parser.add_argument('-p', '--prompt', type=str, default='base', help='prompt template name under prompts_spartun/')
    parser.add_argument('--case', type=str, default='ALL', help='ALL or case index like 0 or 0+ for from-index')
    return parser


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_output_dir(model: str, prompt: str) -> str:
    return str(get_project_root() / "output_spurtun" / f"{model.split('/')[-1]}_prompt_{prompt}")


def load_cases() -> List[Dict[str, Any]]:
    """Load SPARTUN cases with rules metadata from new format.
    
    Converts from sample_spartun_with_rules_used.json format to internal format.
    """
    data_path = get_project_root() / "data" / "SPARTUN" / "sample_spartun_with_rules_used.json"
    with open(data_path, 'r', encoding='utf-8') as f:
        full_data = json.load(f)
    
    # Convert to internal format expected by the rest of the pipeline
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
                # Preserve extra metadata for potential future use
                "rule_used": q.get("rule_used", []),
                "question_info": q.get("question_info", {})
            }
            normalized["questions"].append(normalized_q)
        
        cases.append(normalized)
    
    return cases


def select_indices(total: int, case_arg: str) -> List[int]:
    if case_arg == "ALL":
        return list(range(total))
    base = case_arg.strip('+')
    try:
        start = int(base)
    except Exception:
        return list(range(total))
    if case_arg.endswith('+'):
        return list(range(start, total))
    else:
        return [start] if 0 <= start < total else []


def normalize_gold(questions: List[Dict[str, Any]]) -> Dict[int, List[str]]:
    gold_map: Dict[int, List[str]] = {}
    for q in questions:
        qid = int(q.get("q_id"))
        gold = q.get("gold", [])
        gold_upper = [str(x).upper() for x in gold]
        gold_map[qid] = gold_upper
    return gold_map


def parse_pred(pred_json: Dict[str, Any]) -> Dict[int, List[str]]:
    # Expect schema: { "answers": [ {"q_id": int, "answer": str|[str]} ] }
    ans_map: Dict[int, List[str]] = {}
    answers = pred_json.get("answers", []) if isinstance(pred_json, dict) else []
    for ans in answers:
        try:
            qid = int(ans.get("q_id"))
        except Exception:
            continue
        a = ans.get("answer")
        if a is None:
            continue
        if isinstance(a, list):
            vals = [str(v).upper() for v in a]
        else:
            vals = [str(a).upper()]
        ans_map[qid] = vals
    return ans_map


def evaluate_case(gold_map: Dict[int, List[str]], pred_map: Dict[int, List[str]]) -> Dict[str, float]:
    # Define correctness per question as exact match of sets
    total = len(gold_map)
    correct = 0
    for qid, gold_vals in gold_map.items():
        pred_vals = pred_map.get(qid, [])
        if set(pred_vals) == set(gold_vals):
            correct += 1
    return {
        "total_questions": total,
        "num_correct": correct,
        "accuracy": round(correct / total, 4) if total > 0 else 0.0,
    }


def main():
    parser = parse_arguments()
    args = parser.parse_args()

    model = args.model
    prompt = args.prompt
    case_arg = args.case

    output_dir = get_output_dir(model, prompt)
    cases = load_cases()
    indices = select_indices(len(cases), case_arg)

    overall_total = 0
    overall_correct = 0
    case_reports = {}

    for idx in indices:
        case = cases[idx]
        case_id = case.get("case_id", f"case_{idx}")
        gold_map = normalize_gold(case.get("questions", []))

        pred_path = os.path.join(output_dir, f"{case_id}.jsonl")
        if not os.path.exists(pred_path):
            continue
        try:
            with open(pred_path, 'r', encoding='utf-8') as f:
                line = f.readline().strip()
                pred_json = json.loads(line) if line else {}
        except Exception:
            pred_json = {}

        pred_map = parse_pred(pred_json)
        stats = evaluate_case(gold_map, pred_map)
        case_reports[case_id] = stats
        overall_total += stats["total_questions"]
        overall_correct += stats["num_correct"]

    report = {
        "overall_total_questions": overall_total,
        "overall_correct": overall_correct,
        "overall_accuracy": round(overall_correct / overall_total, 4) if overall_total > 0 else 0.0,
        "cases": case_reports,
    }

    eval_dir = get_project_root() / "eval_spurtun"
    os.makedirs(eval_dir, exist_ok=True)
    run_name = f"{model.split('/')[-1]}_prompt_{prompt}"
    out_path = eval_dir / f"{run_name}_report.json"
    with open(str(out_path), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(f"<evaluate_spartun> Report saved to {out_path}")


if __name__ == "__main__":
    main()


