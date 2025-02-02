import json
import os
from kani import Kani
from kani.engines.huggingface import HuggingEngine
import asyncio
import argparse
from datetime import datetime
from sentence_transformers import CrossEncoder
import torch
import math

parser = argparse.ArgumentParser(description='')
parser.add_argument('--model', type=str, help='model name')
parser.add_argument('--prompt', type=str)
parser.add_argument('--context', type=str, help='If none, run with no context; if new, run with new context; if day, run...')
parser.add_argument('--case', type=str, help='If ALL, run all cases; if a case number like 3-4-1, run that case; if a case number followed by a "+" like 3-4-1+, run that case and all cases after it.')
parser.add_argument('--extraction', action='store_true', help='Enable extraction mode')

args = parser.parse_args()
MODEL = args.model
PROMPT = args.prompt
CASE = args.case if args.case else "ALL"
EXTRACTION = args.extraction

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')

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

def prompt_extract(context, query, keep_ratio=0.5):
    sentences = context.split('\n')
    total_sentences = len(sentences)
    top_k = max(1, math.ceil(keep_ratio * total_sentences)) 
    scores = reranker.predict([(s, query) for s in sentences])
    top_indices = torch.argsort(torch.tensor(scores), descending=True)[:top_k]
    top_indices_sorted = sorted(top_indices.tolist())
    selected_sentences = [sentences[i] for i in top_indices_sorted]
    return ' '.join(selected_sentences) 

def build_prompt(turns):
    prompts = []
    context_sofar = ""
    for turn in turns:

        new_context = turn['new_context']
        context_sofar += new_context
        overall_context = ""
        if args.context == "none":
            overall_context = ""
        else:
            overall_context = "Story:\n"
            if args.context == "new":
                overall_context += new_context + "\n"
            elif args.context == "day":
                overall_context += context_sofar + "\n"

        character_counter = 0
        characters = "Characters:\n"
        for character in turn['characters']:
            characters += f"Character {character_counter}\n"
            characters += f"Name: {character['name']}\n"
            characters += f"Description: {character['description']}\n"
            character_counter += 1

        evidence_counter = 0
        evidences = "Evidences:\n"
        for evidence in turn['evidences']:
            evidences += f"Evidence {evidence_counter}\n"
            evidences += f"Name: {evidence['name']}\n"
            evidences += f"Description: {evidence['description1']}\n"
            evidence_counter += 1

        testimony_counter = 0
        testimonies = "Testimonies:\n"
        for testimony in turn['testimonies']:
            testimonies += f"Testimony {testimony_counter}\n"
            testimonies += f"Testimony: {testimony['testimony']}\n"
            testimonies += f"Person: {testimony['person']}\n"
            testimony_counter += 1

        if EXTRACTION:
            query = prompt_prefix + characters + evidences + testimonies + prompt_suffix
            extracted_context = prompt_extract(overall_context, query)
            prompt = extracted_context + "\n" + characters + evidences + testimonies
        else:
            prompt = overall_context + "\n" + characters + evidences + testimonies

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
    extract = ""
    if EXTRACTION:
        extract = "extracted"
    output_dir = f'../output/{MODEL.split("/")[-1]}_{PROMPT}_{extract}'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(os.path.join(output_dir, 'metada.json'), 'w') as file:
        json.dump({
            'model': MODEL,
            'prompt': PROMPT,
            'case': CASE,
            'timestamp': timestamp
        }, file, indent=2)
    engine = HuggingEngine(model_id = MODEL, use_auth_token=True, model_load_kwargs={"device_map": "auto"})
    ai = Kani(engine, system_prompt="")
    all_fnames = sorted(os.listdir(data_dir))
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
        print(fname)
        turns = parse_json(os.path.join(data_dir, fname))
        prompts = build_prompt(turns)
        #print(prompts)
        answer_jsons, full_responses = run_model(prompts)
        for answer_json in answer_jsons:
            print(answer_json)
        with open(os.path.join(output_dir, fname.split('.')[0] + '.jsonl'), 'w') as file:
            for answer_json in answer_jsons:
                file.write(answer_json + "\n")
        with open(os.path.join(output_dir, fname.split('.')[0] + '_full_responses.txt'), 'w') as file:
            for response in full_responses:
                file.write(response + "\n")