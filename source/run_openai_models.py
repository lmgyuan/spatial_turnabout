import json
import os
import argparse
from datetime import datetime
import time
from dotenv import load_dotenv

load_dotenv("../.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

from openai import OpenAI
client = OpenAI(
    api_key=OPENAI_API_KEY
)

parser = argparse.ArgumentParser(description='')
parser.add_argument('--model', type=str, default='o3-mini', help='model name')
parser.add_argument('--prompt', type=str)
parser.add_argument('--context', type=str, help='If none, run with no context; if new, run with new context; if day, run...')
parser.add_argument('--case', type=str, help='If ALL, run all cases; if a case number like 3-4-1, run that case; if a case number followed by a "+" like 3-4-1+, run that case and all cases after it.')

# python run_openai_models.py --model gpt-4o-mini --prompt harry_v1.2

args = parser.parse_args()
MODEL = args.model
PROMPT = args.prompt
CASE = args.case if args.case else "ALL"

with open("prompts/" + PROMPT + ".json", 'r') as file:
    # parse json
    data = json.load(file)
    prompt_prefix = data['prefix']
    prompt_suffix = data['suffix']

def parse_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        characters = []
        evidences = []
        for character in data.get('characters', {}):
            characters.append(character)
        for evidence in data.get('evidences', {}):
            evidences.append(evidence)
        turns = []
        for turn in data["turns"]:
            if turn["noPresent"]:
                continue
            testimonies = []
            for testimony in turn['testimonies']:
                testimonies.append(testimony)
            turns.append({
                'characters': characters,
                'evidences': evidences,
                'testimonies': testimonies,
                'new_context': turn['newContext']
            })
        # [{
        #     'characters': [],
        #     'evidences': [],
        #     'testimonies': [],
        #     'new_context': " "
        # }, {}, {}, ]
        return turns

def build_prompt(turns):
    prompts = []
    context_sofar = ""
    for turn in turns:
        new_context = turn['new_context']
        context_sofar += new_context
        if args.context == "none":
            prompt = ""
        else:
            prompt = "Story:\n"
            if args.context == "new":
                prompt += new_context + "\n"
            elif args.context == "day":
                prompt += context_sofar + "\n"
        character_counter = 0
        prompt += "Characters:\n"
        for character in turn['characters']:
            prompt += f"Character {character_counter}\n"
            prompt += f"Name: {character['name']}\n"
            prompt += f"Description: {character['description1']}\n"
            character_counter += 1
        evidence_counter = 0
        prompt += "Evidences:\n"
        for evidence in turn['evidences']:
            prompt += f"Evidence {evidence_counter}\n"
            prompt += f"Name: {evidence['name']}\n"
            prompt += f"Description: {evidence['description1']}\n"
            evidence_counter += 1
        testimony_counter = 0
        prompt += "Testimonies:\n"
        for testimony in turn['testimonies']:
            prompt += f"Testimony {testimony_counter}\n"
            prompt += f"Testimony: {testimony['testimony']}\n"
            prompt += f"Person: {testimony['person']}\n"
            testimony_counter += 1
        prompts.append(prompt_prefix + prompt + prompt_suffix)
    return prompts

def create_batch(fnames):
    batch = []
    for fname in fnames:
        # print(fname)
        if fname.startswith('4-'):  # Skip validation set
            continue
        turns = parse_json(os.path.join(data_dir, fname))
        prompts = build_prompt(turns)
        # print(prompts)
        for i, prompt in enumerate(prompts):
            request = {
                "custom_id": f"{fname.split('.')[0]}_{i}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."}, 
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1000
                }
            }
            batch.append(request)
    
    assert len(batch) > 0, "Must have at least 1 batch item"
    return batch

def submit_batch_job(jsonl_path):
    batch_input_file = client.files.create(
        file=open(jsonl_path, "rb"),
        purpose="batch"
    )
    batch_input_file_id = batch_input_file.id

    batch_job = client.batches.create(
        input_file_id=batch_input_file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "description": "turnabout llm"
        }
    )
    batch_job_id = batch_job.id
    with open(os.path.join(output_dir, "batch_api_metadata.json"), "w") as f:
        f.write(json.dumps({"batch_job_id": batch_job_id}, indent=4))

    return batch_job_id

if __name__ == "__main__":
    data_dir = '../data/aceattorney_data/final'
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f'../output/{MODEL}_{PROMPT}'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(os.path.join(output_dir, 'metadata.json'), 'w') as file:
        json.dump({
            'model': MODEL,
            'prompt': PROMPT,
            'case': CASE,
            'timestamp': timestamp
        }, file, indent=2)
    all_fnames = sorted([
        fname for fname 
        in os.listdir(data_dir) 
        if not fname.startswith(('4-', '5-', '6-')) and not int((fname.split("_")[0]).split("-")[-1]) % 2 == 1
    ])
    print(all_fnames)
    import sys; sys.exit(0)
    fnames = []
    if CASE == "ALL":
        fnames = all_fnames
    else:
        for i, fname in enumerate(all_fnames):
            if fname.startswith(CASE.strip('+')):
                if CASE.endswith('+'):
                    fnames = all_fnames[i:]
                else:
                    fnames = [fname]
                break

    batch = create_batch(fnames)
    print(batch[0])
    print(batch[1])
    validation = input("Is the batch format ok? [yes/no]")
    if validation != "yes":
        print("Terminating batch job...")
        import sys; sys.exit(0)
    
    jsonl_path = os.path.join(output_dir, "batchinput.jsonl")
    with open(jsonl_path, "w") as f:
        for request in batch:
            f.write(json.dumps(request, ensure_ascii=False) + "\n")
    
    batch_job_id = submit_batch_job(jsonl_path)

    # Initial check
    batch_job = client.batches.retrieve(batch_job_id)
    status = batch_job["status"]
    if status in ["failed", "expired", "cancelling", "cancelled"]:
        print(f"Batch job {status}. Terminating...")
        import sys; sys.exit(0)

    max_tries = 24
    cur = 0
    success = False

    while cur < max_tries:
        cur += 1
        time.sleep(3600)
        print(f"Attempting tries: {cur+1}")
        batch_job = client.batches.retrieve(batch_job_id)
        status = batch_job.status
        if status == "completed":
            success = True
            break
        elif status in ["failed", "expired", "cancelling", "cancelled"]:
            break
    if success:
        print(f"Batch job {status}. Writing ...")
        result_file_id = batch_job.output_file_id
        result = client.files.content(result_file_id).content

        result_file_name = os.path.join(output_dir, "batchoutput.jsonl")

        with open(result_file_name, 'wb') as file:
            file.write(result)

    else:
        print(f"Batch job {status}. Terminating...")