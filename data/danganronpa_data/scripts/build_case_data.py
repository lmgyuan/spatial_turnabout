import re
import json
import string

def get_context_before_trial(ch):
    context_before_trial = ""
    for life in ["Daily-Life", "Deadly-Life"]:
        pt = 1
        while True:
            fname = f"../text_fixed/Chapter-{ch}_{life}_Part-{pt}.txt"
            try:
                with open(fname) as f:
                    txt_content = f.read()
                    context_before_trial += txt_content
            except FileNotFoundError:
                break
            pt += 1
    return context_before_trial

def extract_name(filename):
    return filename.split('-')[1].split('.')[0].rstrip(string.digits)

def parse_debate(txt_lines, out_json, context_before_trial):
    pre_debate_context = ""
    debate_start = False
    speaker = ""
    testimony = ""
    present = []
    next_line_bold = False
    one_more_line = False
    for line in txt_lines:
        line = line.strip()
        # 17-ArgumentBreak.png
        if "-Argument" in line and line.endswith(".png"):
            debate_start = True
            testimonies = []
        if not debate_start:
            pre_debate_context += line + "\n"
        else:
            # 7-Hina16.png
            if line[0].isnumeric() and '-' in line:
                # flush
                if testimony:
                    testimony_dict = {"testimony": testimony, "person": speaker, "present": []}
                    speaker = ""
                    testimony = ""
                    testimonies.append(testimony_dict)
                speaker = extract_name(line)
            # : It was one of you...
            elif line[0] == ":" and speaker != "Narration":
                testimony += line.removeprefix(": ")
            # **
            elif line == "**":
                next_line_bold = True
            # hated her
            elif next_line_bold:
                testimony += " ***" + line + "*** "
                next_line_bold = False
                one_more_line = True
            # !
            elif one_more_line:
                testimony += line
                one_more_line = False
            # There's got to be some reason why Hina feels so strongly... is ignored
            # > Shoot "the only reason you have" with "Aoi's Account"
            elif line.startswith("> Shoot"):
                print(line)
                try:
                    keyword = line.split("Shoot ")[1].split(" with ")[0].strip('"')
                    correct_evidence_name = line.split("Shoot ")[1].split(" with ")[1].strip('"')
                except IndexError:
                    keyword = "N/A"
                    correct_evidence_name = "N/A"
                # flush
                if testimony:
                    testimony_dict = {"testimony": testimony, "person": speaker, "present": []}
                    speaker = ""
                    testimony = ""
                    testimonies.append(testimony_dict)
                # add present field
                for i,testimony_dict in enumerate(testimonies):
                    if "***" + keyword + "***" in testimony_dict["testimony"]:
                        testimonies[i]["present"].append(correct_evidence_name)
                # conclude a debate
                debate_dict = {
                    "category": "cross_examination",
                    "newContext": pre_debate_context,
                    "testimonies": testimonies
                }
                out_json["events"].append(debate_dict)
                pre_debate_context = ""
                debate_start = False 


            
        

for chapter in [6]:
    evidence_list = json.load(open("../json/_truth_bullets.json"))[f"Chapter {chapter}"]
    court_record_dict = {
        "evidence_objects": evidence_list
    }
    context_before_trial = get_context_before_trial(chapter)
    out_fname = f"../json/1-{chapter}.json"
    out_json = {"previousContext": context_before_trial, "court_record": court_record_dict, "events": []}
    # parse debates
    pt = 1
    while True:
        try:
            with open (f"../text_fixed/Chapter-{chapter}_Class-Trial_Part-{pt}.txt") as f:
                print(pt)
                txt_lines = f.readlines()
                parse_debate(txt_lines, out_json, context_before_trial)
            pt += 1

        except FileNotFoundError:
            break
        #break
    with open(out_fname, 'w') as json_file:
        json.dump(out_json, json_file, indent=4)