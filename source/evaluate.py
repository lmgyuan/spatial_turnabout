import json
import os
import argparse

parser = argparse.ArgumentParser(description='')
parser.add_argument('--model', type=str, help='model name')
parser.add_argument('--prompt', type=str)
parser.add_argument('--case', type=str)

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
    gold = []
    with open(os.path.join(data_dir, caseid + ".json"), 'r') as f:
        data = json.load(f)
        evidences = [evidence['name'] for evidence in data['evidences']]
        characters = [character['name'] for character in data['characters']]
        for turn in data['turns']:
            correct_pairs = []
            if turn["noPresent"]:
                gold.append({"evidence": -1, "testimony": -1})
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
                        correct_pairs.append({evidence_type: correct_evidence_index, "testimony": correct_testimony_index})
            gold.append(correct_pairs)
    return gold

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

def evaluate(caseids, preds, golds, verbose=False):
    def vprint(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)
    evidences_by_case = get_evidences_by_case(caseids)
    testimonies_by_case = get_testimonies_by_case(caseids)
    report_json = {
            'model': MODEL,
            'prompt': PROMPT,
            'case': CASE,
            'overall_accuracy': -1,
            "case_details": {}
    }
    overall_correct = 0
    overall_total = 0
    for caseid, pred, gold in zip(caseids, preds, golds):
        vprint(caseid)
        vprint(pred)
        vprint(gold)
        report_json["case_details"][caseid] = {
            "case_accuracy": -1,
            "turns": []
        }
        case_correct = 0
        case_total = 0
        for i in range(len(gold)):
            try:
                for pair in pred[i]:
                    if pair in gold[i]:
                        case_correct += 1
            except IndexError:
                pass
            case_total += 1
            """
            gold_with_names = []
            for possibility in gold[i]:
                try:
                    if "evidence" in possibility:
                        print(testimonies_by_case[caseid][i])
                        print(possibility["testimony"])
                        gold_with_names.append({
                            "evidence": evidences_by_case[caseid]["evidences"][possibility["evidence"]],
                            "testimony": testimonies_by_case[caseid][i][possibility["testimony"]]
                        })
                    elif "character" in possibility:
                        gold_with_names.append({
                            "character": evidences_by_case[caseid]["characters"][possibility["character"]],
                            "testimony": testimonies_by_case[caseid][i][possibility["testimony"]]
                        })
                except TypeError:
                    gold_with_names.append({
                        "evidence": "N/A",
                        "testimony": "N/A"
                    })
            """
            report_json["case_details"][caseid]["turns"].append({
                "gold": gold[i],
                "pred": pred[i] if i < len(pred) else []
            })
        vprint(f"Case accuracy: {case_correct / case_total}")
        report_json["case_details"][caseid]["case_accuracy"] = case_correct / case_total
        overall_correct += case_correct
        overall_total += case_total

    report_json["overall_accuracy"] = overall_correct / overall_total
    vprint(f"Overall accuracy: {overall_correct / overall_total}")

    if CASE != "ALL":
        return
    with open(os.path.join(output_dir, f"report.json"), 'w') as f:
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
    golds = []
    for caseid in caseids:
        pred = parse_pred(caseid)
        gold = parse_gold(caseid)
        preds.append(pred)
        golds.append(gold)
    evaluate(caseids, preds, golds)
