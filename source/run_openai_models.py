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

from run_models import parse_json, build_prompt, build_prompt_prefix_suffix

parser = argparse.ArgumentParser(description='')
parser.add_argument('--model', type=str, help='gpt-4o-mini, o3-mini')
parser.add_argument('--prompt', type=str)
parser.add_argument('--context', type=str, help='If none, run with no context; if new, run with new context; if day, run...')
parser.add_argument('--case', type=str, help='If ALL, run all cases; if a case number like 3-4-1, run that case; if a case number followed by a "+" like 3-4-1+, run that case and all cases after it.')

# python run_openai_models.py --model o3-mini --prompt harry_v1.3

args = parser.parse_args()
MODEL = args.model
PROMPT = args.prompt
CASE = args.case if args.case else "ALL"

PROMPT_PREFIX, PROMPT_SUFFIX = build_prompt_prefix_suffix(PROMPT)

with open("prompts/" + PROMPT + ".json", 'r') as file:
    # parse json
    data = json.load(file)
    prompt_prefix = data['prefix']
    prompt_suffix = data['suffix']
# Load cot examples
if "one_shot" in PROMPT:
    with open("prompts/example_one_shot.txt", "r") as file:
        example_one_shot = file.read()
    prompt_prefix = prompt_prefix.format(example_one_shot=example_one_shot)
elif "few_shot" in PROMPT:
    with open("prompts/example_few_shot.txt", "r") as file:
        example_few_shot = file.read()
    prompt_prefix = prompt_prefix.format(example_few_shot=example_few_shot)

def create_batch(fnames):
    max_token_key = "max_tokens" if "gpt" in MODEL else "max_completion_tokens"
    max_token_val = 1000 if "gpt" in MODEL else 5000
    batch = []
    for fname in fnames:
        turns, data = parse_json(os.path.join(data_dir, fname))
        prompts = build_prompt(turns, data)
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
                    max_token_key: max_token_val
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
        f.write(json.dumps({
            "batch_job_id": batch_job_id, 
            "batch_file_id": batch_input_file_id
        }, indent=4))

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
    # print(all_fnames)
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
    # print(batch[0])
    # print(batch[1])
    jsonl_path = os.path.join(output_dir, "batchinput.jsonl")
    with open(jsonl_path, "w") as f:
        for request in batch:
            f.write(json.dumps(request, ensure_ascii=False) + "\n")
    
    batch_job_id = submit_batch_job(jsonl_path)