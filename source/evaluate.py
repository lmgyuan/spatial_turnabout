import json
import os
import argparse
import copy
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import traceback
import math
from collections import defaultdict
from run_models import get_output_dir, get_fnames

parser = argparse.ArgumentParser(description='')
parser.add_argument('-m', '--model', type=str, help='model name')
parser.add_argument('-p', '--prompt', type=str)
parser.add_argument('--context', type=str, help='new, day')
parser.add_argument('-c', '--case', type=str, help='If ALL, run all cases; if a case number like 3-4-1, run that case; if a case number followed by a "+" like 3-4-1+, run that case and all cases after it.')
parser.add_argument('-n', '--no_description', action='store_true')

args = parser.parse_args()
MODEL = args.model
PROMPT = args.prompt
CASE = args.case if args.case else "ALL"
CONTEXT = args.context if args.context else None

def parse_pred(caseid):
    pred_path = os.path.join(output_dir, caseid.replace(".json", ".jsonl"))
    pred = []
    reasoning = []
    if not os.path.exists(pred_path):
        return pred, reasoning
    # Parse predictions
    with open(pred_path, 'r') as f:
        for line in f:
            try:
                turn_pred = json.loads(line)
                assert "evidence" in turn_pred, f"{caseid}: {turn_pred} missing evidence"
                assert "testimony" in turn_pred, f"{caseid}: {turn_pred} missing testimony"
                pred.append(turn_pred)
                
            except json.JSONDecodeError as e:
                print(f"{caseid}: {e}")
                pred.append({})
    # Parse reasoning
    reasoning_path = os.path.join(output_dir, caseid.replace(".json", "_full_responses.txt"))
    idx = 0
    lines = []
    with open(reasoning_path, 'r') as f:
        reasoning = f.read()
    return pred, reasoning

def parse_gold(caseid, data_dir):
    """
    Return a list of ground truth turns
    """
    gold_indices = []
    gold_names = []
    gold_metadata = {
        "turns": []
    }
    with open(os.path.join(data_dir, caseid), 'r') as f:
        data = json.load(f)
        evidences = [evidence['name'] for evidence in data['evidences']]
        characters = [character['name'] for character in data['characters']]
        # Parse evidence metadata
        n_evidences = len(evidences)
        gold_metadata["evidences"] = evidences
        # Iterate over turns
        for turn in data['turns']:
            correct_pairs_indices = []
            correct_pairs_names = []
            turn_metadata = {}
            if turn["noPresent"]:
                continue
            # Parse testimony metadata
            n_testimonies = len(turn['testimonies'])
            n_action_space = n_evidences * n_testimonies
            for i, testimony in enumerate(turn['testimonies']):
                if testimony["present"]:
                    correct_evidence_names = testimony["present"]
                    for correct_evidence_name in correct_evidence_names:
                        correct_evidence_index = evidences.index(correct_evidence_name)
                        correct_pairs_indices.append({"evidence": correct_evidence_index, "testimony": i})
                        correct_pairs_names.append({"evidence": correct_evidence_name, "testimony": testimony["testimony"]})
            # Add metadata of the turn
            turn_metadata["labels"] = turn["labels"] if "labels" in turn else []
            turn_metadata["n_reasoning"] = len(turn["reasoning"]) if "reasoning" in turn else 0
            turn_metadata["n_action_space"] = n_action_space
            turn_metadata["testimonies"] = turn["testimonies"]
            # Append
            gold_indices.append(correct_pairs_indices)
            gold_names.append(correct_pairs_names)
            gold_metadata["turns"].append(turn_metadata)
    return gold_indices, gold_names, gold_metadata

def init_correct(caseids, data_dir):
    categories = []
    reasoning_steps = []
    for caseid in caseids:
        with open(os.path.join(data_dir, caseid), 'r') as f:
            data = json.load(f)
            for turn in data['turns']:
                if "labels" in turn:
                    for label in turn['labels']:
                        if label:
                            categories.append(label)
                if "reasoning" in turn:
                    len_of_reasoning = len(turn['reasoning'])
                    if len_of_reasoning > 0:
                        reasoning_steps.append(len_of_reasoning)

    categories = list(set(categories))
    reasoning_steps = list(set(reasoning_steps))
    
    categories_correct = {
        label: {
            "correct": 0, 
            'evidence_correct': 0,
            'testimony_correct': 0,
            "total": 0, 
            "accuracy": 0, 
            'evidence_accuracy': 0,
            'testimony_accuracy': 0,
            "bad_cases": []
        } 
        for label in categories
    }
    reasoning_correct = {
        step: {
            "correct": 0, 
            'evidence_correct': 0,
            'testimony_correct': 0,
            "total": 0, 
            "accuracy": 0, 
            'evidence_accuracy': 0,
            'testimony_accuracy': 0,
            "bad_cases": []
        } 
        for step in reasoning_steps
    }
    return categories_correct, reasoning_correct

def evaluate(
    output_dir, 
    data_dir, 
    caseids, 
    preds, 
    reasonings, 
    golds_indices, 
    golds_names, 
    golds_metadata
):
    eval_dir = os.path.join(output_dir, "eval")
    os.makedirs(eval_dir, exist_ok=True)

    report_json = {
            'model': MODEL,
            'prompt': PROMPT,
            'case': CASE,
            'overall_correct': -1,
            'overall_evidence_correct': -1,
            'overall_testimony_correct': -1,
            'overall_total': -1,
            'overall_accuracy': -1,
            'overall_evidence_accuracy': -1,
            'overall_testimony_accuracy': -1,
            'average_reasoning_tokens': -1,
            'categories_accuracy': {},
            'reasoning_steps_accuracy': {},
            'action_space_accuracy': {},
            "case_details": {}
    }
    overall_correct = 0
    overall_total = 0
    overall_evidence_correct = 0
    overall_testimony_correct = 0
    overall_reasoning_tokens = 0

    # Initialize breakdown metrics
    categories_correct, reasoning_correct = init_correct(caseids, data_dir)
    action_space_correct = {}

    for caseid, pred, reasoning, gold_indices, gold_names, gold_metadata \
        in zip(caseids, preds, reasonings, golds_indices, golds_names, golds_metadata):  # iter each case
        report_json["case_details"][caseid] = {
            "case_accuracy": -1,
            "turns": []
        }
        case_correct = 0
        case_evidence_correct = 0
        case_testimony_correct = 0
        case_total = len(gold_indices)

        case_total_reasoning_tokens = len(reasoning.split(" "))
        overall_reasoning_tokens += case_total_reasoning_tokens
        case_average_reasoning_tokens = round(case_total_reasoning_tokens / case_total, 2)

        for i in range(len(gold_indices)):  # iter each turn
            # Init correctness count
            is_correct = False
            is_evidence_correct = False
            is_testimony_correct = False

            # Evaluate correctness
            if pred[i] in gold_indices[i]:  
                is_correct = True
                case_correct += 1

            # Evaluate evidence correctness
            if "evidence" in pred[i] and any(
                pred[i]["evidence"] == gold_indices[i][j]["evidence"] 
                for j in range(len(gold_indices[i]))
            ):  # Need to check property because it can be {}, default to incorrect
                is_evidence_correct = True
                case_evidence_correct += 1

            # Evaluate testimony correctness
            if "testimony" in pred[i] and any(
                pred[i]["testimony"] == gold_indices[i][j]["testimony"] 
                for j in range(len(gold_indices[i]))
            ):
                is_testimony_correct = True
                case_testimony_correct += 1

            # Evaluate category accuracy
            turn_labels = gold_metadata["turns"][i]["labels"]         
            for label in turn_labels:
                if label:
                    categories_correct[label]["total"] += 1
                    if is_correct:
                        categories_correct[label]["correct"] += 1
                    else:
                        categories_correct[label]["bad_cases"].append({"caseid": caseid, "turn": i})

                    if is_evidence_correct:
                        categories_correct[label]['evidence_correct'] += 1
                    if is_testimony_correct:
                        categories_correct[label]['testimony_correct'] += 1

            # Evaluate reasoning step accuracy
            turn_n_reasoning = gold_metadata["turns"][i]["n_reasoning"] 
            if turn_n_reasoning > 0:
                reasoning_correct[turn_n_reasoning]["total"] += 1
                if is_correct:
                    reasoning_correct[turn_n_reasoning]["correct"] += 1
                else:
                    reasoning_correct[turn_n_reasoning]["bad_cases"].append({"caseid": caseid, "turn": i})

                if is_evidence_correct:
                    reasoning_correct[turn_n_reasoning]['evidence_correct'] += 1
                if is_testimony_correct:
                    reasoning_correct[turn_n_reasoning]['testimony_correct'] += 1

            # Evaluate action space accuracy
            n_action_space_raw = gold_metadata["turns"][i]["n_action_space"]
            # Binned by 20 starting from 100
            action_space = max(math.ceil(n_action_space_raw / 20), 5) * 20
            if action_space not in action_space_correct:
                action_space_correct[action_space] = {
                    "correct": 0,
                    "total": 0,
                    "evidence_correct": 0,
                    "testimony_correct": 0,
                    "bad_cases": []
                }
            action_space_correct[action_space]["total"] += 1
            if is_correct:
                action_space_correct[action_space]["correct"] += 1
            else:
                action_space_correct[action_space]["bad_cases"].append({"caseid": caseid, "turn": i})

            if is_evidence_correct:
                action_space_correct[action_space]["evidence_correct"] += 1
            if is_testimony_correct:
                action_space_correct[action_space]["testimony_correct"] += 1

            # Log turn data
            try:
                out_pred = {
                    "evidence_id": pred[i]["evidence"],
                    "evidence": gold_metadata["evidences"][pred[i]["evidence"]],
                    "testimony_id": pred[i]["testimony"],
                    "testimony": gold_metadata["turns"][i]["testimonies"][pred[i]["testimony"]]
                }
            except Exception as e:
                print(f"{caseid} - {i} - {pred[i]}: {e}")
                out_pred = {
                    "evidence_id": -1,
                    "evidence": "N/A",
                    "testimony_id": -1,
                    "testimony": "N/A"
                }
            gold = [{
                    "evidence_id": a["evidence"],
                    "evidence": b["evidence"],
                    "testimony_id": a["testimony"],
                    "testimony": b["testimony"]
                } for a,b in zip(gold_indices[i], gold_names[i])
            ]
            report_json["case_details"][caseid]["turns"].append({
                'case_accuracy': round(case_correct / case_total, 4),
                'mean_n_reasoning_tokens': case_average_reasoning_tokens,
                "gold": gold,
                "pred": out_pred,
            })

        # Increment case data
        overall_correct += case_correct
        overall_total += case_total 
        overall_evidence_correct += case_evidence_correct
        overall_testimony_correct += case_testimony_correct

    # Log overall data
    report_json['overall_correct'] = overall_correct
    report_json['overall_total'] = overall_total
    report_json["overall_accuracy"] = round(overall_correct / overall_total, 4)
    report_json["average_reasoning_tokens"] = overall_reasoning_tokens // overall_total

    report_json['overall_evidence_correct'] = overall_evidence_correct
    report_json['overall_testimony_correct'] = overall_testimony_correct
    report_json['overall_evidence_accuracy'] = round(overall_evidence_correct / overall_total, 4)
    report_json['overall_testimony_accuracy'] = round(overall_testimony_correct / overall_total, 4)

    # Log breakdown accuracy
    report_json["categories_accuracy"] = {
        label: {
            "accuracy": round(stats["correct"] / stats["total"], 4),
            "evidence_accuracy": round(stats["evidence_correct"] / stats["total"], 4),
            "testimony_accuracy": round(stats["testimony_correct"] / stats["total"], 4),
            **stats, 
        }
        for label, stats in sorted(categories_correct.items())
        if stats["total"] > 0
    }
    report_json["reasoning_steps_accuracy"] = {
        step: {
            "accuracy": round(stats["correct"] / stats["total"], 4),
            "evidence_accuracy": round(stats["evidence_correct"] / stats["total"], 4),
            "testimony_accuracy": round(stats["testimony_correct"] / stats["total"], 4),
            **stats, 
        }
        for step, stats in sorted(reasoning_correct.items())
        if stats["total"] > 0
    }
    report_json["action_space_accuracy"] = {
        action_space: {
            "accuracy": round(stats["correct"] / stats["total"], 4),
            "evidence_accuracy": round(stats["evidence_correct"] / stats["total"], 4),
            "testimony_accuracy": round(stats["testimony_correct"] / stats["total"], 4),
            **stats, 
        }
        for action_space, stats in sorted(action_space_correct.items())
        if stats["total"] > 0
    }

    # Write to json
    with open(os.path.join(eval_dir, f"report.json"), 'w') as f:
        json.dump(report_json, f, indent=2)
    print(f"Report saved to {eval_dir}/report.json")

if __name__ == "__main__":
    data_dir = '../data/aceattorney_data/final'
    output_dir = get_output_dir()   
    caseids = get_fnames(data_dir, output_dir, eval=True)

    preds = []
    reasonings = []
    golds_indices = []
    golds_names = []
    golds_metadata = []
    caseids_final = []

    for i, caseid in enumerate(caseids):
        pred, reasoning = parse_pred(caseid)
        if not pred: 
            print(f"Case {caseid.split('_')[0]}, no pred. Skipping...")
            continue

        gold_indices, gold_names, gold_metadata = parse_gold(caseid, data_dir)

        if len(pred) != len(gold_indices):
            print(f"Case {caseid.split('_')[0]}, num of pred: {len(pred)} != {len(gold_indices)}. Skipping...")
            continue

        caseids_final.append(caseid)
        preds.append(pred)  # List of dicts
        reasonings.append(reasoning)  # List of strings
        golds_indices.append(gold_indices)  # List of list of dicts
        golds_names.append(gold_names)
        golds_metadata.append(gold_metadata)

    print(f"Evaluating {len(caseids_final)} court days...")
    evaluate(
        output_dir, 
        data_dir,
        caseids_final, 
        preds, 
        reasonings, 
        golds_indices, 
        golds_names, 
        golds_metadata
    )
