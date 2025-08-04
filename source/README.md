# Turnabout LLM Evaluation Scripts

Scripts for evaluating LLM deductive reasoning on detective game contradictions.

**Task:** Find contradictions between evidence and witness testimonies using spatial, temporal, behavioral, physical, numerical, and causal reasoning.

**Supported Models:** OpenAI (`gpt-*`, `o3-*`, `o4-*`) and Nebius (`nebius-*`)

## Basic Usage

```bash
# Fast parallel evaluation (recommended)
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv4_explicit --context sum --label spatial --max_workers 20

# Sequential evaluation (for debugging)
python run_models_spatial.py -m nebius-llama3.3-70b -p base --context sum --label spatial

# Evaluate results
python evaluate_spatial.py -m nebius-llama3.3-70b -p rulesv4_explicit --context sum --label spatial
```

## Key Features

**RAG + Proposition Generation:** Control both rule retrieval and proposition generation
```bash
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv3_rag_prop_t15_p5_improved --context sum --label spatial
```

**Dynamic RAG:** Auto-select most relevant rules
```bash
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv3_rag_t10_improved --context sum --label spatial
```

**Dynamic Propositions:** Generate case-specific reasoning rules
```bash
python run_models_parallel.py -m nebius-llama3.3-70b -p prop_generated_explicit --context sum --label spatial
```

## Command Options

| Option | Description | Values |
|--------|-------------|---------|
| `-m, --model` | Model name | `gpt-*`, `nebius-*` |
| `-p, --prompt` | Prompt type | `base`, `rulesv4_explicit`, `*_rag_*`, etc. |
| `--context` | Context strategy | `sum`, `full`, `none` |
| `--label` | Reasoning filter | `spatial`, `temporal`, `behavioral`, `physical`, `numerical`, `causal` |
| `--max_workers` | Parallel workers | `20-57` (parallel version only) |

## Environment Setup

Create `.env` file in project root:
```
OPENAI_API_KEY=your_key_here
NEBIUS_API_KEY=your_key_here
```

## Key Prompts

| Prompt | Purpose |
|--------|---------|
| `base.json` | Basic contradiction detection |
| `rulesv4_explicit.json` | Spatial reasoning with explicit rules |
| `rulesv3_rag_t10_improved.json` | RAG with 10 most relevant rules |
| `rulesv3_rag_prop_t15_p5_improved.json` | RAG (15 rules) + Props (5) |
| `prop_generated_explicit.json` | Dynamic proposition generation |
| `cot_one_shot.json` | Chain-of-thought reasoning |

## Technical Details

**RAG System:** `_t{N}` controls rule count (e.g., `_t10` = 10 rules)
**Proposition Control:** `_p{M}` controls generated propositions (e.g., `_p5` = 5 propositions)
**Parallel vs Sequential:** Use `run_models_parallel.py` for speed, `run_models_spatial.py` for debugging

## Example Workflows

```bash
# Test different reasoning types
python run_models_parallel.py -m nebius-llama3.3-70b -p base --context sum --label spatial --max_workers 20
python run_models_parallel.py -m nebius-llama3.3-70b -p base --context sum --label temporal --max_workers 20
python run_models_parallel.py -m nebius-llama3.3-70b -p base --context sum --label behavioral --max_workers 20

# Compare rule-based vs RAG vs dynamic propositions
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv4_explicit --context sum --label spatial
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv3_rag_t10_improved --context sum --label spatial
python run_models_parallel.py -m nebius-llama3.3-70b -p prop_generated_explicit --context sum --label spatial

# Evaluate results
python evaluate_spatial.py -m nebius-llama3.3-70b -p rulesv4_explicit --context sum --label spatial
```

---

For detailed technical documentation, see `README_legacy.md`. 