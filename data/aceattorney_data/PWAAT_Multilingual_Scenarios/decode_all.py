import os
import shutil
import subprocess
import re

DEC_PROGRAM = "D:\\Dev\\GSTools-master\\GSMdtTools\\bin\\Debug\\netcoreapp3.1\\GSMdtTools.exe"
SCENARIO_FOLDERS = [
    "D:\\Games\\Phoenix Wright Ace Attorney Trilogy\\PWAAT_Data\\StreamingAssets\\GS1\\scenario",
    "D:\\Games\\Phoenix Wright Ace Attorney Trilogy\\PWAAT_Data\\StreamingAssets\\GS2\\scenario",
    "D:\\Games\\Phoenix Wright Ace Attorney Trilogy\\PWAAT_Data\\StreamingAssets\\GS3\\scenario",
]
OUTPUT_FOLDERS = [
    "D:\\Dev\\PWAAT_Multilingual_Scenarios\\GS1",
    "D:\\Dev\\PWAAT_Multilingual_Scenarios\\GS2",
    "D:\\Dev\\PWAAT_Multilingual_Scenarios\\GS3",
]

def extract_language(filename):
    # Match pattern like *_x.mdt where x is a single letter
    match = re.search(r'_([a-zA-Z])\.mdt$', filename)
    if match:
        return match.group(1)  # return the letter, e.g., 'f' or 'u'
    else:
        return None  # no language suffix

def do_one_file(folder, file, out_folder):
    print(f"Processing {folder} -> {file}...")
    # filename looks like sc1_0_text_f.mdt
    # first extract the _f part
    language = extract_language(file)
    if language is None:
        language = "j"
    lang_out_dir = os.path.join(out_folder, language)
    os.makedirs(lang_out_dir, exist_ok=True)

    input_path = os.path.join(folder, file)
    print(f"  Running MDT decoder on `{input_path}`")
    subprocess.run([DEC_PROGRAM, input_path], check=True)

    jsonl_file = file + ".jsonl"
    src_jsonl = os.path.join(folder, jsonl_file)
    if not os.path.exists(src_jsonl):
        print(f"  [Error] .jsonl not successfully generated for {folder} -> {file}")
        return

    dst_jsonl = os.path.join(lang_out_dir, jsonl_file)
    print(f"  Moving `{src_jsonl}` to `{dst_jsonl}`")
    shutil.move(src_jsonl, dst_jsonl)

def do_one_folder(folder, out_folder):
    for file in os.listdir(folder):
        if file.endswith(".mdt"):
            do_one_file(folder, file, out_folder)

def run():
    for (folder, out_folder) in zip(SCENARIO_FOLDERS, OUTPUT_FOLDERS):
        do_one_folder(folder, out_folder)

if __name__ == "__main__":
    run()