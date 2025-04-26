import os
import json
from datetime import datetime

from run_models import (
    get_output_dir, 
    get_fnames, 
    parse_json, 
    load_model, 
    run_model, 
    build_prompt_prefix_suffix,
    parse_arguments,
    submit_batch_job
)

def build_prompt(turns, prev_context, PROMPT_PREFIX, PROMPT_SUFFIX, CONTEXT, NO_DESCRIPTION, disable_context_span=False):
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
            CONTEXT is None and not disable_context_span:  # Always and only add context span if no context provided
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

def filter_turns(turns):
    filtered_turns = []
    for turn in turns:
        testimonies = turn["testimonies"]
        for testimony in testimonies:
            if "source" in testimony and "is_self_contained" in testimony["source"] \
            and testimony["source"]["is_self_contained"] == "no":
                filtered_turns.append(turn)
                break
    return filtered_turns

def run_job(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION, client, client_name, output_dir, data_dir, disable_context_span=False):
    for fname in fnames:
        # Parse and build prompt
        turns, context = parse_json(os.path.join(data_dir, fname))
        turns = filter_turns(turns)
        if not turns:
            continue
        PROMPT_PREFIX, PROMPT_SUFFIX = build_prompt_prefix_suffix(PROMPT)
        prompts = build_prompt(
            turns, 
            context, 
            PROMPT_PREFIX, 
            PROMPT_SUFFIX, 
            CONTEXT, 
            NO_DESCRIPTION, 
            disable_context_span=disable_context_span
        )
        print(fname)
        # print(prompts[0])
        # import sys; sys.exit(0)

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

def create_batch(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION, data_dir, disable_context_span=False):
    max_token_key = "max_tokens" if "gpt" in MODEL else "max_completion_tokens"
    max_token_val = 1000 if "gpt" in MODEL else 5000
    batch = []
    for fname in fnames:
        turns, prev_context = parse_json(os.path.join(data_dir, fname))
        turns = filter_turns(turns)
        if not turns:
            continue
        PROMPT_PREFIX, PROMPT_SUFFIX = build_prompt_prefix_suffix(PROMPT)
        prompts = build_prompt(
            turns, 
            prev_context, 
            PROMPT_PREFIX, 
            PROMPT_SUFFIX, 
            CONTEXT, 
            NO_DESCRIPTION, 
            disable_context_span
        )
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

def run_batch_job(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION, client, output_dir, data_dir, disable_context_span=False):
    jsonl_path = os.path.join(output_dir, "batchinput.jsonl")
    batch = create_batch(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION, data_dir, disable_context_span)
    with open(jsonl_path, "w") as f:
        for request in batch:
            f.write(json.dumps(request, ensure_ascii=False) + "\n")    
    # import sys; sys.exit(0)
    batch_job_id = submit_batch_job(jsonl_path, client, output_dir)
    return batch_job_id

if __name__ == "__main__":
    parser = parse_arguments()
    parser.add_argument('-d', '--disable_context_span', action='store_true')
    args = parser.parse_args()
    
    MODEL = args.model
    PROMPT = args.prompt
    CASE = args.case if args.case else "ALL"
    CONTEXT = args.context
    NO_DESCRIPTION = args.no_description
    DISABLE_CONTEXT_SPAN = args.disable_context_span

    data_dir = '../data/aceattorney_data/final'
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Make output dir
    output_dir = get_output_dir(
        MODEL, 
        PROMPT, 
        CONTEXT, 
        CASE, 
        NO_DESCRIPTION, 
        NOT_SELF_CONTAINED_ONLY=True, 
        DISABLE_CONTEXT_SPAN=DISABLE_CONTEXT_SPAN
    )
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
    fnames = get_fnames(data_dir, output_dir, CASE)

    # Run cases
    if MODEL in ["gpt-4o-mini", "gpt-4o", "o3-mini"]:
        run_batch_job(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION, client, output_dir, data_dir, DISABLE_CONTEXT_SPAN)
    else:
        run_job(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION, client, client_name, output_dir, data_dir, DISABLE_CONTEXT_SPAN)
