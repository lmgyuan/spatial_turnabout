# Import necessary modules and libraries
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any

from run_llm_model import run_model


# Define the SimulatorClosedLLM class
class SimulatorClosedLLM:
    def __init__(
        self,
        model: str = 'gpt-4o',              # Default model name
        prompt: str = 'default',            # Default prompt file name
        case: str = 'dev',                # Default case identifier
        metric: str = 'accuracy',           # Evaluation metric
        cot_few_shot: bool = True,          # Enable chain-of-thought with few-shot examples
        summary: bool = False,              # Enable context summarization
        log_level: str = 'INFO',           # Logging level
        log_file: str = None,               # Optional log file name
        case_dir: str = "../case_data/final_full_context/" # Directory for case data
    ):
        # Initialize instance variables with provided parameters
        self.MODEL = model
        self.PROMPT = prompt
        self.CASE = case
        self.METRIC = metric
        self.COT_FEW_SHOT = cot_few_shot
        self.SUMMARY = summary
        self.LOG_LEVEL = log_level
        self.LOG_FILE = log_file
        self.CASE_DIR = case_dir

        # Setup logging with timestamp to differentiate log files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Current timestamp
        cot_suffix = "_cot_few_shot" if self.COT_FEW_SHOT else ""  # Suffix for CoT configuration
        summary_suffix = "_context_summary" if self.SUMMARY else ""  # Suffix for summarization configuration

        # Determine the log file path
        if self.LOG_FILE:
            log_file = os.path.join(
                os.getcwd(),
                f"logs/close_llm/job_{self.MODEL}_{self.PROMPT}{cot_suffix}{summary_suffix}_{self.LOG_FILE}_{timestamp}.log"
            )
        else:
            log_file = os.path.join(
                os.getcwd(),
                f"logs/close_llm/job_{self.MODEL}_{self.PROMPT}{cot_suffix}{summary_suffix}_{timestamp}.log"
            )
        # Initialize logging configuration
        self.setup_logging(self.LOG_LEVEL, log_file)

        # Log the simulator initialization details
        logging.info(f"Simulator initialized with model={self.MODEL}, prompt={self.PROMPT}, case={self.CASE}, cot={self.COT_FEW_SHOT}")

        # Initialize the output directory and create it if it doesn't exist
        self.output_dir = os.path.join("closed_model_output", self.MODEL, self.PROMPT, "_dev_dir")
        os.makedirs(self.output_dir, exist_ok=True)
        logging.info(f"Output directory set to: {self.output_dir}")

    def setup_logging(self, log_level: str, log_file: str = None):
        """Set up logging configuration."""
        # Convert the log level string to a numeric level
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f'Invalid log level: {log_level}')

        # Define the log message format and date format
        log_format = '%(asctime)s [%(levelname)s] %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'

        # Configure logging
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
            print("Logging to file:", log_file)
        else:
            # Configure logging to console only
            logging.basicConfig(
                level=numeric_level,
                format=log_format,
                datefmt=date_format
            )
            print("Logging to console only")

    def load_prompt(self, prompt_name: str) -> str:
        """Load the prompt from a file."""
        # Construct the prompt file path
        prompt_path = os.path.join(os.getcwd(), 'prompts/system_prompts', f'{prompt_name}.txt')
        logging.info(f"Loading prompt from: {prompt_path}")
        try:
            # Read the prompt file content
            with open(prompt_path, 'r') as file:
                prompt = file.read().strip()
            logging.info(f"Prompt loaded successfully. Length: {len(prompt)} characters")
            return prompt
        except FileNotFoundError:
            # Log an error if the prompt file is not found
            logging.error(f"Prompt file not found: {prompt_path}")
            return ""
        except Exception as e:
            # Handle other exceptions
            logging.error(f"Error reading prompt file: {e}")
            return ""

    def extract_json_from_response(self, response: str) -> str:
        """Extract the innermost JSON object from the model's response."""
        try:
            # First, look for the 'Final Answer:' marker
            marker = "Final Answer:"
            idx = response.find(marker)
            if idx != -1:
                # Extract everything after 'Final Answer:'
                json_str = response[idx + len(marker):].strip()
            else:
                # If no marker is found, assume the entire response might be JSON
                json_str = response.strip()

            # Remove Markdown code block markers if present
            if json_str.startswith('```'):
                json_str = json_str.strip('`').strip()
                # Remove the 'json' label if present
                if json_str.startswith('json'):
                    json_str = json_str[4:].strip()
            return json_str
        except Exception as e:
            # Log any exceptions during extraction
            logging.error(f"Error extracting JSON from response: {e}")
            return None

    async def get_model_action(
        self,
        model: str,
        prompt: str,
        turn_data: Dict[str, Any],
        court_record: Dict[str, List[Dict[str, str]]],
        cot: bool,
        should_summarize: bool
    ) -> Dict[str, Any]:
        """Generate the model's action based on the current turn data and court record."""
        logging.info(f"Generating model action for turn: {turn_data.get('turn_number', 'Unknown')}")
        messages = [{"role": "system", "content": prompt}]
        try:
            # Prepare the context
            context = ""
            if should_summarize:
                context = await self.summarize_context(turn_data, model)
            else:
                context = turn_data.get("context", "")

            # Prepare the prompt
            if cot:
                # Add few-shot examples for chain-of-thought
                prompt += (
                    'The following is the chain-of-thought QA history that you may find useful in helping you make a decision:\n'
                )
                # Add few-shot examples (adjusted to be relevant)
                cot_prompt = self.load_cot_prompt()
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
                    'Explain your reasoning step by step before providing the JSON object. \n '
                    'Conclude your answer with "Final Answer:" followed by the JSON object on a new line.\n'
                    'Do not write any things after the JSON and make sure you use "Final Answer:" followed by the JSON object.\n'
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
            logging.info(f"Full prompt: {full_prompt}")
            messages = [{"role": "user", "content": full_prompt}]

            attempts = 0
            max_attempts = 3
            while attempts < max_attempts:
                attempts += 1
                try:
                    logging.info("Attempting to get model action")
                    # Call the model to get response
                    assistant_reply = await run_model(model, messages) 
                    logging.info(f"Assistant reply: {assistant_reply}")

                    # Extract action from the model's response
                    json_response = self.extract_json_from_response(assistant_reply)
                    if json_response:
                        # Remove Markdown code block markers if present
                        json_response = json_response.strip('`').strip()
                        # Remove the 'json' label if present
                        if json_response.startswith('json'):
                            json_response = json_response[4:].strip()
                        action = json.loads(json_response)
                        if action.get("action") == "present" and "testimony" in action and "evidence" in action:
                            logging.info(f"Valid action received: {action}")
                            # Optionally verify reasoning
                            reasoning_correct = await self.verify_reasoning(model, assistant_reply, action)
                            if not reasoning_correct:
                                messages.append({"role": "assistant", "content": assistant_reply})
                                messages.append({
                                    "role": "user",
                                    "content": "Your previous response was incorrect. Please provide a valid JSON object with 'action', 'testimony', and 'evidence' fields. " +
                                               "The 'action' must be 'present'. Make sure that the testimony and evidence you pick match your reasoning."
                                })
                                continue
                            return {"action": action, "response": assistant_reply}
                        else:
                            logging.warning(f"Invalid action received: {action}")
                            # Update messages with the assistant's response and revision suggestions
                            messages.append({"role": "assistant", "content": assistant_reply})
                            messages.append({
                                "role": "user",
                                "content": "Your previous response was in an incorrect format. Please provide a valid JSON " +
                                           "object with 'action', 'testimony', and 'evidence' fields. " +
                                           "The 'action' must be 'present'. Remember to explain your reasoning step by step before providing the JSON object."
                            })
                    else:
                        # If JSON extraction fails, inform the model and retry
                        logging.warning("Model response did not contain a valid JSON object.")
                        messages.append({"role": "assistant", "content": assistant_reply})
                        messages.append({
                            "role": "user",
                            "content": "Your previous response did not contain a valid JSON object. Please provide a valid JSON response."
                        })
                except json.JSONDecodeError as e:
                    # Handle JSON decoding errors
                    logging.error(f"JSON decoding error: {e}")
                    messages.append({"role": "assistant", "content": assistant_reply})
                    messages.append({
                        "role": "user",
                        "content": ("There was an error decoding your JSON response. Please ensure it is properly formatted."
                                    "Write 'Final Answer:' followed by a JSON object.")
                    })
                except Exception as e:
                    # Handle other exceptions
                    logging.error(f"Error during model action generation: {e}")
                    return {"action": None, "response": None}
            # If all attempts fail, return None
            logging.error("Failed to obtain a valid action from the model after multiple attempts.")
            return {"action": None, "response": None}
        except Exception as e:
            # Handle exceptions in the method
            logging.error(f"Error in get_model_action: {e}")
            return {"action": None, "response": None}

    async def verify_reasoning(self, model: str, model_reasoning: str, action: Dict[str, Any]) -> bool:
        """Verify if the model's reasoning is correct even if the output is wrong."""
        logging.info("Verifying model's reasoning with LLM")

        messages = [
            {"role": "system", "content": "You are a helpful assistant that evaluates reasoning correctness."},
            {"role": "user", "content": (
                f"Given the following reasoning:\n{model_reasoning}\n"
                f"And the action proposed:\n{action}\n"
                "Please determine if the reasoning leading to the action is correct, even if the final answer is wrong. "
                "Respond with 'True' if the reasoning is correct, otherwise 'False'."
            )}
        ]

        try:
            response = await run_model(model, messages)
            reasoning_correct = response.strip().lower() == 'true'
            logging.info(f"Reasoning verification result: {reasoning_correct}")
            return reasoning_correct
        except Exception as e:
            logging.error(f"Error verifying reasoning: {e}")
            return False

    async def simulate(
        self,
        model: str,
        prompt: str,
        case_data: List[Dict[str, Any]],
        cot: bool,
        should_summarize: bool
    ) -> List[Dict[str, Any]]:
        """Simulate the case and return the model's outputs."""
        outputs = []
        logging.info(f"Starting simulation for model: {model}")
        try:
            for turn_number, turn_data in enumerate(case_data, 1):
                logging.info(f"Processing turn {turn_number}")
                # No present available in this turn
                if turn_data.get("no_present"):
                    logging.info("No present available in this turn. Skipping.")
                    continue

                court_record = {
                    "objects": turn_data["court_record"]["evidence_objects"],
                    "characters": turn_data["characters"]
                }

                if turn_data["category"] == "cross_examination":
                    results = await self.get_model_action(model, prompt, turn_data, court_record, cot, should_summarize)
                    action = results["action"]
                    response = results["response"]
                    if action is None:
                        logging.warning(f"No valid action obtained for turn {turn_number}. Skipping.")
                        continue
                    outputs.append({
                        "turn": turn_data,
                        "action": action,
                        "response": response
                    })
                    logging.info(f"Action for turn {turn_number}: {action}")
            logging.info(f"Simulation complete. Total outputs: {len(outputs)}")
            return outputs
        except Exception as e:
            logging.error(f"Error during simulation: {e}")
            return outputs

    async def start_inference(self):
        """Run the inference process."""
        logging.info(f"Starting inference for Model: {self.MODEL}, Prompt: {self.PROMPT}, Case: {self.CASE}")

        # Determine which case files to process
        case_files = []
        if self.CASE == "dev":
            # Process all cases used during development
            case_dir = self.CASE_DIR if self.CASE_DIR else "../case_data/final_full_context/"
            try:
                case_files = [f for f in os.listdir(case_dir) if f.endswith('.json') and (f.startswith('1-') or f.startswith('2-'))]
                if not case_files:
                    logging.error("No case files found for inference.")
                    return
            except FileNotFoundError:
                logging.error(f"Case directory not found: {case_dir}")
                return
            except Exception as e:
                logging.error(f"Error accessing case files: {e}")
                return
        else:
            # Process a specific case
            case_files = [f"{self.CASE}.json"]

        # Load the system prompt
        prompt = self.load_prompt(self.PROMPT)

        # Iterate over each case file
        logging.info("List of case files: ", case_files)
        for case_file in case_files:
            case_name = os.path.splitext(case_file)[0]
            self.CASE = case_name  # Update the current case name
            case_file_path = os.path.join(self.CASE_DIR, case_file)
            logging.info(f"Loading case data from: {case_file_path}")
            try:
                with open(case_file_path, 'r') as file:
                    case_data = json.load(file)
                logging.info(f"Case data loaded successfully. Number of turns: {len(case_data)}")
            except FileNotFoundError:
                logging.error(f"Case file not found: {case_file_path}")
                continue
            except Exception as e:
                logging.error(f"Error loading case data: {e}")
                continue

            # Run the simulation
            outputs = await self.simulate(self.MODEL, prompt, case_data, self.COT_FEW_SHOT, self.SUMMARY)

            # Save the outputs
            cot_suffix = "_cot_few_shot" if self.COT_FEW_SHOT else ""
            summary_suffix = "_context_summary" if self.SUMMARY else ""
            output_file = os.path.join(self.output_dir, f"{self.CASE}_output{cot_suffix}{summary_suffix}.json")
            try:
                logging.info(f"Saving output to: {output_file}")
                with open(output_file, 'w') as file:
                    json.dump(outputs, file, indent=2)
                logging.info(f"Output saved successfully. Number of outputs: {len(outputs)}")
            except IOError as e:
                logging.error(f"Error writing output to file: {output_file}, {e}")
                continue

        logging.info("Inference complete.")

    def load_model_output(self) -> list:
        """Load the model's output for the given case."""
        cot_suffix = "_cot_few_shot" if self.COT_FEW_SHOT else ""
        summary_suffix = "_context_summary" if self.SUMMARY else ""
        output_file = os.path.join(self.output_dir, f"{self.CASE}_output{cot_suffix}{summary_suffix}.json")
        logging.info(f"Loading model output from: {output_file}")
        try:
            with open(output_file, 'r') as file:
                data = json.load(file)
            logging.info(f"Model output loaded successfully. Number of outputs: {len(data)}")
            return data
        except FileNotFoundError:
            logging.error(f"Model output file not found: {output_file}")
            return []
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from model output: {e}")
            return []
        except Exception as e:
            logging.error(f"Error loading model output: {e}")
            return []

    def load_existing_evaluation_file(self, file_path: str) -> list:
        """Load existing evaluations from a JSON file if it exists."""
        if os.path.exists(file_path):
            logging.info(f"Loading existing evaluation results from: {file_path}")
            try:
                with open(file_path, 'r') as eval_file:
                    return json.load(eval_file)
            except Exception as e:
                logging.error(f"Error loading existing evaluation file: {e}")
                return []
        else:
            logging.info(f"No existing evaluation file found. A new file will be created at: {file_path}")
            return []

    def calculate_accuracy(self, model_output: list) -> tuple:
        """Calculate the accuracy of the model's output."""
        logging.info("Calculating accuracy...")
        correct_actions = 0
        total_actions = 0
        evaluation_results = []

        for output in model_output:
            total_actions += 1
            turn = output["turn"]
            action = output["action"]
            if isinstance(action, dict):
                action_type = action.get("action")
                evidence_index = action.get("evidence")
                testimony_index = action.get("testimony")
            else:
                action_parts = action.split("@")
                action_type = action_parts[0]
                evidence_index = action_parts[1]
                testimony_index = action_parts[2]
            is_correct = False  # Default to incorrect unless proven otherwise
            evidence = None
            testimony = None
            e = None

            if action_type == "present":
                try:
                    # Attempt to retrieve the evidence and testimony based on indices
                    evidence_index = int(evidence_index)
                    testimony_index = int(testimony_index)
                    evidence = turn["court_record"]["evidence_objects"][evidence_index]["name"]
                    testimony = turn["testimonies"][testimony_index]
                    is_correct = evidence in testimony.get("present", [])

                    if is_correct:
                        correct_actions += 1

                    logging.info(f"Turn {total_actions}: Action - {action_type}, Evidence - {evidence}, Correct: {is_correct}")
                except (IndexError, ValueError, KeyError) as e:
                    # Handle index errors and other potential exceptions
                    logging.error(f"Turn {total_actions}: Error accessing evidence or testimony - {e}. Marked as incorrect.")
                    is_correct = False

                # Record evaluation details for this turn
                evaluation_results.append({
                    "case_name": self.CASE,
                    "model_action": action_type,
                    "evidence": evidence,
                    "testimony": testimony,
                    "turn_number": total_actions,
                    "is_correct": is_correct,
                    "total_turns": len(model_output),
                    "error": str(e) if e else None
                })

        accuracy = correct_actions / total_actions if total_actions > 0 else 0
        logging.info(f"Calculation complete. Correct actions: {correct_actions}, Total actions: {total_actions}")

        return evaluation_results, accuracy

    async def start_evaluation(self):
        """Run the evaluation process."""
        logging.info(f"Starting evaluation for Model: {self.MODEL}, Prompt: {self.PROMPT}, Metric: {self.METRIC}")

        # Determine which case files to evaluate
        case_files = []
        if self.CASE == "dev":
            # Evaluate all cases used during development
            case_dir = self.CASE_DIR if self.CASE_DIR else "../case_data/final_full_context/"
            try:
                case_files = [f for f in os.listdir(case_dir) if f.endswith('.json') and (f.startswith('1-') or f.startswith('2-'))]
                if not case_files:
                    logging.error("No case files found for evaluation.")
                    return
            except FileNotFoundError:
                logging.error(f"Case directory not found: {case_dir}")
                return
            except Exception as e:
                logging.error(f"Error accessing case files: {e}")
                return
        else:
            # Evaluate a specific case
            case_files = [f"{self.CASE}.json"]

        # Iterate over each case file for evaluation
        for case_file in case_files:
            case_name = os.path.splitext(case_file)[0]
            self.CASE = case_name  # Update the current case name

            # Load the model's output for the case
            model_output = self.load_model_output()
            if not model_output:
                logging.error(f"No model output to evaluate for case {self.CASE}.")
                continue

            if self.METRIC == 'accuracy':
                # Calculate accuracy and get evaluation results
                evaluation_results, result = self.calculate_accuracy(model_output)
                logging.info(f"Final Accuracy for case {self.CASE}: {result:.2f}")

                # Construct the evaluation output file path
                cot_suffix = "_cot_few_shot" if self.COT_FEW_SHOT else ""
                summary_suffix = "_context_summary" if self.SUMMARY else ""
                evaluation_output_file = os.path.join(self.output_dir, f"evaluation_{self.CASE}{cot_suffix}{summary_suffix}.json")
                os.makedirs(os.path.dirname(evaluation_output_file), exist_ok=True)
                # Save the evaluation results
                self.save_evaluation_results(evaluation_output_file, evaluation_results)
            else:
                logging.warning(f"Metric '{self.METRIC}' is not implemented.")

        logging.info("Evaluation complete.")

    def save_evaluation_results(self, evaluation_output_file: str, new_results: list):
        """Save evaluation results to the specified JSON file."""
        try:
            # Load existing evaluation data if the file exists
            existing_results = self.load_existing_evaluation_file(evaluation_output_file)

            # Append new results to existing data
            combined_results = existing_results + new_results

            # Save the updated results to the file
            with open(evaluation_output_file, 'w') as eval_file:
                json.dump(combined_results, eval_file, indent=4)
            logging.info(f"Evaluation results saved to: {evaluation_output_file}")
        except IOError as e:
            logging.error(f"Error writing evaluation results to file: {evaluation_output_file}, {e}")
        except Exception as e:
            logging.error(f"Unexpected error saving evaluation results: {e}")

    @staticmethod
    def load_cot_prompt(prompt_name="1-1-1_cot_prompt"):
        """Load the chain-of-thought prompt from a file."""
        prompt_path = os.path.join(os.getcwd(), 'prompts/cot_prompts', f'{prompt_name}.txt')
        try:
            with open(prompt_path, 'r') as file:
                prompt = file.read().strip()
            logging.info(f"CoT prompt loaded successfully. content: {prompt}")
            return prompt
        except FileNotFoundError:
            logging.error(f"CoT prompt file not found: {prompt_path}")
            return ""
        except Exception as e:
            logging.error(f"Error loading CoT prompt: {e}")
            return ""

    async def summarize_context(self, turn_data: Dict[str, Any], model: str) -> str:
        """Summarize the context using the run_model function."""
        logging.info("Requesting context summary from LLM")
         
        # Prepare the message content
        evidence_summaries = "\n".join([f"evidence {i}: {evidence}" for i, evidence in enumerate(turn_data["court_record"]["evidence_objects"])])
        testimony_summaries = "\n".join([f"testimony {i}: {testimony['testimony']}" for i, testimony in enumerate(turn_data["testimonies"])])
        full_context = turn_data["context"]

        messages = [
            {"role": "system", "content": "You are a helpful assistant that summarizes text while preserving key details."},
            {"role": "user", "content": (
                f"Please summarize the following context concisely while preserving the key information:\n"
                f"{evidence_summaries}\n"
                f"{testimony_summaries}\n"
                f"Full context: {full_context}\n"
                "Your response should be in the format:\n"
                "\"evidence 1: summary\"\n"
                "\"evidence 2: summary\"\n"
                "\"testimony 1: summary\"\n"
                "\"testimony 2: summary\"\n"
                "\"summary of full context\""
            )}
        ]
        logging.info(f"Messages to be summarized: {messages}")

        try:
            # Use the run_model function to get the summary
            response = await run_model(model, messages)
            summary = response.strip()
            logging.info(f"Context successfully summarized: {summary}")
        except Exception as e:
            logging.error(f"Error summarizing context: {e}")
            summary = full_context  # Fall back to original context if summarization fails

        return summary
    

# Entry point of the script
if __name__ == '__main__':
    # Create an instance of the SimulatorClosedLLM with desired parameters
    simulator = SimulatorClosedLLM(
        model='gpt-4o',            # Model name
        prompt='default',          # Prompt file name
        case='dev',                # Case identifier ('dev' to process multiple cases)
        metric='accuracy',         # Evaluation metric to use
        cot_few_shot=True,         # Enable chain-of-thought few-shot prompting
        summary=False,             # Enable context summarization
        log_level='INFO',         # Set the logging level
        log_file=None              # Specify a log file name if needed
    )
    # Run the inference and evaluation asynchronously
    asyncio.run(simulator.start_inference())
    # asyncio.run(simulator.start_evaluation())
