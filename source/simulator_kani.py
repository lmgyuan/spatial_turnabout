# One-shot with -prompt arg
import argparse
import json
import asyncio
import os
from typing import List, Dict, Any

# Import the necessary LLM API libraries
from transformers import pipeline as hf_pipeline
import openai

# Set up argument parsing
parser = argparse.ArgumentParser(description='Run an LLM model on a given case')
parser.add_argument('--model', type=str, required=True, help='Name of the LLM model to use')
parser.add_argument('--prompt', type=str, default='default', help='Name of the prompt file to use')
parser.add_argument('--case', type=str, required=True, help='Identifier of the case in the format of X-Y-Z')


async def run_open_source_model(model: str, messages: List[Dict[str, str]], prompt: str) -> str:
    """Run an open-source model using the Hugging Face pipeline."""
    full_prompt = prompt + "\n" + "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    generator = hf_pipeline("text-generation", model=model)
    response = generator(full_prompt, max_length=500, num_return_sequences=1)[0]['generated_text']
    return response.split(full_prompt)[-1].strip()


async def run_closed_source_model(model: str, messages: List[Dict[str, str]], prompt: str) -> str:
    """Run a closed-source model (e.g., OpenAI's GPT models)."""
    full_messages = [{"role": "system", "content": prompt}] + messages
    response = await openai.ChatCompletion.acreate(model=model, messages=full_messages)
    return response.choices[0].message.content.strip()


def load_prompt(prompt_name: str) -> str:
    """Load the prompt from a file."""
    prompt_path = os.path.join('source', 'prompts/system_prompts', f'{prompt_name}.txt')
    with open(prompt_path, 'r') as file:
        return file.read().strip()


async def get_model_action(model: str, prompt: str, turn_data: Dict[str, Any],
                           court_record: Dict[str, List[Dict[str, str]]]) -> str:
    """Generate the model's action based on the current turn data and court record."""
    context = turn_data["context"] + "\n"
    messages = []

    if turn_data["category"] == "cross_examination":
        prompt += "\nBelow are the witness' testimonies:\n"
        for i, action_data in enumerate(turn_data["testimonies"]):
            prompt += f"{i}: {action_data['testimony']}\n"
        prompt += "Below are the evidences you have:\n"
        for i, obj in enumerate(court_record["objects"]):
            prompt += f"{i}: {obj['name']}\n"
        prompt += (
            'You may now present evidence that is helpful in finding a contradiction in the testimony. '
            'To present evidence, answer the question with a JSON object in the format of {"action": '
            '"present", "testimony": <number of the testimony>, "evidence": <number of the evidence>}, '
            'for example {"action": "present", "testimony": 5, "evidence": 2}'
        )

    messages.append({"role": "user", "content": context + prompt})

    if model in ['gpt-3.5-turbo', 'gpt-4']:  # Add more closed-source models as needed
        response = await run_closed_source_model(model, messages, prompt)
    else:
        response = await run_open_source_model(model, messages, prompt)

    try:
        action = json.loads(response)
        if action.get("action") == "present":
            return f"present@{action['evidence']}@{action['testimony']}"
        else:
            raise ValueError("Invalid action")
    except (json.JSONDecodeError, ValueError):
        return "invalid"


async def simulate(model: str, prompt: str, case_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Simulate the case and return the model's outputs."""
    outputs = []
    for turn_data in case_data:
        if turn_data.get("no_present"):
            continue

        court_record = {"objects": turn_data["court_record"]["evidence_objects"]}

        if turn_data["category"] == "cross_examination":
            action = await get_model_action(model, prompt, turn_data, court_record)
            outputs.append({
                "turn": turn_data,
                "action": action
            })

    return outputs


async def main():
    args = parser.parse_args()

    # Load the case data
    case_file_path = f"../case_data/generated/parsed/{args.case}.json"
    with open(case_file_path, 'r') as file:
        case_data = json.load(file)

    # Load the prompt
    prompt = load_prompt(args.prompt)

    # Run the simulation
    outputs = await simulate(args.model, prompt, case_data)

    # Save the outputs
    output_dir = os.path.join(args.model, args.prompt)
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{args.case}_output.json")
    with open(output_file, 'w') as file:
        json.dump(outputs, file, indent=2)

    print(f"Output saved to {output_file}")


if __name__ == '__main__':
    asyncio.run(main())

# # One-shot
# # simulator_kani.py
#
# import argparse
# import json
# import asyncio
# from run_llm_model import run_model  # Import the run_model function
#
# # Read the predefined response for incorrect evidence presentation
# WRONG_EVIDENCE_RESPONSE = open("../case_data/hand_coded/wrong_evidence_response.txt", "r").read()
#
# # Set up command-line argument parsing
# parser = argparse.ArgumentParser(description='')
# parser.add_argument('--case', type=str, help='Identifier of the case in the format of X-Y')
# parser.add_argument('--player', type=str, help='Name of the LLM model to use')
# args = parser.parse_args()
#
# async def get_model_action(turn_data, court_record):
#     """
#     Generates the LLM's action based on the current turn data and court record.
#     Allows multiple attempts if the response is not valid.
#     """
#     # Construct the context for the LLM
#     context = turn_data["context"] + "\n"
#     feedback_messages = []  # List to hold feedback messages for the LLM
#
#     while True:
#         # Build the prompt including any feedback messages
#         prompt = ""
#         if feedback_messages:
#             prompt += "\n".join(feedback_messages) + "\n"
#
#         # Add the main content to the prompt
#         if turn_data["category"] == "cross_examination":
#             # Add witness testimonies to the prompt
#             prompt += "Below are the witness' testimonies:\n"
#             for i, action_data in enumerate(turn_data["testimonies"]):
#                 prompt += f"{i}: {action_data['testimony']}\n"
#             # Add available evidence to the prompt
#             prompt += "Below are the evidences you have:\n"
#             for i, obj in enumerate(court_record["objects"]):
#                 prompt += f"{i}: {obj['name']}\n"
#             # Provide instructions for the LLM to present evidence
#             prompt += (
#                 'You may now present evidence that is helpful in finding a contradiction in the testimony. '
#                 'To present evidence, answer the question with a JSON object in the format of {"action": '
#                 '"present", "testimony": <number of the testimony>, "evidence": <number of the evidence>}, '
#                 'for example {"action": "present", "testimony": 5, "evidence": 2}'
#             )
#         else:
#             # If not cross-examination, skip this turn
#             return None
#
#         # Combine context and prompt
#         full_prompt = context + prompt
#
#         try:
#             # Generate the LLM's response
#             gen_json = await run_model(args.player, full_prompt)
#         except Exception as e:
#             print(f"Error occurred: {e}")
#             continue
#
#         print("The model generated this json: ", gen_json)
#
#         try:
#             # Attempt to parse the LLM's response as JSON
#             response = json.loads(gen_json)
#             if response.get("action") == "present":
#                 # Construct the action string expected by the simulation
#                 gen_text = "present@" + str(response["evidence"]) + "@" + str(response["testimony"])
#                 print("Action received from LLM: ", gen_text)
#                 return gen_text
#             else:
#                 print("Invalid action:", gen_json)
#                 # Add feedback message
#                 feedback_messages.append("Invalid action provided. Please provide a 'present' action in the correct format.")
#         except json.JSONDecodeError:
#             # If the JSON is not well-formed, add feedback and continue the loop
#             print("Invalid JSON format.")
#             feedback_messages.append("Your previous input was not a well-formed JSON. Please try again.")
#
# async def simulate(case_data):
#     """
#     Simulates the case by iterating through each turn,
#     handling cross-examination logic, processing the LLM's actions,
#     and updating the game state.
#     """
#     # Initialize the court record
#     num_questions = 0  # Total number of questions (turns requiring an answer)
#     num_correct = 0    # Number of correct answers provided by the LLM
#
#     # Iterate over each turn in the case data
#     for turn_data in case_data:
#         court_record = {"objects": [], "people": []}
#         print("Context of current turn: ", turn_data["context"])
#         if turn_data.get("no_present"):
#             print("There is no evidence or people to be presented in this turn, so skipping.")
#             continue
#
#         # This is a valid question turn
#         num_questions += 1
#
#         # Update the court record with the current turn's evidence
#         court_record["objects"] = turn_data["court_record"]["evidence_objects"]
#         court_record["characters"] = turn_data["characters"]
#
#         # Check if the current turn is a cross-examination phase
#         if turn_data["category"] == "cross_examination":
#             can_proceed = False  # Flag to determine if we can proceed to the next turn
#
#             # Continue prompting until the LLM provides a valid 'present' action
#             while not can_proceed:
#                 # Display the witness testimonies with their indices
#                 print("\n=== Cross Examination ===\n")
#                 for i, action_data in enumerate(turn_data["testimonies"]):
#                     print(f"{i}: {action_data['testimony']}")
#
#                 # Get the LLM's action
#                 user_input = await get_model_action(turn_data, court_record)
#                 if user_input is None:
#                     # If get_model_action returns None, skip this turn
#                     break
#
#                 # Process the LLM's action
#                 try:
#                     user_action = user_input.split("@")[0]
#                 except IndexError:
#                     print("Invalid format of action. Please ensure the action is in the correct format.")
#                     continue
#
#                 if user_action != "present":
#                     print("Invalid action provided.")
#                     # Since the action is not 'present', allow the LLM to try again
#                     continue
#
#                 # Extract indices from the action string
#                 try:
#                     user_evidence_index = int(user_input.split("@")[1])
#                     user_testimony_index = int(user_input.split("@")[2])
#                 except (IndexError, ValueError):
#                     print("Invalid format of action. Please ensure the action is in the correct format.")
#                     continue
#
#                 # Get the name of the evidence presented and the testimony
#                 try:
#                     user_evidence = court_record["objects"][user_evidence_index]["name"]
#                     action_data = turn_data["testimonies"][user_testimony_index]
#                 except IndexError:
#                     # If the indices are out of range, inform and continue
#                     print("Invalid indices provided.")
#                     continue
#
#                 # Check if the presented evidence is correct for the selected testimony
#                 if user_evidence in action_data["present"]:
#                     # Correct evidence presented; increment num_correct
#                     print("Correct evidence presented!")
#                     num_correct += 1
#                 else:
#                     # Incorrect evidence; provide feedback but move on to the next turn
#                     print(WRONG_EVIDENCE_RESPONSE)
#                 # Proceed to the next turn regardless
#                 can_proceed = True
#
#     # At the end, print the results
#     print(f"Total questions: {num_questions}")
#     print(f"Total correct answers: {num_correct}")
#     print(f"Final Accuracy: {num_correct / num_questions}")
#
#
# async def main():
#     """
#     Loads the case data and starts the simulation.
#     """
#     # Construct the file path for the case data
#     file_path = "../case_data/generated/parsed/{}.json".format(args.case)
#     print("Looking for file:", file_path)
#     try:
#         # Open and load the case data from the JSON file
#         with open(file_path, 'r') as file:
#             case_data = json.load(file)
#         # Start the simulation with the loaded case data
#         await simulate(case_data)
#     except FileNotFoundError:
#         print(f"File not found: {file_path}")
#         raise
#
# if __name__ == '__main__':
#     # Run the main function asynchronously
#     asyncio.run(main())


# Long-context multiple turns memory
# import argparse
# import json
# import asyncio
# from run_llm_model import run_model
#
# # Read the predefined response for incorrect evidence presentation
# WRONG_EVIDENCE_RESPONSE = open("../case_data/hand_coded/wrong_evidence_response.txt", "r").read()
# TRUNCATE_PAST_DIALOGS = 6
#
# # Set up command-line argument parsing
# parser = argparse.ArgumentParser(description='')
# parser.add_argument('--case', type=str, help='Identifier of the case in the format of X-Y')
# parser.add_argument('--player', type=str, help='Name of the LLM model to use')
# args = parser.parse_args()
#
# async def get_model_action(past_dialogs, turn_data, court_record):
#     """
#     Generates the LLM's action based on the current turn data and court record.
#     """
#     # Construct the context and prompt for the LLM
#     context = turn_data["context"] + "\n"
#     prompt = ""
#     if turn_data["category"] == "cross_examination":
#         # Add witness testimonies to the prompt
#         prompt += "Below are the witness' testimonies:\n"
#         for i, action_data in enumerate(turn_data["testimonies"]):
#             prompt += f"{i} {action_data['testimony']}\n"
#         # Add available evidence to the prompt
#         prompt += "Below are the evidences you have:\n"
#         for i, obj in enumerate(court_record["objects"]):
#             prompt += f"{i} {obj['name']}\n"
#         # Provide instructions for the LLM to present evidence
#         prompt += (
#             'You may now present evidence that is helpful in finding a contradiction in the testimony. '
#             'To present evidence, answer the question with a JSON object in the format of {"action": '
#             '"present", "testimony": <number of the testimony>, "evidence": <number of the evidence>}, '
#             'for example {"action": "present", "testimony": 5, "evidence": 2}'
#         )
#
#     # Add the prompt to the conversation history
#     prompt_dict = {"role": "user", "content": context + prompt}
#     past_dialogs.append(prompt_dict)
#     is_json_well_formed = False
#
#     while not is_json_well_formed:
#         model_run_success = False
#         while not model_run_success:
#             try:
#                 # Generate the LLM's response
#                 gen_json = await run_model(args.player, past_dialogs, prompt)
#                 model_run_success = True
#             except Exception as e:
#                 print(f"Error occurred: {e}")
#                 print("Input too long, truncating past dialogs")
#                 # Truncate past dialogs to avoid input length issues
#                 past_dialogs = past_dialogs[2:]
#                 continue
#         print("The model generated this json: ", gen_json)
#         # Add the LLM's response to the conversation history
#         response_dict = {"role": "assistant", "content": gen_json}
#         past_dialogs.append(response_dict)
#         try:
#             # Attempt to parse the LLM's response as JSON
#             response = json.loads(gen_json)
#             if response.get("action") == "present":
#                 # Construct the action string expected by the simulation
#                 gen_text = "present@" + str(response["evidence"]) + "@" + str(response["testimony"])
#             else:
#                 print("Invalid action:", gen_json)
#                 # Inform the LLM of the invalid action
#                 past_dialogs.append({"role": "user", "content": "Invalid action provided. Please provide a 'present' action in the correct format."})
#                 continue
#         except json.JSONDecodeError:
#             # If the JSON is not well-formed, inform the LLM and continue the loop
#             past_dialogs.append({"role": "user", "content": "Your previous input was not a well-formed JSON. Please try again."})
#             continue
#         is_json_well_formed = True
#     print("Action received from LLM: ", gen_text)
#     return gen_text, past_dialogs
#
# async def simulate(case_data):
#     """
#     Simulates the case by iterating through each turn,
#     handling cross-examination logic, processing the LLM's actions,
#     and updating the game state.
#     """
#     # Initialize the court record and conversation history
#     court_record = {"objects": [], "people": []}
#     past_dialogs = []
#     num_questions = 0
#     num_correct = 0
#
#     # Iterate over each turn in the case data
#     for turn_data in case_data:
#         print("Context of current turn: ", turn_data["context"])
#         if turn_data["no_present"]:
#             print("There is evidence or people to be presented in this turn, so skip")
#             continue
#         # We are answering a valid question
#         num_questions += 1
#
#         # Update the court record with the current turn's evidence
#         court_record["objects"] = turn_data["court_record"]["evidence_objects"]
#
#         # Check if the current turn is a cross-examination phase
#         if turn_data["category"] == "cross_examination":
#             can_proceed = False  # Flag to determine if we can proceed to the next turn
#
#             # Continue prompting until the correct evidence is presented
#             while not can_proceed:
#                 # Display the witness testimonies with their indices
#                 print("\n=== Cross Examination ===\n")
#                 for i, action_data in enumerate(turn_data["testimonies"]):
#                     print(f"{i}: {action_data['testimony']}")
#
#                 # Get the LLM's action and updated past dialogs
#                 user_input, past_dialogs = await get_model_action(past_dialogs, turn_data, court_record)
#
#                 # Process the LLM's action
#                 user_action = user_input.split("@")[0]
#                 user_evidence_index = int(user_input.split("@")[1])
#                 user_testimony_index = int(user_input.split("@")[-1])
#
#                 if user_action == "present":
#                     # Get the name of the evidence presented
#                     try:
#                         user_evidence = court_record["objects"][user_evidence_index]["name"]
#                         # Retrieve the corresponding testimony data
#                         action_data = turn_data["testimonies"][user_testimony_index]
#                     except IndexError:
#                         # If the indices are out of range, inform the LLM and continue
#                         print("Invalid indices provided.")
#                         past_dialogs.append({"role": "user", "content": "Invalid evidence or testimony number provided. Please try again with valid numbers."})
#                         continue
#
#                     # Check if the presented evidence is correct for the selected testimony
#                     if user_evidence in action_data["present"]:
#                         # Correct evidence presented; proceed to the next turn
#                         print("Correct evidence presented!")
#                         can_proceed = True
#                         num_correct += 1
#                     else:
#                         # Incorrect evidence; provide feedback and continue the loop
#                         print(WRONG_EVIDENCE_RESPONSE)
#                         # Append the feedback to the conversation history
#                         past_dialogs.append({"role": "user", "content": WRONG_EVIDENCE_RESPONSE})
#                 else:
#                     # Invalid action received; inform the LLM
#                     print("Invalid action provided.")
#                     past_dialogs.append({"role": "user", "content": "Invalid action provided. Please provide a 'present' action in the correct format."})
#
# async def main():
#     """
#     Loads the case data and starts the simulation.
#     """
#     # Construct the file path for the case data
#     file_path = "../case_data/scripts/generated/parsed/{}.json".format(args.case)
#     print("Looking for file:", file_path)
#     try:
#         # Open and load the case data from the JSON file
#         with open(file_path, 'r') as file:
#             case_data = json.load(file)
#         # Start the simulation with the loaded case data
#         await simulate(case_data)
#     except FileNotFoundError:
#         print(f"File not found: {file_path}")
#         raise
#
# if __name__ == '__main__':
#     # Run the main function asynchronously
#     asyncio.run(main())


# TODO: The below is written by Manvi
# import argparse
# import json
# import asyncio
# from run_llm_model import run_model
# # import openai
#
# WRONG_EVIDENCE_RESPONSE = open("../case_data/hand_coded/wrong_evidence_response.txt", "r").read()
# TRUNCATE_PAST_DIALOGS = 6
#
# parser = argparse.ArgumentParser(description='')
# parser.add_argument('--case', type=str, help='Identifier of the case in the format of X-Y')
# parser.add_argument('--player', type=str, help='human, or an LLM model name')
# args = parser.parse_args()
#
# async def get_model_action(past_dialogs, turn_data, court_record):
#     if args.player == "human":
#         return input(), past_dialogs
#     else:
#         context = turn_data["context"] + "\n"
#         if turn_data["category"] == "cross_examination":
#             prompt = "Below are the witness' testimonies:\n"
#             for i, action_data in enumerate(turn_data["testimonies"]):
#                 prompt += str(i) + " " + action_data["testimony"] + "\n"
#             prompt += "Below are the evidences you have:\n"
#             for i, obj in enumerate(court_record["objects"]):
#                 prompt += str(i) + " " + obj["name"] + "\n"
#             # prompt += 'You may either press the witness about a specific testimony or present evidence at a testimony to show a contradiction. To press, answer the question with a JSON object in the format of {"action": "press", "testimony": <number of the testimony>}, for example {"action": "press", "testimony": 3}. To present evidence, answer the question with a JSON object in the format of {"action": "present", "testimony": <number of the testimony>, "evidence": <number of the evidence>}, for example {"action": "present", "testimony": 5, "evidence": 2}. Otherwise, you could view the court record by answering with a JSON object in the format of {"action": "court record"}.'
#             prompt += ('You may now present evidence that is helpful in finding a contradiction in the testimony. ' +
#                        'To present evidence, answer the question with a JSON object in the format of {"action": ' +
#                        '"present", "testimony": <number of the testimony>, "evidence": <number of the evidence>}, ' +
#                        'for example {"action": "present", "testimony": 5, "evidence": 2}')
#         prompt_dict = {"role": "user", "content": context + prompt}
#         past_dialogs.append(prompt_dict)
#         is_json_well_formed = False
#         while not is_json_well_formed:
#             model_run_success = False
#             while not model_run_success:
#                 try:
#                     gen_json = await run_model(args.player, past_dialogs, prompt)
#                     model_run_success = True
#                 except Exception as e:
#                     print(f"Error occurred: {e}")
#                     print("Input too long, truncating past dialogs")
#                     past_dialogs = past_dialogs[2:]
#                     continue
#             print("The model generated this json: ", gen_json)
#             response_dict = {"role": "assistant", "content": gen_json}
#             past_dialogs.append(response_dict)
#             try:
#                 response = json.loads(gen_json)
#                 if response.get("action") == "present":
#                     gen_text = "present@" + str(response["evidence"]) + "@" + str(response["testimony"])
#                 else:
#                     print("Invalid action:", gen_json)
#                     raise ValueError("Invalid action")
#             except json.JSONDecodeError:
#                 past_dialogs.append(
#                     {"role": "user", "content": "Your previous input was not a well-formed JSON. Please try again."})
#                 continue
#             is_json_well_formed = True
#             # try:
#             #     if "action" in json.loads(gen_json) and json.loads(gen_json)["action"] == "court record":
#             #         gen_text = "court record"
#             #     elif turn_data["category"] == "cross_examination":
#             #         if json.loads(gen_json)["action"] == "present":
#             #             gen_text = "present@" + str(json.loads(gen_json)["evidence"]) + "@" + str(json.loads(gen_json)["testimony"])
#             #         else:
#             #             print(gen_json)
#             #             raise ValueError("Invalid action")
#             # except json.decoder.JSONDecodeError:
#             #     past_dialogs.append({"role": "user", "content": "Your previous input was not a well-formed JSON. Please try again."})
#             #     continue
#             # is_json_well_formed = True
#         print(gen_text)
#         return gen_text, past_dialogs
#
# def list_court_record(court_record):
#     output = ""
#     output += "===Court Record===\n"
#     output += "Objects:\n"
#     count = 0
#     for obj in court_record["objects"]:
#         output += str(count) + " " + obj["name"] + "\n"
#         output += ":  " + obj["description"] + "\n"
#         count += 1
#     output += "\nPeople:\n"
#     for person in court_record["people"]:
#         output += str(count) + " " + person["name"] + "\n"
#         output += ":  " + person["description"] + "\n"
#         count += 1
#     output += "This is the end of the court record. Please resume your task above."
#     return output
#
# async def simulate(case_data):
#     court_record = {"objects": [], "people": []}
#     past_dialogs = []
#     for turn_data in case_data:
#         print("context of current turn: ", turn_data["context"])
#         court_record["objects"] = turn_data["court_record"]["evidence_objects"]
#         if turn_data["category"] == "cross_examination":
#             can_proceed = False
#             while not can_proceed:
#                 print("\n===Cross Examination===\n")
#                 for i, action_data in enumerate(turn_data["testimonies"]):
#                     print(str(i) + ": " + action_data["testimony"])
#                 print("\nTo present evidence, enter 'present@<number of the evidence>@<number of the testimony>'.\n")
#                 print("\n> ")
#                 user_input, past_dialogs = await get_model_action(past_dialogs, turn_data, court_record)
#                 if user_input == "court record":
#                     print(list_court_record(court_record))
#                     past_dialogs.append({"role": "user", "content": list_court_record(court_record)})
#                     continue
#                 user_action = user_input.split("@")[0]
#                 user_testimony_index = user_input.split("@")[-1]
#                 if user_action == "present":
#                     user_evidence = court_record["objects"][int(user_input.split("@")[1])]["name"]
#                 action_data = turn_data["testimonies"][int(user_testimony_index)]
#                 if user_action == "present":
#                     if user_evidence in action_data["present"]:
#                         can_proceed = True
#                     else:
#                         print(WRONG_EVIDENCE_RESPONSE)
#                         past_dialogs.append({"role": "user", "content": WRONG_EVIDENCE_RESPONSE})
#
# async def main():
#     file_path = "../case_data/scripts/generated/parsed/{}.json".format(args.case)
#     print("Looking for file:", file_path)
#     try:
#         with open(file_path, 'r') as file:
#             case_data = json.load(file)
#         await simulate(case_data)
#     except FileNotFoundError:
#         print(f"File not found: {file_path}")
#         raise
#
# if __name__ == '__main__':
#     asyncio.run(main())
#
