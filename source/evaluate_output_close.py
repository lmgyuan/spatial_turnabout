import argparse
import json
import os

parser = argparse.ArgumentParser(description='Evaluate the output of an LLM model on a given case')
parser.add_argument('--model', type=str, required=True, help='Name of the LLM model used')
parser.add_argument('--prompt', type=str, required=True, help='Name of the prompt used')
parser.add_argument('--case', type=str, required=False, help='Identifier of the case in the format of X-Y-Z')
parser.add_argument('--metric', type=str, default='accuracy', help='Metric to evaluate (e.g., accuracy)')


def load_case_data(case: str) -> dict:
    """Load the original case data."""
    case_file_path = f"../case_data/generated/parsed/{case}.json"
    print(f"Loading case data from: {case_file_path}")
    with open(case_file_path, 'r') as file:
        data = json.load(file)
    print(f"Case data loaded successfully. Number of turns: {len(data)}")
    return data


def load_model_output(model: str, prompt: str, case: str) -> dict:
    """Load the model's output for the given case."""
    output_file = os.path.join("closed_model_output", model, prompt, f"{case}_output.json")
    print(f"Loading model output from: {output_file}")
    with open(output_file, 'r') as file:
        data = json.load(file)
    print(f"Model output loaded successfully. Number of outputs: {len(data)}")
    return data


def load_existing_evaluation_file(file_path: str) -> list:
    """Load existing evaluations from a JSON file if it exists."""
    if os.path.exists(file_path):
        print(f"Loading existing evaluation results from: {file_path}")
        with open(file_path, 'r') as eval_file:
            return json.load(eval_file)
    else:
        print(f"No existing evaluation file found. A new file will be created at: {file_path}")
        return []


def calculate_accuracy(model_output: list, case_name: str, model: str, prompt: str) -> float:
    """Calculate the accuracy of the model's output and save the result to a JSON file."""
    print("Calculating accuracy...")
    correct_actions = 0
    total_actions = 0
    evaluation_results = []

    for output in model_output:
        total_actions += 1
        turn = output["turn"]
        action = output["action"].split("@")
        if action[0] == "present":
            evidence = turn["court_record"]["evidence_objects"][int(action[1])]["name"]
            testimony = turn["testimonies"][int(action[2])]
            is_correct = evidence in testimony["present"]
            if is_correct:
                correct_actions += 1

            # Record evaluation details for this turn
            evaluation_results.append({
                "case_name": case_name,
                "model_action": action[0],
                "evidence": evidence,
                "testimony": testimony,  # Assuming testimony has a "text" field
                "turn_number": total_actions,
                "is_correct": is_correct,
                "total_turns": len(model_output)
            })
            print(f"Turn {total_actions}: Action - {action[0]}, Evidence - {evidence}, Correct: {is_correct}")

    accuracy = correct_actions / total_actions if total_actions > 0 else 0
    print(f"Calculation complete. Correct actions: {correct_actions}, Total actions: {total_actions}")

    return evaluation_results, accuracy


def save_evaluation_results(evaluation_output_file: str, new_results: list):
    """Save evaluation results to the specified JSON file, appending them to existing data if the file exists."""
    # Load existing evaluation data if the file exists
    existing_results = load_existing_evaluation_file(evaluation_output_file)

    # Append new results to existing data
    combined_results = existing_results + new_results

    # Save the updated results to the file
    with open(evaluation_output_file, 'w') as eval_file:
        json.dump(combined_results, eval_file, indent=4)
    print(f"Evaluation results saved to: {evaluation_output_file}")


def main():
    args = parser.parse_args()
    print(
        f"\nStarting evaluation for Model: {args.model}, Prompt: {args.prompt}, Case: {args.case}, Metric: {args.metric}")

    model_output = load_model_output(args.model, args.prompt, args.case)

    if args.metric == 'accuracy':
        evaluation_results, result = calculate_accuracy(model_output, args.case, args.model, args.prompt)
        print(f"Final Accuracy: {result:.2f}")

        # Save the evaluation results to the JSON file
        evaluation_output_file = os.path.join("closed_model_output", args.model, args.prompt, "evaluation.json")
        os.makedirs(os.path.dirname(evaluation_output_file), exist_ok=True)
        save_evaluation_results(evaluation_output_file, evaluation_results)
    else:
        print(f"Metric '{args.metric}' is not implemented.")

    print("Evaluation complete.")


if __name__ == '__main__':
    main()

# import argparse
# import json
# import os
#
# parser = argparse.ArgumentParser(description='Evaluate the output of an LLM model on a given case')
# parser.add_argument('--model', type=str, required=True, help='Name of the LLM model used')
# parser.add_argument('--prompt', type=str, required=True, help='Name of the prompt used')
# parser.add_argument('--case', type=str, required=False, help='Identifier of the case in the format of X-Y-Z')
# parser.add_argument('--metric', type=str, default='accuracy', help='Metric to evaluate (e.g., accuracy)')
#
# def load_case_data(case: str) -> dict:
#     """Load the original case data."""
#     case_file_path = f"../case_data/generated/parsed/{case}.json"
#     print(f"Loading case data from: {case_file_path}")
#     with open(case_file_path, 'r') as file:
#         data = json.load(file)
#     print(f"Case data loaded successfully. Number of turns: {len(data)}")
#     return data
#
# def load_model_output(model: str, prompt: str, case: str) -> dict:
#     """Load the model's output for the given case."""
#     output_file = os.path.join("closed_model_output", model, prompt, f"{case}_output.json")
#     print(f"Loading model output from: {output_file}")
#     with open(output_file, 'r') as file:
#         data = json.load(file)
#     print(f"Model output loaded successfully. Number of outputs: {len(data)}")
#     return data
#
# def calculate_accuracy(model_output: list) -> float:
#     """Calculate the accuracy of the model's output."""
#     print("Calculating accuracy...")
#     correct_actions = 0
#     total_actions = 0
#
#     for output in model_output:
#         total_actions += 1
#         turn = output["turn"]
#         action = output["action"].split("@")
#         if action[0] == "present":
#             evidence = turn["court_record"]["evidence_objects"][int(action[1])]["name"]
#             testimony = turn["testimonies"][int(action[2])]
#             if evidence in testimony["present"]:
#                 correct_actions += 1
#             print(f"Turn {total_actions}: Action - {action[0]}, Evidence - {evidence}, Correct: {evidence in testimony['present']}")
#
#     # for turn, output in zip(case_data, model_output):
#     #     if turn["category"] == "cross_examination":
#     #         total_actions += 1
#     #         action = output["action"].split("@")
#     #         if action[0] == "present":
#     #             evidence = turn["court_record"]["evidence_objects"][int(action[1])]["name"]
#     #             testimony = turn["testimonies"][int(action[2])]
#     #             if evidence in testimony["present"]:
#     #                 correct_actions += 1
#     #             print(f"Turn {total_actions}: Action - {action[0]}, Evidence - {evidence}, Correct: {evidence in testimony['present']}")
#
#     accuracy = correct_actions / total_actions if total_actions > 0 else 0
#     print(f"Calculation complete. Correct actions: {correct_actions}, Total actions: {total_actions}")
#     return accuracy
#
# def main():
#     args = parser.parse_args()
#     print(f"\nStarting evaluation for Model: {args.model}, Prompt: {args.prompt}, Case: {args.case}, Metric: {args.metric}")
#
#     # case_data = load_case_data(args.case)
#     model_output = load_model_output(args.model, args.prompt, args.case)
#
#     if args.metric == 'accuracy':
#         result = calculate_accuracy(model_output)
#         print(f"Final Accuracy: {result:.2f}")
#     else:
#         print(f"Metric '{args.metric}' is not implemented.")
#
#     print("Evaluation complete.")
#
# if __name__ == '__main__':
#     main()

# import argparse
# import json
# import os
#
# parser = argparse.ArgumentParser(description='Evaluate the output of an LLM model on a given case')
# parser.add_argument('--model', type=str, required=True, help='Name of the LLM model used')
# parser.add_argument('--prompt', type=str, required=True, help='Name of the prompt used')
# parser.add_argument('--case', type=str, required=True, help='Identifier of the case in the format of X-Y-Z')
# parser.add_argument('--metric', type=str, default='accuracy', help='Metric to evaluate (e.g., accuracy)')
#
# def load_case_data(case: str) -> dict:
#     """Load the original case data."""
#     case_file_path = f"../case_data/generated/parsed/{case}.json"
#     with open(case_file_path, 'r') as file:
#         return json.load(file)
#
# def load_model_output(model: str, prompt: str, case: str) -> dict:
#     """Load the model's output for the given case."""
#     output_file = os.path.join("closed_model_output", model, prompt, f"{case}_output.json")
#     with open(output_file, 'r') as file:
#         return json.load(file)
#
# def calculate_accuracy(case_data: dict, model_output: dict) -> float:
#     """Calculate the accuracy of the model's output."""
#     correct_actions = 0
#     total_actions = 0
#
#     for turn, output in zip(case_data, model_output):
#         if turn["category"] == "cross_examination":
#             total_actions += 1
#             action = output["action"].split("@")
#             if action[0] == "present":
#                 evidence = turn["court_record"]["evidence_objects"][int(action[1])]["name"]
#                 testimony = turn["testimonies"][int(action[2])]
#                 if evidence in testimony["present"]:
#                     correct_actions += 1
#
#     return correct_actions / total_actions if total_actions > 0 else 0
#
# def main():
#     args = parser.parse_args()
#
#     case_data = load_case_data(args.case)
#     model_output = load_model_output(args.model, args.prompt, args.case)
#
#     if args.metric == 'accuracy':
#         result = calculate_accuracy(case_data, model_output)
#         print(f"Accuracy: {result:.2f}")
#     else:
#         print(f"Metric '{args.metric}' is not implemented.")
#
# if __name__ == '__main__':
#     main()