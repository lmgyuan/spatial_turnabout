import argparse
import json
import random
from pathlib import Path


def extract_rules(prefix_text: str):
    marker = "## SPATIAL REASONING RULES:\n"
    start_idx = prefix_text.find(marker)
    if start_idx == -1:
        raise ValueError("Could not find '## SPATIAL REASONING RULES:' marker in prefix")
    start_idx += len(marker)

    # Find the end marker for rules block (the '---' divider)
    end_marker_candidates = ["\n\n---", "\n---"]
    end_idx = -1
    for cand in end_marker_candidates:
        end_idx = prefix_text.find(cand, start_idx)
        if end_idx != -1:
            break
    if end_idx == -1:
        raise ValueError("Could not find end of rules block before '---'")

    rules_block = prefix_text[start_idx:end_idx]
    # Each rule is one non-empty line
    rules = [ln for ln in rules_block.splitlines() if ln.strip()]
    # Deduplicate while preserving order (some rules are duplicated in the source)
    seen = set()
    unique_rules = []
    for r in rules:
        if r not in seen:
            seen.add(r)
            unique_rules.append(r)
    return unique_rules, start_idx, end_idx


def build_new_prefix(orig_prefix: str, selected_rules: list[str], start_idx: int, end_idx: int) -> str:
    return orig_prefix[:start_idx] + "\n".join(selected_rules) + orig_prefix[end_idx:]


def main():
    parser = argparse.ArgumentParser(description="Create a randomized rules prompt from an existing prompt JSON")
    parser.add_argument("--input", type=Path, default=Path("source/prompts/rulesv3_improved.json"))
    parser.add_argument("--output", type=Path, default=Path("source/prompts/rulesv3_random_improved.json"))
    parser.add_argument("--num_rules", type=int, default=15)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    data = json.loads(args.input.read_text(encoding="utf-8"))
    prefix = data["prefix"]
    suffix = data["suffix"]

    all_rules, start_idx, end_idx = extract_rules(prefix)
    if args.num_rules > len(all_rules):
        raise ValueError(f"Requested {args.num_rules} rules but only {len(all_rules)} unique rules available")

    # Sample indices, then keep original order by sorting indices
    sampled_indices = sorted(random.sample(range(len(all_rules)), k=args.num_rules))
    selected_rules = [all_rules[i] for i in sampled_indices]

    new_prefix = build_new_prefix(prefix, selected_rules, start_idx, end_idx)

    out = {"prefix": new_prefix, "suffix": suffix}
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=4), encoding="utf-8")


if __name__ == "__main__":
    main()


