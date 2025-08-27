import csv
import os
from collections import defaultdict, OrderedDict
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt


# Resolve paths relative to project root (parent of this file's directory)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH_DEFAULT = os.path.join(BASE_DIR, "eval", "nebius_models_evaluation_summary.csv")
OUTPUT_PNG_DEFAULT = os.path.join(BASE_DIR, "eval", "meeting11_plot1.png")


def parse_model_and_run_type(model_config: str) -> Tuple[str, str]:
    """Parse model name and run type from model_config.

    Expected pattern examples:
    - llama3.3-70b_prompt_base_context_sum_label_spatial
    - llama3.3-70b_prompt_et_suggested_et3_improved_v2_context_sum_label_spatial
    - qwen-32b_prompt_rules_generated_r10_improved_v2_context_sum_label_spatial
    """
    try:
        # split once at _prompt_
        if "_prompt_" not in model_config:
            # fallback: split at first _prompt
            pivot = model_config.find("_prompt")
            if pivot != -1:
                model_name = model_config[:pivot]
                rest = model_config[pivot + 1:]
            else:
                return model_config, "unknown"
        else:
            parts = model_config.split("_prompt_")
            model_name = parts[0]
            rest = parts[1]

        # run type ends before _context if present
        run_type = rest.split("_context")[0]
        return model_name, run_type
    except Exception:
        return model_config, "unknown"


def load_accuracy_data(csv_path: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def build_grouped_data(rows: List[Dict[str, str]]) -> Tuple[List[str], List[str], Dict[str, Dict[str, float]]]:
    """Return (models, run_types, accuracy_by_model_then_run_type).

    - models: ordered list of model names
    - run_types: ordered list of run types (global across models)
    - accuracy map: { model: { run_type: overall_accuracy_float } }
    """
    model_order: List[str] = []
    run_type_order: List[str] = []
    acc_map: Dict[str, Dict[str, float]] = defaultdict(dict)

    for row in rows:
        model_config = row.get("model_config", "")
        overall_acc_str = row.get("overall_accuracy", "")
        if not model_config or not overall_acc_str:
            continue
        try:
            overall_acc = float(overall_acc_str)
        except ValueError:
            continue

        model_name, run_type = parse_model_and_run_type(model_config)
        if model_name not in model_order:
            model_order.append(model_name)
        if run_type not in run_type_order:
            run_type_order.append(run_type)
        acc_map[model_name][run_type] = overall_acc

    return model_order, run_type_order, acc_map


def get_run_type_color_map(run_types: List[str]) -> Dict[str, str]:
    """Assign consistent colors to run types. Use a fixed palette for first few known types.
    Fallback to matplotlib tab colors for extras.
    """
    # Predefine common run types for consistent coloring
    predefined: Dict[str, str] = OrderedDict([
        ("base", "#1f77b4"),  # blue
        ("et_suggested_et2_improved_v2", "#ff7f0e"),  # orange
        ("et_suggested_et3_improved_v2", "#ff7f0e"),  # same color for ET-Suggested variants
        ("rules_generated_r5_improved_v2", "#2ca02c"),  # green
        ("rules_generated_r10_improved_v2", "#d62728"),  # red
        ("rules_generated_r15_improved_v2", "#9467bd"),  # purple
    ])

    colors: Dict[str, str] = {}
    tab_cycle = plt.rcParams["axes.prop_cycle"].by_key().get("color", [])
    tab_idx = 0

    for rt in run_types:
        if rt in predefined:
            colors[rt] = predefined[rt]
        else:
            # fallback color
            colors[rt] = tab_cycle[tab_idx % max(1, len(tab_cycle))]
            tab_idx += 1
    return colors


def plot_grouped_bar(
    models: List[str],
    run_types: List[str],
    acc_map: Dict[str, Dict[str, float]],
    output_png: str,
) -> None:
    num_models = len(models)
    num_runs = len(run_types)
    if num_models == 0 or num_runs == 0:
        raise ValueError("No data to plot.")

    run_colors = get_run_type_color_map(run_types)

    fig, ax = plt.subplots(figsize=(max(12, num_models * 2.2), 6.5))

    # bar width and positions
    total_group_width = 0.8
    bar_width = total_group_width / num_runs
    x_positions = list(range(num_models))

    for run_idx, run_type in enumerate(run_types):
        offsets = [x - total_group_width / 2 + run_idx * bar_width + bar_width / 2 for x in x_positions]
        values = []
        for model in models:
            acc = acc_map.get(model, {}).get(run_type, None)
            values.append(acc if acc is not None else 0.0)
        bars = ax.bar(offsets, values, width=bar_width, color=run_colors.get(run_type, "gray"), label=run_type)
        # Add percentage labels above bars
        for x, v in zip(offsets, values):
            ax.text(x, v + 0.01, f"{v * 100:.1f}%", ha="center", va="bottom", fontsize=8)

    # X axis labels
    ax.set_xticks(x_positions)
    ax.set_xticklabels(models, rotation=20, ha="right")

    # Y axis as percentage
    ax.set_ylabel("Accuracy")
    ax.set_ylim(0, 1.0)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{int(y * 100)}%"))

    ax.set_title("Overall Accuracy by Model and Run Type")
    # Place legend inside the plot at upper-left to avoid shrinking the plot area
    ax.legend(title="Run Type", loc="upper left", frameon=True, fontsize=9, title_fontsize=10)
    ax.grid(axis="y", linestyle=":", alpha=0.4)

    os.makedirs(os.path.dirname(output_png), exist_ok=True)
    # Use tight layout and trim excess whitespace in the output image
    plt.tight_layout(pad=0.6)
    plt.savefig(output_png, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    csv_path = CSV_PATH_DEFAULT
    output_png = OUTPUT_PNG_DEFAULT

    rows = load_accuracy_data(csv_path)
    models, run_types, acc_map = build_grouped_data(rows)
    # Hard-code base accuracies where requested
    acc_map.setdefault("qwen-32b", {})["base"] = 0.19
    acc_map.setdefault("qwen3-32b", {})["base"] = 0.40
    if "base" not in run_types:
        run_types = ["base"] + run_types
    plot_grouped_bar(models, run_types, acc_map, output_png)
    print(f"Saved plot: {output_png}")


if __name__ == "__main__":
    main()


