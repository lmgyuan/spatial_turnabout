import json
import os
import argparse

parser = argparse.ArgumentParser(description='')
parser.add_argument('--model', type=str, help='model name')
parser.add_argument('--prompt', type=str)
parser.add_argument('--case', type=str)

# python evaluate.py --model deepseek-ai/DeepSeek-R1-Distill-Llama-70B --prompt harry_v1

args = parser.parse_args()
MODEL = args.model
PROMPT = args.prompt
CASE = args.case if args.case else "ALL"

data_dir = '../data/aceattorney_data/final'
output_dir = f'../output/{MODEL.split("/")[-1]}_{PROMPT}'

def parse_pred(caseid):
    pred = []
    with open(os.path.join(output_dir, caseid + ".jsonl"), 'r') as f:
        for line in f:
            try:
                pred.append(json.loads(line))
            except json.JSONDecodeError:
                pred.append({})
    return pred

def parse_gold(caseid):
    gold_indices = []
    gold_names = []
    with open(os.path.join(data_dir, caseid + ".json"), 'r') as f:
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
                        try:
                            correct_evidence_index = evidences.index(correct_evidence_name)
                            evidence_type = "evidence"
                        except ValueError:
                            correct_evidence_index = characters.index(correct_evidence_name)
                            evidence_type = "character"
                        correct_testimony_index = i
                        correct_pairs_indices.append({evidence_type: correct_evidence_index, "testimony": correct_testimony_index})
                        correct_pairs_names.append({evidence_type: correct_evidence_name, "testimony": testimony["testimony"]})
            gold_indices.append(correct_pairs_indices)
            gold_names.append(correct_pairs_names)
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

def evaluate(caseids, preds, golds_indices, golds_names, verbose=False):
    def vprint(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)
    evidences_by_case = get_evidences_by_case(caseids)  # key: caseid, value: {'evidences': , 'characters': }
    testimonies_by_case = get_testimonies_by_case(caseids)  # key: caseid, value: [["test1, test2"], ["test1"], ["test1"]]
    labels_by_case = get_labels_by_case(caseids) # key: caseid, value: [{"labels": [], "reasoning": []}, {"labels": [], "reasoning": []}..]

    report_json = {
            'model': MODEL,
            'prompt': PROMPT,
            'case': CASE,
            'overall_accuracy': -1,
            'categories_accuracy': {},
            'reasoning_steps_accuracy': {},
            "case_details": {}
    }
    overall_correct = 0
    overall_total = 0
    categories = list(set([turn_category 
                for turns_label in labels_by_case.values() 
                for turn_label in turns_label
                for turn_category in turn_label["labels"]]))

    categories_correct = {label: {"correct": 0, "total": 0, "accuracy": 0, "bad_cases": []} for label in categories}
    reasoning_correct = {idx: {"correct": 0, "total": 0, "accuracy": 0, "bad_cases": []} for idx in range(1, 7)}

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
        case_total = 0
        for i in range(len(gold_indices)):  # num of turns for each case
            # Compute standard accuracy
            is_correct = False
            if pred[i] in gold_indices[i]:  
                is_correct = True
                case_correct += 1
            case_total += 1

            # Compute category accuracy
            turn_labels = labels_by_case[caseid][i]["labels"]  # Return empty list if none            
            for label in turn_labels:
                categories_correct[label]["total"] += 1
                if is_correct:
                    categories_correct[label]["correct"] += 1
                else:
                    categories_correct[label]["bad_cases"].append(f"{caseid}_{i}")

            # Compute reasoning accuracy
            turn_reasoning = labels_by_case[caseid][i]["reasoning"]  # Return empty list if none
            turn_n_reasoning = len(turn_reasoning)
            if turn_n_reasoning > 0:
                reasoning_correct[turn_n_reasoning]["total"] +=1
                if is_correct:
                    reasoning_correct[turn_n_reasoning]["correct"] += 1
                else:
                    reasoning_correct[turn_n_reasoning]["bad_cases"].append(f"{caseid}_{i}")

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
                        "evidence": evidences_by_case[caseid]["evidences"][pred[i]["evidence"]],
                        "testimony_id": pred[i]["testimony"],
                        "testimony": testimonies_by_case[caseid][i][pred[i]["testimony"]] if pred[i]["testimony"] < len(testimonies_by_case[caseid][i]) else "N/A"
                    }
                elif "character" in pred[i]:
                    out_pred = {
                        "character_id": pred[i]["character"],
                        "character": evidences_by_case[caseid]["characters"][pred[i]["character"]],
                        "testimony_id": pred[i]["testimony"],
                        "testimony": testimonies_by_case[caseid][pred[i]["testimony"]]
                    }
            except TypeError:
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

    report_json["overall_accuracy"] = round(overall_correct / overall_total, 4)
    vprint(f"Overall accuracy: {overall_correct / overall_total}")

    for label in categories:
        accuracy = categories_correct[label]["correct"] / categories_correct[label]["total"]
        categories_correct[label]["accuracy"] = round(accuracy, 4)
    report_json["categories_accuracy"] = categories_correct

    for idx in reasoning_correct.keys():
        if reasoning_correct[idx]["total"] == 0:
            continue
        accuracy = reasoning_correct[idx]["correct"] / reasoning_correct[idx]["total"]
        reasoning_correct[idx]["accuracy"] = round(accuracy, 4)
    report_json["reasoning_steps_accuracy"] = reasoning_correct

    if CASE != "ALL":
        return
    with open(os.path.join(output_dir, f"report_v3.json"), 'w') as f:
        json.dump(report_json, f, indent=2)

if __name__ == "__main__":
    all_caseids = [n.split('.')[0] for n in sorted(os.listdir(data_dir))]
    if CASE == "ALL":
        caseids = all_caseids
    else:
        for caseid in all_caseids:
            if caseid.startswith(CASE):
                caseids = [caseid]
    preds = []
    golds_indices = []
    golds_names = []
    for caseid in caseids:
        pred = parse_pred(caseid)
        gold_indices, gold_names = parse_gold(caseid)
        preds.append(pred)  # List of dicts
        golds_indices.append(gold_indices)  # List of list of dicts
        golds_names.append(gold_names)
        if len(pred) != len(gold_indices):
            print(f"Case {caseid}, num of pred: {len(pred)} is not equal to num of turn: {len(gold_indices)}. Skipping...\n")
    evaluate(caseids, preds, golds_indices, golds_names)
