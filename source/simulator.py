import argparse
import json
from run_gpt import run_chatgpt
import openai

WRONG_EVIDENCE_RESPONSE = open("../case_data/hand_coded/wrong_evidence_response.txt", "r").read()
TRUNCATE_PAST_DIALOGS = 6

parser = argparse.ArgumentParser(description='')
parser.add_argument('--case', type=str, help='Identifier of the case in the format of X-Y')
parser.add_argument('--player', type=str, help='human, or an OpenAI model name')
args = parser.parse_args()

def get_input(past_dialogs, turn_data, court_record):
    if args.player == "human":
        return input(), past_dialogs
    else:
        context = turn_data["context"] + "\n"
        if turn_data["category"] == "cross_examination":
            prompt = "Below are the witness' testimonies:\n"
            for i, action_data in enumerate(turn_data["testimonies"]):
                prompt += str(i) + " " + action_data["testimony"] + "\n"
            prompt += "Below are the evidences you have:\n"
            for i, obj in enumerate(court_record["objects"]):
                prompt += str(i) + " " + obj["name"] + "\n"
            prompt += 'You may either press the witness about a specific testimony or present evidence at a testimony to show a contradiction. To press, answer the question with a JSON object in the format of {"action": "press", "testimony": <number of the testimony>}, for example {"action": "press", "testimony": 3}. To present evidence, answer the question with a JSON object in the format of {"action": "present", "testimony": <number of the testimony>, "evidence": <number of the evidence>}, for example {"action": "present", "testimony": 5, "evidence": 2}. Otherwise, you could view the court record by answering with a JSON object in the format of {"action": "court record"}.'
        prompt_dict = {"role": "user", "content": context + prompt}
        past_dialogs.append(prompt_dict)
        is_json_well_formed = False
        while not is_json_well_formed:
            gpt_run_success = False
            while not gpt_run_success:
                # try:
                    gen_json = run_chatgpt(past_dialogs, args.player)
                # except openai.error.InvalidRequestError:
                    print("Input too long, truncating past dialogs")
                    past_dialogs = past_dialogs[2:]
                    continue
                    gpt_run_success = True
            print(gen_json)
            response_dict = {"role": "assistant", "content": gen_json}
            past_dialogs.append(response_dict)
            try:
                if "action" in json.loads(gen_json) and json.loads(gen_json)["action"] == "court record":
                    gen_text = "court record"
                elif turn_data["category"] == "cross_examination":
                    if json.loads(gen_json)["action"] == "present":
                        gen_text = "present@" + str(json.loads(gen_json)["evidence"]) + "@" + str(json.loads(gen_json)["testimony"])
                    else:
                        print(gen_json)
                        raise ValueError("Invalid action")
            except json.decoder.JSONDecodeError:
                past_dialogs.append({"role": "user", "content": "Your previous input was not a well-formed JSON. Please try again."})
                continue
            is_json_well_formed = True
        print(gen_text)
        return gen_text, past_dialogs
    
def list_court_record(court_record):
    output = ""
    output += "===Court Record===\n"
    output += "Objects:\n"
    count = 0
    for obj in court_record["objects"]:
        output += str(count) + " " + obj["name"] + "\n"
        output += ":  " + (obj.get("description2") or obj["description1"]) + "\n"
        count += 1
    output += "\nPeople:\n"
    for person in court_record["people"]:
        output += str(count) + " " + person["name"] + "\n"
        output += ":  " + person["age"] + "\n"
        output += ":  " + person["gender"] + "\n"
        output += ":  " + (person.get("description2") or person["description1"]) + "\n"
        count += 1
    output += "This is the end of the court record. Please resume your task above."
    return output

def simulate(case_data):
    court_record = {"objects": [], "people": []}
    past_dialogs = []
    for turn_data in case_data:
        #print("Turn: {}".format(turn) + "\n" + "-"*10 + "\n")
        print(turn_data["context"])
        court_record["objects"] = turn_data["court_record"]["evidence_objects"]
        court_record["people"] = turn_data["characters"]
        if turn_data["category"] == "cross_examination":
            can_proceed = False
            while not can_proceed:
                print("\n===Cross Examination===\n")
                for i, action_data in enumerate(turn_data["testimonies"]):
                    print(str(i) + ": " + action_data["testimony"])
                print("\nTo present evidence or a person, enter 'present@<number of the evidence or number of the person>@<number of the testimony>'.\n")
                print("\n> ")
                user_input, past_dialogs = get_input(past_dialogs, turn_data, court_record)
                if user_input == "court record":
                    print(list_court_record(court_record))
                    past_dialogs.append({"role": "user", "content": list_court_record(court_record)})
                    continue
                user_action = user_input.split("@")[0]
                user_testimony_index = user_input.split("@")[-1]
                if user_action == "present":
                    user_evidence = court_record["objects"][int(user_input.split("@")[1])]["name"]
                    user_profile = court_record["people"][int(user_input.split("@")[1])]["name"]
                action_data = turn_data["testimonies"][int(user_testimony_index)]
                # present correct evidence on correct testimony
                if user_action == "present":
                    if user_evidence in action_data["present"] or user_profile in action_data["present"]:
                        can_proceed = True
                        #print(action_data["present_response"])
                        # past_dialogs.append({"role": "user", "content": action_data["present_response"]})
                    else:
                        print(WRONG_EVIDENCE_RESPONSE)
                        past_dialogs.append({"role": "user", "content": WRONG_EVIDENCE_RESPONSE})

def main():
    with open("../case_data/scripts/generated/parsed/{}.json".format(args.case), 'r') as file:
        case_data = json.load(file)

    simulate(case_data)
    

if __name__ == '__main__':
    main()
