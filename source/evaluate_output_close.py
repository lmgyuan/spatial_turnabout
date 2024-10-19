import argparse
import json
import os
import logging

parser = argparse.ArgumentParser(description='Evaluate the output of an LLM model on a given case')
parser.add_argument('--model', type=str, required=True, help='Name of the LLM model used')
parser.add_argument('--prompt', type=str, required=True, help='Name of the prompt used')
parser.add_argument('--case', type=str, required=False, help='Identifier of the case in the format of X-Y-Z')
parser.add_argument('--metric', type=str, default='accuracy', help='Metric to evaluate (e.g., accuracy)')
parser.add_argument('--cot_few_shot', action='store_true', help='Enable chain-of-thought with few-shot examples')
# Add an option to set the logging level
parser.add_argument('--log_level', type=str, default='INFO', help='Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
# Add an option to specify a log file
parser.add_argument('--log_file', type=str, help='File path to save logs')


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
        # Configure logging to file, appending if the file exists
        logging.basicConfig(
            level=numeric_level,
            format=log_format,
            datefmt=date_format,
            handlers=[
                logging.FileHandler(log_file, mode='a'),
                logging.StreamHandler()  # Also output to console
            ]
        )
    else:
        # Configure logging to console only
        logging.basicConfig(
            level=numeric_level,
            format=log_format,
            datefmt=date_format
        )


def load_case_data(case: str) -> dict:
    """Load the original case data."""
    case_file_path = f"../case_data/generated/parsed/{case}.json"
    logging.debug(f"Loading case data from: {case_file_path}")
    with open(case_file_path, 'r') as file:
        data = json.load(file)
    logging.info(f"Case data loaded successfully. Number of turns: {len(data)}")
    return data


def load_model_output(model: str, prompt: str, case: str, cot_few_shot: bool) -> dict:
    """Load the model's output for the given case."""
    # Include 'cot_few_shot' suffix if enabled
    cot_few_shot_suffix = "_cot_few_shot" if cot_few_shot else ""
    output_file = os.path.join("closed_model_output", model, prompt, f"{case}_output{cot_few_shot_suffix}.json")
    logging.debug(f"Loading model output from: {output_file}")
    with open(output_file, 'r') as file:
        data = json.load(file)
    logging.info(f"Model output loaded successfully. Number of outputs: {len(data)}")
    return data


def load_existing_evaluation_file(file_path: str) -> list:
    """Load existing evaluations from a JSON file if it exists."""
    if os.path.exists(file_path):
        logging.info(f"Loading existing evaluation results from: {file_path}")
        with open(file_path, 'r') as eval_file:
            return json.load(eval_file)
    else:
        logging.info(f"No existing evaluation file found. A new file will be created at: {file_path}")
        return []


def calculate_accuracy(model_output: list, case_name: str, model: str, prompt: str) -> tuple:
    """Calculate the accuracy of the model's output and save the result to a JSON file."""
    logging.info("Calculating accuracy...")
    correct_actions = 0
    total_actions = 0
    evaluation_results = []

    for output in model_output:
        total_actions += 1
        turn = output["turn"]
        action = output["action"].split("@")
        is_correct = False  # Default to incorrect unless proven otherwise
        evidence = None
        testimony = None

        if action[0] == "present":
            try:
                # Attempt to retrieve the evidence and testimony based on indices
                evidence_index = int(action[1])
                testimony_index = int(action[2])
                evidence = turn["court_record"]["evidence_objects"][evidence_index]["name"]
                testimony = turn["testimonies"][testimony_index]
                is_correct = evidence in testimony["present"]

                if is_correct:
                    correct_actions += 1

                logging.debug(f"Turn {total_actions}: Action - {action[0]}, Evidence - {evidence}, Correct: {is_correct}")
            except (IndexError, ValueError, KeyError) as e:
                # Handle index errors and other potential exceptions
                logging.error(f"Turn {total_actions}: Error accessing evidence or testimony - {e}. Marked as incorrect.")
                is_correct = False

            # Record evaluation details for this turn
            evaluation_results.append({
                "case_name": case_name,
                "model_action": action[0],
                "evidence": evidence,
                "testimony": testimony,
                "turn_number": total_actions,
                "is_correct": is_correct,
                "total_turns": len(model_output),
                "error": str(e) if 'e' in locals() else None
            })

    accuracy = correct_actions / total_actions if total_actions > 0 else 0
    logging.info(f"Calculation complete. Correct actions: {correct_actions}, Total actions: {total_actions}")

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
    logging.info(f"Evaluation results saved to: {evaluation_output_file}")


def main():
    args = parser.parse_args()
    cot_few_shot_suffix = "_cot_few_shot" if args.cot_few_shot else ""
    # Setup logging with log file
    if args.log_file:
        log_file = os.getcwd() + f"/logs/close_llm/evaluate_log_{args.model}_{args.prompt}{cot_few_shot_suffix}_{args.log_file}.log"
    else:
        log_file = os.getcwd() + f"/logs/close_llm/evaluate_log_{args.model}_{args.prompt}{cot_few_shot_suffix}_log.log"

    setup_logging(args.log_level, log_file)
    logging.info(
        f"Starting evaluation for Model: {args.model}, Prompt: {args.prompt}, Case: {args.case}, Metric: {args.metric}"
    )

    model_output = load_model_output(args.model, args.prompt, args.case, args.cot_few_shot)

    if args.metric == 'accuracy':
        evaluation_results, result = calculate_accuracy(model_output, args.case, args.model, args.prompt)
        logging.info(f"Final Accuracy: {result:.2f}")

        # Save the evaluation results to the JSON file
        evaluation_output_file = os.path.join("closed_model_output", args.model, args.prompt,
                                              f"evaluation{cot_few_shot_suffix}.json")
        os.makedirs(os.path.dirname(evaluation_output_file), exist_ok=True)
        save_evaluation_results(evaluation_output_file, evaluation_results)
    else:
        logging.warning(f"Metric '{args.metric}' is not implemented.")

    logging.info("Evaluation complete.")


if __name__ == '__main__':
    main()
