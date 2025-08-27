import json
import sys
import os


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python source/check_et_cache_stats.py <path_to_et_cache.json>")
        sys.exit(1)

    cache_path = sys.argv[1]
    if not os.path.exists(cache_path):
        print(f"File not found: {cache_path}")
        sys.exit(1)

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to read JSON: {e}")
        sys.exit(1)

    total_turns = 0
    empty_ev = 0
    empty_ts = 0
    empty_both = 0

    for key, entry in data.items():
        if not isinstance(entry, dict):
            continue
        ev = entry.get("evidences", [])
        ts = entry.get("testimonies", [])

        ev_empty = not ev
        ts_empty = not ts

        total_turns += 1
        if ev_empty:
            empty_ev += 1
        if ts_empty:
            empty_ts += 1
        if ev_empty and ts_empty:
            empty_both += 1

    print(f"File: {cache_path}")
    print(f"Total turns: {total_turns}")
    print(f"Empty evidences: {empty_ev}")
    print(f"Empty testimonies: {empty_ts}")
    print(f"Empty both: {empty_both}")


if __name__ == "__main__":
    main()


