import json
import os
import asyncio
import argparse
from datetime import datetime

def parse_arguments():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-m', '--model', type=str, help='model name')
    parser.add_argument('-p', '--prompt', type=str, help='prompt name')
    parser.add_argument('--context', type=str, help='new, day, sum')
    parser.add_argument('-c', '--case', type=str, help='If ALL, run all cases; if a case number like 3-4-1, run that case; if a case number followed by a "+" like 3-4-1+, run that case and all cases after it.')
    parser.add_argument('-n', '--no_description', action='store_true')
    return parser

def get_output_dir(MODEL, PROMPT, CONTEXT, CASE, NO_DESCRIPTION):
    output_dir = f'../output/{MODEL.split("/")[-1]}_{PROMPT}'
    if CONTEXT is not None:
        output_dir += f"_context_{CONTEXT}"
    if NO_DESCRIPTION:
        output_dir += "_no_desc"    
    if CASE != "ALL":
        output_dir += f"_case_{CASE}"
    return output_dir

def get_fnames(data_dir, output_dir, CASE, eval=False):
    """Return list of .json files"""
    all_fnames = sorted([
        fname for fname 
        in os.listdir(data_dir) 
        if fname.endswith('.json')
        if int((fname.split("_")[0]).split("-")[-1]) % 2 == 0
        if not fname.startswith(('7-', '8-'))  # skip test split
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

    print(f"<get_fnames> Found {len(fnames)} cases")

    if not eval:
        fnames_to_check = fnames.copy()
        for fname in fnames_to_check:
            if os.path.exists(os.path.join(output_dir, fname.split('.')[0] + '.jsonl')):
                # print(f"Skipping existing {fname.split('.')[0] + '.jsonl'}")
                fnames.remove(fname)

    print(f"<get_fnames> Running {len(fnames)} new cases")
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
            turn_dict = {
                'characters': characters,
                'evidences': evidences,
                'testimonies': testimonies,
                'new_context': turn['newContext']
            }
            summarized_context = ""
            if 'summarizedContext' in turn: summarized_context = turn['summarizedContext']
            elif 'summarized_context' in turn: summarized_context = turn['summarized_context']
            turn_dict['summarized_context'] = summarized_context
            turns.append(turn_dict)
        return turns, data["previousContext"]

def build_prompt(turns, prev_context, PROMPT_PREFIX, PROMPT_SUFFIX, CONTEXT, NO_DESCRIPTION):
    prompts = []
    context_sofar = ""
    for turn in turns:
        context_is_added = False
        new_context = turn['new_context']
        context_sofar += new_context
        if CONTEXT is None:
            prompt = ""
        else:
            prompt = "Story:\n"
            if CONTEXT == "new":
                prompt += prev_context + "\n" + new_context + "\n"
            elif CONTEXT == "day":
                prompt += prev_context + "\n" + context_sofar + "\n"
            elif CONTEXT == "sum":
                prompt = "Summarized Context:\n" + turn['summarized_context'] + "\n"
        character_counter = 0
        prompt += "Characters:\n"
        for character in turn['characters']:
            prompt += f"Character {character_counter}\n"
            prompt += f"Name: {character['name']}\n"
            if not NO_DESCRIPTION:
                prompt += f"Description: {character['description1']}\n"
            character_counter += 1

        # Format evidences
        evidence_counter = 0
        evidences = []
        for evidence in turn['evidences']:
            evidence_string = f"Evidence {evidence_counter}\n"
            evidence_string += f"Name: {evidence['name']}\n"
            if not NO_DESCRIPTION:
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
            testimony["source"]["is_self_contained"] == "no" and \
            CONTEXT is None:  # Always and only add context span if no context provided
                context_span = testimony["source"]["context_span"]
                if not context_is_added and not NO_DESCRIPTION:
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

def get_json_answer(multiline_string):
    lines = multiline_string.splitlines()
    target = lines[-1]
    try:
        json_answer = json.loads(target)
    except json.JSONDecodeError:
        try:
            target = lines[-2]
            json_answer = json.loads(target)
        except json.JSONDecodeError:
            # print(f"Error parsing JSON: {multiline_string[:-1]}")
            json_answer = {}
    
    return json_answer

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

        answer_json = get_json_answer(full_answer)
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

    else:  # an api model
        from dotenv import load_dotenv
        from openai import OpenAI

        load_dotenv("../.env")

        model_key = model
        if model in ["gpt-4o-mini", "gpt-4o", "o3-mini"]:
            model_key = "openai"

        auth = {
            "deepseek": {
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
                "base_url": "https://api.deepseek.com",
                "name": "deepseek-reasoner"
            },
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "name": model
            }
        }

        if "base_url" in auth[model_key]:
            client = OpenAI(
                api_key=auth[model_key]["api_key"],
                base_url=auth[model_key]["base_url"]
            )
        else:
            client = OpenAI(
                api_key=auth[model_key]["api_key"],
            )

        name = auth[model_key]["name"]

    return client, name

def create_batch(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION, data_dir):
    max_token_key = "max_tokens" if "gpt" in MODEL else "max_completion_tokens"
    max_token_val = 1000 if "gpt" in MODEL else 5000
    batch = []
    for fname in fnames:
        turns, prev_context = parse_json(os.path.join(data_dir, fname))
        PROMPT_PREFIX, PROMPT_SUFFIX = build_prompt_prefix_suffix(PROMPT)
        prompts = build_prompt(turns, prev_context, PROMPT_PREFIX, PROMPT_SUFFIX, CONTEXT, NO_DESCRIPTION)
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

def submit_batch_job(jsonl_path, client, output_dir):
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

def run_batch_job(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION, client, output_dir, data_dir):
    jsonl_path = os.path.join(output_dir, "batchinput.jsonl")
    batch = create_batch(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION, data_dir)
    with open(jsonl_path, "w") as f:
        for request in batch:
            f.write(json.dumps(request, ensure_ascii=False) + "\n")
    
    batch_job_id = submit_batch_job(jsonl_path, client, output_dir)
    return batch_job_id

def run_job(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION, client, client_name, output_dir, data_dir):
    for fname in fnames:
        # Parse and build prompt
        print(fname)
        turns, context = parse_json(os.path.join(data_dir, fname))
        PROMPT_PREFIX, PROMPT_SUFFIX = build_prompt_prefix_suffix(PROMPT)
        prompts = build_prompt(turns, context, PROMPT_PREFIX, PROMPT_SUFFIX, CONTEXT, NO_DESCRIPTION)

        # Answer
        answer_jsons, full_responses = run_model(prompts, client, client_name)
        for answer_json in answer_jsons:
            print(answer_json)

        # Log
        with open(os.path.join(output_dir, fname.split('.')[0] + '.jsonl'), 'w') as file:
            for answer_json in answer_jsons:
                file.write(json.dumps(answer_json) + "\n")
        with open(os.path.join(output_dir, fname.split('.')[0] + '_outputs.json'), 'w') as file:
            json_response = []
            for idx, response in enumerate(full_responses):
                json_response.append({
                    "idx": idx,
                    "prompt": prompts[idx],
                    "response": response,
                    "response_json": answer_jsons[idx]
                })
            file.write(json.dumps(json_response, indent=2))

if __name__ == "__main__":
    parser = parse_arguments()
    args = parser.parse_args()
    MODEL = args.model
    PROMPT = args.prompt
    CASE = args.case if args.case else "ALL"
    CONTEXT = args.context
    NO_DESCRIPTION = args.no_description

    data_dir = '../data/aceattorney_data/final'
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Make output dir
    output_dir = get_output_dir(MODEL, PROMPT, CONTEXT, CASE, NO_DESCRIPTION)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(os.path.join(output_dir, 'metadata.json'), 'w') as file:
        json.dump({
            'model': MODEL,
            'prompt': PROMPT,
            'context': CONTEXT,
            'case': CASE,
            'no_description': NO_DESCRIPTION,
            'timestamp': timestamp
        }, file, indent=2)
    # Load model
    client, client_name = load_model(MODEL)

    # Collect cases
    fnames = get_fnames(data_dir, output_dir, CASE)

    # Run cases
    if MODEL in ["gpt-4o-mini", "gpt-4o", "o3-mini"]:
        run_batch_job(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION, client, output_dir, data_dir)
    else:
        run_job(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION, client, client_name, output_dir, data_dir)
