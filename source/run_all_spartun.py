"""
Run all SPARTUN experiments for a given model.
Usage: python run_all_spartun.py -m deepinfra-gemma3-4b --max_workers 20
"""

import argparse
import subprocess
import sys

# All 7 prompts for SPARTUN experiments
PROMPTS = [
    # Baseline
    "base",
    
    # Gold Rules (Oracle upper bound)
    "gold_rules_improved",
    
    # Static Rules (RC-Static)
    "rulesv5_improved",
    
    # RAG Rules (RC-RAG@10)
    "rulesv5_rag_t10_improved",
    
    # Proposition Augmentation (PA@10)
    "prop_generated_p10_improved_v2",
    
    # Auto-Generated Rules (AR@10)
    "rules_generated_r10_improved_v2",
    
    # RAG + Props Combined
    "rag_prop_generated_t10_p10_improved_v2",
]


def run_experiment(model, prompt, max_workers):
    """Run a single experiment."""
    cmd = [
        sys.executable, "run_spartun_parallel.py",
        "-m", model,
        "-p", prompt,
        "--case", "100",  # First 100 cases = 666 questions (matches previous experiments)
        "--max_workers", str(max_workers)
    ]
    print(f"\n{'='*60}")
    print(f"RUNNING: {model} | {prompt}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd)
    return result.returncode == 0


def run_evaluation(model, prompt):
    """Run evaluation for a single experiment."""
    cmd = [
        sys.executable, "evaluate_spartun.py",
        "-m", model,
        "-p", prompt
    ]
    print(f"Evaluating: {model} | {prompt}")
    
    result = subprocess.run(cmd)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run all SPARTUN experiments")
    parser.add_argument("-m", "--model", type=str, required=True, help="Model name (e.g., deepinfra-gemma3-4b)")
    parser.add_argument("--max_workers", type=int, default=20, help="Number of parallel workers (default: 20)")
    parser.add_argument("--eval_only", action="store_true", help="Only run evaluation (skip experiments)")
    parser.add_argument("--prompts", type=str, nargs="+", default=None, help="Specific prompts to run (default: all)")
    args = parser.parse_args()
    
    model = args.model
    max_workers = args.max_workers
    prompts_to_run = args.prompts if args.prompts else PROMPTS
    
    print(f"\n{'#'*60}")
    print(f"# SPARTUN EXPERIMENTS")
    print(f"# Model: {model}")
    print(f"# Prompts: {len(prompts_to_run)}")
    print(f"# Max Workers: {max_workers}")
    print(f"# Eval Only: {args.eval_only}")
    print(f"{'#'*60}\n")
    
    success_count = 0
    fail_count = 0
    
    for i, prompt in enumerate(prompts_to_run, 1):
        print(f"\n[{i}/{len(prompts_to_run)}] Processing: {prompt}")
        
        # Run experiment (unless eval_only)
        if not args.eval_only:
            success = run_experiment(model, prompt, max_workers)
            if not success:
                print(f"WARNING: Experiment failed for {prompt}")
                fail_count += 1
                continue
        
        # Run evaluation
        eval_success = run_evaluation(model, prompt)
        if eval_success:
            success_count += 1
        else:
            print(f"WARNING: Evaluation failed for {prompt}")
            fail_count += 1
    
    print(f"\n{'#'*60}")
    print(f"# COMPLETED")
    print(f"# Success: {success_count}/{len(prompts_to_run)}")
    print(f"# Failed: {fail_count}/{len(prompts_to_run)}")
    print(f"{'#'*60}\n")


if __name__ == "__main__":
    main()


