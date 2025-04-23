import os
import json
import re
import pandas as pd # Import pandas
import openpyxl # Import openpyxl

def count_cross_examinations(directory_path, output_excel_filename="cross_examination_counts.xlsx"):
    """
    Counts the number of turns with 'noPresent': False in JSON files
    within the specified directory, filtering by filename pattern (1-1-1 to 6-6-4).
    Outputs the results (for files with count > 0) to an Excel file.

    Args:
        directory_path (str): The path to the directory containing the JSON files.
        output_excel_filename (str): The name for the output Excel file.

    Returns:
        None: Prints summary and saves the Excel file.
    """
    files_processed = 0
    files_skipped = 0
    files_with_errors = []
    results_for_excel = [] # List to store results for Excel output

    print(f"Scanning directory: {directory_path}")

    # Define the regex pattern to match filenames like X-Y-Z_*.json
    # X: 1-6, Y: 1-6, Z: 1-4
    filename_pattern = re.compile(r'^([1-6])-([1-6])-([1-4])_.*\.json$')

    # Ensure the directory exists
    if not os.path.isdir(directory_path):
        print(f"Error: Directory not found - {directory_path}")
        return

    all_files = sorted(os.listdir(directory_path)) # Sort for consistent order

    for filename in all_files:
        if filename.endswith(".json"):
            # Check if the filename matches the desired pattern
            match = filename_pattern.match(filename)
            if not match:
                # print(f" - Skipping {filename} (does not match pattern)") # Keep this commented unless debugging
                files_skipped += 1
                continue # Skip files that don't match the X-Y-Z pattern and ranges

            # If the pattern matches, proceed with processing
            file_path = os.path.join(directory_path, filename)
            file_ce_count = 0
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Check if 'turns' key exists and is a list
                turns = data.get("turns")
                if isinstance(turns, list):
                    for turn in turns:
                        # Check if 'turn' is a dictionary and 'noPresent' key exists and is False
                        if isinstance(turn, dict) and turn.get("noPresent") is False:
                             # Also check if 'category' is 'cross_examination' for robustness
                             if turn.get("category") == "cross_examination":
                                file_ce_count += 1
                # else: # Don't warn if 'turns' is missing, just means 0 CEs
                     # print(f"Warning: 'turns' key missing or not a list in {filename}")

                # Only add to results if there's at least one CE
                if file_ce_count > 0:
                    print(f" - Found {file_ce_count} cross-examinations in {filename}")
                    results_for_excel.append({
                        "Filename": filename,
                        "Cross Examination Count": file_ce_count
                    })
                # else: # Optional: print files with 0 CEs if needed for debugging
                    # print(f" - Found 0 cross-examinations in {filename}")

                files_processed += 1

            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON in {filename}")
                files_with_errors.append(filename)
            except FileNotFoundError:
                 print(f"Error: File not found - {file_path}")
                 files_with_errors.append(filename)
            except Exception as e:
                print(f"An unexpected error occurred processing {filename}: {e}")
                files_with_errors.append(filename)
        else:
             # print(f"Warning: Skipping non-JSON file - {filename}") # Keep commented unless debugging
             files_skipped += 1 # Count non-json files as skipped too

    # --- Generate Excel File ---
    excel_file_path = ""
    if results_for_excel:
        try:
            df = pd.DataFrame(results_for_excel)
            # Save Excel in the same directory as the script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            excel_file_path = os.path.join(script_dir, output_excel_filename)
            df.to_excel(excel_file_path, index=False, engine='openpyxl')
            print(f"\nSuccessfully created Excel file: {excel_file_path}")
        except Exception as e:
            print(f"\nError creating Excel file: {e}")
            excel_file_path = "" # Reset path if saving failed
    else:
        print("\nNo cross-examinations found in matching files. Excel file not created.")


    # --- Final Summary ---
    print("\n--- Summary ---")
    print(f"Total JSON files matching pattern processed: {files_processed}")
    print(f"Total files skipped (no match or not JSON): {files_skipped}")
    print(f"Total files with cross-examinations (count > 0): {len(results_for_excel)}")
    if excel_file_path:
         total_ces_in_excel = sum(item['Cross Examination Count'] for item in results_for_excel)
         print(f"Total cross-examinations listed in Excel: {total_ces_in_excel}")
    if files_with_errors:
        print(f"Files with errors ({len(files_with_errors)}): {', '.join(files_with_errors)}")


# --- Main execution ---
if __name__ == "__main__":
    # Adjust the path relative to where you run the script
    final_data_dir = os.path.join('..', '..', 'final') # Relative path from scripts/Yuan

    # Or specify the absolute path directly if needed
    # final_data_dir = '/path/to/your/aceattorney_data/final'

    # Define the desired name for the output Excel file
    excel_filename = "ace_attorney_cross_examinations.xlsx"

    count_cross_examinations(final_data_dir, output_excel_filename=excel_filename)
