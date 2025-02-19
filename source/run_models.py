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
                'new_context': turn['newContext'],
                'is_self_contained' : turn['is_self_contained']
            })
            #break
        return turns

def prompt_extract(context, query, keep_ratio=0.5):
    sentences = context.split('\n\n')
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
        is_self_contained = turn['is_self_contained']
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
            characters += f"Description: {character['description1']}\n"
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

        # if EXTRACTION:
        #     query = prompt_prefix + "\n" + characters + "\n" + evidences + "\n" + testimonies + "\n" + prompt_suffix
        #     extracted_context = prompt_extract(overall_context, query)
        #     prompt = "Story:\n" + extracted_context + "\n" + characters + "\n" + evidences + "\n" + testimonies
        # else:
        #     prompt = overall_context + "\n" + characters + "\n" + evidences + "\n" + testimonies

        # prompt = ""
        # if is_self_contained:
        #     prompt = characters + "\n" + evidences + "\n" + testimonies
        # else:
        #     prompt = overall_context + "\n" + characters + "\n" + evidences + "\n" + testimonies

        # print("query: \n")
        # print(query + "\n" + "\n")
        # print("overall: \n")
        # print(overall_context + "\n" + "\n")
        # print("extracted: \n")
        # print(extracted_context + "\n" + "\n")
        prompt = overall_context + "\n" +characters + "\n" + evidences + "\n" + testimonies
        prompts.append(prompt_prefix + prompt + prompt_suffix)

        # prompts.append({'prompt': prompt_prefix + "\n" + prompt + "\n" + prompt_suffix, 'story': overall_context})
        # prompts.append({'prompt': prompt, 'story': overall_context})

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

# async def call_model(prompt):
#     response = await ai.chat_round_str(prompt, temperature=0.6)
#     return response

# def get_last_line(multiline_string):
#     lines = multiline_string.splitlines()
#     return lines[-1] if lines else ""

# def run_model(prompt_pairs):
#     answer_jsons = []
#     full_responses = []

#     with open("include_story_log.txt", "a") as log_file:
#         for prompt_pair in prompt_pairs:
#             prompt, story = prompt_pair  # Unpacking the two-variable object
            
#             # First model call
#             include_story = asyncio.run(call_model(prompt_prefix + "\n" + prompt + "\n" + prompt_suffix + "\n\n" + "do you believe you have sufficient information to answer the above question or do you need the story that gives additional context on the sequence of events being discussed in the testimony. Respond only with a yes or no. Yes if you need additional context and no if you do not."))
#             print(include_story)
            
#             # Logging the result
#             log_file.write(f"Include Story: {include_story}\n\n")
        
#             # Second model call using output from the first call
#             if include_story == "yes":
#                 prompt = prompt_prefix + story + "\n" + prompt + "\n" + prompt_suffix
#             else:
#                 prompt = prompt_prefix + "\n" + prompt + "\n" + prompt_suffix

#             response = asyncio.run(call_model(prompt))
#             answer_json = get_last_line(response)
            
#             # Collecting results
#             answer_jsons.append(answer_json)
#             full_responses.append(response)
    
#     return answer_jsons, full_responses


if __name__ == "__main__":
    data_dir = '../data/aceattorney_data/final'
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f'../output/{MODEL.split("/")[-1]}_{PROMPT}_{args.context}'
    if EXTRACTION:
        output_dir += '_extracted'
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