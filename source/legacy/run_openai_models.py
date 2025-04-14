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
    get_output_dir,
    parse_arguments,
)

# python run_openai_models.py --model o3-mini --prompt harry_v1.3 

if __name__ == "__main__":
    args = parse_arguments()
    MODEL = args.model
    PROMPT = args.prompt
    CASE = args.case if args.case else "ALL"
    CONTEXT = args.context
    NO_DESCRIPTION = args.no_description   

    data_dir = '../data/aceattorney_data/final'
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_dir = get_output_dir(MODEL, PROMPT, CONTEXT, CASE, NO_DESCRIPTION)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(os.path.join(output_dir, 'metadata.json'), 'w') as file:
        json.dump({
            'model': MODEL,
            'prompt': PROMPT,
            'case': CASE,
            'timestamp': timestamp
        }, file, indent=2)

    fnames = get_fnames(data_dir, output_dir, CASE)

    batch = create_batch(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION)
    # print(batch[0])
    # print(batch[1])
    # import sys; sys.exit()

    jsonl_path = os.path.join(output_dir, "batchinput.jsonl")
    with open(jsonl_path, "w") as f:
        for request in batch:
            f.write(json.dumps(request, ensure_ascii=False) + "\n")
    
    batch_job_id = submit_batch_job(jsonl_path)