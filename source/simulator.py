import argparse
import json

WRONG_EVIDENCE_RESPONSE = open("../case_data/wrong_evidence_response.txt", "r").read()

def simulate(case_data):
    court_record = {"objects": [], "people": []}
    for turn, turn_data in case_data.items():
        print("Turn: {}".format(turn) + "\n" + "-"*10 + "\n")
        print(turn_data["context"])
        for add_object in turn_data["court_record"]["add"]["objects"]:
            court_record["objects"].append(add_object)
        for add_person in turn_data["court_record"]["add"]["people"]:
            court_record["people"].append(add_person)
        # TODO: logic for modify is TBD
        if turn_data["category"] == "multiple_choice":
            can_proceed = False
            while not can_proceed:
                print("\n===Multiple Choice===\n")
                for action_data in turn_data["actions"]:
                    print(action_data["choice"])
                print("\n> ")
                user_input = input()
                if user_input == "court record":
                    print(court_record)
                    continue
                for action_data in turn_data["actions"]:
                    if user_input == action_data["choice"]:
                        print(action_data["response"])
                        if action_data["is_correct"] == 1:
                            can_proceed = True
                        break
                else:
                    print("Invalid input")
        elif turn_data["category"] == "cross_examination":
            can_proceed = False
            while not can_proceed:
                print("\n===Cross Examination===\n")
                for action_data in turn_data["actions"]:
                    if action_data["action"] == "press":
                        print(action_data["testimony"])
                print("\n> ")
                user_input = input()
                if user_input == "court record":
                    print(court_record)
                    continue
                user_action = user_input.split("@")[0]
                user_testimony = user_input.split("@")[-1]
                if user_action == "present":
                    user_evidence = user_input.split("@")[1]
                for action_data in turn_data["actions"]:
                    # press any testimony
                    if user_action == "press" and user_testimony == action_data["testimony"] and action_data["action"] == "press":
                        print(action_data["response"])
                        break
                    # present correct evidence on correct testimony
                    elif user_action == "present" and user_testimony == action_data["testimony"] and action_data["action"] == "present" and user_evidence == action_data["evidence"]:
                        assert action_data["is_correct"] == 1
                        can_proceed = True
                        print(action_data["response"])
                        break
                    # present incorrect evidence or on incorrect testimony
                    elif user_action == "present" and user_testimony == action_data["testimony"] and action_data["action"] == "present":
                        print(WRONG_EVIDENCE_RESPONSE)
                else:
                    print("Invalid input")
        elif turn_data["category"] == "present":
            can_proceed = False
            while not can_proceed:
                print("\n===Present===\n")
                print("\n> ")
                if user_input == "court record":
                    print(court_record)
                    continue
                user_input = input()
                user_evidence = user_input
                for action_data in turn_data["actions"]:
                    # present correct evidence
                    if action_data["evidence"] == user_evidence:
                        assert action_data["is_correct"] == 1
                        can_proceed = True
                        print(action_data["response"])
                        break
                    # present incorrect evidence
                    elif action_data["evidence"] == "WRONG_EVIDENCE":
                        print(action_data["response"])
                        break
                else:
                    print("Invalid input")
        #break

def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--case', type=str, help='Identifier of the case in the format of X-Y')
    args = parser.parse_args()

    with open("../case_data/{}.json".format(args.case), 'r') as file:
        case_data = json.load(file)

    simulate(case_data)
    

if __name__ == '__main__':
    main()
