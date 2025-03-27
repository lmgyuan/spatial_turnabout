# Turnabout LLM

This project benchmarks LLMs' deductive reasoning ability using interactive detective novel games such as [Ace Attorney](https://en.wikipedia.org/wiki/Ace_Attorney) and [Danganronpa](https://en.wikipedia.org/wiki/Danganronpa). This repo includes our datasets, scripts, and analyses.

![Objection!](images/objection.jpg)

## Why interactive detective novels?

Detective stories contain some of the most difficult reasoning problems, which are meticulously crafted to be intriguing and obscure. Moreover, solving these problems often require intuition from long passages of context. With these two reasons combined, evaluating LLMs on detective stories brings about unique challenges. 

Unfortunately, most detective novels like Sherlock Holmes can hardly be used for evaluation because they do not contain explicit questions to pose to models. However, games like Ace Attorney surprasses this constraint, as the interactive gameplay provides a natural interface with LLMs.

## Dataset

Detailed information about the Turnabout LLM dataset can be found at [data/](data/aceattorney_data/final). We provide datasets from Ace Attorney and Danganronpa that can be used to evaluate LLMs' deductive reasoning ability. The game data is crawled and parsed from [an Ace Attorney Wiki](https://aceattorney.fandom.com/wiki/Category:Transcripts) and [a Danganronpa archive](https://lparchive.org/Danganronpa-Trigger-Happy-Havoc/). Some notes:

- We only consider the textual elements, which are core to reasoning in most cases
    - Whenver visuals are needed for reasoning, they are captioned, though a multimodal evaluation might come in future work
- For Ace Attorney
  - We only consider the cross-examination gameplay during trials, neglecting other gameplay elements such as investigation, psyche-locks, etc.
  - While characters and evidences may change throughout the game, we only consider the final list of them with their final descriptions in each case
- For Danganronpa
  - We only consider the non-stop debate gameplay during trials, neglecting other gameplay elements such as socializing, hangman gambit, etc.

For each turn (either a cross-examination or a non-stop debate gameplay), the following information are provided:

1. A list of characters and their descriptions (Ace Attorney only)
2. A list of evidences (Ace Attorney) or truth bullets (Danganronpa) and their descriptions
3. A list of testimonies

The task is to take the above as input and predict a contradicting pair of evidence or character (Ace Attorney only) and a testimony. 

## Evaluation

To use an LLM with a prompt to make inference on the dataset, go to `/source` and run

> python run_models.py --model MODEL --prompt PROMPT --case CASE --context CONTEXT

where `MODEL` is the name of a HuggingFace model such as `deepseek-ai/DeepSeek-R1`. PROMPT is the ID of a prompt stored in `/source/prompt`. CASE is "ALL" to run all cases, a case ID like 1-2-2 to run a particular case, or 1-2-2+ to run all cases including and after this one. CONTEXT is ...

Running this command will produce `/output/MODEL_PROMPT`, storing models' output.

To evaluate said output, run
> python evaluate.py --model MODEL --prompt PROMPT --case CASE --context CONTEXT

This will create a `report.json` in the same output folder. 

## License
Following the source of our data, [fandom.com](https://www.fandom.com/licensing), our resources are licensed under Creative Commons Attribution-Share Alike License 3.0 (Unported) (CC BY-SA). 