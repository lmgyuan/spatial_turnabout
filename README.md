# Turnabout LLM

This repo contains a textual simulator of the game Ace Attorney to evaluate LLMs' reasoning ability.

## Case Data
The game data for each case are from [Ace Attorney Wiki](https://aceattorney.fandom.com/wiki/Category:Transcripts), processed as a JSON to record the flow and texts. In `/case_data`:
- `hand_coded/` contains hand-annotated data. For example, `1-1.json` reflects the original Case 1-1, while `1-1-x.json` is a perturbed version of 1-1
- `generated/` contains automatically scraped and parsed data
- `scripts/` contains code to scrape and parse the data

## Simulator
To run the simulator, run:
> python simulator.py --case CASE --player PLAYER

where
- `CASE` is the case number, such as 1-1
- `PLAYER` is either human, or an OpenAI model name like gpt-4
