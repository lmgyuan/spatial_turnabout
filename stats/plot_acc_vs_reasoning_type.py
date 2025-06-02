import argparse
import json
import math
from collections import defaultdict

MODELS = [
  "deepseek-chat",
  "deepseek-R1-8b",
  "deepseek-R1-32b",
  "deepseek-R1-70b",
  "deepseek-reasoner",
  "gpt-4.1",
  "gpt-4.1-mini",
  "llama-3.1-8b",
  "llama-3.1-70b",
  "o3-mini",
  "o4-mini",
  "QwQ-32B"
]

def wilson_score(total, n_correct, z=1.0):
  k = n_correct
  n = total
  phat = k / n
  denominator = 1 + z**2 / n
  centre = phat + z**2 / (2 * n)
  margin = z * math.sqrt((phat * (1 - phat) / n) + (z**2 / (4 * n**2)))
  lower_bound = (centre - margin) / denominator
  return lower_bound

def main(args):
  counts = defaultdict(lambda: 0)

  acc_results = defaultdict(lambda: dict())

  for model in MODELS:
    eval_filename = f"eval/{model}_prompt_base_report.json"
    eval_result = json.load(open(eval_filename))
    for (key, values) in eval_result["categories_accuracy"].items():
      counts[key] = values["total"]
      acc_results[key][model] = values["accuracy"]

  lines = [f"len,n," + ",".join([model for model in MODELS]) + "\n"]
  for (key, values) in acc_results.items():
    lines.append(f"{key},{counts[key]}," + ",".join([f"{values[model] * 100}" if model in values else "0" for model in MODELS]) + "\n")
  with open("stats/acc_vs_reasoning_type.csv", "w") as f:
    f.writelines(lines)


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  args = parser.parse_args()
  main(args)
