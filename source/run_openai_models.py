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

from run_models import (
    parse_json, 
    build_prompt, 
    build_prompt_prefix_suffix, 
    get_fnames, 
    get_output_dir
)

parser = argparse.ArgumentParser(description='')
parser.add_argument('-m', '--model', type=str, help='gpt-4o-mini, o3-mini')
parser.add_argument('-p', '--prompt', type=str)
parser.add_argument('--context', type=str, help='If none, run with no context; if new, run with new context; if day, run...')
parser.add_argument('-c', '--case', type=str, help='If ALL, run all cases; if a case number like 3-4-1, run that case; if a case number followed by a "+" like 3-4-1+, run that case and all cases after it.')

# python run_openai_models.py --model o3-mini --prompt harry_v1.3

args = parser.parse_args()
MODEL = args.model
PROMPT = args.prompt
CASE = args.case if args.case else "ALL"
CONTEXT = args.context if args.context else None

PROMPT_PREFIX, PROMPT_SUFFIX = build_prompt_prefix_suffix(PROMPT)

def create_batch(fnames):
    max_token_key = "max_tokens" if "gpt" in MODEL else "max_completion_tokens"
    max_token_val = 1000 if "gpt" in MODEL else 5000
    batch = []
    for fname in fnames:
        turns, prev_context = parse_json(os.path.join(data_dir, fname))
        prompts = build_prompt(turns, prev_context)
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

    output_dir = get_output_dir()
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(os.path.join(output_dir, 'metadata.json'), 'w') as file:
        json.dump({
            'model': MODEL,
            'prompt': PROMPT,
            'case': CASE,
            'timestamp': timestamp
        }, file, indent=2)

    fnames = get_fnames(data_dir, output_dir)

    batch = create_batch(fnames)
    # print(batch[0])
    # print(batch[1])
    # import sys; sys.exit()

    jsonl_path = os.path.join(output_dir, "batchinput.jsonl")
    with open(jsonl_path, "w") as f:
        for request in batch:
            f.write(json.dumps(request, ensure_ascii=False) + "\n")
    
    batch_job_id = submit_batch_job(jsonl_path)