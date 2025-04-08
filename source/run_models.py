import json
import os
import asyncio
import argparse
from datetime import datetime

parser = argparse.ArgumentParser(description='')
parser.add_argument('-m', '--model', type=str, help='model name')
parser.add_argument('-p', '--prompt', type=str)
parser.add_argument('--context', type=str, help='new, day')
parser.add_argument('-c', '--case', type=str, help='If ALL, run all cases; if a case number like 3-4-1, run that case; if a case number followed by a "+" like 3-4-1+, run that case and all cases after it.')
parser.add_argument('-n', '--no_description', action='store_true')

# python run_models.py --model deepseek-ai/DeepSeek-R1-Distill-Llama-8B --prompt harry_v1.3

args = parser.parse_args()
MODEL = args.model
PROMPT = args.prompt
CASE = args.case if args.case else "ALL"
CONTEXT = args.context if args.context else None

def get_output_dir():
    output_dir = f'../output/{MODEL.split("/")[-1]}_{PROMPT}'
    if args.context is not None:
        output_dir += f"_context_{CONTEXT}"
    if args.no_description:
        output_dir += "_no_desc"
    if CASE != "ALL":
        output_dir += f"_case_{args.case}"
    return output_dir

def get_fnames(data_dir, output_dir):
    """Return list of .json files"""
    all_fnames = sorted([
        fname for fname 
        in os.listdir(data_dir) 
        if fname.endswith('.json')
        if not int((fname.split("_")[0]).split("-")[-1]) % 2 == 1
        if not fname.startswith(('7-'))  # skip test split
    ])
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

    print(f"Found {len(fnames)} cases")

    fnames_to_check = fnames.copy()
    for fname in fnames_to_check:
        if os.path.exists(os.path.join(output_dir, fname.split('.')[0] + '.jsonl')):
            print(f"Skipping existing {fname.split('.')[0] + '.jsonl'}")
            fnames.remove(fname)

    print(f"Running {len(fnames)} cases")
    return fnames

def build_prompt_prefix_suffix(prompt_arg):
    with open("prompts/" + prompt_arg + ".json", 'r') as file:
        # parse json
        data = json.load(file)
        prompt_prefix = data['prefix']
        prompt_suffix = data['suffix']

    # Load cot examples
    if "one_shot" in prompt_arg:
        with open("prompts/example_one_shot.txt", "r") as file:
            example_one_shot = file.read()
        prompt_prefix = prompt_prefix.format(example_one_shot=example_one_shot)

    elif "few_shot" in prompt_arg:
        with open("prompts/example_few_shot.txt", "r") as file:
            example_few_shot = file.read()
        prompt_prefix = prompt_prefix.format(example_few_shot=example_few_shot)

    return prompt_prefix, prompt_suffix

PROMPT_PREFIX, PROMPT_SUFFIX = build_prompt_prefix_suffix(PROMPT)

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
        return turns, data["previousContext"]

def build_prompt(turns, prev_context):
    prompts = []
    context_sofar = ""
    for turn in turns:
        context_is_added = False
        new_context = turn['new_context']
        context_sofar += new_context
        if args.context is None:
            prompt = ""
        else:
            prompt = "Story:\n"
            if args.context == "new":
                prompt += prev_context + "\n" + new_context + "\n"
            elif args.context == "day":
                prompt += prev_context + "\n" + context_sofar + "\n"
        character_counter = 0
        prompt += "Characters:\n"
        for character in turn['characters']:
            prompt += f"Character {character_counter}\n"
            prompt += f"Name: {character['name']}\n"
            if not args.no_description:
                prompt += f"Description: {character['description1']}\n"
            character_counter += 1

        # Format evidences
        evidence_counter = 0
        evidences = []
        for evidence in turn['evidences']:
            evidence_string = f"Evidence {evidence_counter}\n"
            evidence_string += f"Name: {evidence['name']}\n"
            if not args.no_description:
                evidence_string += f"Description: "
                descriptions = []
                for key in evidence.keys():
                    if 'description' in key:
                        descriptions.append(evidence[key])
                evidence_string += " ".join(descriptions) + "\n"
            evidences.append(evidence_string)
            evidence_counter += 1
        
        # Format testimonies
        testimony_counter = 0
        testimonies = []
        for testimony in turn['testimonies']:
            testimony_string = f"Testimony {testimony_counter}\n"
            testimony_string += f"Testimony: {testimony['testimony']}\n"
            testimony_string += f"Person: {testimony['person']}\n"
            # Provide context if needed
            if "source" in testimony and \
            all(
                field in testimony["source"] 
                for field in ["is_self_contained", "context_span"]
            ) and \
            testimony["source"]["is_self_contained"] == "no":
                context_span = testimony["source"]["context_span"]
                if not context_is_added and not args.no_description:
                    for i, evidence_string in enumerate(evidences):
                        evidence_spans = testimony["source"]["evidence_span"]
                        if isinstance(evidence_spans, str):
                            evidence_spans = [evidence_spans]
                        for evidence_span in evidence_spans:
                            if evidence_span in evidence_string: # Find evidence
                                evidences[i] += f"{context_span}\n"  # Add context span
                    context_is_added = True
            testimony_counter += 1
            testimonies.append(testimony_string)
        
        # Build rest of the prompt
        prompt += f"Evidences:\n{''.join(evidences)}\nTestimonies:\n{''.join(testimonies)}\n"
        prompts.append(PROMPT_PREFIX + prompt + PROMPT_SUFFIX)
    return prompts

def get_last_line(multiline_string):
    lines = multiline_string.splitlines()
    return lines[-1] if lines else ""

def run_model(prompts, client, client_name):
    answer_jsons = []
    full_responses = []
    for prompt in prompts:
        #print(prompt)
        if type(client).__name__ == "Kani":  # Use kani api
            async def run_model():
                response = await client.chat_round_str(prompt, temperature=0.6)
                #print(response)
                return response

            full_answer = asyncio.run(run_model())

        elif type(client).__name__ == "OpenAI":  # Use openai api
            response = client.chat.completions.create(
                model=client_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": prompt},
                ],
                stream=False
            )

            full_answer = response.choices[0].message.content
            try: 
                cot = response.choices[0].message.reasoning_content
                print(f"COT returned for {client_name}")
                full_answer = cot + "\n\n" + full_answer
            except Exception as e:
                print(f"When trying to get COT for {client_name}: {e}")
                print(f"No COT for {client_name}")

        else:
            raise ValueError(f"Unknown client: {client}")

        answer_json = get_last_line(full_answer)
        answer_jsons.append(answer_json)
        full_responses.append(full_answer)

    return answer_jsons, full_responses

def load_model(model):
    if "/" in model:  # a huggingface model
        from kani import Kani
        from kani.engines.huggingface import HuggingEngine
        import torch

        torch.cuda.empty_cache()
        engine = HuggingEngine(
            model_id = model, 
            use_auth_token=True, 
            model_load_kwargs={"device_map": "auto"}
        )
        client = Kani(engine, system_prompt="")

        name = model.split("/")[-1]

    else:
        from dotenv import load_dotenv
        from openai import OpenAI

        load_dotenv("../.env")
        auth = {
            "deepseek": {
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
                "base_url": "https://api.deepseek.com",
                "name": "deepseek-reasoner"
            }
        }

        client = OpenAI(
            api_key=auth[model]["api_key"],
            base_url=auth[model]["base_url"]
        )

        name = auth[model]["name"]

    return client, name

if __name__ == "__main__":
    data_dir = '../data/aceattorney_data/final'
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Make output dir
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

    # Load model
    client, client_name = load_model(MODEL)

    # Collect cases
    fnames = get_fnames(data_dir, output_dir)

    # Run cases
    for fname in fnames:
        # Parse and build prompt
        print(fname)
        turns, context = parse_json(os.path.join(data_dir, fname))
        prompts = build_prompt(turns, context)
        # print("\n...\n".join(prompts))
        # import sys; sys.exit(0)

        # Answer
        answer_jsons, full_responses = run_model(prompts, client, client_name)
        for answer_json in answer_jsons:
            print(answer_json)

        # Log
        with open(os.path.join(output_dir, fname.split('.')[0] + '.jsonl'), 'w') as file:
            for answer_json in answer_jsons:
                file.write(answer_json + "\n")
        with open(os.path.join(output_dir, fname.split('.')[0] + '_full_responses.txt'), 'w') as file:
            for response in full_responses:
                file.write(response + "\n")
        with open(os.path.join(output_dir, fname.split('.')[0] + '_prompt.txt'), 'w') as file:
            for prompt in prompts:
                file.write(prompt + "\n\n")