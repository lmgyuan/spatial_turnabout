import json
import os
import argparse
import copy
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import traceback
import math

parser = argparse.ArgumentParser(description='')
parser.add_argument('-m', '--model', type=str, help='model name')
parser.add_argument('-p', '--prompt', type=str)
parser.add_argument('--case', type=str)
parser.add_argument('--context', type=str, help='new, day, partial')
parser.add_argument('-n', '--no_description', action='store_true')

# python evaluate.py --model deepseek-ai/DeepSeek-R1-Distill-Llama-70B --prompt harry_v1

args = parser.parse_args()
MODEL = args.model
PROMPT = args.prompt
CASE = args.case if args.case else "ALL"
CONTEXT = args.context if args.context else 'no_context'

data_dir = '../data/aceattorney_data/final'
output_dir = f'../output/{MODEL.split("/")[-1]}_{PROMPT}'
if args.context is not None:
    output_dir += f"_{CONTEXT}"
if args.no_description:
    output_dir += "_no_description" 

def parse_pred(caseid):
    pred = []
    with open(os.path.join(output_dir, caseid + ".jsonl"), 'r') as f:
        for line in f:
            try:
                pred.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"{caseid}: {e}")
                pred.append({})
    return pred

def parse_gold(caseid):
    """
    gold_indices = [[{"evidence": 2, "testimony": 3}, {"evidence":4, "testimony": 3}], [{...}]]
    """
    gold_indices = []
    gold_names = []
    with open(os.path.join(data_dir, caseid + ".json"), 'r') as f:
        try:
            data = json.load(f)
            evidences = [evidence['name'] for evidence in data['evidences']]
            characters = [character['name'] for character in data['characters']]
            for turn in data['turns']:
                correct_pairs_indices = []
                correct_pairs_names = []
                if turn["noPresent"]:
                    continue
                for i, testimony in enumerate(turn['testimonies']):
                    if testimony["present"]:
                        correct_evidence_names = testimony["present"]
                        for correct_evidence_name in correct_evidence_names:
                            correct_evidence_index = evidences.index(correct_evidence_name)
                            evidence_type = "evidence"
                            correct_testimony_index = i
                            correct_pairs_indices.append({evidence_type: correct_evidence_index, "testimony": correct_testimony_index})
                            correct_pairs_names.append({evidence_type: correct_evidence_name, "testimony": testimony["testimony"]})
                gold_indices.append(correct_pairs_indices)
                gold_names.append(correct_pairs_names)
        except Exception:
            print(f"\n\n{caseid} error:\n\n")
            traceback.print_exc()
            return [], []
    return gold_indices, gold_names

def get_evidences_by_case(caseids):
    evidences_by_case = {}
    for caseid in caseids:
        with open(os.path.join(data_dir, caseid + ".json"), 'r') as f:
            data = json.load(f)
            evidences = [evidence['name'] for evidence in data['evidences']]
            characters = [character['name'] for character in data['characters']]
            evidences_by_case[caseid] = {"evidences": evidences, "characters": characters}
    return evidences_by_case
    
def get_testimonies_by_case(caseids):
    testimonies_by_case = {}
    for caseid in caseids:
        testimonies_by_case[caseid] = []
        with open(os.path.join(data_dir, caseid + ".json"), 'r') as f:
            data = json.load(f)
            for turn in data['turns']:
                testimonies = []
                if turn["noPresent"]:
                    continue
                for testimony in turn['testimonies']:
                    testimonies.append(testimony["testimony"])
                testimonies_by_case[caseid].append(testimonies)
    return testimonies_by_case

def get_labels_by_case(caseids):
    labels_by_case = {}
    for caseid in caseids:
        labels_by_case[caseid] = []
        with open(os.path.join(data_dir, caseid + ".json"), 'r') as f:
            data = json.load(f)
            for turn in data['turns']:
                if turn["noPresent"]:
                    continue
                if "labels" in turn and "reasoning" in turn:
                    labels_by_case[caseid].append(
                        {"labels": turn["labels"], "reasoning": turn["reasoning"]}
                    )
                else:
                    labels_by_case[caseid].append({"labels": [], "reasoning": []})
    return labels_by_case

def plot_category_accuracies(categories_correct):
    categories = list(categories_correct.keys())
    totals = [data['total'] for data in categories_correct.values()]
    
    # Get all three accuracy metrics
    accuracies = [data['accuracy'] for data in categories_correct.values()]
    evidence_accuracies = [data['evidence_accuracy'] for data in categories_correct.values()]
    testimony_accuracies = [data['testimony_accuracy'] for data in categories_correct.values()]
    
    plt.figure(figsize=(14, 7))
    
    # Set width and positions
    bar_width = 0.25
    r1 = np.arange(len(categories))
    r2 = [x + bar_width for x in r1]
    r3 = [x + bar_width for x in r2]
    
    # Create the three bar types
    plt.bar(r1, accuracies, width=bar_width, label='Overall Accuracy', color='forestgreen')
    plt.bar(r2, evidence_accuracies, width=bar_width, label='Evidence Accuracy', color='royalblue')
    plt.bar(r3, testimony_accuracies, width=bar_width, label='Testimony Accuracy', color='darkorange')
    
    plt.title(f'{MODEL.split("/")[-1]}: Accuracy by Category', pad=20)
    plt.xlabel('Category')
    plt.ylabel('Accuracy')
    plt.ylim(0, 1.1)  # Set y-axis from 0 to 1.1 to accommodate labels
    
    # Add category labels at appropriate positions
    plt.xticks([r + bar_width for r in range(len(categories))], categories, rotation=45, ha='right')
    
    # Add accuracy values above bars
    for i in range(len(categories)):
        plt.text(r1[i], accuracies[i] + 0.02, f'{accuracies[i]:.1%}', ha='center', va='bottom', fontsize=8)
        plt.text(r2[i], evidence_accuracies[i] + 0.02, f'{evidence_accuracies[i]:.1%}', ha='center', va='bottom', fontsize=8)
        plt.text(r3[i], testimony_accuracies[i] + 0.02, f'{testimony_accuracies[i]:.1%}', ha='center', va='bottom', fontsize=8)
    
    plt.legend()
    plt.tight_layout()
    
    plt.savefig(os.path.join(output_dir, 'report_category_accuracies.png'))
    plt.close()

def plot_reasoning_accuracies(reasoning_correct):
    steps = list(reasoning_correct.keys())
    totals = [data['total'] for data in reasoning_correct.values()]
    
    # Get all three accuracy metrics
    accuracies = [data['accuracy'] for data in reasoning_correct.values()]
    evidence_accuracies = [data['evidence_accuracy'] for data in reasoning_correct.values()]
    testimony_accuracies = [data['testimony_accuracy'] for data in reasoning_correct.values()]
    
    plt.figure(figsize=(14, 7))
    
    # Convert steps to strings to prevent numerical interpolation on x-axis
    step_labels = [str(step) for step in steps]
    
    # Set width and positions
    bar_width = 0.25
    r1 = np.arange(len(steps)) - bar_width
    r2 = np.arange(len(steps))
    r3 = np.arange(len(steps)) + bar_width
    
    # Create three bar types
    plt.bar(r1, accuracies, width=bar_width, label='Overall Accuracy', color='forestgreen')
    plt.bar(r2, evidence_accuracies, width=bar_width, label='Evidence Accuracy', color='royalblue')
    plt.bar(r3, testimony_accuracies, width=bar_width, label='Testimony Accuracy', color='darkorange')

    plt.title(f'{MODEL.split("/")[-1]}: Accuracy by Number of Reasoning Steps')
    plt.xlabel('Number of Reasoning Steps')
    plt.ylabel('Accuracy')
    plt.ylim(0, 1.1)
    
    # Add accuracy values above bars
    for i in range(len(steps)):
        plt.text(r1[i], accuracies[i] + 0.02, f'{accuracies[i]:.1%}', ha='center', va='bottom', fontsize=8)
        plt.text(r2[i], evidence_accuracies[i] + 0.02, f'{evidence_accuracies[i]:.1%}', ha='center', va='bottom', fontsize=8)
        plt.text(r3[i], testimony_accuracies[i] + 0.02, f'{testimony_accuracies[i]:.1%}', ha='center', va='bottom', fontsize=8)
    
    plt.legend()
    plt.xticks(r2, step_labels)  # Use string labels at positions r2 (middle bars)
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(os.path.join(output_dir, 'report_reasoning_steps_accuracies.png'))
    plt.close()

def plot_difficulty_accuracies(difficulty_correct):
    difficulty_correct = {str(k): v for k, v in difficulty_correct.items()}
    difficulties = list(difficulty_correct.keys())
    totals = [data['total'] for data in difficulty_correct.values()]
    
    # Get all three accuracy metrics
    accuracies = [data['accuracy'] for data in difficulty_correct.values()]
    evidence_accuracies = [data['evidence_accuracy'] for data in difficulty_correct.values()]
    testimony_accuracies = [data['testimony_accuracy'] for data in difficulty_correct.values()]
    
    # Dynamic figsize based on number of difficulties
    num_difficulties = len(difficulties)
    width = max(8, num_difficulties * 2.5)  # Increased width to accommodate 3 bars per category
    plt.figure(figsize=(width, 7))
    
    # Set width and positions
    bar_width = 0.25
    x = np.arange(len(difficulties))
    r1 = x - bar_width
    r2 = x
    r3 = x + bar_width
    
    # Create three bar types
    plt.bar(r1, accuracies, width=bar_width, label='Overall Accuracy', color='forestgreen')
    plt.bar(r2, evidence_accuracies, width=bar_width, label='Evidence Accuracy', color='royalblue')
    plt.bar(r3, testimony_accuracies, width=bar_width, label='Testimony Accuracy', color='darkorange')

    plt.title('Accuracy by Sizes of Action Space')
    plt.xlabel('Sizes of Action Space')
    plt.ylabel('Accuracy')
    plt.ylim(0, 1.1)  # Set y-axis from 0 to 1.1 to accommodate labels
    
    # Add accuracy values above bars
    for i in range(len(difficulties)):
        plt.text(r1[i], accuracies[i] + 0.02, f'{accuracies[i]:.1%}', ha='center', va='bottom', fontsize=8)
        plt.text(r2[i], evidence_accuracies[i] + 0.02, f'{evidence_accuracies[i]:.1%}', ha='center', va='bottom', fontsize=8)
        plt.text(r3[i], testimony_accuracies[i] + 0.02, f'{testimony_accuracies[i]:.1%}', ha='center', va='bottom', fontsize=8)
    
    plt.legend()
    plt.xticks(x, difficulties)  # Set x-ticks at the correct positions with difficulty labels
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(os.path.join(output_dir, 'report_action_space_accuracies.png'))
    plt.close()

def evaluate(caseids, preds, golds_indices, golds_names, verbose=False):
    def vprint(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)
    evidences_by_case = get_evidences_by_case(caseids)  # key: caseid, value: {'evidences': [], 'characters': []}
    testimonies_by_case = get_testimonies_by_case(caseids)  # key: caseid, value: [["test1, test2"], ["test1"], ["test1"]]
    labels_by_case = get_labels_by_case(caseids) # key: caseid, value: [{"labels": [], "reasoning": []}, {"labels": [], "reasoning": []}..]

    report_json = {
            'model': MODEL,
            'prompt': PROMPT,
            'case': CASE,
            'overall_correct': -1,
            'overall_correct_evidence': -1,
            'overall_correct_testimony': -1,
            'overall_total': -1,
            'overall_accuracy': -1,
            'overall_evidence_accuracy': -1,
            'overall_testimony_accuracy': -1,
            'categories_accuracy': {},
            'reasoning_steps_accuracy': {},
            'action_space_accuracy': {},
            "case_details": {}
    }
    overall_correct = 0
    overall_total = 0
    overall_correct_evidence = 0
    overall_correct_testimony = 0
    categories = list(set([turn_category 
                for turns_label in labels_by_case.values() 
                for turn_label in turns_label
                for turn_category in turn_label["labels"]]))

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
        idx: {
            "correct": 0, 
            'evidence_correct': 0,
            'testimony_correct': 0,
            "total": 0, 
            "accuracy": 0, 
            'evidence_accuracy': 0,
            'testimony_accuracy': 0,
            "bad_cases": []
        } 
        for idx in range(1, 10)
    }
    difficulty_correct = {}

    for caseid, pred, gold_indices, gold_names \
        in zip(caseids, preds, golds_indices, golds_names):  # num of cases
        vprint(caseid)
        vprint(pred)
        vprint(gold_indices)
        report_json["case_details"][caseid] = {
            "case_accuracy": -1,
            "turns": []
        }
        case_correct = 0
        case_evidence_correct = 0
        case_testimony_correct = 0
        case_total = 0
        for i in range(len(gold_indices)):  # num of turns for each case
            # Compute standard accuracy
            is_correct = False
            is_evidence_correct = False
            is_testimony_correct = False
            # print(f"{caseid} - {i} - {pred[i]}")
            if pred[i] in gold_indices[i]:  
                is_correct = True
                case_correct += 1
            if "evidence" in pred[i] and any(pred[i]["evidence"] == gold_indices[i][j]["evidence"] for j in range(len(gold_indices[i]))):
                is_evidence_correct = True
                case_evidence_correct += 1
            elif 'character' in pred[i] or 'evidence' not in pred[i]:
                print(f"{caseid} pred[{i}] missing evidence: {pred[i]}")

            if "testimony" in pred[i] and any(pred[i]["testimony"] == gold_indices[i][j]["testimony"] for j in range(len(gold_indices[i]))):
                is_testimony_correct = True
                case_testimony_correct += 1
            elif "testimony" not in pred[i]:
                print(f"{caseid} pred[{i}] missing testimony: {pred[i]}")

            case_total += 1

            # Compute category accuracy
            turn_labels = labels_by_case[caseid][i]["labels"]  # Return empty list if none            
            for label in turn_labels:
                categories_correct[label]["total"] += 1
                if is_correct:
                    categories_correct[label]["correct"] += 1
                else:
                    categories_correct[label]["bad_cases"].append(f"{caseid}_{i}")

                if is_evidence_correct:
                    categories_correct[label]['evidence_correct'] += 1
                if is_testimony_correct:
                    categories_correct[label]['testimony_correct'] += 1

            # Compute reasoning accuracy
            turn_reasoning = labels_by_case[caseid][i]["reasoning"]  # Return empty list if none
            turn_n_reasoning = len(turn_reasoning)
            if turn_n_reasoning > 0:
                reasoning_correct[turn_n_reasoning]["total"] +=1
                if is_correct:
                    reasoning_correct[turn_n_reasoning]["correct"] += 1
                else:
                    reasoning_correct[turn_n_reasoning]["bad_cases"].append(f"{caseid}_{i}")

                if is_evidence_correct:
                    reasoning_correct[turn_n_reasoning]['evidence_correct'] += 1
                if is_testimony_correct:
                    reasoning_correct[turn_n_reasoning]['testimony_correct'] += 1

            # Compute difficulty accuracy
            n_evidences = len(evidences_by_case[caseid]["evidences"])
            n_testimonies = len(testimonies_by_case[caseid][i])
            difficulty = max(math.ceil((n_evidences * n_testimonies) / 20), 5)

            if difficulty not in difficulty_correct.keys():
                difficulty_correct[difficulty] = {
                    "correct": 0, 
                    'evidence_correct': 0,
                    'testimony_correct': 0,
                    "total": 0, 
                    "accuracy": 0, 
                    'evidence_accuracy': 0,
                    'testimony_accuracy': 0,
                    "bad_cases": []
                }
            difficulty_correct[difficulty]["total"] += 1
            if is_correct:
                difficulty_correct[difficulty]["correct"] += 1
            else:
                difficulty_correct[difficulty]["bad_cases"].append(f"{caseid}_{i}")

            if is_evidence_correct:
                difficulty_correct[difficulty]["evidence_correct"] += 1
            if is_testimony_correct:
                difficulty_correct[difficulty]["testimony_correct"] += 1

            try:
                if not pred[i]:
                    out_pred = {
                        "evidence_id": -1,
                        "evidence": "N/A",
                        "testimony_id": -1,
                        "testimony": "N/A"
                    }
                elif "evidence" in pred[i]:
                    out_pred = {
                        "evidence_id": pred[i]["evidence"],
                        "evidence": evidences_by_case[caseid]["evidences"][pred[i]["evidence"]] if pred[i]["evidence"] < len(evidences_by_case[caseid]["evidences"]) else "N/A",
                        "testimony_id": pred[i]["testimony"],
                        "testimony": testimonies_by_case[caseid][i][pred[i]["testimony"]] if pred[i]["testimony"] < len(testimonies_by_case[caseid][i]) else "N/A"
                    }
                elif "character" in pred[i]:
                    print(f"caseid {caseid} {i} has character in pred")
                    out_pred = {
                        "character_id": pred[i]["character"],
                        "character": evidences_by_case[caseid]["characters"][pred[i]["character"]] if pred[i]["character"] < len(evidences_by_case[caseid]["characters"]) else "N/A",
                        "testimony_id": pred[i]["testimony"],
                        "testimony": testimonies_by_case[caseid][i][pred[i]["testimony"]] if pred[i]["testimony"] < len(testimonies_by_case[caseid][i]) else "N/A"
                    }
            except Exception:
                print(f"{caseid} - {i} - {pred[i]}")
                traceback.print_exc()
                out_pred = {
                    "evidence_id": -1,
                    "evidence": "N/A",
                    "testimony_id": -1,
                    "testimony": "N/A"
                }
            

            report_json["case_details"][caseid]["turns"].append({
                "gold": [{
                    "evidence_id": a["evidence"],
                    "evidence": b["evidence"],
                    "testimony_id": a["testimony"],
                    "testimony": b["testimony"]
                } if "evidence" in a else {
                    "character_id": a["character"],
                    "character": b["character"],
                    "testimony_id": a["testimony"],
                    "testimony": b["testimony"]
                } for a,b in zip(gold_indices[i], gold_names[i])],
                "pred": out_pred
            })

        vprint(f"Case accuracy: {case_correct / case_total}")
        report_json["case_details"][caseid]["case_accuracy"] = round(case_correct / case_total, 4)
        overall_correct += case_correct
        overall_total += case_total
        overall_correct_evidence += case_evidence_correct
        overall_correct_testimony += case_testimony_correct

    report_json['overall_correct'] = overall_correct
    report_json['overall_total'] = overall_total
    report_json["overall_accuracy"] = round(overall_correct / overall_total, 4)
    vprint(f"Overall accuracy: {overall_correct / overall_total}")

    report_json['overall_correct_evidence'] = overall_correct_evidence
    report_json['overall_correct_testimony'] = overall_correct_testimony
    report_json['overall_evidence_accuracy'] = round(overall_correct_evidence / overall_total, 4)
    report_json['overall_testimony_accuracy'] = round(overall_correct_testimony / overall_total, 4)

    # Log category accuracy
    # if "" in categories_correct.keys():
    #     print(f"Found typo: ")
    #     categories_correct[" "]["total"] += categories_correct[" "]["total"]  # Handle typos
    #     categories_correct[" "]["correct"] += categories_correct[" "]["correct"] 
    #     del categories_correct[" "]
    categories_correct = {
        label: {
            **stats, 
            "accuracy": round(stats["correct"] / stats["total"], 4),
            "evidence_accuracy": round(stats["evidence_correct"] / stats["total"], 4),
            "testimony_accuracy": round(stats["testimony_correct"] / stats["total"], 4)
        }
        for label, stats in categories_correct.items()
    }
    categories_correct = dict(sorted(categories_correct.items()))  # First sort for visualization
    report_json["categories_accuracy"] = categories_correct

    # Log reasoning step accuracy
    reasoning_correct = {
        label: {
            **stats, 
            "accuracy": round(stats["correct"] / stats["total"], 4),
            "evidence_accuracy": round(stats["evidence_correct"] / stats["total"], 4),
            "testimony_accuracy": round(stats["testimony_correct"] / stats["total"], 4)
        }
        for label, stats in reasoning_correct.items()
        if stats["total"] > 0
    }
    reasoning_correct = dict(sorted(reasoning_correct.items()))
    report_json["reasoning_steps_accuracy"] = reasoning_correct

    # Log difficulty accuracy
    difficulty_correct = {
        (difficulty * 20): {
            **stats, 
            "accuracy": round(stats["correct"] / stats["total"], 4),
            "evidence_accuracy": round(stats["evidence_correct"] / stats["total"], 4),
            "testimony_accuracy": round(stats["testimony_correct"] / stats["total"], 4)
        }
        for difficulty, stats in difficulty_correct.items()
        if stats["total"] > 0
    }
    difficulty_correct = dict(sorted(difficulty_correct.items()))
    report_json["action_space_accuracy"] = difficulty_correct

    # Log json
    if CASE != "ALL":
        return
    with open(os.path.join(output_dir, f"report.json"), 'w') as f:
        json.dump(report_json, f, indent=2)

    # Plot
    plot_category_accuracies(categories_correct)
    plot_reasoning_accuracies(reasoning_correct)
    plot_difficulty_accuracies(difficulty_correct)

if __name__ == "__main__":
    all_caseids = [n.split('.')[0] for n in sorted(os.listdir(data_dir)) if not n.startswith(('4-', '5-', '6-'))]
    if CASE == "ALL":
        caseids = all_caseids
    else:
        for caseid in all_caseids:
            if caseid.startswith(CASE):
                caseids = [caseid]
    preds = []
    golds_indices = []
    golds_names = []
    caseids_final = []
    for i, caseid in enumerate(caseids):
        pred_path = os.path.join(output_dir, caseid + ".jsonl")
        if not os.path.exists(pred_path):
            # print(f"{caseid.split('_')[0]} does not exist. Skipping...")
            continue

        if int((caseid.split("_")[0]).split("-")[-1]) % 2 == 1:  # Skip odd cases
            continue

        pred = parse_pred(caseid)
        gold_indices, gold_names = parse_gold(caseid)
        if len(pred) != len(gold_indices):
            print(f"Case {caseid.split('_')[0]}, num of pred: {len(pred)} is not equal to num of turn: {len(gold_indices)}. Skipping...\n")
            continue

        caseids_final.append(caseid)
        preds.append(pred)  # List of dicts
        golds_indices.append(gold_indices)  # List of list of dicts
        golds_names.append(gold_names)
    
    caseids = caseids_final
    print(f"Evaluating {len(caseids)} court days...")
    evaluate(caseids, preds, golds_indices, golds_names)
