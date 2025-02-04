FEW_SHOT_DECOMPOSITION = """

Q: 
You are provided with a list of characters, evidences and testimonies.
Evidence 0
Name: Attorney's Badge
Description: No one would believe I was a defense attorney if I didn't carry this.
Evidence 1
Name: Cindy's Autopsy Report
Description: Time of death: 7/31, 4PM-5PM. Cause of death: loss of blood due to blunt trauma.
Evidence 2
Name: Statue
Description: A statue in the shape of \"The Thinker\". It's rather heavy.
Evidence 3
Name: Blackout Record
Description: Electricity to Ms. Stone's building was out from noon to 6 PM on the day of the crime.
Testimony 0
Testimony: I thought to call the police immediately!
Testimony 1
Testimony: I went to a nearby park and found a public phone.
Testimony 2
Testimony: I remember the time exactly: It was 1:00 PM.

Which evidence/character and testimony contradict each other?

A: 

To answer the question "which evidence/character and testimony contradict each other", we need to know:
"Does any piece of evidence mention a park nearby?"
"If so, does description of the park contradict with the witness' account of calling the police in the park?"
"Does any piece of evidence mention the time when the crime happened?"
"If so, does descriptions of the time contradict with 1:00 PM?"
"If you find the contradiction, then answer the contradiction with {{"evidence": **number**, "testimony": **number**}}"

Q:

You are provided with a list of characters, evidences and testimonies.
Evidence 0
Name: Guidemap
Description: Guidemap to Global Studios. Click here for details.
Evidence 1
Name: Jack's Autopsy Report
Description: Time of death: 10/15 at 2:30 PM. Cause: Pierced through the chest by a spear.
Evidence 2
Name: Cody's Camera
Description: A new digital camera. Cody always carries it, though he's still learning how to use it.
Testimony 0
Testimony: When I came out by the studio, there was the Steel Samurai!
Testimony 1
Testimony: It totally rocked! Right before my eyes, out came the bad guy!
Testimony 2
Testimony: If I had my camera with me, that woulda been the time for a shot, I tell you.

Which evidence/character and testimony contradict each other?

A:

To answer the question "which evidence/character and testimony contradict each other", we need to know:
"Does any piece of evidence mention the occurrence Steel Samurai?"
"If so, does description of the Steel Samurai make it unlikely that the witness had seen him?"
"Does any piece of evidence mention the witness' camera?"
"If so, does descriptions of the witness' camera make his explanation unlikely?"
"If you find the contradiction, then answer the contradiction with {{"evidence": **number**, "testimony": **number**}}"

Q:

{question}

A:

"""

FEW_SHOT_PROBLEM_SOLVING = """



"""

TEST_PROMPT = """

You are provided with a list of characters, evidences and testimonies.
Evidence 0
Name: Attorney's Badge
Description: Proof of my profession. The first and last time I used it was a year ago.
Evidence 1
Name: Doug's Autopsy Report
Description: Date and time of death: 4/9 at 3 PM. Cause of death was a fatal electric shock.
Evidence 2
Name: Crime Photo 1
Description: The crime took place behind an Ivy U. building. The victim is lying head down. He is wearing a plain shirt. There is a broken power cable with sparks hanging above him. An umbrella with a bent handle lies open in a distance.
Evidence 3
Name: Crime Photo 2
Description: The victim's hand is holding a bottle a medicine labeled as coldkiller. The victim's watch stopped at the time of death at 3:05.
Evidence 4
Name: Coldkiller X
Description: Found clutched in the victim's hand. Covered in Wright's fingerprints.
Evidence 5
Name: Umbrella
Description: Owned by the victim. Found broken near an electrical pole at the crime scene.
Evidence 6
Name: Phoenix's Testimony
Description: The victim fell on top of his umbrella. There was a loud sound when this happened.
Evidence 7
Name: Dahlia's Present
Description: A small bottle necklace given to Wright on the day they met. He shows it to everyone.
Evidence 8
Name: Newspaper Clipping
Description: An article from 8/28, almost 8 months ago. Click here for details.
Evidence 9
Name: Student's Testimony
Description: The old power cable broke due to some sort of impact on 4/9 at 2:55 PM.
Evidence 10
Name: Police Report
Description: A report on the incident eight months ago.
*Incident Overview

Location: District Courthouse
Date/Time: August 27, 4:00 PM
Victim: Diego Armando (Age 28)
Occupation: Lawyer
Suspect: Dahlia Hawthorne (Age 19)

*Details
- Armando ingested poison while interviewing the suspect regarding another case.
- Traces of poison were found in the victim's coffee cup.
- No poison was found in the vicinity or on the suspect's person. It is unclear how the poison entered the victim's coffee cup.
Testimony 0
Testimony: Um, I... I admit I was there...
Person: Phoenix
Testimony 1
Testimony: But I'm not a killer! All I did was find his body!
Person: Phoenix
Testimony 2
Testimony: I hardly knew the guy to begin with...
Person: Phoenix
Testimony 3
Testimony: I never even talked to that stuck-up British wannabe!
Person: Phoenix
Testimony 4
Testimony: He was always walking around with a huge Union Jack on the back of his shirt.
Person: Phoenix
Which evidence/character and testimony contradict each other? You must only answer one pair. Your answer must end with a JSON format like so: {"evidence": 2, "testimony": 3} or {"character": 4, "testimony": 11}

"""


def least_to_most_prompt(question):
    # Stage 1: Problem decomposition
    decomp_prompt = FEW_SHOT_DECOMPOSITION.format(question=question)
    subproblems = run_model(decomp_prompt)
    
    # Stage 2: Sequential problem solving
    solving_prompt = FEW_SHOT_PROBLEM_SOLVING.format()
    final_answer = run_model(solving_prompt)
    
    return final_answer