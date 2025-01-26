import json
import os
import argparse

parser = argparse.ArgumentParser(description='')
parser.add_argument('--model', type=str, help='model name')
parser.add_argument('--prompt', type=str)
parser.add_argument('--case', type=str)

args = parser.parse_args()
MODEL = args.model
PROMPT_FILE = args.prompt + ".json"
CASE = args.case if args.case else "ALL"

if __name__ == "__main__":
    data_dir = '../data/aceattorney_data/final'
    output_dir = f'../output/{MODEL.split("/")[-1]}_{PROMPT_FILE}'
    all_fnames = sorted(os.listdir(data_dir))
    if CASE == "ALL":
        fnames = sorted(os.listdir(data_dir))
    else:
        for fname in all_fnames:
            if fname.startswith(CASE):
                fnames = [fname]
    for fname in fnames:
        print(fname)
        # parse pred
        with open(os.path.join(output_dir, fname.split(".")[0] + ".jsonl"), 'r') as f:
            pred = []
            for line in f:
                pred.append(json.loads(line))
        # parse gold
        with open(os.path.join(data_dir, fname), 'r') as f:
            gold = []
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
        # evaluate
        correct = 0
        total = 0
        print(pred)
        print(gold)
        for i in range(len(pred)):
            for pair in pred[i]:
                if pair in gold[i]:
                    correct += 1
                total += 1
        print(f"Accuracy: {correct / total}")
