#!/usr/bin/env python3
"""
Create a filtered Ace Attorney dataset for context=sum and label=spatial runs.

What this does:
- Reads input cases from data/aceattorney_data/final
- Keeps only turns labeled 'spatial' (and not marked noPresent)
- Removes long context that isn't used by context=sum by blanking:
  - Root-level previousContext
  - Per-turn newContext
- Writes results to data/aceattorney_data/final_spatial_sum

Notes:
- Does NOT modify any source modules; it's a standalone utility.
- Keeps characters, evidences, testimonies, summarizedContext, labels, etc. unchanged.
"""

import argparse
import json
import os
from typing import Any, Dict, List


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def has_label(turn: Dict[str, Any], label_filter: str) -> bool:
    """Replicate the label filtering logic used in run_models_spatial.py.

    - If labels is a list: keep if label_filter in the list
    - If labels is a string: keep if it equals label_filter
    - If missing/other: treat as no
    """
    turn_labels = turn.get("labels", [])
    if isinstance(turn_labels, list):
        return label_filter in turn_labels
    if isinstance(turn_labels, str):
        return turn_labels == label_filter
    return False


def transform_case(case_data: Dict[str, Any], label_filter: str) -> Dict[str, Any]:
    """Return a new case JSON with only spatial turns and stripped long context.

    - previousContext -> ""
    - For each kept turn: newContext -> ""
    - Keep summarizedContext and all other fields unchanged
    - Drop turns with noPresent=True
    """
    out: Dict[str, Any] = {
        # Blank the long root context not used by context=sum
        "previousContext": "",
        # Preserve characters/evidences exactly
        "characters": case_data.get("characters", []),
        "evidences": case_data.get("evidences", []),
        # Keep other top-level fields if present (non-breaking)
    }

    # Copy through any other root keys except the ones we explicitly manage
    for k, v in case_data.items():
        if k in {"previousContext", "characters", "evidences", "turns"}:
            continue
        out[k] = v

    # Filter and transform turns
    turns_in: List[Dict[str, Any]] = case_data.get("turns", [])
    turns_out: List[Dict[str, Any]] = []

    for turn in turns_in:
        # Skip turns that won't be used by the runner anyway
        if turn.get("noPresent", False):
            continue
        if not has_label(turn, label_filter):
            continue

        # Clone the turn shallowly and blank newContext
        # Keep summarizedContext and all other fields as-is
        new_turn = dict(turn)
        new_turn["newContext"] = ""
        turns_out.append(new_turn)

    out["turns"] = turns_out
    return out


def process_all(input_dir: str, output_dir: str, label_filter: str = "spatial") -> None:
    ensure_dir(output_dir)

    files = [f for f in os.listdir(input_dir) if f.endswith(".json")]
    total_files = len(files)
    kept_turns = 0
    total_turns = 0

    for fname in sorted(files):
        in_path = os.path.join(input_dir, fname)
        out_path = os.path.join(output_dir, fname)

        try:
            with open(in_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[WARN] Skipping {fname}: failed to read JSON ({e})")
            continue

        total_turns += len(data.get("turns", []))
        transformed = transform_case(data, label_filter)
        n_kept = len(transformed.get("turns", []))
        kept_turns += n_kept

        # Skip saving cases with zero spatial turns; also remove any stale output
        if n_kept == 0:
            try:
                if os.path.exists(out_path):
                    os.remove(out_path)
            except Exception as e:
                print(f"[WARN] Failed to remove stale file {out_path}: {e}")
            continue

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(transformed, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to write {out_path}: {e}")

    print(
        f"Done. Processed {total_files} files. Kept {kept_turns}/{total_turns} turns labeled '{label_filter}'.\n"
        f"Output: {output_dir}"
    )


def main():
    parser = argparse.ArgumentParser(description="Filter Ace Attorney dataset for context=sum and label=spatial")
    parser.add_argument(
        "--input",
        default=os.path.join("data", "aceattorney_data", "final"),
        help="Input directory with original case JSON files",
    )
    parser.add_argument(
        "--output",
        default=os.path.join("data", "aceattorney_data", "final_spatial_sum"),
        help="Output directory for filtered JSON files",
    )
    parser.add_argument(
        "--label",
        default="spatial",
        help="Turn label to keep (default: spatial)",
    )
    args = parser.parse_args()

    process_all(args.input, args.output, args.label)


if __name__ == "__main__":
    main()


