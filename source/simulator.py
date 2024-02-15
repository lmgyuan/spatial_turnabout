import argparse
import json
from run_gpt import run_chatgpt

WRONG_EVIDENCE_RESPONSE = open("../case_data/wrong_evidence_response.txt", "r").read()
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
        if turn_data["category"] == "multiple_choice":
            prompt = "Select one of the following choices:\n"
            choices = []
            for i, action_data in enumerate(turn_data["actions"]):
                prompt += str(i) + " " + action_data["choice"] + "\n"
                choices.append(action_data["choice"])
            prompt += 'Answer the question with a JSON object in the format of {"answer": <number of the choice>}, for example {"answer": 0}. Otherwise, you could view the court record by answering with a JSON object in the format of {"action": "court record"}.'
        elif turn_data["category"] == "cross_examination":
            prompt = "Below are the witness' testimonies:\n"
            for i, action_data in enumerate(turn_data["testimonies"]):
                prompt += str(i) + " " + action_data["testimony"] + "\n"
            prompt += "Below are the evidences you have:\n"
            for i, obj in enumerate(court_record["objects"]):
                prompt += str(i) + " " + obj["name"] + "\n"
            prompt += 'You may either press the witness about a specific testimony or present evidence at a testimony to show a contradiction. To press, answer the question with a JSON object in the format of {"action": "press", "testimony": <number of the testimony>}, for example {"action": "press", "testimony": 3}. To present evidence, answer the question with a JSON object in the format of {"action": "present", "testimony": <number of the testimony>, "evidence": <number of the evidence>}, for example {"action": "present", "testimony": 5, "evidence": 2}. Otherwise, you could view the court record by answering with a JSON object in the format of {"action": "court record"}.'
        elif turn_data["category"] == "present":
            prompt = "Below are the evidences you have:\n"
            evidences = []
            for i, obj in enumerate(court_record["objects"]):
                prompt += str(i) + " " + obj["name"] + "\n"
                evidences.append(obj["name"])
            prompt += 'You will present evidence at a testimony to show a contradiction. Do so by answering the question with a JSON object in the format of {"action": "present", "evidence": <name of the evidence>}, for example {"action": "present", "evidence": Broken Clock}. Otherwise, you could view the court record by answering with a JSON object in the format of {"action": "court record"}.'
        #print(prompt)
        prompt_dict = {"role": "user", "content": context + prompt}
        if prompt_dict in past_dialogs:
            prompt_dict = {"role": "user", "content": prompt}
        past_dialogs.append(prompt_dict)
        # Truncate past dialogs
        #if len(past_dialogs) > TRUNCATE_PAST_DIALOGS:
        #    past_dialogs = past_dialogs[-TRUNCATE_PAST_DIALOGS:]
        is_json_well_formed = False
        while not is_json_well_formed:   
            gen_json = run_chatgpt(past_dialogs, args.player)
            print(gen_json)
            response_dict = {"role": "assistant", "content": gen_json}
            past_dialogs.append(response_dict)
            try:
                if "action" in json.loads(gen_json) and json.loads(gen_json)["action"] == "court record":
                    gen_text = "court record"
                elif turn_data["category"] == "multiple_choice":
                    gen_text = json.loads(gen_json)["answer"]
                elif turn_data["category"] == "cross_examination":
                    if json.loads(gen_json)["action"] == "press":
                        gen_text = "press@" + str(json.loads(gen_json)["testimony"])
                    elif json.loads(gen_json)["action"] == "present":
                        gen_text = "present@" + str(json.loads(gen_json)["evidence"]) + "@" + str(json.loads(gen_json)["testimony"])
                    else:
                        print(gen_json)
                        raise ValueError("Invalid action")
                elif turn_data["category"] == "present":
                    gen_text = evidences[json.loads(gen_json)["evidence"]]
            except json.decoder.JSONDecodeError:
                past_dialogs.append({"role": "user", "content": "Your previous input was not a well-formed JSON. Please try again."})
                continue
            is_json_well_formed = True
        print(gen_text)
        #explanation_prompt = "Please explain your reasoning."
        #explanation_dict = {"role": "user", "content": explanation_prompt}
        #gen_explanation = run_chatgpt(past_dialogs + [explanation_dict], args.player)
        #print("Explanation: ", gen_explanation)
        #print(past_dialogs)
        return gen_text, past_dialogs
    
def list_court_record(court_record):
    output = ""
    output += "===Court Record===\n"
    output += "Objects:\n"
    count = 0
    for obj in court_record["objects"]:
        output += str(count) + " " + obj["name"] + "\n"
        output += "  " + obj["description"] + "\n"
        count += 1
    output += "\nPeople:\n"
    for person in court_record["people"]:
        output += str(count) + " " + person["name"] + "\n"
        output += "  " + person["description"] + "\n"
        count += 1
    output += "This is the end of the court record. Please resume your task above."
    return output

def simulate(case_data):
    court_record = {"objects": [], "people": []}
    #past_dialogs = [{"role": "system", "content": "You will play a text-based game of Ace Attorney. You will be given a scenario and you will have to make choices to proceed. You can type 'court record' to view the court record at any time."}]
    past_dialogs = []
    for turn, turn_data in case_data.items():
        #print("Turn: {}".format(turn) + "\n" + "-"*10 + "\n")
        #print(turn_data["context"])
        for add_object in turn_data["court_record"]["add"]["objects"]:
            court_record["objects"].append(add_object)
        for add_person in turn_data["court_record"]["add"]["people"]:
            court_record["people"].append(add_person)
        # TODO: logic for modify is TBD
        if False:
        #if turn_data["category"] == "multiple_choice":
            can_proceed = False
            while not can_proceed:
                print("\n===Multiple Choice===\n")
                for action_data in turn_data["actions"]:
                    print(action_data["choice"])
                print("\n> ")
                user_input, past_dialogs = get_input(past_dialogs, turn_data, court_record)
                if user_input == "court record":
                    print(list_court_record(court_record))
                    past_dialogs.append({"role": "user", "content": list_court_record(court_record)})
                    continue
                for action_data in turn_data["actions"]:
                    if user_input == action_data["choice"]:
                        #print(action_data["response"])
                        past_dialogs.append({"role": "user", "content": action_data["response"]})
                        if action_data["is_correct"] == 1:
                            can_proceed = True
                        break
                else:
                    print("Invalid input")
        #if False:
        if turn_data["category"] == "cross_examination":
            can_proceed = False
            while not can_proceed:
                print("\n===Cross Examination===\n")
                for i, action_data in enumerate(turn_data["testimonies"]):
                    print(str(i) + ": " + action_data["testimony"])
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
                action_data = turn_data["testimonies"][int(user_testimony_index)]
                # press any testimony
                if user_action == "press":
                    print(action_data["press_response"])
                    past_dialogs.append({"role": "user", "content": action_data["press_response"]})
                    if action_data["critical_press"] == 1:
                        pass # TODO: modify the testimony
                # present correct evidence on correct testimony
                elif user_action == "present":
                    if "correct_present" in action_data and user_evidence in action_data["correct_present"]:
                        can_proceed = True
                        print(action_data["present_response"])
                        past_dialogs.append({"role": "user", "content": action_data["present_response"]})
                    else:
                        print(WRONG_EVIDENCE_RESPONSE)
                        past_dialogs.append({"role": "user", "content": WRONG_EVIDENCE_RESPONSE})
        if False:
        #elif turn_data["category"] == "present":
            can_proceed = False
            while not can_proceed:
                print("\n===Present===\n")
                print("\n> ")
                user_input, past_dialogs = get_input(past_dialogs, turn_data, court_record)
                if user_input == "court record":
                    print(list_court_record(court_record))
                    past_dialogs.append({"role": "user", "content": list_court_record(court_record)})
                    continue
                user_choice = user_input
                for action_data in turn_data["actions"]:
                    # present correct evidence
                    if action_data["evidence"] == user_evidence:
                        assert action_data["is_correct"] == 1
                        can_proceed = True
                        #print(action_data["response"])
                        past_dialogs.append({"role": "user", "content": action_data["response"]})
                        break
                    # present incorrect evidence
                    elif action_data["evidence"] == "WRONG_EVIDENCE":
                        #print(action_data["response"])
                        past_dialogs.append({"role": "user", "content": action_data["response"]})
                        break
                else:
                    print("Invalid input")
        #break

def main():
    with open("../case_data/{}.json".format(args.case), 'r') as file:
        case_data = json.load(file)

    simulate(case_data)
    

if __name__ == '__main__':
    main()
