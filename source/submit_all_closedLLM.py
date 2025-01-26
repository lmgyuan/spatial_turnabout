import os
import subprocess
from datetime import datetime

# Set variables
MODEL = "gpt-4o"
PROMPT = "default"
METRIC = "accuracy"
CASE_DIR = "../case_data/final_full_context/"
EVALUATION_FILE = os.path.join("closed_model_output", MODEL, PROMPT, "evaluation_cot_few_shot_context_summary.json")

def run_simulation(case_name, job_log):
    """Run the simulation for a given case."""
    subprocess.run([
        "python", "simulator_closedLLM.py",
        "--model", MODEL,
        "--prompt", PROMPT,
        "--case", case_name,
        "--cot_few_shot",
        "--log_file", job_log,
    ])

def run_evaluation(case_name, eval_log):
    """Run the evaluation for a given case."""
    subprocess.run([
        "python", "evaluate_output_close.py",
        "--model", MODEL,
        "--prompt", PROMPT,
        "--case", case_name,
        "--metric", METRIC,
        "--cot_few_shot",
        "--log_file", eval_log,
    ])

def main():
    print("Starting batch evaluation for all cases")
    print(f"Model used: {MODEL}, Prompt: {PROMPT}, cot_few_shot: Yes, summary: No")

    # Delete the evaluation file if it exists
    if os.path.exists(EVALUATION_FILE):
        os.remove(EVALUATION_FILE)
        print(f"Deleted existing evaluation file: {EVALUATION_FILE}")

    # Get current date and time in the desired format (e.g., YYYYMMDD_HHMMSS)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


    # Loop through all JSON files in the specified directory
    for case_file in os.listdir(CASE_DIR):
        if case_file.endswith(".json") and (case_file.startswith("1-") or case_file.startswith("2-")):
            case_name = os.path.splitext(case_file)[0]
            eval_log = f"test_log_new_cot5"
            job_log = f"text_log_new_cot5"

            print(f"Processing case: {CASE_DIR}{case_name}")

            # Run the simulation
            run_simulation(case_name, job_log)

            # Run the evaluation
            run_evaluation(case_name, eval_log)

            print("----------------------------------------")

    print("Batch evaluation complete")

if __name__ == "__main__":
    main()

# # Set variables
# MODEL = "gpt-4o"
# PROMPT = "default"
# METRIC = "accuracy"
# CASE_DIR = "../case_data/final_full_context/"
# EVALUATION_FILE = os.path.join("closed_model_output", MODEL, PROMPT, "evaluation_cot_few_shot.json")

# def run_simulation(case_name, job_log):
#     """Run the simulation for a given case."""
#     subprocess.run([
#         "python", "simulator_closedLLM.py",
#         "--model", MODEL,
#         "--prompt", PROMPT,
#         "--case", case_name,
#         "--cot_few_shot",
#         "--log_file", job_log
#     ])

# def run_evaluation(case_name, eval_log):
#     """Run the evaluation for a given case."""
#     subprocess.run([
#         "python", "evaluate_output_close.py",
#         "--model", MODEL,
#         "--prompt", PROMPT,
#         "--case", case_name,
#         "--metric", METRIC,
#         "--cot_few_shot",
#         "--log_file", eval_log
#     ])

# def main():
#     print("Starting batch evaluation for all cases")
#     print(f"Model used: {MODEL}, Prompt: {PROMPT}, cot_few_shot: Yes")

#     # Delete the evaluation file if it exists
#     if os.path.exists(EVALUATION_FILE):
#         os.remove(EVALUATION_FILE)
#         print(f"Deleted existing evaluation file: {EVALUATION_FILE}")

#     # Loop through all JSON files in the specified directory
#     for case_file in os.listdir(CASE_DIR):
#         if case_file.endswith(".json") and case_file.startswith("1-"):
#             case_name = os.path.splitext(case_file)[0]
#             eval_log = "test_log_new_cot2"
#             job_log = "text_log_new_cot2"

#             print(f"Processing case: {CASE_DIR}{case_name}")

#             # # Run the simulation
#             # run_simulation(case_name, job_log)

#             # Run the evaluation
#             run_evaluation(case_name, eval_log)

#             print("----------------------------------------")

#     print("Batch evaluation complete")

# if __name__ == "__main__":
#     main()



# # Set variables
# MODEL = "gpt-4o"
# PROMPT = "default"
# METRIC = "accuracy"
# CASE_DIR = "../case_data/final_full_context/"
# EVALUATION_FILE = os.path.join("closed_model_output", MODEL, PROMPT, "evaluation.json")

# def run_simulation(case_name, job_log):
#     """Run the simulation for a given case."""
#     subprocess.run([
#         "python", "simulator_closedLLM.py",
#         "--model", MODEL,
#         "--prompt", PROMPT,
#         "--case", case_name,
#         "--log_file", job_log
#     ])

# def run_evaluation(case_name, eval_log):
#     """Run the evaluation for a given case."""
#     subprocess.run([
#         "python", "evaluate_output_close.py",
#         "--model", MODEL,
#         "--prompt", PROMPT,
#         "--case", case_name,
#         "--metric", METRIC,
#         "--log_file", eval_log
#     ])

# def main():
#     print("Starting batch evaluation for all cases")
#     print(f"Model used: {MODEL}, Prompt: {PROMPT}, cot_few_shot: No")

#     # Delete the evaluation file if it exists
#     if os.path.exists(EVALUATION_FILE):
#         os.remove(EVALUATION_FILE)
#         print(f"Deleted existing evaluation file: {EVALUATION_FILE}")

#     # Loop through all JSON files in the specified directory
#     for case_file in os.listdir(CASE_DIR):
#         if case_file.endswith(".json") and case_file.startswith("1-"):
#             case_name = os.path.splitext(case_file)[0]
#             eval_log = "test_log_new_3"
#             job_log = "text_log_new_3"

#             print(f"Processing case: {CASE_DIR}{case_name}")

#             # Run the simulation
#             run_simulation(case_name, job_log)

#             # Run the evaluation
#             run_evaluation(case_name, eval_log)

#             print("----------------------------------------")

#     print("Batch evaluation complete")

# if __name__ == "__main__":
#     main()

