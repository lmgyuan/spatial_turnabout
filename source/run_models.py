import json
import os
from kani import Kani
from kani.engines.huggingface import HuggingEngine
import asyncio
import argparse
from datetime import datetime

parser = argparse.ArgumentParser(description='')
parser.add_argument('--model', type=str, help='model name')
parser.add_argument('--prompt', type=str)
parser.add_argument('--context', type=str, help='If none, run with no context; if new, run with new context; if day, run...')
parser.add_argument('--case', type=str, help='If ALL, run all cases; if a case number like 3-4-1, run that case; if a case number followed by a "+" like 3-4-1+, run that case and all cases after it.')

# python run_models.py --model deepseek-ai/DeepSeek-R1-Distill-Llama-8B --prompt harry_v1.2

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
            #break
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

def run_model(prompts):
    answer_jsons = []
    full_responses = []
    for prompt in prompts:
        #print(prompt)
        async def run_model():
            response = await ai.chat_round_str(prompt, temperature=0.6)
            #print(response)
            return response

        response = asyncio.run(run_model())
        def get_last_line(multiline_string):
            lines = multiline_string.splitlines()
            return lines[-1] if lines else ""
        answer_json = get_last_line(response)
        answer_jsons.append(answer_json)
        full_responses.append(response)
    return answer_jsons, full_responses


if __name__ == "__main__":
    data_dir = '../data/aceattorney_data/final'
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f'../output/{MODEL.split("/")[-1]}_{PROMPT}'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(os.path.join(output_dir, 'metadata.json'), 'w') as file:
        json.dump({
            'model': MODEL,
            'prompt': PROMPT,
            'case': CASE,
            'timestamp': timestamp
        }, file, indent=2)
    engine = HuggingEngine(model_id = MODEL, use_auth_token=True, model_load_kwargs={"device_map": "auto"})
    ai = Kani(engine, system_prompt="")
    all_fnames = sorted(os.listdir(data_dir))
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
    for fname in fnames:
        if fname.startswith(('4-', '5-', '6-')):  # Skip validation set
            continue
        if int((fname.split("_")[0]).split("-")[-1]) % 2 == 1:  # Skip odd cases
            continue
        if os.path.exists(os.path.join(output_dir, fname.split('.')[0] + '.jsonl')):
            print(f"Skipping existing outputs {fname.split('.')[0] + '.jsonl'}")
            continue
        print(fname)
        turns = parse_json(os.path.join(data_dir, fname))
        prompts = build_prompt(turns)
        # print(prompts)
        answer_jsons, full_responses = run_model(prompts)
        for answer_json in answer_jsons:
            print(answer_json)
        with open(os.path.join(output_dir, fname.split('.')[0] + '.jsonl'), 'w') as file:
            for answer_json in answer_jsons:
                file.write(answer_json + "\n")
        with open(os.path.join(output_dir, fname.split('.')[0] + '_full_responses.txt'), 'w') as file:
            for response in full_responses:
                file.write(response + "\n")