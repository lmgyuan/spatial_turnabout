import json
import os

FILE_PATHS = []
turn_count = 0

for i in range(1, 5):
    FILE_PATHS.append(f"3-3-{i}_Recipe_for_Turnabout.json")

for file_path in FILE_PATHS:
    with open(file_path, 'r') as f:
        data = json.load(f)
    turn_count += len(data['turns'])

print(turn_count)
