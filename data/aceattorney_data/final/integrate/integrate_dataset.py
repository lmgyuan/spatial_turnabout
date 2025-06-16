import json
import os
import glob

def create_integrated_dataset():
    # Load the prompt prefix and suffix
    with open('source/prompts/base.json', 'r') as f:
        prompt_data = json.load(f)
    prompt_prefix = prompt_data['prefix']
    prompt_suffix = prompt_data['suffix']

    # Path to the directory containing the final JSON files
    final_data_path = 'data/aceattorney_data/final/'
    output_path = 'data/aceattorney_data/final/integrate/'
    
    # Get all JSON files in the directory
    json_files = glob.glob(os.path.join(final_data_path, '*.json'))

    all_turns_data = []

    for file_path in json_files:
        with open(file_path, 'r') as f:
            data = json.load(f)

        file_prefix = os.path.basename(file_path).replace('.json', '')

        # Create a mapping from evidence name to index
        try:
            evidence_name_to_id = {evidence['name']: i for i, evidence in enumerate(data['evidences'])}
        except:
            print("--------------------------------")
            print(f"No evidences for {file_path}")
            print("--------------------------------")
            continue

        # Format evidence string
        evidence_str = "Evidence:\n"
        for i, evidence in enumerate(data['evidences']):
            desc = evidence['description1']
            if 'description2' in evidence and evidence['description2']:
                desc += " " + evidence['description2']
            evidence_str += f"[{i}] Name: {evidence['name']}\nDescription: {desc}\n\n"

        for turn_idx, turn in enumerate(data['turns']):
            if turn['category'] != 'cross_examination':
                continue
            if turn['noPresent']:
                continue
                
            source = f"{file_prefix}_{turn_idx}"

            # Format testimonies string
            testimonies_str = "Testimonies:\n"
            for i, testimony in enumerate(turn['testimonies']):
                testimonies_str += f"[{i}] Testimony: {testimony['testimony']}\n"
            
            try: 
                summarized_context = f"Summarized context:\n{turn['summarizedContext']}\n"
            except:
                print("--------------------------------")
                print(f"No summarized context for {file_path} {turn_idx}")
                summarized_context = ""

            input_json = {
                "prefix": prompt_prefix,
                "evidence": evidence_str,
                "testimonies": testimonies_str,
                "summarized_context": summarized_context,
                "suffix": prompt_suffix,
                "full_input": f"{prompt_prefix}\n{evidence_str}\n{testimonies_str}\n{summarized_context}\n{prompt_suffix}"
            }
            output_pairs = []
            if not turn.get('noPresent', True):
                for testimony_idx, testimony in enumerate(turn['testimonies']):
                    if 'present' in testimony and testimony['present']:
                        for evidence_name in testimony['present']:
                            if evidence_name in evidence_name_to_id:
                                evidence_id = evidence_name_to_id[evidence_name]
                                output_pairs.append([testimony_idx, evidence_id])
            
            all_turns_data.append({
                "source": source,
                "input": input_json,
                "output": output_pairs
            })

    # Write the integrated dataset to a new JSON file
    output_file_path = os.path.join(output_path, 'integrated_dataset.json')
    with open(output_file_path, 'w') as f:
        json.dump(all_turns_data, f, indent=2)

    print(f"Integrated dataset created at: {output_file_path}")

if __name__ == '__main__':
    create_integrated_dataset()
