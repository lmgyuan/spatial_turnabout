import json
import os

# Get all JSON files in current directory
json_files = [f for f in os.listdir('.') if f.endswith('.json')]

for json_file in json_files:
    # Read the JSON file
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Process each turn's contexts
    if 'turns' in data:
        if 'previousContext' in data:
            data['previousContext'] = data['previousContext'].replace('\n', '')

        for turn in data['turns']:
            if 'previousContext' in turn:
                # Remove newlines from previousContext
                turn['previousContext'] = turn['previousContext'].replace('\n', '')
            
            if 'newContext' in turn:
                # Remove newlines from newContext 
                turn['newContext'] = turn['newContext'].replace('\n', '')
    
    # Write back the modified JSON
    with open(json_file, 'w') as f:
        print("Finished processing. Writing back to", json_file)
        json.dump(data, f, indent=2)

print("All files processed.")