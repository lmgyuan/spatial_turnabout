json_path = "../GS1/en/sc0_text_u.mdt.jsonl"

import json

texts = []
with open(json_path, 'r') as file:
    for line in file:
        if line.strip():  # Skip empty lines
            try:
                item = json.loads(line.strip())
                content = item.get('content', '')
                # Only append non-empty content
                if content and content.strip():
                    texts.append(content)

            except json.JSONDecodeError as e:
                print(f"Error decoding line: {e}")
                print(f"Problematic line: {line[:100]}")  # Print part of the line for debugging

# Print the count of text entries
print(f"Found {len(texts)} non-empty text entries")

# Print the first 10 text entries to verify content
if texts:
    print("\nFirst 10 text entries:")
    for i, text in enumerate(texts[:10]):
        print(f"{i+1}. {text}")

# Optionally, print all texts
print("\nAll texts:")
print(texts)