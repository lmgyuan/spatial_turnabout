import json
import os
import csv

def get_eval_data(output_root_dir):
    res = []
    for output in sorted(os.listdir(output_root_dir)):
        if output.endswith("report.json"):
            # print(output)
            parts = output.split("_")
            model, prompt, context, description = "", "", "", ""
            model = parts[0]
            if len(parts) > 2 and parts[1] == "prompt":  # Extract prompt
                prompt = parts[2]
            if "context" in parts:
                context = parts[parts.index("context") + 1]
            else:
                context = "none"
            if "desc" in parts:  # Only exist if no description
                description = "false"
            else:
                description = "true"
            if "case" in parts:
                case = parts[parts.index("case") + 1]
            else:
                case = "ALL"

            with open(os.path.join(output_root_dir, output), "r") as f:
                eval_data = json.load(f)
            res.append({
                "model": model,
                "prompt": prompt,
                "context": context,
                "description": description,
                "case": case,
                "eval": eval_data
            })

    # Get metadata keys from first eval data
    if len(res) == 0:
        return [], {}
    metadata_keys = {}
    metadata_keys["categories"] = []
    metadata_keys["reasoning_steps"] = []
    metadata_keys["action_space"] = []
    for k in res[0]["eval"]["categories_accuracy"].keys():
        metadata_keys["categories"].append(k)
    for k in res[0]["eval"]["reasoning_steps_accuracy"].keys():
        metadata_keys["reasoning_steps"].append(k)
    for k in res[0]["eval"]["action_space_accuracy"].keys():
        metadata_keys["action_space"].append(k)

    return res, metadata_keys

if __name__ == "__main__":
    output_root_dir = "../output/evals"
    res, metadata_keys = get_eval_data(output_root_dir)

    # Write to csv
    with open(os.path.join(output_root_dir, "eval.csv"), "w") as f:
        writer = csv.writer(f)
        writer.writerow([
            "model", 
            "prompt",
            "context",
            "description",
            "case",
            "overall_total",
            "overall_accuracy",
            "overall_evidence_accuracy",
            "overall_testimony_accuracy",
            "average_reasoning_tokens",
            *[item for k in metadata_keys["categories"] for item in (f"{k}_total", f"{k}_accuracy")],
            *[item for k in metadata_keys["reasoning_steps"] for item in (f"{k}_total", f"{k}_accuracy")],
            *[item for k in metadata_keys["action_space"] for item in (f"{k}_total", f"{k}_accuracy")],
        ])
        for r in res:
            categories_data = r['eval'].get('categories_accuracy', {})
            reasoning_steps_data = r['eval'].get('reasoning_steps_accuracy', {})
            action_space_data = r['eval'].get('action_space_accuracy', {})

            writer.writerow([
                r["model"], 
                r["prompt"], 
                r["context"],
                r["description"],
                r["case"],
                r["eval"].get("overall_total", "N/A"),
                r["eval"].get("overall_accuracy", "N/A"),
                r["eval"].get("overall_evidence_accuracy", "N/A"),
                r["eval"].get("overall_testimony_accuracy", "N/A"),
                r["eval"].get("average_reasoning_tokens", "N/A"),
                *[categories_data.get(k, {}).get(field, "N/A") for k in metadata_keys["categories"] for field in ("total", "accuracy")],
                *[reasoning_steps_data.get(k, {}).get(field, "N/A") for k in metadata_keys["reasoning_steps"] for field in ("total", "accuracy")],
                *[action_space_data.get(k, {}).get(field, "N/A") for k in metadata_keys["action_space"] for field in ("total", "accuracy")],
            ])

    
        

