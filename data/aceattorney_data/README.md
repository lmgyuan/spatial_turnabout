## Annotations

In each episode (e.g., 2-1-1), a "turn" is a turn of cross-examination which a series of testimonies. A "present" event happens in a testimony, where one or more evidence can be presented. 

On the present-level, the following information is annotated:
- `evidence_span`: the substring span in the evidence description that directly causes the contradiction
- `testimony_span`: the substring span in the testimony text that directly causes the contradiction
- `explanation`: a short explanation of the contradiction
- `is_self_contained`: whether finding the contradiction requires additional context beyond the current testimony and evidence
- `context_span`: the substring span in above context, if any
- `difficulty`: one of the following:
    - Easy: the contradiction is explicitly local. E.g., testimony "I saw Yuan come into the office at 3AM" evidence: "Yuan is with Adil in a bar at 3AM"
    - Medium: the contradiction is implicitly local. E.g., testimony "I saw Yuan come into the office at 3AM" evidence: "Yuan is abroad with Adil for the whole month" -> the implied logical link is that "If someone travels abroad for a month, they cannot be in the office at any time within"
    - Hard: the contradiction requires external context. E.g., testimony "I saw Yuan come into the office at 3AM" evidence: "Yuan is seen at the bar at 2:30AM" && previous context "It takes one hour to go from the bar to the office"
    - Common sense: the contradiction requires non-trivial common sense

On the turn-level, the following information is annotated:
- `noPresent`: whether this turn does not have anything to present to progress the game; if true, this turn is neglected from evaluation
- `difficulty`: aggregated as being the lowest of the present-level difficulty annotations
- `labels`: one or more of the following labels about what type of reasoning is required:
    - numerical: e.g., "1 gunshot" vs. "2 gunshots"
    - temporal: e.g., "before noon" vs. "after 3PM"
    - spatial: e.g., "at the airport" vs. "on the bus"
    - object property: e.g., "death by blunt object" vs. "weapon was a gun"
    - behavior: e.g., "hates music" vs. "listen to music every day"
    - spelling: e.g., "Harry" vs. "Henry"