import argparse
import json
import math
from collections import defaultdict

MODELS = [
  "deepseek-R1-8b",
  "deepseek-R1-32b",
  "deepseek-R1-70b",
  "gpt-4.1-mini",
  "llama-3.1-8b",
  "llama-3.1-70b",
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
  wilson_results = defaultdict(lambda: dict())

  for model in MODELS:
    eval_filename = f"eval/{model}_prompt_base_report.json"
    eval_result = json.load(open(eval_filename))
    for (key, values) in eval_result["reasoning_steps_accuracy"].items():
      counts[key] = values["total"]
      print(values["total"], counts[key])
      acc_results[key][model] = values["accuracy"]
      wilson_results[key][model] = wilson_score(values["total"], values["correct"])

  lines = [f"len,n," + ",".join([model for model in MODELS]) + "\n"]
  for (key, values) in acc_results.items():
    lines.append(f"{key},{counts[key]}," + ",".join([f"{values[model]}" if model in values else "0" for model in MODELS]) + "\n")
  with open("stats/acc_vs_len_reason_chain.csv", "w") as f:
    f.writelines(lines)

  wilson_lines = [f"len," + ",".join([model for model in MODELS]) + "\n"]
  for (key, values) in wilson_results.items():
    wilson_lines.append(f"{key}," + ",".join([f"{values[model]}" if model in values else "0" for model in MODELS]) + "\n")
  with open("stats/wilson_lower_bound_vs_len_reason_chain.csv", "w") as f:
    f.writelines(wilson_lines)


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  args = parser.parse_args()
  main(args)
