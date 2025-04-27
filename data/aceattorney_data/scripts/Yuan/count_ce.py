import os
import json
import re
import pandas as pd # Import pandas
import openpyxl # Import openpyxl

def count_cross_examinations(directory_path, output_excel_filename="cross_examination_counts.xlsx"):
    """
    Counts the number of turns with 'noPresent': False in JSON files
    within the specified directory. Only processes JSON files starting with '9' or '10'.
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

    # Ensure the directory exists
    if not os.path.isdir(directory_path):
        print(f"Error: Directory not found - {directory_path}")
        return

    all_files = sorted(os.listdir(directory_path)) # Sort for consistent order

    for filename in all_files:
        # Only process JSON files that start with 9 or 10
        if filename.endswith(".json") and (filename.startswith("9") or filename.startswith("10")):
            # Process all JSON files
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
                            file_ce_count += 1
                else:
                    print(f"Warning: 'turns' key missing or not a list in {filename}")

                # Only add to results if there's at least one CE
                if file_ce_count > 0:
                    print(f" - Found {file_ce_count} cross-examinations in {filename}")
                    results_for_excel.append({
                        "Filename": filename,
                        "Cross Examination Count": file_ce_count
                    })

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
            files_skipped += 1 # Count non-matching files as skipped

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
    print(f"Total JSON files processed: {files_processed}")
    print(f"Total files skipped (not matching criteria): {files_skipped}")
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
    excel_filename = "ace_attorney_cross_examinations_9_10.xlsx"

    count_cross_examinations(final_data_dir, output_excel_filename=excel_filename)
