import subprocess
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Verify that the OpenAI API key is set
if not os.environ.get("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY environment variable is not set.")
    print("Please create a .env file with your OpenAI API key or set it in your environment.")
    exit(1)

# Verify that the required files exist
case_file = "data/aceattorney_data/final/1-2-2_Turnabout_Sisters.json"
verifier_file = "data/aceattorney_data/scripts/Yuan/coding_verifier/verifier_prompt.txt"

if not os.path.exists(case_file):
    print(f"Error: Case file not found: {case_file}")
    exit(1)

if not os.path.exists(verifier_file):
    print(f"Error: Verifier prompt file not found: {verifier_file}")
    exit(1)

# Run the main script
print("Starting the Ace Attorney contradiction verification process...")
print(f"Processing case file: {case_file}")

try:
    # Run the verification script
    subprocess.run(["python", "data/aceattorney_data/scripts/Yuan/coding_verifier/contradiction_verification.py", 
                    "--file", case_file], check=True)
    
    print("\nVerification completed successfully!")
    
except subprocess.CalledProcessError as e:
    print(f"Error running the verification script: {e}")
    exit(1)
except KeyboardInterrupt:
    print("\nProcess interrupted by user.")
    exit(0) 