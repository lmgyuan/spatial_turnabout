import os
import re # Import regex

# --- Configuration ---
INPUT_DIR = os.path.join("data", "aceattorney_data", "generated", "japanese_crafted", "AA3", "3-3_Context")
FILENAME = "3-3_CE1.txt" # Use the same name for input and output
# Regex to find common control characters (tab, newline, carriage return)
CONTROL_CHARS_PATTERN = re.compile(r'[\t\n\r]')

# --- Main Logic ---
def main():
    filepath = os.path.join(INPUT_DIR, FILENAME)

    if not os.path.exists(filepath):
        print(f"Error: File not found at {filepath}")
        return

    print(f"Processing file: {filepath}")
    original_content = ""
    single_line_content = ""

    try:
        # Step 1: Read the original content
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
        print(f"Successfully read {len(original_content)} characters.")

        # Step 2: Remove all common control characters (newline, tab, carriage return)
        single_line_content = CONTROL_CHARS_PATTERN.sub('', original_content)
        # Optionally, normalize spaces if needed after removal
        # single_line_content = re.sub(r'\s+', ' ', single_line_content).strip()
        print(f"Content processed into a single line of {len(single_line_content)} characters (control chars removed).")

        # Step 3: Overwrite the original file with the cleaned content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(single_line_content)
        print(f"Successfully overwrote {filepath} with the cleaned single-line content.")

    except Exception as e:
        print(f"An error occurred during processing: {e}")

if __name__ == "__main__":
    main() 