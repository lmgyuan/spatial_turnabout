# Turnabout LLM

This project benchmarks LLMs' deductive reasoning ability using interactive detective novel games such as [Ace Attorney](https://en.wikipedia.org/wiki/Ace_Attorney) and [Danganronpa](https://en.wikipedia.org/wiki/Danganronpa). This repo includes our datasets, scripts, and analyses.

![Objection!](images/objection.jpg)

> The name "Turnabout" is a naming convention from Ace Attorney as a nod to the playable character's knack for completely changing the direction of a trial, against all odds.

## Why interactive detective novels?

Detective stories contain some of the most difficult reasoning problems, which are meticulously crafted to be intriguing and obscure. Moreover, such deduction requires diverse reasoning ability and may require information retrieval from long passages of context. Therefore, evaluating LLMs on detective stories brings about unique challenges. 

Most detective novels like Sherlock Holmes can hardly be used for evaluation because they do not contain explicit questions to pose to models. However, games like Ace Attorney surprasses this constraint, as the interactive gameplay provides a natural interface with LLMs. Specifically, the core gameplay mechanism is to read through a story, examine existing evidences, listen to witness testimonies, and find one contradiction between an evidence and a testimony. In essence, this is multiple choice question where the action space is `num_evidences x num_testimonies` which is usually hundreds.

Despite possible subjectivity, games like Ace Attorney are critically acclaimed with a sizeable player community that generally agree upon the validity of questions and answers. While challenging even for human players, an attentive player should be able to find most contradictions. However, as of the time of writing, no LLM could achieve more than 40\% accuracy.

## Dataset

Detailed information about the Turnabout LLM dataset can be found at [data/](data/); **see the README there for more information**. We pose this dataset to evaluate LLMs' deductive reasoning ability. The game data is crawled and parsed from [an Ace Attorney Wiki](https://aceattorney.fandom.com/wiki/Category:Transcripts) and [a Danganronpa archive](https://lparchive.org/Danganronpa-Trigger-Happy-Havoc/). We make the following design choices:
- We only consider the textual elements, which are core to reasoning in most cases. Whenver visuals are needed for reasoning, they are captioned, though a multimodal evaluation might come in future work.
- For Ace Attorney, we only consider the cross-examination gameplay during trials, neglecting other gameplay elements such as investigation, psyche-locks, etc.
- For Danganronpa, we only consider the non-stop debate gameplay during trials, neglecting other gameplay elements such as socializing, hangman gambit, etc.

For each turn (either a cross-examination or a non-stop debate), the input to a model is:

1. A list of evidences (Ace Attorney) or truth bullets (Danganronpa) and their descriptions
2. A list of testimonies
3. The story context (only in some settings)

The output a model is a contradicting pair of evidence and a testimony. While most turns are self-contained, some require specific information from the story context. This becomes a needle-in-a-haystack information retrieval problem that is particularly challenging for LLMs.

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

## Citation
If you find our work useful, please cite TODO.