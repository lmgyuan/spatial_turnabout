import json

def calculate_accuracy(file_path: str):
    """Calculate the accuracy based on the number of correct actions in a JSON file."""
    try:
        with open(file_path, 'r') as file:
            # Load the list of JSON documents
            documents = json.load(file)

        total_documents = len(documents)
        correct_documents = sum(1 for doc in documents if doc["is_correct"])

        # Calculate accuracy
        accuracy = correct_documents / total_documents if total_documents > 0 else 0

        # Print the results
        print(f"Total documents: {total_documents}")
        print(f"Correct documents: {correct_documents}")
        print(f"Accuracy: {accuracy:.2f}")

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' contains invalid JSON.")
    except KeyError as e:
        print(f"Error: Missing expected key {e} in the JSON data.")

if __name__ == "__main__":
    file_path = 'evaluation.json'  # Replace with your JSON file path
    calculate_accuracy(file_path)
