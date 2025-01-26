import json
import os
from kani import Kani
from kani.engines.huggingface import HuggingEngine
from kani.prompts.impl import LLAMA3_PIPELINE
from kani.prompts.impl import GEMMA_PIPELINE
import asyncio

def parse_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        turns = []
        for turn in data:
            #print("Evidence Objects:")
            evidences = []
            for evidence in turn.get('court_record', {}).get('evidence_objects', []):
                # print(f"  - Name: {evidence['name']}")
                # print(f"    Type: {evidence['type']}")
                # print(f"    Obtained: {evidence['obtained']}")
                # print(f"    Description: {evidence['description1']}")
                # print(f"    Current Chapter: {evidence['currentChapter']}")
                # print()
                evidences.append(evidence)
            
            #print("Testimonies:")
            testimonies = []
            for testimony in turn.get('testimonies', []):
                # print(f"  - Testimony: {testimony['testimony']}")
                # print(f"    Person: {testimony['person']}")
                # if 'present' in testimony:
                #     print(f"    Present: {', '.join(testimony['present'])}")
                # if 'source' in testimony:
                #     print(f"    Source: {testimony['source']}")
                # print()
                testimonies.append(testimony)
            turns.append({
                'evidences': evidences,
                'testimonies': testimonies
            })
            #break
        return turns

def build_prompt(turns):
    prompt_prefix = "You are provided with a list of evidences and testimonies.\n"
    prompt_suffix = """Which evidence and testimony contradict each other? You must only answer one pair. Your answer must end with a JSON format like so: {"evidence": 2, "testimony": 3}"""
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
    
MODEL = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"

def run_model(model, prompts):
    answer_jsons = []
    for prompt in prompts:
        print(prompt)
        engine = HuggingEngine(model_id = model, use_auth_token=True, model_load_kwargs={"device_map": "auto"})
        ai = Kani(engine, system_prompt="")

        async def run_model():
            response = await ai.chat_round_str(prompt)
            print(response)
            return response

        response = asyncio.run(run_model())
        def get_last_line(multiline_string):
            lines = multiline_string.splitlines()
            return lines[-1] if lines else ""
        answer_json = get_last_line(response)
        answer_jsons.append(answer_json)
    return answer_jsons


if __name__ == "__main__":
    turns = parse_json('../case_data/final/3-1-1_Turnabout_Memories.json')
    prompts = build_prompt(turns)
    #print(prompts)
    answer_jsons = run_model(MODEL, prompts)
    for answer_json in answer_jsons:
        print(answer_json)