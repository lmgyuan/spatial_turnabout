# Complex Spatial Reasoning over Narratives

Code and data for reproducing the experiments in this paper.

**Task:** Given evidence and witness testimonies, identify the contradicting pair. Models must extract implicit spatial relationships from prose and detect geometric impossibilities. We evaluate on Turnabout (narrative-embedded spatial reasoning) and SpaRTUN (explicit spatial reasoning).

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root with your API keys:
```
OPENAI_API_KEY=your_key
NEBIUS_API_KEY=your_key
```

## Project Structure

```
source/                  # All pipeline code
  run_models_spatial.py  # Turnabout inference (parallel)
  run_models_parallel.py # Turnabout inference (parallel, alt)
  run_spartun_parallel.py# SpaRTUN inference
  evaluate_spatial.py    # Turnabout evaluation
  evaluate_spartun.py    # SpaRTUN evaluation
  generate_plots.py      # Generate result plots
  models.json            # Model name mappings
  prompts/               # Turnabout prompt templates
  prompts_spartun/       # SpaRTUN prompt templates
data/
  aceattorney_data/final/     # Ace Attorney cases (133 JSON files)
  danganronpa_data/final/     # Danganronpa cases (7 JSON files)
  SPARTUN/                    # SpaRTUN dataset
Rules/
  RuleText5.txt          # Hand-curated spatial rules for Turnabout (130 rules)
  RuleText.txt           # Hand-curated spatial rules for SpaRTUN (73 rules)
output_spatial/          # Turnabout model outputs
output_spurtun/          # SpaRTUN model outputs
eval/                    # Turnabout evaluation reports
eval_spurtun/            # SpaRTUN evaluation reports
```

## Running Experiments

All commands run from the `source/` directory.

### Turnabout

```bash
# Inference — run a model with a prompt on the spatial subset
python run_models_spatial.py -m nebius-llama3.3-70b -p base --context sum --label spatial
python run_models_spatial.py -m nebius-llama3.3-70b -p rulesv5_improved --context sum --label spatial
python run_models_spatial.py -m nebius-llama3.3-70b -p rules_generated_r10_improved_v2 --context sum --label spatial

# Evaluation
python evaluate_spatial.py -m nebius-llama3.3-70b --data aceattorney --label spatial
python evaluate_spatial.py --all --data aceattorney    # evaluate all runs
```

**Key arguments:**
- `-m MODEL` — model name from `models.json` (e.g., `nebius-llama3.3-70b`, `nebius-qwen3-32b`, `nebius-kimi-k2`)
- `-p PROMPT` — prompt template name from `prompts/` (without `.json`)
- `--context sum` — include summarized story context
- `--label spatial` — filter to spatial reasoning turns only

### SpaRTUN

```bash
# Inference
python run_spartun_parallel.py -m nebius-llama3.3-70b -p base --case ALL
python run_spartun_parallel.py -m nebius-llama3.3-70b -p rulesv5_improved --case ALL
python run_spartun_parallel.py -m nebius-llama3.3-70b -p rules_generated_r10_improved_v2 --case ALL

# Evaluation
python evaluate_spartun.py -m nebius-llama3.3-70b -p base
```

**Key arguments:**
- `--case ALL` — run all 666 cases (default: first 20)
- `--case N` — run first N cases

### Available Pipelines (Prompt Names)

| Pipeline | Turnabout Prompt | SpaRTUN Prompt |
|---|---|---|
| B0 (Baseline) | `base` | `base` |
| C0 (Spatial Cue) | `base_spatial_ablation` | — |
| RC-Static (All Rules) | `rulesv5_improved` | `rulesv5_improved` |
| RC-RAG@k (Retrieved Rules) | `rulesv5_rag_t{k}_improved` | `rulesv5_rag_t10_improved` |
| PA@p (Propositions) | `prop_generated_p{p}_improved_v2` | `prop_generated_p10_improved_v2` |
| RC+PA-RAG (Combined) | `rulesv5_rag_prop_t15_p{p}_improved_v2` | `rag_prop_generated_t10_p10_improved_v2` |
| AR@k (Auto-Generated Rules) | `rules_generated_r{k}_improved_v2` | `rules_generated_r10_improved_v2` |
| Gold (Oracle) | use `--reasoning props` | `gold_rules_improved` |