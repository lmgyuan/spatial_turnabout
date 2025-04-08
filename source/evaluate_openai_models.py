import os
from datetime import datetime
import json
import argparse

from evaluate import parse_gold, evaluate

from dotenv import load_dotenv
load_dotenv("../.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

from openai import OpenAI
client = OpenAI(
    api_key=OPENAI_API_KEY
)

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

def check_status(output_dir):
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

        result_file_name = os.path.join(output_dir, "batchoutput.jsonl")

        with open(result_file_name, 'wb') as file:
            file.write(result)

        return True

    return False

def parse_pred(caseid, data):
    caseid_base = os.path.join(data_dir, caseid + ".json")

    full_responses = []
    responses = []
    for line in data:
        if caseid in line["custom_id"]:
            full_response = line["response"]["body"]["choices"][0]["message"]["content"]
            try:
                last_line = full_response.splitlines()[-1]
                json_response = last_line[last_line.index("{") : last_line.index("}") + 1]
                response = json.loads(json_response)
            except Exception:
                try:
                    new_line = full_response.splitlines()[-2]
                    json_response = new_line[new_line.index("{") : new_line.index("}") + 1]
                    response = json.loads(json_response)
                except Exception:
                    response = {"evidence": -1, "testimony": -1}

            full_responses.append(full_response)
            responses.append(response)
    
    return responses, full_responses

if __name__ == "__main__":
    data_dir = '../data/aceattorney_data/final'
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f'../output/{MODEL}_{PROMPT}'

    ret = check_status(output_dir)

    if ret:
        # Load ground truths from data dir
        all_caseids = sorted([
            fname.split('.')[0] for fname 
            in os.listdir(data_dir) 
            if not fname.startswith(('4-', '5-', '6-')) and not int((fname.split("_")[0]).split("-")[-1]) % 2 == 1
        ])
        # print(all_fnames)
        caseids = []
        if CASE == "ALL":
            caseids = all_caseids
        else:
            for caseid in all_caseids:
                if caseid.startswith(CASE):
                    caseids = [caseid]

        # Load predictions from output dir
        with open(os.path.join(output_dir, "batchoutput.jsonl"), "r") as file:
            data = [json.loads(line) for line in file]
        
        preds = []
        golds_indices = []
        golds_names = []
        caseids_final = []
        
        for i, caseid in enumerate(caseids):
            pred, full_pred = parse_pred(caseid, data)
            gold_indices, gold_names = parse_gold(caseid)

            if len(pred) != len(gold_indices):
                print(f"Case {caseid.split('_')[0]}, num of pred: {len(pred)} is not equal to num of turn: {len(gold_indices)}. Skipping...\n")
                continue

            with open(os.path.join(output_dir, f"{caseid}_full_responses.txt"), "w") as f:
                for line in full_pred:
                    f.write(line + "\n" + "*" * 30 + "\n")
            
            with open(os.path.join(output_dir, f"{caseid}.jsonl"), "w") as f:
                for line in pred:
                    f.write(json.dumps(line) + "\n")

            caseids_final.append(caseid)
            preds.append(pred)  # List of dicts
            golds_indices.append(gold_indices)  # List of list of dicts
            golds_names.append(gold_names)
        
        caseids = caseids_final
        print(f"Evaluating {len(caseids)} court days...")
        evaluate(caseids, preds, golds_indices, golds_names)