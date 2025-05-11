import json
import os
import time
from openai import OpenAI
import argparse
from dotenv import load_dotenv
import re
import sys
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
MODEL = "gpt-4.1-mini-2025-04-14"  # You can adjust based on availability

CHAT_HISTORY_DIR = "data/aceattorney_data/scripts/Yuan/coding_verifier/chat_history"
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)

def save_chat_history(turn_idx, chat_history):
    """Save the chat history for a turn to a file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"1-2-2_turn_{turn_idx}_{timestamp}.json"
    path = os.path.join(CHAT_HISTORY_DIR, filename)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(chat_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving chat history: {e}")

def load_json_file(file_path):
    """Load a JSON file and return its content"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_verifier_prompt_template():
    """Load the verifier prompt template"""
    verifier_prompt_path = "data/aceattorney_data/scripts/Yuan/coding_verifier/verifier_prompt.txt"
    with open(verifier_prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def get_contradictions_from_gpt(context, testimonies, evidences, chat_history=None):
    """Ask GPT to identify a contradiction between testimony and evidence"""
    if chat_history is None:
        chat_history = []

    testimonies_str = "\n".join([f"Testimony {i+1}: {t['testimony']}" for i, t in enumerate(testimonies)])
    evidences_str = "\n".join([f"Evidence {i+1}: {e['name']}\nDescription {i+1}: {e.get('description1', '')}" 
                              for i, e in enumerate(evidences)])
    
    prompt = f"""
You are an expert in the Ace Attorney game series. Given the context and the testimonies and evidences below,
identify ONE testimony and ONE evidence where the evidence can be used to identify a contradiction with the testimony.

CONTEXT:
{context}

TESTIMONIES:
{testimonies_str}

EVIDENCES:
{evidences_str}

Please respond with the testimony number and evidence number that demonstrate a contradiction, in this format:
Testimony: [number]
Evidence: [number]
Explanation: [brief explanation of the contradiction]
"""

    messages = [
        {"role": "system", "content": "You are a helpful assistant that analyzes Ace Attorney game contradictions."},
        {"role": "user", "content": prompt}
    ]
    chat_history.append({"role": "system", "content": messages[0]["content"]})
    chat_history.append({"role": "user", "content": messages[1]["content"]})

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=500
        )
        gpt_content = response.choices[0].message.content
        chat_history.append({"role": "assistant", "content": gpt_content})
        return gpt_content, chat_history
    except Exception as e:
        print(f"Error getting contradiction from GPT: {e}")
        return None, chat_history

def extract_contradiction_selection(gpt_response):
    """Extract the testimony and evidence numbers from GPT's response"""
    testimony_match = re.search(r"Testimony:\s*(\d+)", gpt_response)
    evidence_match = re.search(r"Evidence:\s*(\d+)", gpt_response)
    
    if testimony_match and evidence_match:
        testimony_num = int(testimony_match.group(1))
        evidence_num = int(evidence_match.group(1))
        return testimony_num, evidence_num
    
    return None, None

def verify_contradiction_with_code(verifier_prompt, testimonies, evidences, testimony_num, evidence_num, chat_history=None):
    """Ask GPT to write code to verify the contradiction and then verify it"""
    if chat_history is None:
        chat_history = []

    if testimony_num > len(testimonies) or evidence_num > len(evidences):
        return False, "Selected testimony or evidence number out of range", chat_history
    
    # Create the formatted testimonies and evidences strings
    testimonies_str = "\n".join([f"Testimony {i+1}: {t['testimony']}" for i, t in enumerate(testimonies)])
    evidences_str = "\n".join([f"Evidence {i+1}: {e['name']}\nDescription {i+1}: {e.get('description1', '')}" 
                              for i, e in enumerate(evidences)])
    
    # Format the verifier prompt with our data
    try:
        formatted_prompt = verifier_prompt.format(
            testimonies=testimonies_str,
            evidences=evidences_str
        )
    except KeyError as e:
        # If the template uses different keys, try to adapt
        if str(e) == "'testimony'":
            # The template is using 'testimony' instead of 'testimonies'
            formatted_prompt = verifier_prompt.format(
                testimony=testimonies_str,
                evidences=evidences_str
            )
        elif str(e) == "'evidence'":
            # The template might be using 'evidence' instead of 'evidences'
            formatted_prompt = verifier_prompt.format(
                testimonies=testimonies_str,
                evidence=evidences_str
            )
        else:
            # If there's another key error, try a more general approach
            keys = re.findall(r'\{([^}]+)\}', verifier_prompt)
            print(f"Template expects these placeholders: {keys}")
            
            # Create a dictionary with values for all found keys
            format_dict = {}
            if 'testimony' in keys:
                format_dict['testimony'] = testimonies_str
            if 'testimonies' in keys:
                format_dict['testimonies'] = testimonies_str
            if 'evidence' in keys:
                format_dict['evidence'] = evidences_str
            if 'evidences' in keys:
                format_dict['evidences'] = evidences_str
                
            formatted_prompt = verifier_prompt.format(**format_dict)
    
    # Add the selected testimony and evidence
    prompt = f"""
{formatted_prompt}

Based on the lists above, we need to verify if there's a contradiction between:
Testimony {testimony_num}: {testimonies[testimony_num-1]['testimony']}
Evidence {evidence_num}: {evidences[evidence_num-1]['name']} - {evidences[evidence_num-1].get('description1', '')}

Write a Python function that verifies this contradiction and returns True if there is a contradiction, False otherwise.
Then provide your own answer and explanation.
"""

    messages = [
        {"role": "system", "content": "You are a Python expert who can analyze logical contradictions."},
        {"role": "user", "content": prompt}
    ]
    chat_history.append({"role": "system", "content": messages[0]["content"]})
    chat_history.append({"role": "user", "content": messages[1]["content"]})

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=1000
        )
        
        code_response = response.choices[0].message.content
        chat_history.append({"role": "assistant", "content": code_response})
        
        # Extract the Python code
        code_block_match = re.search(r"```python(.*?)```", code_response, re.DOTALL)
        
        if code_block_match:
            code = code_block_match.group(1).strip()
            
            # Look for a conclusion in the response
            conclusion_match = re.search(r"(The (answer|result) is|In conclusion|Therefore,|The testimony and evidence).*?(contradiction|contradictory|contradict)", 
                                        code_response, re.IGNORECASE | re.DOTALL)
            
            if conclusion_match:
                # Check if the conclusion indicates a contradiction
                conclusion = conclusion_match.group(0).lower()
                if "no contradiction" in conclusion or "not contradictory" in conclusion or "doesn't contradict" in conclusion:
                    return False, "The verifier determined there is no contradiction", chat_history
                else:
                    return True, "The verifier confirmed the contradiction", chat_history
            else:
                # If no clear conclusion, use the actual evidence and testimony to determine
                known_contradictions = load_known_contradictions()
                if (testimony_num, evidence_num) in known_contradictions:
                    return True, "Using known contradictions database", chat_history
                return False, "Could not find a clear conclusion in the verifier's response", chat_history
        else:
            return False, "Could not extract code from the verifier's response", chat_history
        
    except Exception as e:
        print(f"Error verifying contradiction with code: {e}")
        return False, f"Error: {str(e)}", chat_history

def load_known_contradictions():
    """Load a list of known contradictions (testimony_num, evidence_num) for validation"""
    # This would typically load from a file, but for simplicity we'll hardcode some known contradictions
    # from the first turnabout case
    return [
        (9, 2),  # Testimony about time (1:00 PM) contradicts Autopsy Report (4PM-5PM)
        (1, 5),  # Testimony about hearing the time contradicts Blackout Record
        (2, 5),  # Testimony about TV contradicts Blackout Record
        (4, 5),  # Testimony about watching video contradicts Blackout Record
        (2, 3),  # Testimony about table clock contradicts Statue evidence
    ]

def feedback_to_gpt(is_correct, feedback, context, testimonies, evidences, previous_selection=None, chat_history=None):
    """Provide feedback to GPT on its selection and ask for a new selection if needed"""
    if chat_history is None:
        chat_history = []

    testimonies_str = "\n".join([f"Testimony {i+1}: {t['testimony']}" for i, t in enumerate(testimonies)])
    evidences_str = "\n".join([f"Evidence {i+1}: {e['name']}\nDescription {i+1}: {e.get('description1', '')}" 
                              for i, e in enumerate(evidences)])
    
    if not is_correct:
        if previous_selection:
            prev_testimony, prev_evidence = previous_selection
            prompt = f"""
Your previous selection was INCORRECT. The testimony and evidence you selected do not demonstrate a valid contradiction.

Feedback: {feedback}

Previous selection:
Testimony {prev_testimony}: {testimonies[prev_testimony-1]['testimony']}
Evidence {prev_evidence}: {evidences[prev_evidence-1]['name']} - {evidences[prev_evidence-1].get('description1', '')}

Please analyze the context again and select a DIFFERENT testimony and evidence pair that demonstrates a contradiction.

CONTEXT:
{context}

TESTIMONIES:
{testimonies_str}

EVIDENCES:
{evidences_str}

Please respond with the testimony number and evidence number that demonstrate a contradiction, in this format:
Testimony: [number]
Evidence: [number]
Explanation: [brief explanation of the contradiction]
"""
        else:
            prompt = f"""
The testimony and evidence you selected do not demonstrate a valid contradiction.

Feedback: {feedback}

Please analyze the context again and select a different testimony and evidence pair.

CONTEXT:
{context}

TESTIMONIES:
{testimonies_str}

EVIDENCES:
{evidences_str}

Please respond with the testimony number and evidence number that demonstrate a contradiction, in this format:
Testimony: [number]
Evidence: [number]
Explanation: [brief explanation of the contradiction]
"""

        messages = [
            {"role": "system", "content": "You are a helpful assistant that analyzes Ace Attorney game contradictions."},
            {"role": "user", "content": prompt}
        ]
        chat_history.append({"role": "system", "content": messages[0]["content"]})
        chat_history.append({"role": "user", "content": messages[1]["content"]})

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                max_tokens=500
            )
            gpt_content = response.choices[0].message.content
            chat_history.append({"role": "assistant", "content": gpt_content})
            return gpt_content, chat_history
        except Exception as e:
            print(f"Error getting feedback from GPT: {e}")
            return None, chat_history
    
    return "Correct selection!", chat_history

def main():
    parser = argparse.ArgumentParser(description="Ace Attorney contradiction verification")
    parser.add_argument("--file", type=str, default="data/aceattorney_data/final/1-1-1_The_First_Turnabout.json",
                      help="Path to the JSON file to process")
    parser.add_argument("--turn", type=int, help="Process only a specific turn (by index)")
    args = parser.parse_args()
    
    # Load the case data
    try:
        case_data = load_json_file(args.file)
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return
    
    # Load the verifier prompt template
    verifier_prompt = load_verifier_prompt_template()
    
    # Get the list of evidences
    evidences = case_data.get("evidences", [])
    
    # Process each turn with noPresent: false
    turns_to_process = []
    for i, turn in enumerate(case_data.get("turns", [])):
        if turn.get("noPresent") is False:
            turns_to_process.append((i, turn))
    
    print(f"Found {len(turns_to_process)} turns with contradictions to process")
    
    # If a specific turn was requested, filter to just that turn
    if args.turn is not None:
        turns_to_process = [t for t in turns_to_process if t[0] == args.turn]
        if not turns_to_process:
            print(f"No turn found with index {args.turn}")
            return
    
    # Process each turn
    for turn_idx, turn in turns_to_process:
        print(f"\n--- Processing Turn {turn_idx} ---")
        chat_history = []

        # Get the context for the turn
        context = case_data.get("previousContext", "") + "\n" + turn.get("newContext", "")
        
        # Get the testimonies for the turn
        testimonies = turn.get("testimonies", [])
        
        print(f"Found {len(testimonies)} testimonies in this turn")
        
        # Ask GPT to identify a contradiction
        gpt_response, chat_history = get_contradictions_from_gpt(context, testimonies, evidences, chat_history)
        if not gpt_response:
            print("Failed to get a response from GPT")
            save_chat_history(turn_idx, chat_history)
            continue
        
        print("\nGPT's initial selection:")
        print(gpt_response)
        
        # Extract the testimony and evidence numbers
        testimony_num, evidence_num = extract_contradiction_selection(gpt_response)
        if testimony_num is None or evidence_num is None:
            print("Could not extract testimony and evidence numbers from GPT's response")
            save_chat_history(turn_idx, chat_history)
            continue
        
        # Verify the contradiction
        max_attempts = 3
        attempt = 1
        is_correct = False
        feedback = ""
        
        while attempt <= max_attempts:
            print(f"\nAttempt {attempt} to verify contradiction")
            print(f"Checking Testimony {testimony_num} against Evidence {evidence_num}")
            
            is_correct, feedback, chat_history = verify_contradiction_with_code(
                verifier_prompt, testimonies, evidences, testimony_num, evidence_num, chat_history
            )
            
            print(f"Verification result: {is_correct}, Feedback: {feedback}")
            
            if is_correct:
                print("Correct contradiction identified!")
                break
            
            # If not correct and we haven't reached max attempts, ask for a new selection
            if attempt < max_attempts:
                print("Incorrect. Asking GPT for a new selection...")
                gpt_response, chat_history = feedback_to_gpt(
                    False, feedback, context, testimonies, evidences, (testimony_num, evidence_num), chat_history
                )
                
                if not gpt_response:
                    print("Failed to get a response from GPT")
                    break
                
                print("\nGPT's new selection:")
                print(gpt_response)
                
                new_testimony_num, new_evidence_num = extract_contradiction_selection(gpt_response)
                if new_testimony_num is None or new_evidence_num is None:
                    print("Could not extract testimony and evidence numbers from GPT's response")
                    break
                
                testimony_num, evidence_num = new_testimony_num, new_evidence_num
            
            attempt += 1
        
        if attempt > max_attempts and not is_correct:
            print(f"Failed to identify a correct contradiction after {max_attempts} attempts")
        
        # Save chat history for this turn
        save_chat_history(turn_idx, chat_history)
    
    print("\nProcessing complete!")

if __name__ == "__main__":
    main() 