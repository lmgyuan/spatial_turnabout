"""
=============================================================================
run_models_parallel_v2.py - Global Parallel Version
=============================================================================

This version parallelizes across ALL cases and ALL turns globally, rather than
within each case. This is much more efficient when most cases have only 1-2 turns.

KEY DIFFERENCES FROM run_models_parallel.py:
- Collects ALL turns from ALL cases first
- Processes ALL turns in parallel simultaneously
- Maps results back to correct case and turn for output
- Much better for datasets where cases have few turns each

ARCHITECTURE:
1. Scan all cases and collect all (case, turn_idx, prompt) tuples
2. Process ALL tuples in parallel with max_workers
3. Group results back by case for proper file output
4. Maintain identical output format and error handling

USAGE EXAMPLES:
- python run_models_parallel_v2.py -m nebius-llama3.3-70b -p base --context sum --label spatial --max_workers 57
- python run_models_parallel_v2.py -m nebius-qwen-32b -p rulesv4_explicit --context sum --label spatial --max_workers 20

NOTE: All commands work identically to run_models_spatial.py
=============================================================================
"""

import json
import os
import asyncio
import re
import argparse
import traceback
from datetime import datetime
import concurrent.futures
from threading import Lock
from collections import defaultdict

# Global variable for prop generator
current_prop_generator = None

def parse_arguments():
    parser = argparse.ArgumentParser(description='')
    # General args
    parser.add_argument('-m', '--model', type=str, help='model name')
    parser.add_argument('-p', '--prompt', type=str, help='prompt name')
    parser.add_argument('--context', type=str, help='full, sum')
    parser.add_argument('--case', type=str, default="ALL", help='If ALL, run all cases; if a case number like 3-4-1, run that case; if a case number followed by a "+" like 3-4-1+, run that case and all cases after it.')
    parser.add_argument('--no_description', action='store_true')
    parser.add_argument('--data', type=str, default='aceattorney', help='dataset name, aceattorney or danganronpa')
    parser.add_argument('--label', type=str, default=None, help='filter cases by label (e.g., spatial, temporal, etc.)')
    parser.add_argument('--reasoning', type=str, default='none', choices=['none', 'full', 'facts', 'props'], 
                        help='Include reasoning in prompts: none (default), full (all reasoning), facts (only facts), props (only propositions)')
    parser.add_argument('--max_workers', type=int, default=20, help='Number of parallel API calls (default: 20, recommended for global parallelization)')

    # Evaluation args
    parser.add_argument('-a', '--all', action='store_true', help='Evaluate all existing models')
    return parser

# OS operations

def get_output_dir(MODEL, PROMPT, CONTEXT, CASE, NO_DESCRIPTION, DATA, LABEL, REASONING):
    output_dir = f'../output_spatial/{MODEL.split("/")[-1]}_prompt_{PROMPT}'
    if CONTEXT is not None:
        output_dir += f"_context_{CONTEXT}"
    if NO_DESCRIPTION:
        output_dir += "_desc_none"    
    if CASE != "ALL":
        output_dir += f"_case_{CASE}"
    if DATA == 'danganronpa':
        output_dir += f"_data_{DATA}"
    if LABEL is not None:
        output_dir += f"_label_{LABEL}"
    if REASONING != 'none':
        output_dir += f"_reasoning_{REASONING}"
    return output_dir

def get_fnames(data_dir, output_dir, CASE, eval=False, verbose=True):
    """Return list of .json files"""
    all_fnames = sorted([
        fname for fname 
        in os.listdir(data_dir) 
        if fname.endswith('.json')
        # if not fname.startswith(('7-', '8-'))  # skip test split
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

    if verbose: print(f"<get_fnames> Found {len(fnames)} total cases")

    if not eval:
        fnames_to_check = fnames.copy()
        for fname in fnames_to_check:
            if os.path.exists(os.path.join(output_dir, fname.split('.')[0] + '.jsonl')):
                # print(f"Skipping existing {fname.split('.')[0] + '.jsonl'}")
                fnames.remove(fname)

    if verbose:print(f"<get_fnames> Running {len(fnames)} new cases")
    return fnames

# Prompt builders

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

def parse_json(file_path, label_filter=None):
    """Parse JSON file and optionally filter turns by label"""
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        characters = []
        evidences = []
        prev_context = re.sub(r'\n+', ' ', data.get("previousContext", ""))  # Remove newlines

        for character in data.get('characters', {}):
            characters.append(character)
        for evidence in data.get('evidences', {}):
            evidences.append(evidence)
        turns = []
        for turn in data.get("turns", []):
            if turn["noPresent"]:
                continue
            
            # Apply label filtering at turn level
            if label_filter is not None:
                turn_labels = turn.get("labels", [])
                has_label = False
                if isinstance(turn_labels, list) and label_filter in turn_labels:
                    has_label = True
                elif isinstance(turn_labels, str) and turn_labels == label_filter:
                    has_label = True
                
                # Skip this turn if it doesn't have the required label
                if not has_label:
                    continue
            
            testimonies = []
            for testimony in turn['testimonies']:
                testimonies.append(testimony)
            turn_dict = {
                'characters': characters,
                'evidences': evidences,
                'testimonies': testimonies,
                'newContext': re.sub(r'\n+', ' ', turn['newContext']),
                'summarizedContext': turn.get('summarizedContext', ""),
                'reasoning': turn.get('reasoning', [])  # Extract reasoning, default to empty list
            }
            turns.append(turn_dict)
        return turns, prev_context

def truncate_context(context, MODEL):
    context_size = len(context)  # Count characters, not tokens

    # Truncate context for specific models
    max_context_size = -1
    if "deepseek" in MODEL or "deepseek-chat" in MODEL:  # Roughly 66000 tokens for deepseek
        max_context_size = 230000
    # elif "70b" in MODEL:  # Roughtly 20000 tokens for 70b
    #     max_context_size = 80000
    if max_context_size != -1:
        start_idx = context_size - max_context_size
        context = "..." + context[start_idx:]

    return context

def build_prompt(
    turns, 
    prev_context, 
    PROMPT_PREFIX, 
    PROMPT_SUFFIX, 
    CONTEXT, 
    NO_DESCRIPTION, 
    MODEL,
    REASONING,
    PROMPT_ARG=None,
    case_name=None,
    label_filter=None,
    data='aceattorney'
):
    prompts = []
    context_sofar = ""
    
    # Use global prop generator if needed (ONLY for prop_generated prompts)
    prop_generator = None
    if PROMPT_ARG and "prop_generated" in PROMPT_ARG:
        global current_prop_generator
        if current_prop_generator is None:
            try:
                from prop_generator import PropGenerator
                current_prop_generator = PropGenerator()
                print(f"[INFO] Prop generation mode activated for prompt: {PROMPT_ARG}")
            except ImportError:
                print(f"[WARNING] PropGenerator not available, falling back to standard prompt")
        prop_generator = current_prop_generator
    
    for turn_idx, turn in enumerate(turns):
        context_is_added = False
        new_context = turn['newContext']  
        new_context = re.sub(r'\n+', ' ', new_context)  # Remove newlines
        context_sofar += new_context
        if CONTEXT is None:
            prompt = ""
        else:
            prompt = "Story:\n"
            full_context = "" 
            if CONTEXT == "full":
                full_context += prev_context + "\n" + context_sofar + "\n"
            elif CONTEXT == "sum":
                full_context += turn['summarizedContext'] + "\n"

            full_context = truncate_context(full_context, MODEL)

            prompt += full_context

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
                testimony["source"].get("is_self_contained", "yes") == "no" and \
                CONTEXT is None:
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
        
        # Add reasoning if requested
        reasoning_section = ""
        if REASONING != 'none' and turn['reasoning']:
            reasoning_section = "Reasoning:\n"
            reasoning_items = []
            
            if REASONING == 'full':
                reasoning_items = turn['reasoning']
            elif REASONING == 'facts':
                reasoning_items = [item for item in turn['reasoning'] if item.startswith('Fact')]
            elif REASONING == 'props':
                reasoning_items = [item for item in turn['reasoning'] if item.startswith('Prop')]
            
            for i, item in enumerate(reasoning_items, 1):
                reasoning_section += f"{i}. {item}\n"
            reasoning_section += "\n"
        
        # Build rest of the prompt
        prompt += f"Evidences:\n{''.join(evidences)}\nTestimonies:\n{''.join(testimonies)}\n{reasoning_section}"
        
        # Generate turn-specific props ONLY if prop_generated prompt is used
        enhanced_prefix = PROMPT_PREFIX
        if prop_generator is not None:
            try:
                # Load model for prop generation (same as main model)
                client, client_name = load_model(MODEL)
                
                generated_props = prop_generator.generate_turn_props(
                    turn, client, client_name, case_name, turn_idx
                )
                props_text = "\n".join([f"Prop {i+1}: {prop}" 
                                      for i, prop in enumerate(generated_props)])
                enhanced_prefix = PROMPT_PREFIX.replace("{generated_props}", props_text)
                
                print(f"[INFO] Generated {len(generated_props)} props for {case_name} turn {turn_idx} (Total logged: {len(prop_generator.props_log)})")
                print(f"[DEBUG] Props for turn {turn_idx}: {generated_props[0][:50]}...")  # Show first prop snippet for verification
                
            except Exception as e:
                print(f"[WARNING] Prop generation failed for turn {turn_idx}: {e}")
                enhanced_prefix = PROMPT_PREFIX.replace("{generated_props}", 
                                                       "No specific propositions generated.")
        
        # Enhance prompt with RAG if using RAG prompt
        elif PROMPT_ARG and "rag" in PROMPT_ARG and "{dynamic_rules}" in PROMPT_PREFIX:
            try:
                from rag import enhance_prompt_with_rag, log_rules_usage
                # Parse top_k from prompt name (e.g., rulesv3_rag_t10 -> top_k=10)
                top_k = 5  # Default value
                match = re.search(r'_t(\d+)', PROMPT_ARG)
                if match:
                    top_k = int(match.group(1))
                enhanced_prefix, rules_metadata, used_top_k = enhance_prompt_with_rag(PROMPT_PREFIX, turn, top_k, return_rules_metadata=True)
                
                # Log rules usage
                if case_name:
                    turn_idx = prompts.__len__()  # Current turn index
                    log_rules_usage(case_name, turn_idx, rules_metadata, used_top_k, MODEL, PROMPT_ARG, CONTEXT, label_filter, NO_DESCRIPTION, data, REASONING)
            except ImportError:
                print("[WARNING] RAG module not available, using original prompt")
            except Exception as e:
                print(f"[WARNING] RAG enhancement failed: {e}, using original prompt")
        
        # Debug: Show when using props for a turn
        if prop_generator is not None and "Prop 1:" in enhanced_prefix:
            evidence_names = [ev.get('name', 'Unknown') for ev in turn.get('evidences', [])]
            print(f"[DEBUG] Using generated props in prompt for turn {turn_idx}, evidences: {evidence_names[:3]}...")
        
        prompts.append(enhanced_prefix + prompt + PROMPT_SUFFIX)
    
    return prompts

# Model runners

def get_json_answer(multiline_string):
    lines = multiline_string.splitlines()
    target = lines[-1]
    try:
        json_answer = json.loads(target)
        cot = "\n".join(lines[:-1])
    except json.JSONDecodeError:
        try:
            target = lines[-2]
            json_answer = json.loads(target)
            cot = "\n".join(lines[:-2])
        except json.JSONDecodeError:
            # print(f"Error parsing JSON: {multiline_string[:-1]}")
            json_answer = {}
            cot = ""
    return json_answer, cot

def run_single_prompt(prompt, client, client_name, global_idx, case_name, turn_idx):
    """Run a single prompt and return the result with case and turn information"""
    try:
        cot = ""
        if type(client).__name__ == "Kani":  # Use kani api
            async def run_async_model():
                response = await client.chat_round_str(prompt, temperature=0)
                return response

            full_answer = asyncio.run(run_async_model())

        elif type(client).__name__ == "OpenAI":  # Use openai api
            response = client.chat.completions.create(
                model=client_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": prompt},
                ],
                stream=False,
                temperature=0,
                seed=42  # Add deterministic seed for consistency
            )
            full_answer = response.choices[0].message.content

            # Get COT
            try: 
                cot = response.choices[0].message.reasoning_content
                if cot is not None:  # Only concatenate if COT is not None
                    full_answer = cot + "\n\n" + full_answer
                else:
                    cot = ""  # Set to empty string if None
            except Exception as e:
                cot = ""

        else:
            raise ValueError(f"<run_single_prompt> Unknown client: {client}")

        answer_json, parsed_cot = get_json_answer(full_answer)

        if cot == "":  # Only when model does not return its COT field
            cot = parsed_cot
            
        return {
            'global_idx': global_idx,
            'case_name': case_name,
            'turn_idx': turn_idx,
            'answer_json': answer_json,
            'cot': cot,
            'prompt': prompt,
            'has_error': answer_json == {}
        }
        
    except Exception as e:  # Handle errors, such as rate limit, context window, etc.
        print(f"<run_single_prompt> Error for {case_name} turn {turn_idx}: {str(e)}")
        return {
            'global_idx': global_idx,
            'case_name': case_name,
            'turn_idx': turn_idx,
            'answer_json': {},
            'cot': "",
            'prompt': prompt,
            'has_error': True
        }

def load_model(model, config_path="models.json"):
    with open(config_path, 'r') as file:
        config = json.load(file)
    
    # Store original model key for type detection
    original_model = model
    
    # Resolve model name from config
    model = config.get(model, model)
    
    # Check for API models first using the original model key (before checking for "/" which indicates HuggingFace)
    is_api_model = False
    
    if any(m_name in original_model for m_name in ["gpt", "o3", "o4"]) or \
       "deepseek" in original_model or \
       "nebius" in original_model:
        is_api_model = True
    
    if not is_api_model and "/" in model:  # a huggingface model
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

        model_key = original_model

        if any(m_name in original_model for m_name in ["gpt", "o3", "o4"]):
            model_key = "openai"

        elif "deepseek" in original_model:  # deepseek-reasoner (R1), deepseek-chat (V3)
            model_key = "deepseek"

        elif "nebius" in original_model:  # nebius models
            model_key = "nebius"

        auth = {
            "deepseek": {
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
                "base_url": "https://api.deepseek.com",
                "name": model
            },
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "name": model
            },
            "nebius": {
                "api_key": os.getenv("NEBIUS_API_KEY"),
                "base_url": "https://api.studio.nebius.com/v1/",
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

# Global parallel processing functions

def collect_all_tasks(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION, data_dir, label_filter=None, reasoning=None):
    """Collect all tasks (case, turn, prompt) that need to be processed"""
    print(f"<collect_all_tasks> Collecting tasks from {len(fnames)} cases...")
    
    global current_prop_generator
    if PROMPT and "prop_generated" in PROMPT:
        current_prop_generator = None
    
    tasks = []
    skip_count = 0
    PROMPT_PREFIX, PROMPT_SUFFIX = build_prompt_prefix_suffix(PROMPT)
    
    for fname in fnames:
        case_name = fname.split('.')[0]
        try:
            turns, context = parse_json(os.path.join(data_dir, fname), label_filter)
            if turns == []:  # Skip cases with no turns
                skip_count += 1
                continue
                
            prompts = build_prompt(turns, context, PROMPT_PREFIX, PROMPT_SUFFIX, CONTEXT, NO_DESCRIPTION, MODEL, reasoning, PROMPT,
                                  case_name=case_name, label_filter=label_filter, data=data_dir.split('/')[-2])
            
            # Add each prompt as a task
            for turn_idx, prompt in enumerate(prompts):
                tasks.append({
                    'case_name': case_name,
                    'turn_idx': turn_idx,
                    'prompt': prompt
                })
                
        except Exception as e:
            print(f"<collect_all_tasks> Error processing {fname}: {e}")
            skip_count += 1
            continue
    
    print(f"<collect_all_tasks> Collected {len(tasks)} total tasks, skipped {skip_count} cases")
    return tasks

def run_all_tasks_parallel(tasks, client, client_name, max_workers=20):
    """Run all tasks in parallel and return results organized by case"""
    print(f"<run_all_tasks_parallel> Running {len(tasks)} tasks with max_workers={max_workers}")
    
    results = []
    completed_count = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks to the thread pool
        future_to_task = {
            executor.submit(
                run_single_prompt, 
                task['prompt'], 
                client, 
                client_name, 
                idx,  # global index
                task['case_name'], 
                task['turn_idx']
            ): idx 
            for idx, task in enumerate(tasks)
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_task):
            result = future.result()
            results.append(result)
            completed_count += 1
            
            if completed_count % 10 == 0 or completed_count == len(tasks):
                print(f"<run_all_tasks_parallel> Completed {completed_count}/{len(tasks)} tasks")
    
    # Sort results by global index to maintain original order
    results.sort(key=lambda x: x['global_idx'])
    
    # Group results by case
    case_results = defaultdict(list)
    for result in results:
        case_results[result['case_name']].append(result)
    
    # Sort turns within each case
    for case_name in case_results:
        case_results[case_name].sort(key=lambda x: x['turn_idx'])
    
    return dict(case_results)

def save_case_results(case_name, case_results, output_dir):
    """Save results for a single case in the standard format"""
    # Extract data
    answer_jsons = [result['answer_json'] for result in case_results]
    cots = [result['cot'] for result in case_results]
    prompts = [result['prompt'] for result in case_results]
    
    # Save .jsonl file
    with open(os.path.join(output_dir, case_name + '.jsonl'), 'w') as file:
        for answer_json in answer_jsons:
            file.write(json.dumps(answer_json) + "\n")
    
    # Save _outputs.json file
    with open(os.path.join(output_dir, case_name + '_outputs.json'), 'w') as file:
        json_response = []
        for idx, (answer_json, cot, prompt) in enumerate(zip(answer_jsons, cots, prompts)):
            json_response.append({ 
                "idx": idx,
                "prompt": prompt,
                "response_json": answer_json,
                "cot": cot
            })
        file.write(json.dumps(json_response, indent=2))

# Main processing function

def run_job_global_parallel(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION, client, client_name, output_dir, data_dir, label_filter=None, reasoning=None, max_workers=20):
    """Main function that runs everything in global parallel mode"""
    global current_prop_generator
    
    # Reset prop generator for new run
    if PROMPT and "prop_generated" in PROMPT:
        current_prop_generator = None
    
    print(f"<run_job_global_parallel> Starting global parallel processing")
    
    # Step 1: Collect all tasks from all cases
    tasks = collect_all_tasks(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION, data_dir, label_filter, reasoning)
    
    if not tasks:
        print(f"<run_job_global_parallel> No tasks to process")
        return
    
    # Step 2: Run all tasks in parallel
    case_results = run_all_tasks_parallel(tasks, client, client_name, max_workers)
    
    # Step 3: Save results for each case
    error_count = 0
    for case_name, results in case_results.items():
        try:
            # Check for errors in this case
            has_error = any(result['has_error'] for result in results)
            if has_error:
                error_count += 1
                print(f"<run_job_global_parallel> Error in case {case_name}")
            
            # Print results (for compatibility)
            for result in results:
                print(result['answer_json'])
            
            # Save case results
            save_case_results(case_name, results, output_dir)
            
        except Exception as e:
            print(f"<run_job_global_parallel> Error saving {case_name}: {e}")
            error_count += 1
    
    print(f"<run_job_global_parallel> Completed processing. Cases with errors: {error_count}")
    
    # Save props log if prop generation was used
    try:
        if 'current_prop_generator' in globals() and current_prop_generator is not None:
            print(f"[INFO] Saving props log with {len(current_prop_generator.props_log)} total turns")
            current_prop_generator.save_props_log(output_dir, MODEL.split("/")[-1], PROMPT)
        elif PROMPT and "prop_generated" in PROMPT:
            print(f"[WARNING] Prop generation was expected but no props were logged")
    except Exception as e:
        print(f"[WARNING] Failed to save props log: {e}")

if __name__ == "__main__":
    parser = parse_arguments()
    args = parser.parse_args()
    MODEL = args.model
    PROMPT = args.prompt
    CASE = args.case if args.case else "ALL"
    CONTEXT = args.context
    NO_DESCRIPTION = args.no_description
    DATA = args.data
    LABEL = args.label
    REASONING = args.reasoning
    MAX_WORKERS = args.max_workers

    if DATA == 'aceattorney':
        data_dir = '../data/aceattorney_data/final'
    elif DATA == 'danganronpa':
        data_dir = '../data/danganronpa_data/final'

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Make output dir
    output_dir = get_output_dir(MODEL, PROMPT, CONTEXT, CASE, NO_DESCRIPTION, DATA, LABEL, REASONING)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(os.path.join(output_dir, 'metadata.json'), 'w') as file:
        json.dump({
            'model': MODEL,
            'prompt': PROMPT,
            'context': "none" if CONTEXT is None else CONTEXT,
            'case': CASE if CASE != "ALL" else "all",
            'no_description': NO_DESCRIPTION,
            'data': DATA,
            'label': LABEL if LABEL is not None else "none",
            'reasoning': REASONING,
            'timestamp': timestamp,
            'parallel_processing': 'global_v2',  # Mark this as global parallel version
            'max_workers': MAX_WORKERS
        }, file, indent=2)
    
    # Load model
    client, client_name = load_model(MODEL)

    # Collect cases
    fnames = get_fnames(data_dir, output_dir, CASE)

    # Run cases using global parallel processing
    print(f"Using global parallel processing with max_workers={MAX_WORKERS}")
    run_job_global_parallel(fnames, MODEL, PROMPT, CONTEXT, NO_DESCRIPTION, client, client_name, output_dir, data_dir, LABEL, REASONING, MAX_WORKERS) 