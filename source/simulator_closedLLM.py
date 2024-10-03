import argparse
import json
import asyncio
import os
from typing import List, Dict, Any

# Import the run_model function from run_llm_model.py
from run_llm_model import run_model

# Set up argument parsing
parser = argparse.ArgumentParser(description='Run an LLM model on a given case')
parser.add_argument('--model', type=str, required=True, help='Name of the LLM model to use')
parser.add_argument('--prompt', type=str, default='default', help='Name of the prompt file to use')
parser.add_argument('--case', type=str, required=True, help='Identifier of the case in the format of X-Y-Z')


def load_prompt(prompt_name: str) -> str:
    """Load the prompt from a file."""
    prompt_path = os.path.join(os.getcwd(), 'prompts', f'{prompt_name}.txt')
    print(f"Loading prompt from: {prompt_path}")
    with open(prompt_path, 'r') as file:
        prompt = file.read().strip()
    print(f"Prompt loaded successfully. Length: {len(prompt)} characters")
    return prompt


async def get_model_action(model: str, prompt: str, turn_data: Dict[str, Any],
                           court_record: Dict[str, List[Dict[str, str]]]) -> str:
    """Generate the model's action based on the current turn data and court record."""
    print(f"Generating model action for turn: {turn_data.get('turn_number', 'Unknown')}")
    context = turn_data["context"] + "\n"
    
    # Adding cross-examination data to the prompt
    if turn_data["category"] == "cross_examination":
        prompt += "\nBelow are the witness' testimonies:\n"
        for i, action_data in enumerate(turn_data["testimonies"]):
            prompt += f"{i}: {action_data['testimony']}\n"
        prompt += "Below are the evidences you have:\n"
        for i, obj in enumerate(court_record["objects"]):
            prompt += f"{i}: {obj}\n"
        prompt += "Below are the people relevant in this case:\n"
        for i, character in enumerate(court_record["characters"]):
            prompt += f"{i}: {character}\n"
        prompt += (
            'You may now present evidence that is helpful in finding a contradiction in the testimony. '
            'To present evidence, answer the question with a JSON object in the format of {"action": '
            '"present", "testimony": <number of the testimony>, "evidence": <number of the evidence>}, '
            'for example {"action": "present", "testimony": 5, "evidence": 2}\n'
            'Your response should contain only the JSON object, no other text, no markdown formatting, and no explanations.\n'
            'The following is the context of the case that you may find useful in helping you make decision:\n'
        )


    full_prompt = prompt + context

    print("Prompt content: \n", prompt)

    print(f"Full prompt length: {len(full_prompt)} characters")

    while True:
        print("Attempting to get model action")
        # Use the run_model function from run_llm_model.py
        response = await run_model(model, full_prompt)
        print(f"Model response received. Length: {len(response)} characters")
        print("Model response content: ", response)

        try:
            action = json.loads(response)
            if action.get("action") == "present" and "testimony" in action and "evidence" in action:
                print(f"Valid action received: {action}")
                return f"present@{action['evidence']}@{action['testimony']}"
            else:
                print(f"Invalid action received: {action}")
                # Add an error message to prompt the model to give a valid response
                full_prompt += ("\n\nYour previous response was in an incorrect format. Please provide a valid JSON "
                                "object with 'action', 'testimony', and 'evidence' fields. "
                                "The 'action' must be 'present'.")
        except json.JSONDecodeError:
            print("JSON decode error: response is not a valid JSON object")
            # Add an error message to prompt the model to give a valid response
            full_prompt += ("\n\nYour previous response was not a valid JSON object. "
                            "Please provide a valid JSON response.")
    # # A parameter we can set by ourselves
    # max_retries = 3
    # for attempt in range(max_retries):
    #     print(f"Attempt {attempt + 1} to get model action")
    #     # Use the run_model function from run_llm_model.py
    #     response = await run_model(model, full_prompt)
    #     print(f"Model response received. Length: {len(response)} characters")
    #
    #     try:
    #         action = json.loads(response)
    #         if action.get("action") == "present" and "testimony" in action and "evidence" in action:
    #             print(f"Valid action received: {action}")
    #             return f"present@{action['evidence']}@{action['testimony']}"
    #         else:
    #             print(f"Invalid action received: {action}")
    #             if attempt < max_retries - 1:
    #                 full_prompt += ("\n\nYour previous response was invalid. Please provide a valid JSON "
    #                                 "object with 'action', 'testimony', and 'evidence' fields. "
    #                                 "The 'action' must be 'present'.")
    #             else:
    #                 print("Max attempts reached. Returning error message.")
    #                 return "invalid action after multiple attempts"
    #     except json.JSONDecodeError:
    #         print(f"JSON decode error on attempt {attempt + 1}")
    #         if attempt < max_retries - 1:
    #             full_prompt += ("\n\nYour previous response was not a valid JSON object. "
    #                             "Please provide a valid JSON response.")
    #         else:
    #             print("Max attempts reached. Returning error message.")
    #             return "invalid JSON returned by the LLM after multiple attempts"


async def simulate(model: str, prompt: str, case_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Simulate the case and return the model's outputs."""
    outputs = []
    print(f"\nStarting simulation for model: {model}")
    for turn_number, turn_data in enumerate(case_data, 1):
        print(f"Processing turn {turn_number}")
        # No present available in this turn
        if turn_data.get("no_present"):
            print("No present available in this turn. Skipping.")
            continue

        court_record = {"objects": turn_data["court_record"]["evidence_objects"],
                        "characters": turn_data["characters"]}

        if turn_data["category"] == "cross_examination":
            action = await get_model_action(model, prompt, turn_data, court_record)
            outputs.append({
                "turn": turn_data,
                "action": action
            })
            print(f"Action for turn {turn_number}: {action}")

    print(f"Simulation complete. Total outputs: {len(outputs)}")
    return outputs


async def main():
    args = parser.parse_args()
    print(f"Starting script with arguments: model={args.model}, prompt={args.prompt}, case={args.case}")

    # Load the case data
    case_file_path = f"../case_data/generated/parsed/{args.case}.json"
    print(f"Loading case data from: {case_file_path}")
    with open(case_file_path, 'r') as file:
        case_data = json.load(file)
    print(f"Case data loaded successfully. Number of turns: {len(case_data)}")

    # Load the prompt
    prompt = load_prompt(args.prompt)

    # Run the simulation
    outputs = await simulate(args.model, prompt, case_data)

    # Save the outputs
    output_dir = os.path.join("closed_model_output", args.model, args.prompt)
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{args.case}_output.json")
    print(f"Saving output to: {output_file}")
    with open(output_file, 'w') as file:
        json.dump(outputs, file, indent=2)

    print(f"Output saved successfully. Number of outputs: {len(outputs)}")


if __name__ == '__main__':
    asyncio.run(main())

# import argparse
# import json
# import asyncio
# import os
# from typing import List, Dict, Any
# 
# # Import the run_model function from run_llm_model.py
# from run_llm_model import run_model
# 
# # Set up argument parsing
# parser = argparse.ArgumentParser(description='Run an LLM model on a given case')
# parser.add_argument('--model', type=str, required=True, help='Name of the LLM model to use')
# parser.add_argument('--prompt', type=str, default='default', help='Name of the prompt file to use')
# parser.add_argument('--case', type=str, required=True, help='Identifier of the case in the format of X-Y-Z')
# 
# 
# def load_prompt(prompt_name: str) -> str:
#     """Load the prompt from a file."""
#     prompt_path = os.path.join(os.getcwd(), 'prompts', f'{prompt_name}.txt')
#     with open(prompt_path, 'r') as file:
#         return file.read().strip()
# 
# 
# async def get_model_action(model: str, prompt: str, turn_data: Dict[str, Any],
#                            court_record: Dict[str, List[Dict[str, str]]]) -> str:
#     """Generate the model's action based on the current turn data and court record."""
#     context = turn_data["context"] + "\n"
# 
#     if turn_data["category"] == "cross_examination":
#         prompt += "\nBelow are the witness' testimonies:\n"
#         for i, action_data in enumerate(turn_data["testimonies"]):
#             prompt += f"{i}: {action_data['testimony']}\n"
#         prompt += "Below are the evidences you have:\n"
#         for i, obj in enumerate(court_record["objects"]):
#             prompt += f"{i}: {obj['name']}\n"
#         for i, character in enumerate(court_record["characters"]):
#             prompt += f"{i}: {character}\n"
#         prompt += (
#             'You may now present evidence that is helpful in finding a contradiction in the testimony. '
#             'To present evidence, answer the question with a JSON object in the format of {"action": '
#             '"present", "testimony": <number of the testimony>, "evidence": <number of the evidence>}, '
#             'for example {"action": "present", "testimony": 5, "evidence": 2}'
#         )
# 
#     full_prompt = context + prompt
# 
#     # A parameter we can set by ourselves
#     max_retries = 3
#     for attempt in range(max_retries):
#         # Use the run_model function from run_llm_model.py
#         response = await run_model(model, full_prompt)
# 
#         try:
#             action = json.loads(response)
#             if action.get("action") == "present" and "testimony" in action and "evidence" in action:
#                 return f"present@{action['evidence']}@{action['testimony']}"
#             else:
#                 if attempt < max_retries - 1:
#                     full_prompt += ("\n\nYour previous response was invalid. Please provide a valid JSON "
#                                     "object with 'action', 'testimony', and 'evidence' fields. "
#                                     "The 'action' must be 'present'.")
#                 else:
#                     return "invalid action after multiple attempts"
#         except json.JSONDecodeError:
#             if attempt < max_retries - 1:
#                 full_prompt += ("\n\nYour previous response was not a valid JSON object. "
#                                 "Please provide a valid JSON response.")
#             else:
#                 return "invalid JSON returned by the LLM after multiple attempts"
# 
#     return "max retries reached without a valid response"
# 
# 
# async def simulate(model: str, prompt: str, case_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#     """Simulate the case and return the model's outputs."""
#     outputs = []
#     for turn_data in case_data:
#         # No present available in this turn
#         if turn_data.get("no_present"):
#             continue
# 
#         court_record = {"objects": turn_data["court_record"]["evidence_objects"],
#                         "characters": turn_data["characters"]}
# 
#         if turn_data["category"] == "cross_examination":
#             action = await get_model_action(model, prompt, turn_data, court_record)
#             outputs.append({
#                 "turn": turn_data,
#                 "action": action
#             })
# 
#     return outputs
# 
# 
# async def main():
#     args = parser.parse_args()
# 
#     # Load the case data
#     case_file_path = f"../case_data/generated/parsed/{args.case}.json"
#     with open(case_file_path, 'r') as file:
#         case_data = json.load(file)
# 
#     # Load the prompt
#     prompt = load_prompt(args.prompt)
# 
#     # Run the simulation
#     outputs = await simulate(args.model, prompt, case_data)
# 
#     # Save the outputs
#     output_dir = os.path.join("closed_model_output", args.model, args.prompt)
#     os.makedirs(output_dir, exist_ok=True)
#     output_file = os.path.join(output_dir, f"{args.case}_output.json")
#     with open(output_file, 'w') as file:
#         json.dump(outputs, file, indent=2)
# 
#     print(f"Output saved to {output_file}")
# 
# 
# if __name__ == '__main__':
#     asyncio.run(main())