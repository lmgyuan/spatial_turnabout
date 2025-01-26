import json
import json
import pandas as pd
from collections import defaultdict


def calculate_accuracy(file_path: str):
    """Calculate the accuracy based on the number of correct actions for each case_name in a JSON file."""
    try:
        with open(file_path, 'r') as file:
            # Load the list of JSON documents
            documents = json.load(file)

        # Dictionary to store case_name grouped documents
        case_name_group = defaultdict(list)

        # Group documents by case_name
        for doc in documents:
            case_name = doc.get("case_name")
            if case_name:
                case_name_group[case_name].append(doc)
            else:
                print("Error: Missing 'case_name' in one or more documents.")

        # Prepare data for the DataFrame
        data = []
        for case_name, docs in case_name_group.items():
            total_documents = len(docs)
            correct_documents = sum(1 for doc in docs if doc.get("is_correct"))

            # Calculate accuracy
            accuracy = correct_documents / total_documents if total_documents > 0 else 0

            # Append the data as a row
            data.append({
                'case_name': case_name,
                'accuracy': accuracy
            })

        # Return the DataFrame for this file
        return pd.DataFrame(data)

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' contains invalid JSON.")
    except KeyError as e:
        print(f"Error: Missing expected key {e} in the JSON data.")
    return pd.DataFrame()


def generate_combined_excel(file_paths: dict, output_excel_path: str):
    """Generate an Excel report for both evaluation files."""
    all_dfs = []

    for name, path in file_paths.items():
        df = calculate_accuracy(path)
        df.rename(columns={'accuracy': f'{name}_accuracy'}, inplace=True)
        all_dfs.append(df)

    # Merge the dataframes on 'case_name' (outer join to include all case names from both files)
    print("all_dfs length: ", len(all_dfs))
    if len(all_dfs) > 1:
        combined_df = all_dfs[0]

        # Iteratively merge each subsequent dataframe
        for i in range(1, len(all_dfs)):
            combined_df = combined_df.merge(all_dfs[i], on='case_name', how='outer')
    else:
        combined_df = all_dfs[0]

    # Export to Excel
    combined_df.to_excel(output_excel_path, index=False)
    print(f"Excel file '{output_excel_path}' has been created successfully.")


if __name__ == "__main__":
    file_paths = {
        'cot_all_context': 'evaluation_cot_few_shot.json',  # Replace with your first JSON file path
        'all_context': 'evaluation.json',  # Replace with your second JSON file path
        'cot_no_context': 'evaluation_cot_few_shot_no_context.json',
        'no_cot_no_context': 'evaluation_no_context.json'
    }
    output_excel_path = 'combined_accuracy_report.xlsx'  # Specify the output Excel file path
    generate_combined_excel(file_paths, output_excel_path)
