import argparse
import json
import asyncio
import os
from datetime import datetime
import logging
from typing import List, Dict, Any

# Import the run_model function from run_llm_model.py
from run_llm_model import run_model

# Set up argument parsing
parser = argparse.ArgumentParser(description='Run an LLM model on a given case')
parser.add_argument('--model', type=str, required=True, help='Name of the LLM model to use')
parser.add_argument('--prompt', type=str, default='default', help='Name of the prompt file to use')
parser.add_argument('--case', type=str, required=True, help='Identifier of the case in the format of X-Y-Z')
# Add an option to enable chain-of-thought
parser.add_argument('--cot_few_shot', action='store_true', help='Enable chain-of-thought with few-shot examples')
# Add an option to set the logging level
parser.add_argument('--log_level', type=str, default='DEBUG', help='Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
# Add an option to specify a log file
parser.add_argument('--log_file', type=str, help='File path to save logs')
parser.add_argument('--summary', action='store_true', help='Enable summarization before cot')


def setup_logging(log_level: str, log_file: str = None):
    """Set up logging configuration."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')

    # Define log format
    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    if log_file:
        # Ensure the directory for the log file exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        # Configure logging to file
        logging.basicConfig(
            level=numeric_level,
            format=log_format,
            datefmt=date_format,
            handlers=[
                logging.FileHandler(log_file, mode='a'),
                logging.StreamHandler()  # Also output to console
            ]
        )
        print("Logging to file: ", log_file)
    else:
        # Configure logging to console only
        logging.basicConfig(
            level=numeric_level,
            format=log_format,
            datefmt=date_format
        )
        print("Logging to console only")


def load_prompt(prompt_name: str) -> str:
    """Load the prompt from a file."""
    prompt_path = os.path.join(os.getcwd(), 'prompts/system_prompts', f'{prompt_name}.txt')
    logging.info(f"Loading prompt from: {prompt_path}")
    with open(prompt_path, 'r') as file:
        prompt = file.read().strip()
    logging.info(f"Prompt loaded successfully. Length: {len(prompt)} characters")
    return prompt


def extract_json_from_response(response: str) -> str:
    """Extract the innermost JSON object from the model's response, handling 'Final Answer:' in CoT."""
    try:
        # First, look for the 'Final Answer:' marker
        marker = "Final Answer:"
        idx = response.find(marker)
        if idx != -1:
            # Extract everything after 'Final Answer:'
            response = response[idx + len(marker):].strip()
        else:
            # If 'Final Answer:' is not found, use the entire response
            response = response.strip()

        # Initialize variables to track the innermost JSON object
        brace_stack = []
        innermost_json = ''
        start_idx = None

        # Iterate over the response character by character
        for i, char in enumerate(response):
            if char == '{':
                brace_stack.append(i)
            elif char == '}':
                if brace_stack:
                    start_idx = brace_stack.pop()
                    if not brace_stack:
                        # Found an innermost JSON object
                        innermost_json = response[start_idx:i+1].strip()
                        # Break after finding the innermost JSON object
                        break

        if innermost_json:
            return innermost_json
        else:
            return None
    except Exception as e:
        logging.error(f"Error extracting JSON from response: {e}")
        return None


def load_cot_prompt(prompt_name="1-1-1_cot_prompt"):
    prompt_path = os.path.join(os.getcwd(), 'prompts/cot_prompts', f'{prompt_name}.txt')
    with open(prompt_path, 'r') as file:
        prompt = file.read().strip()
    logging.info(f"CoT prompt loaded successfully. Length: {len(prompt)} characters")
    return prompt


async def get_model_action(model: str, prompt: str, turn_data: Dict[str, Any],
                           court_record: Dict[str, List[Dict[str, str]]], cot: bool) -> str:
    """Generate the model's action based on the current turn data and court record."""
    logging.info(f"Generating model action for turn: {turn_data.get('turn_number', 'Unknown')}")
    context = turn_data["context"] + "\n"

    # Adding cross-examination data to the prompt
    if turn_data["category"] == "cross_examination":
        # Modify the prompt based on whether CoT is enabled
        if cot:
            # Add few-shot examples for chain-of-thought
            prompt += (
                'The following is the chain-of-thought QA history that you may find useful in helping you make a decision:\n'
            )
            # Add few-shot examples (adjusted to be relevant)
            cot_prompt = load_cot_prompt()
            prompt += cot_prompt

        # Basic information for cross-examination
        prompt += "\nBelow are the witness' testimonies:\n"
        for i, action_data in enumerate(turn_data["testimonies"]):
            prompt += f"{i}: {action_data['testimony']}\n"
        prompt += "Below are the evidences you have:\n"
        for i, obj in enumerate(court_record["objects"]):
            prompt += f"{i}: {obj}\n"
        prompt += "Below are the people relevant in this case:\n"
        for i, character in enumerate(court_record["characters"]):
            prompt += f"{i}: {character}\n"

        if cot:
            prompt += (
                'You may now present evidence that is helpful in finding a contradiction in the testimony. '
                'To present evidence, answer the question with a JSON object in the format of {"action": '
                '"present", "testimony": <number of the testimony>, "evidence": <number of the evidence>}, '
                'for example {"action": "present", "testimony": 5, "evidence": 2}.\n'
                'Note that the evidence, character, and testimony is listed from 0 to n-1, so your response should be 0-indexed.\n'
                'Explain your reasoning step by step before providing the JSON object. Conclude your answer with "Final Answer:" followed by the JSON object on a new line.\n'
                'The following is the context of the case that you may find useful in helping you make a decision:\n'
            )
        else:
            prompt += (
                'You may now present evidence that is helpful in finding a contradiction in the testimony. '
                'To present evidence, answer the question with a JSON object in the format of {"action": '
                '"present", "testimony": <number of the testimony>, "evidence": <number of the evidence>}, '
                'for example {"action": "present", "testimony": 5, "evidence": 2}.\n'
                'Note that the evidence, character, and testimony is listed from 0 to n-1, so your response should be 0-indexed.\n'
                'Your response should contain only the JSON object, no other text, no markdown formatting, and no explanations.\n'
                'The following is the context of the case that you may find useful in helping you make a decision:\n'
            )

        full_prompt = prompt + context
        messages = [{"role": "user", "content": full_prompt}]

        while True:
            logging.info("Attempting to get model action")
            # Use the run_model function from run_llm_model.py
            response = await run_model(model, messages)
            logging.info(f"Model response received. Length: {len(response)} characters")
            logging.info("Model response content: %s", response)

            if cot:
                # Try to extract the JSON object from the response
                json_str = extract_json_from_response(response)
                if json_str:
                    try:
                        json_str = json_str.strip()
                        # Remove Markdown code block markers if present
                        if json_str.startswith('```'):
                            json_str = json_str.strip('`').strip()
                        # Remove the 'json' label if present
                        if json_str.startswith('json'):
                            json_str = json_str[len('json'):].strip()
                        # Parse the JSON string
                        action = json.loads(json_str)
                        if action.get("action") == "present" and "testimony" in action and "evidence" in action:
                            logging.info(f"Valid action received: {action}")
                            return {
                                "action": f"present@{action['evidence']}@{action['testimony']}",
                                "response": response
                            }
                        else:
                            logging.warning(f"Invalid action received: {action}")
                            # update messages with the gpt response and revision suggestions
                            messages.append({"role": "assistant", "content": response})
                            messages.append({
                                "role": "user", 
                                "content": "Your previous response was in an incorrect format. Please provide a valid JSON " +
                                "object with 'action', 'testimony', and 'evidence' fields. " +
                                "The 'action' must be 'present'. Remember to explain your reasoning step by step before providing the JSON object."
                                })

                    except json.JSONDecodeError:
                        logging.error("JSON decode error: extracted string is not a valid JSON object\n")
                        logging.info(f"Extracted JSON string: {json_str}")
                        # update messages with the gpt response and revision suggestions
                        messages.append({"role": "assistant", "content": response})
                        messages.append({
                            "role": "user", 
                            "content": "Your previous response was not a valid JSON object. Please provide your reasoning and then a valid JSON response."
                        })

                else:
                    logging.warning("No JSON object found in the response")
                    # update messages with the gpt response and revision suggestions
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user", 
                        "content": "Your previous response did not contain a JSON object. Please explain your reasoning step by step and then provide a valid JSON response."
                    })
            else:
                try:
                    json_str = response.strip()
                    # Clean up the response if it contains Markdown code block markers
                    if json_str.startswith('```'):
                        json_str = json_str.strip('`').strip()
                    if json_str.startswith('json'):
                        json_str = json_str[len('json'):].strip()
                    action = json.loads(json_str)
                    if action.get("action") == "present" and "testimony" in action and "evidence" in action:
                        logging.info(f"Valid action received: {action}")
                        return {
                                "action": f"present@{action['evidence']}@{action['testimony']}",
                                "response": response
                            }
                    else:
                        logging.warning(f"Invalid action received: {action}")
                        # update messages with the gpt response and revision suggestions
                        messages.append({"role": "assistant", "content": response})
                        messages.append({"role": "user", "content": "Your previous response was in an incorrect format. Please provide a valid JSON " +
                            "object with 'action', 'testimony', and 'evidence' fields. " +
                            "The 'action' must be 'present'."})
                    
                except json.JSONDecodeError:
                    logging.error("JSON decode error: response is not a valid JSON object")
                    # update messages with the gpt response and revision suggestions
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": "Your previous response was not a valid JSON object. Please provide a valid JSON response."})
    else:
        logging.warning("No action generated for this turn which is not cross-examination")
        raise ValueError("No action generated for this turn which is not cross-examination")


async def simulate(model: str, prompt: str, case_data: List[Dict[str, Any]], cot: bool) -> List[Dict[str, Any]]:
    """Simulate the case and return the model's outputs."""
    outputs = []
    logging.info(f"Starting simulation for model: {model}")
    for turn_number, turn_data in enumerate(case_data, 1):
        logging.info(f"Processing turn {turn_number}")
        # No present available in this turn
        if turn_data.get("no_present"):
            logging.info("No present available in this turn. Skipping.")
            continue

        court_record = {"objects": turn_data["court_record"]["evidence_objects"],
                        "characters": turn_data["characters"]}

        if turn_data["category"] == "cross_examination":
            results = await get_model_action(model, prompt, turn_data, court_record, cot)
            action = results["action"]
            response = results["response"]
            outputs.append({
                "turn": turn_data,
                "action": action,
                "response": response
            })
            logging.info(f"Action for turn {turn_number}: {action}")

    logging.info(f"Simulation complete. Total outputs: {len(outputs)}")
    return outputs


async def main():
    args = parser.parse_args()
    # Setup logging with optional log file
    cot_few_shot_suffix = "_cot_few_shot" if args.cot_few_shot else ""
    # Get current date and time in the desired format (e.g., YYYYMMDD_HHMMSS)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Setup logging with log file
    if args.log_file:
        log_file = os.getcwd() + f"/logs/close_llm/job_{args.model}_{args.prompt}{cot_few_shot_suffix}_{args.log_file}.log"
    else:
        log_file = os.getcwd() + f"/logs/close_llm/job_{args.model}_{args.prompt}{cot_few_shot_suffix}_default_log_{timestamp}.log"

    setup_logging(args.log_level, log_file)
    logging.info(f"Starting script with arguments: model={args.model}, prompt={args.prompt}, case={args.case}, cot={args.cot_few_shot}")

    # Load the case data
    case_file_path = f"../case_data/final_full_context/{args.case}.json"
    logging.info(f"Loading case data from: {case_file_path}")
    with open(case_file_path, 'r') as file:
        case_data = json.load(file)
    logging.info(f"Case data loaded successfully. Number of turns: {len(case_data)}")

    # Load the system prompt
    prompt = load_prompt(args.prompt)

    # Run the simulation
    outputs = await simulate(args.model, prompt, case_data, args.cot_few_shot)

    # Save the outputs
    output_dir = os.path.join("closed_model_output", args.model, args.prompt)
    os.makedirs(output_dir, exist_ok=True)
    # Include 'cot' in the output filename if enabled
    cot_few_shot_suffix = "_cot_few_shot" if args.cot_few_shot else ""
    output_file = os.path.join(output_dir, f"{args.case}_output{cot_few_shot_suffix}.json")
    logging.info(f"Saving output to: {output_file}")
    with open(output_file, 'w') as file:
        json.dump(outputs, file, indent=2)

    logging.info(f"Output saved successfully. Number of outputs: {len(outputs)}")


if __name__ == '__main__':
    asyncio.run(main())
