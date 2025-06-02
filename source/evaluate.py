import json
import os
import argparse
import copy
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import traceback
import csv
import math
from tqdm import tqdm
from collections import defaultdict

from run_models import get_output_dir, get_fnames, parse_arguments

# Parsing functions

def parse_pred(caseid, output_dir):
    pred_path = os.path.join(output_dir, caseid.replace(".json", ".jsonl"))
    pred = []
    reasoning = []
    if not os.path.exists(pred_path):
        # print(f"{pred_path}: no pred. Skipping...")
        return pred, reasoning
    # Parse predictions
    with open(pred_path, 'r') as f:
        for i, line in enumerate(f):
            try:
                turn_pred = json.loads(line)
                pred.append(turn_pred)
                
            except Exception as e:
                print(f"{caseid} response {i}: {e}")
                pred.append({"evidence": -1, "testimony": -1})
    # Parse reasoning
    if os.path.exists(os.path.join(output_dir, caseid.replace(".json", "_outputs.json"))):
        with open(os.path.join(output_dir, caseid.replace(".json", "_outputs.json")), 'r') as f:
            output = json.load(f)
            reasoning = [o['cot'] for o in output]  # list of strings

    if all(ans == {} for ans in pred):
        return [], []
    return pred, reasoning

def parse_pred_openai(caseid, input_data, output_data, output_dir):
    caseid_base = caseid.replace(".json", "")
    reasoning = []
    pred = []
    ids = []
    # Get preds
    for line in output_data:
        if caseid_base in line["custom_id"]:
            full_response = line["response"]["body"]["choices"][0]["message"]["content"]
            try:
                last_line = full_response.splitlines()[-1]
                json_response = last_line[last_line.index("{") : last_line.index("}") + 1]
                response = json.loads(json_response)
                cot = "\n".join(full_response.splitlines()[:-1])
            except Exception:
                try:
                    new_line = full_response.splitlines()[-2]
                    json_response = new_line[new_line.index("{") : new_line.index("}") + 1]
                    response = json.loads(json_response)
                    cot = "\n".join(full_response.splitlines()[:-2])
                except Exception:
                    print(
                        f"<parse_pred_openai> Case {line['custom_id'].split('_')[0]} "
                        f"turn {line['custom_id'].split('_')[-1]}: No json output detected"
                    )
                    response = {"evidence": -1, "testimony": -1}
                    cot = ""

            pred.append(response)
            reasoning.append(cot)
            ids.append(line["custom_id"])
    
    if not pred:
        return [], []

    # Get prompts
    prompts = [""] * len(ids)
    for prompt in input_data:
        if prompt["custom_id"] in ids:
            prompts[ids.index(prompt["custom_id"])] = prompt["body"]["messages"][1]["content"]
    if "" in prompts:
        num_missing = prompts.count("")
        print(f"<parse_pred_openai> {caseid_base}: {num_missing} out of {len(ids)} prompts are missing")

    # Log
    with open(os.path.join(output_dir, caseid.split('.')[0] + '.jsonl'), 'w') as file:
        for answer_json in pred:
            file.write(json.dumps(answer_json) + "\n")
    with open(os.path.join(output_dir, caseid.split('.')[0] + '_outputs.json'), 'w') as file:
        json_response = []
        for idx, cot in enumerate(reasoning):
            json_response.append({
                "idx": int(ids[idx].split("_")[-1]),  # May not be idx
                "prompt": prompts[idx],
                "cot": cot,
                "response_json": pred[idx]
            })
        json_response = sorted(
            json_response,
            key=lambda x: int(x["idx"])
        )  # Sort by idx, to match the order of gold_indices
        file.write(json.dumps(json_response, indent=2, ensure_ascii=False))
    
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
    try:
        with open(os.path.join(data_dir, caseid), 'r') as f:
            data = json.load(f)
            evidences = [evidence['name'] for evidence in data.get('evidences', [])]
        characters = [character['name'] for character in data.get('characters', [])]
        # Parse evidence metadata
        n_evidences = len(evidences)
        gold_metadata["evidences"] = evidences
        # Iterate over turns
        for turn in data.get('turns', []):
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
    except Exception as e:
        raise Exception(f"<parse_gold> {caseid}: {traceback.format_exc()}")
    return gold_indices, gold_names, gold_metadata

# Stats functions

def init_correct(data_dir, output_dir):
    categories = []
    reasoning_steps = []
    action_space_sizes = []

    # Get complete caseids
    caseids = get_fnames(data_dir, output_dir, "ALL", eval=True, verbose=False)

    for caseid in caseids:
        with open(os.path.join(data_dir, caseid), 'r') as f:
            data = json.load(f)
            if "turns" not in data or data['turns'] == []:  # Skip if no turns
                continue
            n_evidences = len(data['evidences'])
            for turn in data['turns']:
                if turn["noPresent"]:
                    continue
                n_testimonies = len(turn['testimonies'])
                if "labels" in turn:
                    for label in turn['labels']:
                        if label:
                            categories.append(label)
                if "reasoning" in turn:
                    len_of_reasoning = len(turn['reasoning'])
                    if len_of_reasoning > 0:
                        reasoning_steps.append(len_of_reasoning)
                n_action_space = n_evidences * n_testimonies
                # Contain duplicates to count occurrences
                action_space_sizes.append(n_action_space)  

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
            # "bad_cases": []
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
            # "bad_cases": []
        } 
        for step in reasoning_steps
    }

    action_space_correct = bin_action_space(action_space_sizes)

    return categories_correct, reasoning_correct, action_space_correct

def bin_action_space(action_space_sizes, desired_n_bins=7):
    if len(np.unique(action_space_sizes)) == 1:
        size = action_space_sizes[0]
        bin_edges = np.array([size, size + 1])
        action_n_bins = 1

    else:
        quantiles = np.linspace(0, 1, desired_n_bins + 1)
        bin_edges = np.quantile(action_space_sizes, quantiles)
        bin_edges = np.unique(bin_edges)

        if len(bin_edges) > 1:
            bin_edges[-1] += 1

        actual_n_bins = len(bin_edges) - 1

    bin_labels = []
    for j in range(actual_n_bins):
        lower_bound = bin_edges[j]
        upper_bound = bin_edges[j + 1]
        lower_bound_int = int(np.ceil(lower_bound))
        upper_bound_int = int(np.floor(upper_bound))
        if upper_bound_int <= lower_bound_int:
            label = f"{lower_bound_int}-{lower_bound_int}"
        else:  # upper_bound_int > lower_bound_int
            label = f"{lower_bound_int}-{upper_bound_int - 1}"
        bin_labels.append(label)

    action_space_correct = {
        label: {
            "range": (int(label.split("-")[0]), int(label.split("-")[1])),
            "correct": 0,
            "total": 0,
            "evidence_correct": 0,
            "testimony_correct": 0,
            "accuracy": -1,
            "evidence_accuracy": -1,
            "testimony_accuracy": -1,
            "bad_cases": [],
        }
        for j, label in enumerate(bin_labels)
    }

    return action_space_correct

def calculate_accuracy(correct_dict):
    return {
        label: {
            **stats,  # expand stats first to avoid overwriting
            "accuracy": round(stats["correct"] / stats["total"], 4),
            "evidence_accuracy": round(stats["evidence_correct"] / stats["total"], 4),
            "testimony_accuracy": round(stats["testimony_correct"] / stats["total"], 4),  
        }
        for label, stats in sorted(correct_dict.items())
        if stats["total"] > 0
    }

# Eval functions

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

    report_json = {
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
    action_space_results = []

    # Initialize breakdown metrics
    categories_correct, reasoning_correct, action_space_correct = init_correct(
        data_dir,
        output_dir
    )

    for caseid, pred, reasoning, gold_indices, gold_names, gold_metadata \
        in zip(caseids, preds, reasonings, golds_indices, golds_names, golds_metadata):  # iter each case
        report_json["case_details"][caseid] = {
            "case_accuracy": -1,
            "case_evidence_accuracy": -1,
            "case_testimony_accuracy": -1,
            "mean_n_reasoning_tokens": -1,
            "turns": []
        }

        case_correct = 0
        case_evidence_correct = 0
        case_testimony_correct = 0
        case_total = len(gold_indices)

        case_total_reasoning_tokens = sum([len(r.split(" ")) for r in reasoning])
        overall_reasoning_tokens += case_total_reasoning_tokens
        case_average_reasoning_tokens = round(case_total_reasoning_tokens / case_total, 2)
        report_json["case_details"][caseid]["mean_n_reasoning_tokens"] = case_average_reasoning_tokens

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
                        # categories_correct[label]["bad_cases"].append(f"{caseid} turn {i}")
                        pass

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
                    # reasoning_correct[turn_n_reasoning]["bad_cases"].append(f"{caseid} turn {i}")
                    pass

                if is_evidence_correct:
                    reasoning_correct[turn_n_reasoning]['evidence_correct'] += 1
                if is_testimony_correct:
                    reasoning_correct[turn_n_reasoning]['testimony_correct'] += 1

            # Evaluate action space accuracy
            action_space = gold_metadata["turns"][i]["n_action_space"]
            for label, stats in action_space_correct.items():
                if action_space >= stats["range"][0] and action_space <= stats["range"][1]:
                    action_space_correct[label]["total"] += 1
                    if is_correct:
                        action_space_correct[label]["correct"] += 1
                    else:
                        # action_space_correct[label]["bad_cases"].append(f"{caseid} turn {i}")
                        pass
                    if is_evidence_correct:
                        action_space_correct[label]['evidence_correct'] += 1
                    if is_testimony_correct:
                        action_space_correct[label]['testimony_correct'] += 1
                    break

            # Log turn data
            out_pred = {
                "evidence_id": -1,
                "evidence": "N/A",
                "testimony_id": -1,
                "testimony": "N/A",
                "reasoning": "N/A"
            }
            try:
                out_pred["evidence_id"] = pred[i]["evidence"]
                out_pred["testimony_id"] = pred[i]["testimony"]
                out_pred["evidence"] = gold_metadata["evidences"][out_pred["evidence_id"]]
                out_pred["testimony"] = gold_metadata["turns"][i]["testimonies"][out_pred["testimony_id"]]["testimony"]
                out_pred["reasoning"] = reasoning[i]
            except Exception as e:
                print(
                    f"<evaluate> Case {caseid.split('_')[0]} turn {i} "
                    f"pred: {pred[i]}: {e}"
                )
                
            gold = [{
                    "evidence_id": a["evidence"],
                    "evidence": b["evidence"],
                    "testimony_id": a["testimony"],
                    "testimony": gold_metadata["turns"][i]["testimonies"][a["testimony"]]
                } for a,b in zip(gold_indices[i], gold_names[i])
            ]

            report_json["case_details"][caseid]["turns"].append({
                "gold": gold,
                "pred": out_pred,
                'is_correct': is_correct,
                'is_evidence_correct': is_evidence_correct,
                'is_testimony_correct': is_testimony_correct,
                'labels': turn_labels,
                'n_steps': turn_n_reasoning,
                'n_action_space': action_space,
                "n_reasoning_tokens": len(reasoning[i].split(" ")) if isinstance(reasoning, list) else "N/A"
            })

        # Increment case data
        overall_correct += case_correct
        overall_total += case_total 
        overall_evidence_correct += case_evidence_correct
        overall_testimony_correct += case_testimony_correct

        if case_total > 0:
            report_json["case_details"][caseid]["case_accuracy"] = round(case_correct / case_total, 4)
            report_json["case_details"][caseid]["case_evidence_accuracy"] = round(case_evidence_correct / case_total, 4)
            report_json["case_details"][caseid]["case_testimony_accuracy"] = round(case_testimony_correct / case_total, 4)

    # Log overall data
    report_json['overall_correct'] = overall_correct
    report_json['overall_total'] = overall_total
    report_json['overall_evidence_correct'] = overall_evidence_correct
    report_json['overall_testimony_correct'] = overall_testimony_correct

    if overall_total > 0:
        report_json["overall_accuracy"] = round(overall_correct / overall_total, 4)
        report_json["average_reasoning_tokens"] = overall_reasoning_tokens // overall_total
        report_json['overall_evidence_accuracy'] = round(overall_evidence_correct / overall_total, 4)
        report_json['overall_testimony_accuracy'] = round(overall_testimony_correct / overall_total, 4)

    # Log breakdown accuracy
    report_json["categories_accuracy"] = calculate_accuracy(categories_correct)
    report_json["reasoning_steps_accuracy"] = calculate_accuracy(reasoning_correct)

    action_space_correct = calculate_accuracy(action_space_correct)
    action_space_correct = dict(sorted(
        action_space_correct.items(), 
        key=lambda item: int(item[0].split("-")[0])
    ))
    report_json["action_space_accuracy"] = action_space_correct

    # Write to json
    with open(os.path.join('../eval', f"{os.path.basename(output_dir)}_report.json"), 'w') as f:
        json.dump(report_json, f, indent=2)
    print(f"<evaluate> Report saved to {os.path.join('../eval', f'{os.path.basename(output_dir)}_report.json')}")

def run_eval_job(caseids, output_dir, data_dir, client):
    preds = []
    reasonings = []
    golds_indices = []
    golds_names = []
    golds_metadata = []
    caseids_final = []

    data = []
    if type(client).__name__ == "OpenAI":
        output_data, input_data = [], {}
        output_files = sorted([
            os.path.join(output_dir, output_path) 
            for output_path in os.listdir(output_dir) 
            if output_path.startswith("batchoutput")
        ])  # Guaranteed to be mutually exclusive
        input_files = sorted([
            os.path.join(output_dir, input_path)
            for input_path in os.listdir(output_dir)
            if input_path.startswith("batchinput")
        ])  # Not guaranteed to be mutually exclusive
        for output_file in output_files:
            with open(output_file, "r") as file:
                output_data += [json.loads(line) for line in file]
        for input_file in input_files:
            with open(input_file, "r") as file:
                for line in file:
                    input_line = json.loads(line)
                    input_data[input_line["custom_id"]] = input_line
        input_data = list(input_data.values())
        print(f"<run_eval_job> {len(input_data)} input turns found, {len(output_data)} output turns found")

    skips = 0
    for i, caseid in enumerate(caseids):
        # Summarize ground truth data stats
        gold_indices, gold_names, gold_metadata = parse_gold(caseid, data_dir)

        # Parse predictions
        if client is not None and type(client).__name__ == "OpenAI":
            pred, reasoning = parse_pred_openai(caseid, input_data, output_data, output_dir)
        else:
            pred, reasoning = parse_pred(caseid, output_dir)

        if not pred: 
            skips += 1
            continue

        if len(pred) != len(gold_indices):
            print(f"<run_eval_job> Case {caseid.split('_')[0]}, num of pred: {len(pred)}, num of gold: {len(gold_indices)}. Skipping...")
            continue

        caseids_final.append(caseid)
        preds.append(pred)  # List of dicts
        reasonings.append(reasoning)  # List of strings
        golds_indices.append(gold_indices)  # List of list of dicts
        golds_names.append(gold_names)
        golds_metadata.append(gold_metadata)

    print(f"<run_eval_job> Evaluating {len(caseids_final)} court days...")
    print(f"<run_eval_job> Skipped {skips} court days because of no preds")

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

def check_status(output_dir):
    # Check if the result has been saved
    has_output = True
    duplicate_count = 1
    result_file_name = os.path.join(output_dir, "batchoutput.jsonl")
    input_file_name = os.path.join(output_dir, "batchinput.jsonl")
    while os.path.exists(result_file_name) and os.path.exists(input_file_name):
        result_file_name = os.path.join(output_dir, f"batchoutput_{duplicate_count}.jsonl")
        input_file_name = os.path.join(output_dir, f"batchinput_{duplicate_count}.jsonl")
        duplicate_count += 1
    if os.path.exists(input_file_name):  # There is a standalone input file
        has_output = False

    if has_output: return True
        
    from dotenv import load_dotenv
    load_dotenv("../.env")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    from openai import OpenAI
    client = OpenAI(
        api_key=OPENAI_API_KEY
    )

    with open(os.path.join(output_dir, "batch_api_metadata.json"), "r") as file:
        data = json.load(file)
    batch_job_id = data["batch_job_id"]

    batch_job = client.batches.retrieve(batch_job_id)
    status = batch_job.status
    print(f"Status: {status}")
        
    if status == "completed":
        result_file_id = batch_job.output_file_id
        print(f"file id: {result_file_id}")

        if result_file_id is None:
            print("Error file created")
            result_file_id = batch_job.error_file_id
        
        result = client.files.content(result_file_id).content

        with open(result_file_name, 'wb') as file:
            file.write(result)

        return True

    return False

def evaluate_single_run(output_dir, data_dir, MODEL, CASE="ALL"):
    print(f"Evaluating {MODEL} with prompt {output_dir.split('_')[2]}...")
    caseids = get_fnames(data_dir, output_dir, CASE, eval=True)

    client = None
    if any(m_name in MODEL for m_name in ["gpt", "o3", "o4"]):
        if not check_status(output_dir):
            return
        else:
            from dotenv import load_dotenv
            load_dotenv("../.env")
            OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

            from openai import OpenAI
            client = OpenAI(
                api_key=OPENAI_API_KEY
            )

    run_eval_job(
        caseids, 
        output_dir, 
        data_dir, 
        client, 
    )

def evaluate_all(data_dir, output_root_dir):
    # Find data name
    if "danganronpa" in data_dir:
        data_name = "danganronpa"
    else:
        data_name = "aceattorney"
    # Filter output dirs
    output_dirs = []
    for output in sorted(os.listdir(output_root_dir)):
        if os.path.isdir(os.path.join(output_root_dir, output)) \
            and "prompt" in output:
            if data_name == "danganronpa" and "danganronpa" in output:
                output_dirs.append(os.path.join(output_root_dir, output))
            elif data_name == "aceattorney" and "danganronpa" not in output:
                output_dirs.append(os.path.join(output_root_dir, output))
    # Evaluate all models
    for output_dir in tqdm(output_dirs, total=len(output_dirs), desc="Evaluating all models"):
        MODEL = os.path.basename(output_dir).split("_")[0]
        evaluate_single_run(output_dir, data_dir, MODEL, "ALL")

# OS related functions

def find_output_dir(args):
    MODEL = args.model
    PROMPT = args.prompt
    CASE = args.case if args.case else "ALL"
    CONTEXT = args.context if args.context else None
    NO_DESCRIPTION = args.no_description
    DATA = args.data

    output_dir = get_output_dir(
        MODEL, 
        PROMPT, 
        CONTEXT, 
        CASE, 
        NO_DESCRIPTION,
        DATA
    ) 
    if not os.path.exists(output_dir):
        raise ValueError(f"Output directory {output_dir} does not exist")

    return output_dir

if __name__ == "__main__":
    parser = parse_arguments()
    args = parser.parse_args()

    DATA = args.data
    if DATA == 'aceattorney':
        data_dir = '../data/aceattorney_data/final'
    elif DATA == 'danganronpa':
        data_dir = '../data/danganronpa_data/final'
    output_root_dir = '../output'

    if not os.path.exists("../eval"):
        os.makedirs("../eval")

    if args.all:
        evaluate_all(data_dir, output_root_dir)
    else:
        output_dir = find_output_dir(args)  
        evaluate_single_run(output_dir, data_dir, args.model, args.case)
