import json
import os
import glob
import re

def create_integrated_dataset():
    # Load the prompt prefix and suffix
    with open('source/prompts/base.json', 'r') as f:
        prompt_data = json.load(f)
    prompt_prefix = prompt_data['prefix']
    prompt_suffix = prompt_data['suffix']

    # Path to the directory containing the final JSON files
    final_data_path = 'data/danganronpa_data/final/'
    output_path = 'data/danganronpa_data/final/integrate_dataset/'
    
    # Load all truth bullets
    with open(os.path.join(final_data_path, '_truth_bullets.json'), 'r') as f:
        truth_bullets = json.load(f)

    # Get all JSON files in the directory, excluding the truth bullets file
    json_files = glob.glob(os.path.join(final_data_path, '1-*.json'))

    all_turns_data = []

    for file_path in json_files:
        with open(file_path, 'r') as f:
            data = json.load(f)

        file_prefix = os.path.basename(file_path).replace('.json', '')
        
        # Extract chapter number from filename like "1-1"
        match = re.search(r'1-(\d+)', file_prefix)
        if not match:
            continue
        chapter_num = match.group(1)
        chapter_key = f"Chapter {chapter_num}"

        if chapter_key not in truth_bullets:
            print(f"--------------------------------")
            print(f"No evidences for {chapter_key} in _truth_bullets.json")
            print(f"--------------------------------")
            continue
            
        evidences = truth_bullets[chapter_key]
        evidence_name_to_id = {evidence['name']: i for i, evidence in enumerate(evidences)}

        # Format evidence string
        evidence_str = "Evidence:\n"
        for i, evidence in enumerate(evidences):
            desc = evidence.get('description', '')
            evidence_str += f"[{i}] Name: {evidence['name']}\nDescription: {desc}\n\n"

        if 'turns' not in data:
            continue

        for turn_idx, turn in enumerate(data['turns']):
            if turn.get('category') != 'cross_examination':
                continue
            if turn.get('noPresent', True): # Danganronpa seems to use noPresent, but let's be safe
                continue
                
            source = f"{file_prefix}_{turn_idx}"

            # Format testimonies string
            testimonies_str = "Testimonies:\n"
            for i, testimony in enumerate(turn['testimonies']):
                testimonies_str += f"[{i}] Testimony: {testimony['testimony']}\n"
            
            summarized_context = f"Summarized context:\n{turn.get('summarizedContext', '')}\n"

            input_json = {
                "prefix": prompt_prefix,
                "evidence": evidence_str,
                "testimonies": testimonies_str,
                "summarized_context": summarized_context,
                "suffix": prompt_suffix,
                "full_input": f"{prompt_prefix}\n{evidence_str}\n{testimonies_str}\n{summarized_context}\n{prompt_suffix}"
            }
            output_pairs = []
            
            for testimony_idx, testimony in enumerate(turn['testimonies']):
                if 'present' in testimony and testimony['present']:
                    # In Danganronpa, present is a list of strings
                    for evidence_name in testimony['present']:
                        if evidence_name in evidence_name_to_id:
                            evidence_id = evidence_name_to_id[evidence_name]
                            output_pairs.append([testimony_idx, evidence_id])
            
            if not output_pairs:
                continue

            all_turns_data.append({
                "source": source,
                "input": input_json,
                "output": output_pairs
            })

    # Write the integrated dataset to a new JSON file
    output_file_path = os.path.join(output_path, 'DR_integrate_dataset.json')
    with open(output_file_path, 'w') as f:
        json.dump(all_turns_data, f, indent=2)

    print(f"Integrated dataset created at: {output_file_path}")

if __name__ == '__main__':
    create_integrated_dataset()
