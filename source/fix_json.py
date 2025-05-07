import os
import json
import shutil
for root, dirs, files in os.walk("../output"):
    if "legacy" in root:
        continue
    for file in files:
        if file.startswith("batchinput") or file.startswith("batchoutput"):
            print(f"Processing {os.path.join(root, file)}")

            with open(os.path.join(root, file), "r") as f:
                data = [json.loads(line) for line in f]
            print(f"len of data: {len(data)}")

            new_data = []
            
            for line in data:
                if line["custom_id"].startswith("8-5-1") or line["custom_id"].startswith("8-3-4"):
                    continue
                else:
                    new_data.append(line)
                
            print(f"len of new_data: {len(new_data)}")                        

            with open(os.path.join(root, file), "w") as f:
                for line in new_data:
                    f.write(json.dumps(line) + "\n")

        if file.startswith("8-5-1") or file.startswith("8-3-4"):
            os.remove(os.path.join(root, file))
                
            