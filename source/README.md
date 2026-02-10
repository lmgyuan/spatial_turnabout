# Turnabout LLM Evaluation Scripts (Spatial + SPARTUN)

Scripts for evaluating LLM deductive reasoning on detective game contradictions.

**Task:** Find contradictions between evidence and witness testimonies using spatial, temporal, behavioral, physical, numerical, and causal reasoning.

**Supported Models:** OpenAI (`gpt-*`, `o3-*`, `o4-*`) and Nebius (`nebius-*`)

## Active Pipelines

The system supports five active pipelines for different reasoning approaches.

### 1. **Base / Static Rules (v5)** 
- **Purpose:** Direct contradiction detection with static rules
- **Usage:** `-p base`, `-p rulesv5_improved`
- **Features:** Uses predefined spatial reasoning rules embedded in prompts

### 2. **Proposition Generation**
- **Purpose:** Dynamic generation of case-specific reasoning propositions  
- **Usage:** `-p prop_generated_p{N}_improved[_v2]` (N = 5, 10, 15)
- **Features:** 
  - Generates N propositions per case turn
  - Regular: Generic universal principles
  - V2 variant: Contextually specific to the actual case details
- **Example:** `prop_generated_p10_improved_v2`

### 3. **RAG-Only (Rules v5)**
- **Purpose:** Retrieval-augmented reasoning with dynamic rule selection
- **Usage:** `-p rulesv5_rag_t{K}_improved` (K = 5, 10, 15)
- **Features:** Auto-selects K most relevant rules per turn using semantic similarity

### 4. **Combined RAG + Propositions (v5)**
- **Purpose:** Both dynamic rule retrieval AND proposition generation
- **Usage:** `-p rulesv5_rag_prop_t{K}_p{N}_improved[_v2]`
- **Features:** 
  - Retrieves K relevant rules via RAG
  - Generates N propositions conditioned on retrieved rules
  - V2 variant: Contextually specific propositions
- **Example:** `rulesv5_rag_prop_t10_p5_improved_v2`

### 5. **Rules Generation (consumer v2)**
- **Purpose:** Generate a per-turn set of spatial reasoning rules (no RAG)
- **Usage:** `-p rules_generated_r{N}_improved_v2` (N = 5, 10, 15)
- **Features:**
  - Produces N general-but-case-relevant rules per turn (deterministic: temperature=0, seed=42)
  - Injects rules into consumer templates via `{generated_rules}`
- **Example:** `rules_generated_r10_improved_v2`

## Reasoning Controls

- `--reasoning {none|full|facts|props}`: Include dataset-provided reasoning in the prompt.
  - `full`: include all reasoning lines
  - `facts`: include only lines starting with "Fact"
  - `props`: include only lines starting with "Prop"
  - `none` (default): no reasoning section

## SPARTUN Pipelines

SPARTUN treats each case as a single "turn" (all questions answered in one call). Outputs go to `output_spurtun/<model>_prompt_<prompt>/`.

### Run
```bash
# From source directory
python run_spartun_parallel.py -m nebius-llama3.3-70b -p base
python run_spartun_parallel.py -m nebius-llama3.3-70b -p rulesv5_improved
python run_spartun_parallel.py -m nebius-llama3.3-70b -p rulesv5_rag_t10_improved
python run_spartun_parallel.py -m nebius-llama3.3-70b -p prop_generated_p10_improved_v2
python run_spartun_parallel.py -m nebius-llama3.3-70b -p rules_generated_r10_improved_v2
python run_spartun_parallel.py -m nebius-llama3.3-70b -p rag_prop_generated_t10_p10_improved_v2

# Process first N cases (default 20). Use ALL to run all cases
python run_spartun_parallel.py -m nebius-llama3.3-70b -p base --case 50
python run_spartun_parallel.py -m nebius-llama3.3-70b -p base --case ALL
```

### Evaluate
```bash
python evaluate_spartun.py -m nebius-llama3.3-70b -p base
python evaluate_spartun.py -m nebius-llama3.3-70b -p rulesv5_improved
python evaluate_spartun.py -m nebius-llama3.3-70b -p rulesv5_rag_t10_improved
python evaluate_spartun.py -m nebius-llama3.3-70b -p prop_generated_p10_improved_v2
python evaluate_spartun.py -m nebius-llama3.3-70b -p rules_generated_r10_improved_v2
python evaluate_spartun.py -m nebius-llama3.3-70b -p rag_prop_generated_t10_p10_improved_v2
```

### SPARTUN Controls
- `--case`: `ALL` or a number `N` to run the first N cases (default 20)
- RAG top-k: parsed from `_t{K}` in the prompt name (e.g., `_t10`)
- Prop count: parsed from `_p{N}` (e.g., `_p10`)
- Rules count: parsed from `_r{N}` (e.g., `_r10`)
- `--debug_log_off`: disable detailed logging (enabled by default)

### Prompt Conventions (SPARTUN)
- Final prompts use placeholders:
  - `{all_rules}` (explicit rules)
  - `{dynamic_rules}` (RAG rules)
  - `{generated_rules}` (rules-generated)
  - `{generated_props}` (prop-generated)
  - `{rag_generated_props}` (RAG+prop)
- Intermediary prompts:
  - Rules generation: `{RULE_COUNT}`
  - Prop generation: `{PROP_COUNT}`, `{general_rules}`
  - RAG+Prop generation: `{PROP_COUNT}`, `{rag_rules}`

## Basic Usage

```bash
# Fast parallel evaluation (recommended)
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv5_improved --context sum --label spatial --max_workers 20

# Sequential evaluation (debug-friendly)
python run_models_spatial.py -m nebius-llama3.3-70b -p base --context sum --label spatial

# Evaluate results
python evaluate_spatial.py -m nebius-llama3.3-70b -p rulesv5_improved --context sum --label spatial
```

## Pipeline Examples

**Base Pipeline (v5 rules):**
```bash
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv5_improved --context sum --label spatial
```

**Dynamic Propositions (V2 - contextual):**
```bash
python run_models_parallel.py -m nebius-llama3.3-70b -p prop_generated_p10_improved_v2 --context sum --label spatial
```

**RAG-Only (15 rules):**
```bash
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv5_rag_t15_improved --context sum --label spatial
```

**Combined RAG + Props (10 rules + 5 contextual props):**
```bash
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv5_rag_prop_t10_p5_improved_v2 --context sum --label spatial
```

**Rules Generated (V2 consumer, no RAG):**
```bash
python run_models_parallel.py -m nebius-llama3.3-70b -p rules_generated_r10_improved_v2 --context sum --label spatial
```

## Command Options

| Option | Description | Values |
|--------|-------------|---------|
| `-m, --model` | Model name | `gpt-*`, `nebius-*` |
| `-p, --prompt` | Pipeline & prompt type | See pipeline examples above |
| `--context` | Context strategy | `sum`, `full`, `none` |
| `--label` | Reasoning filter | `spatial`, `temporal`, `behavioral`, `physical`, `numerical`, `causal` |
| `--reasoning` | Include dataset reasoning | `none`, `full`, `facts`, `props` |
| `--no_description` | Drop character/evidence descriptions | flag |
| `--max_workers` | Parallel workers | `20-57` (parallel version only) |
| `--debug_log_off` | Disable detailed LLM logging | flag |

## Environment Setup

Create `.env` file in project root:
```
OPENAI_API_KEY=your_key_here
NEBIUS_API_KEY=your_key_here
```

## Key Prompts by Pipeline

| Pipeline | Prompt | Purpose |
|----------|--------|---------|
| **Base** | `base.json` | Basic contradiction detection (static rules inline) |
| **Base** | `rulesv5_improved.json` | Spatial reasoning with explicit v5 rules |
| **Proposition** | `prop_generated_p5_improved.json` | 5 generic propositions |
| **Proposition** | `prop_generated_p10_improved_v2.json` | 10 contextual propositions |
| **RAG** | `rulesv5_rag_t10_improved.json` | 10 most relevant rules via RAG |
| **Combined** | `rulesv5_rag_prop_t15_p5_improved.json` | 15 rules + 5 generic props |
| **Combined** | `rulesv5_rag_prop_t10_p5_improved_v2.json` | 10 rules + 5 contextual props |
| **Rules Generated** | `rules_generated_r10_improved_v2.json` | Use per-turn generated rules |

## Technical Details

- **Static rules source:** `Rules/RuleText5.txt` is used by RAG; `base.json` inlines a similar ruleset.
- **RAG Control:** `_t{N}` controls rule count (e.g., `_t10` = 10 rules)
- **Proposition Control:** `_p{M}` controls generated propositions (e.g., `_p5` = 5 propositions)
- **Rules Generation Control:** `_r{N}` controls generated rules (e.g., `_r10` = 10 rules; consumer prompts use `{generated_rules}`)
- **V2 Variants:** `_v2` suffix enables contextual propositions
- **Parallel vs Sequential:** Use `run_models_parallel.py` for speed (global parallel over all turns); `run_models_spatial.py` for step-by-step debugging and OpenAI batch mode
- **Debug logging:** Enabled by default; disable with `--debug_log_off`. Logs prompts/responses to `debug_log_*` files in the run's output directory.
- **RAG usage log:** When using RAG, selected rules are logged to `../Rules/rag_rules_used_*.txt` with model/prompt context.

## Example Workflows

```bash
# Test different reasoning types (add reasoning section)
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv5_improved --context sum --label spatial --reasoning full --max_workers 20

# Compare main pipelines
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv5_improved --context sum --label spatial
python run_models_parallel.py -m nebius-llama3.3-70b -p prop_generated_p10_improved_v2 --context sum --label spatial  
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv5_rag_t10_improved --context sum --label spatial
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv5_rag_prop_t15_p5_improved_v2 --context sum --label spatial
python run_models_parallel.py -m nebius-llama3.3-70b -p rules_generated_r10_improved_v2 --context sum --label spatial

# Evaluate results
python evaluate_spatial.py -m nebius-llama3.3-70b -p rulesv5_improved --context sum --label spatial
```

---

For detailed technical documentation, see `README_legacy.md`. 