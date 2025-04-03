import fire
import os
import json

from dotenv import load_dotenv
load_dotenv("../.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

from openai import OpenAI
client = OpenAI(
    api_key=OPENAI_API_KEY
)

def check_status(output_dir):
    output_dir = os.path.join("/home/mh3897/turnabout/output", output_dir)

    with open(os.path.join(output_dir, "batch_api_metadata.json"), "r") as file:
        data = json.load(file)
    batch_job_id = data["batch_job_id"]

    batch_job = client.batches.retrieve(batch_job_id)
    status = batch_job.status
    print(f"Status: {status}")
        
    if status == "completed":
        result_file_id = batch_job.output_file_id
        print(f"file id: {result_file_id}")

        if result_file_id is None:
            print("Error file created")
            result_file_id = batch_job.error_file_id
        
        result = client.files.content(result_file_id).content

        result_file_name = os.path.join(output_dir, "batchoutput.jsonl")

        with open(result_file_name, 'wb') as file:
            file.write(result)

        return True

    return False

if __name__ == "__main__":
    fire.Fire(check_status)

    # python fetch_openai_models.py --output_dir gpt-4o_harry_v1.3 