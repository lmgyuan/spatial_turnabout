"""
Run all Turnabout spatial experiments for a given model.
Usage: python run_all_turnabout.py -m deepinfra-gemma3-4b --max_workers 20
"""

import argparse
import subprocess
import sys

# All 15 prompts for Turnabout spatial experiments
PROMPTS = [
    # Baselines
    "base",
    "base_spatial_ablation",
    
    # Static Rules (RC-Static)
    "rulesv5_improved",
    
    # RAG Rules (RC-RAG@k)
    "rulesv5_rag_t5_improved",
    "rulesv5_rag_t10_improved",
    "rulesv5_rag_t15_improved",
    
    # Proposition Augmentation (PA@p)
    "prop_generated_p5_improved_v2",
    "prop_generated_p10_improved_v2",
    "prop_generated_p15_improved_v2",
    
    # Auto-Generated Rules (AR@k)
    "rules_generated_r5_improved_v2",
    "rules_generated_r10_improved_v2",
    "rules_generated_r15_improved_v2",
    
    # RAG + Props Combined
    "rulesv5_rag_prop_t15_p5_improved_v2",
    "rulesv5_rag_prop_t15_p10_improved_v2",
    "rulesv5_rag_prop_t15_p15_improved_v2",
]


def run_experiment(model, prompt, max_workers):
    """Run a single experiment."""
    cmd = [
        sys.executable, "run_models_parallel.py",
        "-m", model,
        "-p", prompt,
        "--context", "sum",
        "--label", "spatial",
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
        sys.executable, "evaluate_spatial.py",
        "-m", model,
        "-p", prompt,
        "--context", "sum",
        "--label", "spatial"
    ]
    print(f"Evaluating: {model} | {prompt}")
    
    result = subprocess.run(cmd)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run all Turnabout spatial experiments")
    parser.add_argument("-m", "--model", type=str, required=True, help="Model name (e.g., deepinfra-gemma3-4b)")
    parser.add_argument("--max_workers", type=int, default=20, help="Number of parallel workers (default: 20)")
    parser.add_argument("--eval_only", action="store_true", help="Only run evaluation (skip experiments)")
    parser.add_argument("--prompts", type=str, nargs="+", default=None, help="Specific prompts to run (default: all)")
    args = parser.parse_args()
    
    model = args.model
    max_workers = args.max_workers
    prompts_to_run = args.prompts if args.prompts else PROMPTS
    
    print(f"\n{'#'*60}")
    print(f"# TURNABOUT SPATIAL EXPERIMENTS")
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

