import argparse
import json
import math
from collections import defaultdict

# Define models and their family groupings
MODEL_FAMILIES = {
    "GPT": ["gpt-4.1", "gpt-4.1-mini", "o3-mini", "o4-mini"],
    "DeepSeek": ["deepseek-chat", "deepseek-R1-8b", "deepseek-R1-32b", "deepseek-R1-70b", "deepseek-reasoner"],
    "Llama": ["llama-3.1-8b", "llama-3.1-70b"],
    "Other": ["QwQ-32B"]
}

# Flatten the model list
ALL_MODELS = []
for models in MODEL_FAMILIES.values():
    ALL_MODELS.extend(models)

def wilson_score(total, n_correct, z=1.0):
    """Calculate Wilson score lower bound for binomial confidence interval"""
    if total == 0:
        return 0
    k = n_correct
    n = total
    phat = k / n
    denominator = 1 + z**2 / n
    centre = phat + z**2 / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) / n) + (z**2 / (4 * n**2)))
    lower_bound = (centre - margin) / denominator
    return lower_bound

def get_model_family(model_name):
    """Find which family a model belongs to"""
    for family, models in MODEL_FAMILIES.items():
        if model_name in models:
            return family
    return "Unknown"

def main(args):
    # Store results for individual models first
    model_results = {}
    counts_by_length = defaultdict(lambda: 0)
    
    # Collect results for all models
    for model in ALL_MODELS:
        eval_filename = f"eval/{model}_prompt_base_report.json"
        try:
            eval_result = json.load(open(eval_filename))
            model_results[model] = eval_result["reasoning_steps_accuracy"]
            
            # Update total counts for each reasoning length
            for key, values in eval_result["reasoning_steps_accuracy"].items():
                counts_by_length[key] += values["total"]
        except FileNotFoundError:
            print(f"Warning: Could not find evaluation file for {model}")
    
    # Aggregate results by family
    family_accuracy = defaultdict(lambda: defaultdict(lambda: {"correct": 0, "total": 0}))
    family_wilson = defaultdict(lambda: defaultdict(float))
    
    # Calculate total correct/total for each family and reasoning length
    for model, results in model_results.items():
        family = get_model_family(model)
        for length, data in results.items():
            family_accuracy[family][length]["correct"] += data["correct"]
            family_accuracy[family][length]["total"] += data["total"]
    
    # Calculate average accuracy and Wilson score for each family
    for family, lengths in family_accuracy.items():
        for length, data in lengths.items():
            # Calculate accuracy
            if data["total"] > 0:
                accuracy = data["correct"] / data["total"]
                family_accuracy[family][length]["accuracy"] = accuracy
                
                # Calculate Wilson score
                wilson = wilson_score(data["total"], data["correct"])
                family_wilson[family][length] = wilson
    
    # Generate CSV for average accuracy by family
    families = list(MODEL_FAMILIES.keys())
    lines = [f"len,n," + ",".join(families) + "\n"]
    
    for length in sorted(counts_by_length.keys(), key=lambda x: int(x) if x.isdigit() else float('inf')):
        line_parts = [length, str(counts_by_length[length])]
        
        for family in families:
            if length in family_accuracy[family] and "accuracy" in family_accuracy[family][length]:
                line_parts.append(f"{family_accuracy[family][length]['accuracy']:.4f}")
            else:
                line_parts.append("0")
        
        lines.append(",".join(line_parts) + "\n")
    
    # Write accuracy results to CSV
    with open("stats/acc_vs_len_reason_chain_by_fam.csv", "w") as f:
        f.writelines(lines)
    
    # Generate CSV for Wilson scores by family
    wilson_lines = [f"len," + ",".join(families) + "\n"]
    
    for length in sorted(counts_by_length.keys(), key=lambda x: int(x) if x.isdigit() else float('inf')):
        line_parts = [length]
        
        for family in families:
            if length in family_wilson[family]:
                line_parts.append(f"{family_wilson[family][length]:.4f}")
            else:
                line_parts.append("0")
        
        wilson_lines.append(",".join(line_parts) + "\n")
    
    # Write Wilson score results to CSV
    with open("stats/wilson_lower_bound_vs_len_reason_chain_by_fam.csv", "w") as f:
        f.writelines(wilson_lines)
    
    print(f"Results written to stats/acc_vs_len_reason_chain_by_fam.csv")
    print(f"Wilson scores written to stats/wilson_lower_bound_vs_len_reason_chain_by_fam.csv")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot accuracy vs reasoning chain length by model family")
    args = parser.parse_args()
    main(args)
