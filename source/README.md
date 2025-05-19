# Evaluating on TurnaboutLLM

There are two simple steps to a complete model evaluation run. The first step is to use `run_models.py` to run the model to get the outputs. The second step is to use `evaluate.py` to evaluate the outputs and summarize the results.

## Run models

**General syntax**

```python
python run_models.py --model <model_name> --prompt <prompt_name> [--context <context_name>] [--no_description] [OPTIONS]
```

**Example**

```python
python run_models.py -model GPT-4.1 --prompt base --context full
```

Running this command will create a folder `GPT-4.1_prompt_base_context_full` in `../output/` where it contains case-by-case outputs consisting of json answers of all turns (eg.`1-1-1_The_First_Turnabout.jsonl`) and the full model output (eg. `1-1-1_The_First_Turnabout_outputs.json`).

**Arguments**

*   `--model` (Required) The name of the model. For any Hugging Face model, the script supports entering the full model ID of any Hugging Face model, such as `meta-llama/Llama-3.1-8B-Instruct`. For all OpenAI and DeepSeek models, the script also supports entering the official model name specified in their respective APIs, such as `deepseek-reasoner`. To provide acronyms for any model, specify the acronym in `models.json` like `{"llama-3.1-8b" : "meta-llama/Llama-3.1-8B-Instruct"}`.

*   `--prompt` (Required) The name of the prompt template. Can be either `base` for the basic prompt or `cot_one_shot` for the CoT one shot prompt.

*   `--context` The type of context added to the prompt. Default to `None`. If specified as `full`, the script will add all context of the present turn to the prompt. If specified as `sum`, it will add a one-sentence summary of the context to the prompt.

*   `--no_description` Default to `False`. If set to `True`, the script will remove all evidence description from the prompt.

## Evaluate models

**General syntax**

The arguments are exactly the same as the ones for `run_models.py`.

```python
python evaluate.py --model <model_name> --prompt <prompt_name> [--context <context_name>] [--no_description] [OPTIONS]
```

**Example**

```python
python evaluate.py -model GPT-4.1 --prompt base --context full
```

Running this command will create a JSON file `GPT-4.1_prompt_base_context_full_report.json` in `../eval/` where it contains a breakdown of all relevant stats.

**Evaluate all outputs**

```python
python evaluate.py --all
```

Running this command will evaluate all existing model outputs and create all corresponding JSON files in `../eval`.