# Turnabout LLM Evaluation Scripts

Scripts for evaluating LLM deductive reasoning on detective game contradictions.

**Task:** Find contradictions between evidence and witness testimonies using spatial, temporal, behavioral, physical, numerical, and causal reasoning.

**Supported Models:** OpenAI (`gpt-*`, `o3-*`, `o4-*`) and Nebius (`nebius-*`)

## Six Processing Pipelines

The system supports six distinct processing pipelines for different reasoning approaches:

### 1. **Base Pipeline** 
- **Purpose:** Direct contradiction detection with static rules
- **Usage:** `-p base`, `-p rulesv4_explicit`, `-p rulesv3_improved`
- **Features:** Uses predefined spatial reasoning rules embedded in prompts

### 2. **Proposition Generation Pipeline**
- **Purpose:** Dynamic generation of case-specific reasoning propositions  
- **Usage:** `-p prop_generated_p{N}_improved[_v2]` (where N = 5, 10, or 15)
- **Features:** 
  - Generates N propositions per case turn
  - Regular: Generic universal principles
  - V2 variant: Contextually specific to actual case details
- **Example:** `prop_generated_p5_improved_v2`

### 3. **RAG-Only Pipeline**
- **Purpose:** Retrieval-augmented reasoning with dynamic rule selection
- **Usage:** `-p rulesv3_rag_t{K}_improved` (where K = 5, 10, 15)
- **Features:** Auto-selects K most relevant rules per case using semantic similarity

### 4. **Combined RAG + Proposition Pipeline**
- **Purpose:** Both dynamic rule retrieval AND proposition generation
- **Usage:** `-p rulesv3_rag_prop_t{K}_p{N}_improved[_v2]`
- **Features:** 
  - Retrieves K relevant rules via RAG
  - Generates N propositions based on retrieved rules
  - V2 variant: Contextually specific propositions
- **Example:** `rulesv3_rag_prop_t15_p5_improved_v2`

### 5. **Rules Generation Pipeline**
- **Purpose:** Generate a per-turn set of spatial reasoning rules (no RAG)
- **Usage:** `-p rules_generated_r{N}_improved_v2` (where N = 5, 10, or 15)
- **Features:**
  - Produces N general-but-case-relevant rules per turn (deterministic: temperature=0, seed=42)
  - Injects rules into consumer templates via `{generated_rules}`
- **Example:** `rules_generated_r10_improved_v2`

### 6. **ET-Suggested Pipeline (Evidence/Testimony Suggestions)**
- **Purpose:** Per-turn selection of N evidences and N testimonies most likely to contain the contradictory pair (no RAG)
- **Usage:** `-p et_suggested_et{N}_improved_v2` (where N = 2 or 3)
- **Features:**
  - First pass: deterministic selection of N evidence indices and N testimony indices (temperature=0, seed=42)
  - Second pass: injects suggestions and instructs model to search suggestions first, then full pool only if necessary
  - Placeholders: `{suggested_evidences}`, `{suggested_testimonies}`
- **Examples:** `et_suggested_et2_improved_v2`, `et_suggested_et3_improved_v2`

## Basic Usage

```bash
# Fast parallel evaluation 
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv4_explicit --context sum --label spatial --max_workers 20

# Sequential evaluation 
python run_models_spatial.py -m nebius-llama3.3-70b -p base --context sum --label spatial

# Evaluate results
python evaluate_spatial.py -m nebius-llama3.3-70b -p rulesv4_explicit --context sum --label spatial
```

## Pipeline Examples

**Base Pipeline:**
```bash
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv4_explicit --context sum --label spatial
```

**Dynamic Propositions (V2 - contextual):**
```bash
python run_models_parallel.py -m nebius-llama3.3-70b -p prop_generated_p10_improved_v2 --context sum --label spatial
```

**Dynamic RAG (15 rules):**
```bash
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv3_rag_t15_improved --context sum --label spatial
```

**Combined RAG + Props (10 rules + 5 contextual props):**
```bash
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv3_rag_prop_t10_p5_improved_v2 --context sum --label spatial
```

**Rules Generated (V2 - per-turn rules, no RAG):**
```bash
python run_models_parallel.py -m nebius-llama3.3-70b -p rules_generated_r10_improved_v2 --context sum --label spatial
```

**ET-Suggested (N=2 suggestions each):**
```bash
python run_models_parallel.py -m nebius-llama3.3-70b -p et_suggested_et2_improved_v2 --context sum --label spatial
```

## Command Options

| Option | Description | Values |
|--------|-------------|---------|
| `-m, --model` | Model name | `gpt-*`, `nebius-*` |
| `-p, --prompt` | Pipeline & prompt type | See pipeline examples above |
| `--context` | Context strategy | `sum`, `full`, `none` |
| `--label` | Reasoning filter | `spatial`, `temporal`, `behavioral`, `physical`, `numerical`, `causal` |
| `--max_workers` | Parallel workers | `20-57` (parallel version only) |

## Environment Setup

Create `.env` file in project root:
```
OPENAI_API_KEY=your_key_here
NEBIUS_API_KEY=your_key_here
```

## Key Prompts by Pipeline

| Pipeline | Prompt | Purpose |
|----------|--------|---------|
| **Base** | `base.json` | Basic contradiction detection |
| **Base** | `rulesv4_explicit.json` | Spatial reasoning with explicit rules |
| **Proposition** | `prop_generated_p5_improved.json` | 5 generic propositions |
| **Proposition** | `prop_generated_p10_improved_v2.json` | 10 contextual propositions |
| **RAG** | `rulesv3_rag_t10_improved.json` | 10 most relevant rules |
| **Combined** | `rulesv3_rag_prop_t15_p5_improved.json` | 15 rules + 5 generic props |
| **Combined** | `rulesv3_rag_prop_t10_p5_improved_v2.json` | 10 rules + 5 contextual props |
| **Rules Generated** | `rules_generated_r10_improved_v2.json` | Use per-turn generated rules |
| **ET-Suggested** | `et_suggested_et2_improved_v2.json` | Suggest E/T indices; search suggestions first |

## Technical Details

**RAG Control:** `_t{N}` controls rule count (e.g., `_t10` = 10 rules)  
**Proposition Control:** `_p{M}` controls generated propositions (e.g., `_p5` = 5 propositions)  
**Rules Generation Control:** `_r{N}` controls generated rules (e.g., `_r10` = 10 rules; V2 consumer with `{generated_rules}`)
**ET Selection Control:** `_et{N}` controls number of suggested evidences and testimonies (2 or 3)
**V2 Variants:** `_v2` suffix enables contextually specific propositions instead of generic universal principles  
**Parallel vs Sequential:** Use `run_models_parallel.py` for speed, `run_models_spatial.py` for debugging

## Example Workflows

```bash
# Test different reasoning types
python run_models_parallel.py -m nebius-llama3.3-70b -p base --context sum --label spatial --max_workers 20
python run_models_parallel.py -m nebius-llama3.3-70b -p base --context sum --label temporal --max_workers 20
python run_models_parallel.py -m nebius-llama3.3-70b -p base --context sum --label behavioral --max_workers 20

# Compare all five pipelines
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv4_explicit --context sum --label spatial
python run_models_parallel.py -m nebius-llama3.3-70b -p prop_generated_p10_improved_v2 --context sum --label spatial  
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv3_rag_t10_improved --context sum --label spatial
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv3_rag_prop_t15_p5_improved_v2 --context sum --label spatial
python run_models_parallel.py -m nebius-llama3.3-70b -p rules_generated_r10_improved_v2 --context sum --label spatial

# Evaluate results
python evaluate_spatial.py -m nebius-llama3.3-70b -p rulesv4_explicit --context sum --label spatial
```

---

For detailed technical documentation, see `README_legacy.md`. 