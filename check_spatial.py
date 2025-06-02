import json
import os

data_dir = '../data/aceattorney_data/final'
files = [f for f in os.listdir(data_dir) if f.endswith('.json')][:10]  # Check first 10 files

print("Checking for spatial turns in first 10 cases:")
print("-" * 50)

total_spatial = 0
for filename in files:
    try:
        with open(os.path.join(data_dir, filename), 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        turns = [t for t in data.get('turns', []) if not t.get('noPresent', False)]
        spatial_turns = [t for t in turns if 'spatial' in t.get('labels', [])]
        
        print(f"{filename}: {len(spatial_turns)} spatial turns (out of {len(turns)} total)")
        total_spatial += len(spatial_turns)
        
    except Exception as e:
        print(f"{filename}: Error - {e}")

print("-" * 50)
print(f"Total spatial turns in first 10 cases: {total_spatial}") 