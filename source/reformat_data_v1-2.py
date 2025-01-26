import os
import json

source_dir = '../case_data/v1'
target_dir = '../case_data/final'

fnames = [file for file in os.listdir(source_dir) if os.path.isfile(os.path.join(source_dir, file))]

for fname in fnames:
    print(fname)
    with open(os.path.join(source_dir, fname), 'r') as f:
        data = json.load(f)
        if len(data) == 0:
            continue
    characters = data[0]["characters"]
    evidences = data[0]["court_record"]["evidence_objects"]
    new_data = {
        "characters": characters,
        "evidences": evidences,
        "turns": []
    }
    for turn_id, turn in enumerate(data):
        new_data["turns"].append({
            "category": turn["category"],
            "new_context": turn["newContext"],
            "testimonies": turn["testimonies"],
            "no_present": turn["no_present"]
        })
    with open(os.path.join(target_dir, fname), 'w') as f:
        json.dump(new_data, f, indent=2)