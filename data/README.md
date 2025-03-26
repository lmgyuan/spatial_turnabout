# The Turnabout LLM Dataset

## Coverage

The **Turnabout LLM** dataset contains 9 installations of classic detective visual novels:
- (AA1) Phoenix Wright: Ace Attorney 
- (AA2) Phoenix Wright: Ace Attorney – Justice for All 
- (AA3) Phoenix Wright: Ace Attorney – Trials and Tribulations
- (AA4) Apollo Justice: Ace Attorney
- (AA5) Phoenix Wright: Ace Attorney – Dual Destinies
- (AA6) Phoenix Wright: Ace Attorney – Spirit of Justice
- (GAA1) The Great Ace Attorney: Adventures
- (GAA2) The Great Ace Attorney 2: Resolve
- (DGRP1) Danganronpa: Trigger Happy Havoc
> Note: Danganronpa 2: Goodbye Despair and Danganronpa V3: Killing Harmony were not included due to the lack of a well-structured transcript. Let us know if you know those that exist!

The dataset comes in a collection of JSON files. The ready-to-use datasets are found at [[Ace Attorney dataset]](aceattorney_data/final/) and [[Danganronpa dataset]](danganronpa_data/final/).

## Organization

An episode (e.g., 1-2: Turnabout Sisters in AA1) is typically split into multiple chapters (e.g., 1-2-2: the second day, or the court day, of 1-2). Each chapter is represented with a JSON file (e.g., [1-2-2.json](aceattorney_data/final/1-2-2_Turnabout_Sisters.json)). Each chapter JSON file has the following schema:
- `previousContext`: The story that has happened until the start of this chapter. The story is expressed as a long string containing all transcripts, flattened.
- `characters`: Information about all involved characters in the episode
    - `currentChapter`, `name`, `age`, `gender`
    - `description1`, `description2`, ...: episode-specific descriptions extracted from the wiki source. Multiple descriptions happen when the character description is updated through the progression of the game. For simplicity, we concatenate all descriptions in an episode and use that throughout the evaluation.
- `evidences`: Information about all involved evidences in the episode
    - `currentChapter`, `name`, `type`, `obtained`
    - `description1`, `description2`, ...: same as above; episode-specific descriptions extracted from the wiki source. Multiple descriptions happen when the evidence description is updated through the progression of the game. For simplicity, we concatenate all descriptions in an episode and use that throughout the evaluation.
- `turns`: The cross-examination (AA) and class trial (DGRP) portions of the games.

## Annotations

In each episode (e.g., 2-1-1), a "turn" is a turn of cross-examination which a series of testimonies. A "present" event happens in a testimony, where one or more evidence can be presented. 

On the present-level, the following information is annotated:
- `evidence_span`: the substring span in the evidence description that directly causes the contradiction
- `testimony_span`: the substring span in the testimony text that directly causes the contradiction
- `explanation`: a short explanation of the contradiction
- `is_self_contained`: whether finding the contradiction requires additional context beyond the current testimony and evidence
- `context_span`: the substring span in above context, or in an evidence or testimony other than the correct one to present, if any
- `difficulty`: one of the following:
    - Easy: the contradiction is explicitly local. E.g., testimony "I saw Yuan come into the office at 3AM" evidence: "Yuan is with Adil in a bar at 3AM"
    - Medium: the contradiction is implicitly local. E.g., testimony "I saw Yuan come into the office at 3AM" evidence: "Yuan is abroad with Adil for the whole month" -> the implied logical link is that "If someone travels abroad for a month, they cannot be in the office at any time within"
    - Difficult: the contradiction requires external context. E.g., testimony "I saw Yuan come into the office at 3AM" evidence: "Yuan is seen at the bar at 2:30AM" && previous context "It takes one hour to go from the bar to the office"
    - Common sense: the contradiction requires non-trivial common sense

On the turn-level, the following information is annotated:
- `noPresent`: whether this turn does not have anything to present to progress the game; if true, this turn is neglected from evaluation
- `difficulty`: aggregated as being the lowest of the present-level difficulty annotations
- `labels`: one or more of the following labels about what type of reasoning is required:
    - numerical: a present is labeled as "numerical" if and only if the core contradiction is a difference in some numbers (e.g., "I heard 1 gunshot" vs. "2 gunshots were fired"); it should not be labeled so if numbers are mentioned but do not consitute a contradiction (e.g., "I gave the victim 2 items" vs. "The witness never met the victim")
    - temporal: a present is labeled as "temporal" if and only if the core contradiction involves time (e.g., "He died before noon" vs. "Time of death is after 3PM"); this commonly stack with other labels such as "numerical"; it should not be labeled so if time is mentioned but do not consitute a contradiction (e.g., "I met the victim in the morning" vs. "The witness never met the victim")
    - spatial: a present is labeled as "spatial" if and only if the core contradiction involves space (e.g., "I killed him at the bus stop" vs. "The victim was found dead in his home"); it should not be labeled so if space is mentioned but do not consitute a contradiction (e.g., "I met the victim at school" vs. "The witness never met the victim")
    - object property: a present is labeled as "object property" if and only if the core contradiction involves certain non-universal properties of an object (e.g., "I saw him beaten by a club" vs. "Autopsy report shows only trauma of piercing", because a club does not cause piercing damage); this object cannot be time or space, but can be abstract entity such as a concept (e.g., "I never told anyone this idea" vs. "The victim wrote down this idea in a notebook"); it should not be labeled so if a human's *behavior* is involved, and should be instead labeled as "behavior" (see below); at times, this may stack with other labels (e.g., "I did not hear anything from the clock at noon" vs. "The clock sounds at noon" can also be labeled as "temporal", because the mention of the time "noon" is equally core to the contradiction) (e.g., "I saw the vase" vs. "There was a wall between the witness and the vase" can also be labeled as "spatial", because the positioning of the wall and the visibility of the vase are equally core to the contradiction)
    - behavior: a present is labeled as "object property" if and only if the core contradiction involves a human's behavior, either pertaining to their intent, habits, or preference (e.g., "Larry hates music" vs. "Larry is reported to listen to music every day"); extenuating exceptions are not considered unless there is strong evidence otherwise; it should not be labeled so if the contradiction is labeled as something else above, leading to a derivative contradiction in behavior (e.g., "I killed him at the bus stop" vs. "The victim was found dead in his home" may lead to a corollary of "I killed him" vs. "I cannot have killed him")
    - spelling: e.g., "Harry" vs. "Henry"
- `reasoning`: a list of *facts* to arrive at the contradiction. Considerations:
    - A fact can either be an *assertion*, something being true, or a *conditional*, some general rule of implication.
    - The first two facts are always assertions. The first fact is what the witness claims (e.g., "witness claims he saw victim being shot to death"), the second fact is what the evidence suggests (e.g., "the victim died by blunt force"). 
    - The rest, if any, is either assertions from testimonies, evidences, or contexts, or conditionals from common sense or contexts (e.g., "If someone died by blunt force, they did not die by a gunshot.")
    - Modus ponens (assertion P + conditional if P then Q → assertion Q) is the only rule needed to combine a pair of facts.
    - Each fact should be an atomic unit, though subjectivity is inevitable