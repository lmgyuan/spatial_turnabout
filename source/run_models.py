import json
import os
from kani import Kani
from kani.engines.huggingface import HuggingEngine
import asyncio
import argparse

parser = argparse.ArgumentParser(description='')
parser.add_argument('--model', type=str, help='model name')
parser.add_argument('--prompt', type=str)
parser.add_argument('--case', type=str)

args = parser.parse_args()
MODEL = args.model
PROMPT_FILE = args.prompt + ".json"
CASE = args.case if args.case else "ALL"

with open("prompts/" + PROMPT_FILE, 'r') as file:
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
            testimonies = []
            for testimony in turn.get('testimonies', []):
                testimonies.append(testimony)
            turns.append({
                'characters': characters,
                'evidences': evidences,
                'testimonies': testimonies
            })
            #break
        return turns

def build_prompt(turns):
    prompts = []
    for turn in turns:
        prompt = ""
        evidence_counter = 0
        for evidence in turn['evidences']:
            prompt += f"Evidence {evidence_counter}\n"
            prompt += f"Name: {evidence['name']}\n"
            prompt += f"Description: {evidence['description1']}\n"
            evidence_counter += 1
        testimony_counter = 0
        for testimony in turn['testimonies']:
            prompt += f"Testimony {testimony_counter}\n"
            prompt += f"Testimony: {testimony['testimony']}\n"
            prompt += f"Person: {testimony['person']}\n"
            testimony_counter += 1
        prompts.append(prompt_prefix + prompt + prompt_suffix)

    return prompts

def run_model(model, prompts):
    answer_jsons = []
    for prompt in prompts:
        #print(prompt)
        engine = HuggingEngine(model_id = model, use_auth_token=True, model_load_kwargs={"device_map": "auto"})
        ai = Kani(engine, system_prompt="")

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
    return answer_jsons


if __name__ == "__main__":
    data_dir = '../data/aceattorney_data/final'
    output_dir = f'../output/{MODEL.split("/")[-1]}_{PROMPT_FILE}'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    all_fnames = sorted(os.listdir(data_dir))
    if CASE == "ALL":
        fnames = sorted(os.listdir(data_dir))
    else:
        for fname in all_fnames:
            if fname.startswith(CASE):
                fnames = [fname]
    for fname in fnames:
        print(fname)
        turns = parse_json(os.path.join(data_dir, fname))
        prompts = build_prompt(turns)
        #print(prompts)
        answer_jsons = run_model(MODEL, prompts)
        for answer_json in answer_jsons:
            print(answer_json)
        with open(os.path.join(output_dir, fname.split('.')[0] + '.jsonl'), 'w') as file:
            for answer_json in answer_jsons:
                file.write(answer_json + "\n")