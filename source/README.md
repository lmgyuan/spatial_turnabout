# Turnabout LLM: Multi-Dimensional Reasoning Benchmark for Large Language Models

A comprehensive benchmark for evaluating Large Language Models' (LLMs) **deductive reasoning** abilities across multiple cognitive dimensions using interactive detective novel games from the **Ace Attorney** and **Danganronpa** series.

## Recent Updates

**Model Support Simplification (Latest):**
- **Streamlined model support**: Now supports only OpenAI and Nebius models for improved reliability
- **Unified model loading**: All model loading is handled through `model_loader.py`
- **Enhanced error handling**: Clear error messages for unsupported models
- **Code modularization**: Extracted shared `load_model()` function to reduce duplication

**Supported Models:**
- **OpenAI**: `gpt-*`, `o3-*`, `o4-*` variants
- **Nebius**: `nebius-*` variants
- **Unsupported**: DeepSeek and local HuggingFace models (removed for stability)

## Overview

This project transforms detective game scenarios into sophisticated multiple-choice reasoning tasks where models must:

1. **Read case backgrounds** and character descriptions
2. **Examine physical evidence** with various properties
3. **Analyze witness testimonies** containing claims
4. **Identify contradictions** using multi-dimensional reasoning
5. **Apply logical reasoning** across different cognitive domains

The benchmark evaluates models across **six major reasoning dimensions**: **spatial**, **temporal**, **behavioral**, **physical/object property**, **numerical**, and **causal** reasoning, with additional categories like **spelling** errors.

## Reasoning Types Evaluated

The benchmark categorizes reasoning tasks into multiple types:

| Reasoning Type | Description | Example |
|----------------|-------------|---------|
| **Spatial** | Position, orientation, containment relationships | "at the airport" vs. "on the bus" |
| **Temporal** | Time-based reasoning, sequences, timing | "before noon" vs. "after 3PM" |
| **Behavioral** | Human behavior, intent, habits, preferences | "hates music" vs. "listens to music daily" |
| **Physical/Object Property** | Non-universal properties of objects | "death by blunt object" vs. "weapon was a gun" |
| **Numerical** | Quantitative contradictions | "1 gunshot" vs. "2 gunshots" |
| **Causal** | Cause-and-effect relationships | Logical implications and consequences |
| **Spelling** | Name/word variations | "Harry" vs. "Henry" |

**Note:** Many cases involve **multiple reasoning types simultaneously** (e.g., spatial + temporal + causal).

## Quick Start

**Note:** All commands should be run from the `source/` directory unless otherwise specified.

### Basic Model Evaluation
```bash
# Run a model on spatial reasoning tasks (parallel version for faster processing)
python run_models_parallel.py -m nebius-llama3.3-70b -p rulesv4_explicit --context sum --label spatial --max_workers 30

# Run on temporal reasoning tasks  
python run_models_parallel.py -m nebius-qwen-32b -p base --context sum --label temporal --max_workers 25

# Run on behavioral reasoning tasks
python run_models_parallel.py -m nebius-qwen3-32b -p cot_one_shot --context sum --label behavioral --max_workers 25

# Alternative: Use sequential version for smaller datasets or debugging
python run_models_spatial.py -m nebius-llama3.3-70b -p rulesv4_explicit --context sum --label spatial

# Evaluate results
python evaluate_spatial.py -m nebius-llama3.3-70b -p rulesv4_explicit --context sum --label spatial
```

### Advanced Analysis
```bash
# Run with different rule sets (primarily for spatial reasoning)
python run_models_spatial.py -m nebius-llama3.3-70b -p rulesa_explicit --label spatial
python run_models_spatial.py -m llama-3.1-70b -p rulesv3a_explicit --label physical

# Compare multiple models across reasoning types
python evaluate_spatial.py --all --data aceattorney
```

## Core Components

### 1. **Enhanced Model Runner** (`run_models_spatial.py`)

**Note:** Despite the name "spatial", this script handles **all reasoning types** - it's an enhanced version of the original `run_models.py`.

**Key Features:**
- **Label-based filtering**: Target specific reasoning types (`--label spatial`, `--label temporal`, `--label behavioral`, `--label physical`, `--label numerical`, `--label causal`)
- **Multi-dimensional analysis**: Focus evaluation on particular cognitive skills
- **Flexible prompting**: Support for rule-based and standard prompts
- **Context management**: Multiple context strategies (full, summary, or none)

**Usage:**
```bash
python run_models_spatial.py [OPTIONS]

Options:
  -m, --model TEXT          Model name (OpenAI: gpt-*, o3-*, o4-*; Nebius: nebius-*)
  -p, --prompt TEXT         Prompt type (base, rulesv4_explicit, prop_generated_explicit, cot_one_shot, etc.)
  --context TEXT            Context strategy (full, sum, or none)
  --label TEXT              Reasoning type filter (spatial, temporal, behavioral, physical, numerical, causal)
  --case TEXT               Run specific case (e.g., "3-4-1") or range (e.g., "3-4-1+")
  --no_description          Exclude character/evidence descriptions
  --data TEXT               Dataset (aceattorney or danganronpa, default: aceattorney)
  --reasoning TEXT          Include reasoning in prompts: none (default), full (all reasoning), facts (only facts), props (only propositions)
```

**Reasoning Parameter Examples:**
```bash
# Include all reasoning steps in prompts
python run_models_spatial.py -m nebius-llama3.3-70b -p base --context sum --reasoning full

# Include only facts from reasoning
python run_models_spatial.py -m nebius-qwen-32b -p base --context sum --reasoning facts

# Include only propositions from reasoning  
python run_models_spatial.py -m nebius-qwen3-32b -p base --context sum --reasoning props
```

### 2. **Global Parallel Model Runner** (`run_models_parallel.py`)

**Note:** High-performance parallel version that handles **all reasoning types** with dramatically improved efficiency.

**Key Advantages over `run_models_spatial.py`:**
- **Global parallelization**: Processes ALL turns from ALL cases simultaneously
- **Superior efficiency**: Much faster for datasets where cases have few turns each
- **Scalable processing**: Configurable worker threads for optimal resource utilization
- **Identical output format**: Drop-in replacement with same command-line interface
- **Enhanced throughput**: Processes hundreds of turns in parallel instead of sequentially

**When to Use:**
- **Large-scale evaluations**: Processing many cases across multiple reasoning types
- **Time-sensitive research**: When rapid results are needed
- **Resource optimization**: Making full use of available computational resources
- **Batch processing**: Running comprehensive model comparisons

**Usage:**
```bash
python run_models_parallel.py [OPTIONS]

Options:
  # Same as run_models_spatial.py, plus:
  --max_workers INT         Number of parallel API calls (default: 20, recommended for global parallelization)
```

**Performance Examples:**
```bash
# High-throughput spatial reasoning evaluation with 57 parallel workers
python run_models_parallel.py -m nebius-llama3.3-70b -p base --context sum --label spatial --max_workers 57

# Efficient multi-model comparison with 20 parallel workers
python run_models_parallel.py -m nebius-qwen-32b -p rulesv4_explicit --context sum --label spatial --max_workers 20

# Large-scale proposition generation with parallel processing
python run_models_parallel.py -m nebius-llama3.3-70b -p prop_generated_explicit --context sum --label spatial --max_workers 30
```

**Performance Guidelines:**
- **API rate limits**: Adjust `--max_workers` based on provider limits
- **Memory considerations**: Higher worker counts require more system memory
- **Network bandwidth**: Ensure sufficient bandwidth for parallel API calls
- **Recommended settings**: 20-57 workers for most API providers

### 3. **Advanced Evaluator** (`evaluate_spatial.py`)

**Note:** Also handles **all reasoning types** despite the name.

**Capabilities:**
- **Multi-dimensional analysis**: Accuracy by reasoning type, case difficulty, complexity
- **Statistical reporting**: Confidence intervals, significance testing
- **Comparative analysis**: Multi-model performance comparison
- **Error categorization**: Detailed failure mode analysis across reasoning types

### 4. **Model Loader** (`source/model_loader.py`)

**Shared Model Loading System:**
- **Unified interface**: Single function to load any supported model type
- **Provider abstraction**: Handles OpenAI and Nebius models with consistent API
- **Automatic detection**: Identifies model type from name patterns
- **Error handling**: Clear validation and error messages for unsupported models
- **Environment management**: Secure API key loading from `.env` file

**Supported Models:**
- **OpenAI Models**: `gpt-*`, `o3-*`, `o4-*` (GPT-4, GPT-3.5, O3, O4 variants)
- **Nebius Models**: `nebius-*` (Nebius Llama, Qwen, and other variants)

**Usage:**
```python
from model_loader import load_model

# Load any supported model
client, name = load_model("gpt-4")                    # OpenAI API
client, name = load_model("nebius-llama3.3-70b")     # Nebius API
```

### 5. **Proposition Generator** (`source/prop_generator.py`)

**Revolutionary Feature:**
- **Dynamic proposition generation**: Automatically generates turn-specific spatial propositions for each case
- **Context-aware reasoning**: Creates logical principles tailored to specific evidences and testimonies  
- **LLM-powered extraction**: Uses the same evaluation model to generate propositions for reasoning
- **Enhanced spatial logic**: Provides more nuanced rules than static general rules

**How It Works:**
1. **Analysis Phase**: For each turn, analyzes evidences, testimonies, and context
2. **Generation Phase**: Uses LLM to generate turn-specific spatial propositions based on case elements
3. **Integration Phase**: Incorporates generated propositions into the reasoning prompt
4. **Application Phase**: Models apply these context-aware propositions to identify contradictions

**Key Features:**
- **Automatic activation**: Triggered when using prompts containing "prop_generated"
- **Rich context integration**: Uses same format as main prompt (characters, evidences, testimonies)
- **Comprehensive logging**: Saves all generated propositions with metadata for analysis
- **Quality control**: Parses and validates generated propositions before use

**Generated Proposition Examples:**
```
Prop 1: If something is blocked from view, it cannot be seen.
Prop 2: If someone is stabbed to the left chest, her left pocket would be stabbed too.  
Prop 3: If a person A goes to a location where person B is at, person B would have seen person A pass through.
```

**Usage:**
```bash
# Use dynamic proposition generation for spatial reasoning
python run_models_spatial.py -m nebius-llama3.3-70b -p prop_generated_explicit --context sum --label spatial

# Compare with static rule-based approach
python run_models_spatial.py -m nebius-llama3.3-70b -p rulesv4_explicit --context sum --label spatial
```

**Logging and Analysis:**
The system automatically logs all generated propositions to `{output_dir}/props_log_{model}_{timestamp}.json` for detailed analysis of proposition quality and usage patterns.

## Choosing the Right Model Runner

### Performance Comparison: Sequential vs Parallel

| Scenario | Recommended Runner | Reason |
|----------|-------------------|---------|
| **Large-scale evaluations** | `run_models_parallel.py` | Dramatically faster with global parallelization |
| **Multiple reasoning types** | `run_models_parallel.py` | Efficient batch processing across categories |
| **Proposition generation** | `run_models_parallel.py` | Parallel prop generation + parallel evaluation |
| **RAG-enhanced prompts** | `run_models_parallel.py` | Parallel RAG processing + parallel evaluation |
| **Development/debugging** | `run_models_spatial.py` | Sequential processing easier to debug |
| **Single case testing** | `run_models_spatial.py` | Simpler for small-scale experiments |
| **Resource-constrained environments** | `run_models_spatial.py` | Lower memory and network requirements |

### Performance Guidelines

**Parallel Version (`run_models_parallel.py`):**
- **Best for**: Production runs, comprehensive evaluations, time-sensitive research
- **Worker count**: 20-57 workers depending on API rate limits
- **Memory usage**: Higher due to parallel processing
- **Speed improvement**: 3-10x faster depending on dataset characteristics

**Sequential Version (`run_models_spatial.py`):**
- **Best for**: Development, debugging, single case analysis
- **Resource usage**: Lower memory and network requirements
- **Debugging**: Easier to trace issues and monitor progress
- **Compatibility**: Better for environments with strict resource limits

## Spatial Reasoning Rule System

The project implements a sophisticated **hierarchical rule system** specifically for **spatial reasoning** tasks:

### Rule Hierarchy

| Rule Set | File | Rules | Description |
|----------|------|-------|-------------|
| **Basic** | `Rules/RuleText2.txt` | 18 | Core reciprocal spatial relationships |
| **Comprehensive** | `Rules/RuleText.txt` | 74 | Full spatial reasoning with transitivity |
| **Extended** | `Rules/RuleText3.txt` | 117 | Advanced vision, movement, positioning |
| **Optimized** | `Rules/RuleText4.txt` | 44 | Balanced set for practical use |

### Filtered Rule Sets

Based on **empirical analysis** of model usage patterns:

| Filtered Set | File | Rules | Source | Efficiency Gain |
|--------------|------|-------|--------|----------------|
| **Optimized Basic** | `Rules/RuleTexta.txt` | 35 | Rules/RuleText.txt (74) | 52.7% reduction |
| **Optimized Extended** | `Rules/RuleText3a.txt` | 58 | Rules/RuleText3.txt (117) | 49.6% reduction |
| **Optimized Practical** | `Rules/RuleText4a.txt` | 39 | Rules/RuleText4.txt (44) | 11.4% reduction |

## Prompt Engineering System

### Prompt Types

| Prompt | File | Features | Best For |
|--------|------|----------|----------|
| **Base** | `base.json` | Simple contradiction detection | All reasoning types |
| **Chain-of-Thought** | `cot_one_shot.json` | Step-by-step reasoning | Complex multi-step reasoning |
| **Rule-based** | `rules.json`, `rulesv2.json`, etc. | Explicit spatial rules | Spatial reasoning tasks |
| **Explicit** | `*_explicit.json` | Enhanced rule reference instructions | Spatial reasoning with detailed analysis |
| **RAG-enabled** | `*_rag*.json` | Dynamic rule retrieval | Adaptive spatial reasoning |
| **Proposition-based** | `prop_generation.json`, `prop_generated_explicit.json` | Dynamic proposition generation | Advanced spatial reasoning with context-aware rules |

### RAG (Retrieval-Augmented Generation) System

The project implements a **semantic RAG system** for dynamic spatial rule selection, enabling models to access only the most relevant rules for each specific case.

#### RAG Activation

RAG is activated when using prompt names containing `"rag"`. The system:

1. **Detects RAG prompts**: Automatically identifies when a prompt name contains `"rag"`
2. **Parses top_k values**: Extracts the number of rules to retrieve from the prompt name
3. **Dynamically selects rules**: Uses semantic similarity to choose the most relevant spatial rules

#### Top-K Value Configuration

The `top_k` parameter (number of rules to retrieve) is **automatically parsed from the prompt filename**:

| Prompt File | Top-K Value | Rules Retrieved |
|-------------|-------------|----------------|
| `rulesv3_rag_t5.json` | 5 | Top 5 most relevant rules |
| `rulesv3_rag_t10.json` | 10 | Top 10 most relevant rules |
| `rulesv3_rag_t15.json` | 15 | Top 15 most relevant rules |
| `rulesv4_rag.json` | 5 (default) | Default fallback |

#### RAG Implementation Details

**Semantic Similarity**: Uses `sentence-transformers` with `all-MiniLM-L6-v2` model
**Rule Source**: Defaults to `../Rules/RuleText3.txt` (117 spatial rules)
**Context Extraction**: Combines testimonies and evidence descriptions
**Rule Selection**: Cosine similarity between case context and rule embeddings

#### RAG Usage Examples

```bash
# Use RAG with 5 most relevant rules
python run_models_spatial.py -m nebius-llama3.3-70b -p rulesv3_rag_t5 --context sum --label spatial

# Use RAG with 10 most relevant rules  
python run_models_spatial.py -m llama-3.1-70b -p rulesv3_rag_t10 --context sum --label spatial

# Use RAG with 15 most relevant rules
python run_models_spatial.py -m nebius-llama3.3-70b -p rulesv3_rag_t15 --context sum --label spatial
```

#### RAG Benefits

- **Reduced prompt length**: Only includes relevant rules instead of entire rule set
- **Better focus**: Models see rules most applicable to the specific case
- **Adaptive reasoning**: Rule selection adapts to case characteristics
- **Performance tracking**: Logs which rules are selected for analysis

### Explicit Prompting (Spatial Focus)

The **explicit prompts** (`*_explicit.json`) are designed specifically for **spatial reasoning** and provide enhanced instructions that ask models to:

1. **Analyze spatial contradictions** systematically
2. **Check applicable spatial rules** from the provided list
3. **Explicitly cite rules** and explain their application
4. **Provide structured reasoning** in 5-step format
5. **Output structured JSON** responses

## Analysis and Evaluation

### Performance Metrics

- **Overall Accuracy**: Correct contradiction identification
- **Reasoning-Type Accuracy**: Performance by cognitive dimension
- **Rule Usage Rate**: Percentage of spatial cases using spatial rules
- **Multi-dimensional Analysis**: Performance across reasoning type combinations

### Reasoning Type Distribution

Based on dataset statistics, approximate distributions:

- **Physical/Object Property**: ~40-45% of cases
- **Spatial**: ~15-20% of cases  
- **Behavioral**: ~15-20% of cases
- **Causal**: ~30-35% of cases (often combined with others)
- **Temporal**: ~8-12% of cases
- **Numerical**: ~5-8% of cases
- **Spelling**: ~1-3% of cases

**Note:** Many cases involve **multiple reasoning types** simultaneously.

### Example Analysis Output (Spatial Focus):
```
SPATIAL REASONING RULE USAGE ANALYSIS
=====================================
Model: Nebius Llama 3.3 70B (rulesv4_explicit)
Cases Analyzed: 40 spatial cases, 57 turns
Rule Coverage: 84.1% (37/44 rules used)
Rules per Turn: 7.25 average

Most Used Rules:
1. Same room visibility (rule_05): 34 uses
2. Movement direction (rule_08): 26 uses
3. Location change (rule_07): 26 uses
4. Gravity/falling (rule_10): 25 uses
5. Line of sight blocking (rule_01): 24 uses
```

## Project Structure

```
source/
├── run_models_spatial.py          # Enhanced model evaluation (all reasoning types)
├── run_models_parallel.py         # Global parallel model evaluation (all reasoning types)
├── evaluate_spatial.py            # Advanced result analysis (all reasoning types)
├── model_loader.py                # Shared model loading system (OpenAI & Nebius)
├── prop_generator.py              # Dynamic proposition generation system
├── rag.py                         # RAG system for dynamic rule retrieval
├── prompts/                       # Prompt engineering
│   ├── base.json                  # Basic prompts (all reasoning types)
│   ├── cot_one_shot.json         # Chain-of-thought (all reasoning types)
│   ├── rules*.json               # Rule-based prompts (spatial focus)
│   ├── *_explicit.json           # Enhanced explicit prompts (spatial focus)
│   ├── *_rag*.json               # RAG-enabled prompts (spatial focus)
│   ├── prop_generation.json      # Proposition generation prompt
│   ├── prop_generated_explicit.json  # Proposition-enhanced explicit prompt
│   └── ...
├── README.md                      # This documentation
└── README_legacy.md               # Original documentation
```

data/
├── aceattorney_data/             # Ace Attorney cases
├── danganronpa_data/             # Danganronpa cases
└── README.md                     # Data documentation

Rule Files (Spatial Reasoning):
├── Rules/                        # Spatial reasoning rules and analysis
│   ├── RuleText.txt              # 74 comprehensive spatial rules
│   ├── RuleText2.txt             # 18 basic spatial rules
│   ├── RuleText3.txt             # 117 extended spatial rules
│   ├── RuleText4.txt             # 44 optimized spatial rules
│   ├── RuleTexta.txt             # 35 filtered (from RuleText.txt)
│   ├── RuleText3a.txt            # 58 filtered (from RuleText3.txt)
│   ├── RuleText4a.txt            # 39 filtered (from RuleText4.txt)
│   ├── props_spatial.txt         # 82+ extracted spatial propositions
│   └── *_rules_analysis.txt      # Generated rule usage analyses
```

## Data Format

Each case contains:

```json
{
    "case_id": "1-1-1_The_First_Turnabout",
    "characters": [...],           # Character descriptions
    "evidences": [...],           # Physical evidence with various properties
    "turns": [
        {
            "testimonies": [...],  # Witness claims
            "answer": {           # Correct contradiction
                "evidence": 2,
                "testimony": 1
            },
            "reason": "spatial",  # Reasoning type classification
            "labels": ["spatial", "causal"]  # Multiple reasoning types
        }
    ]
}
```

## Research Applications

### Multi-Dimensional Reasoning Research
- **Cross-domain reasoning**: How do models perform across different cognitive dimensions?
- **Reasoning type interactions**: How do models handle cases requiring multiple reasoning types?
- **Cognitive specialization**: Which models excel at which reasoning types?

### Spatial Reasoning Research (Subset)
- **Rule-based reasoning**: How do models apply explicit spatial rules?
- **Implicit reasoning**: Can models reason spatially without explicit rules?
- **Rule optimization**: Which spatial rules are essential vs. redundant?

### Model Comparison
- **Cross-model analysis**: Compare reasoning strategies across different LLMs
- **Reasoning-type performance**: Identify model strengths and weaknesses by cognitive dimension
- **Prompt engineering**: Optimize prompts for specific reasoning types

## Example Workflows

### 1. **Comprehensive Multi-Reasoning Evaluation**
```bash
# Test across different reasoning types (use parallel version for faster processing)
python run_models_parallel.py -m nebius-llama3.3-70b -p base --context sum --label spatial --max_workers 30
python run_models_parallel.py -m nebius-llama3.3-70b -p base --context sum --label temporal --max_workers 30
python run_models_parallel.py -m nebius-llama3.3-70b -p base --context sum --label behavioral --max_workers 30
python run_models_parallel.py -m nebius-llama3.3-70b -p base --context sum --label physical --max_workers 30
python run_models_parallel.py -m nebius-llama3.3-70b -p base --context sum --label numerical --max_workers 30

# Alternative: Use sequential version for smaller datasets or debugging
python run_models_spatial.py -m nebius-llama3.3-70b -p base --context sum --label spatial

# Analyze and compare
python evaluate_spatial.py --all --data aceattorney
```

### 2. **Spatial Reasoning Rule Optimization** 
```bash
# Test original vs. filtered spatial rules
python run_models_spatial.py -m nebius-llama3.3-70b -p rulesv4_explicit --context sum --label spatial
python run_models_spatial.py -m nebius-llama3.3-70b -p rulesv4a_explicit --context sum --label spatial

# Compare spatial rule usage by evaluating the different rule sets
python evaluate_spatial.py -m nebius-llama3.3-70b -p rulesv4_explicit --context sum --label spatial
python evaluate_spatial.py -m nebius-llama3.3-70b -p rulesv4a_explicit --context sum --label spatial
```

### 3. **Cross-Reasoning Type Analysis**
```bash
# Focus on multi-dimensional cases
python run_models_spatial.py -m llama-3.1-70b -p cot_one_shot --context sum --label spatial
python run_models_spatial.py -m llama-3.1-70b -p cot_one_shot --context sum --label behavioral  
python run_models_spatial.py -m llama-3.1-70b -p cot_one_shot --context sum --label causal

# Evaluate each reasoning type separately
python evaluate_spatial.py -m llama-3.1-70b -p cot_one_shot --context sum --label spatial
python evaluate_spatial.py -m llama-3.1-70b -p cot_one_shot --context sum --label behavioral
python evaluate_spatial.py -m llama-3.1-70b -p cot_one_shot --context sum --label causal
```

### 4. **RAG-Enhanced Spatial Reasoning Analysis**
```bash
# Compare different RAG configurations
python run_models_spatial.py -m nebius-llama3.3-70b -p rulesv3_rag_t5 --context sum --label spatial
python run_models_spatial.py -m nebius-llama3.3-70b -p rulesv3_rag_t10 --context sum --label spatial
python run_models_spatial.py -m nebius-llama3.3-70b -p rulesv3_rag_t15 --context sum --label spatial

# Compare RAG vs. non-RAG approaches
python run_models_spatial.py -m nebius-llama3.3-70b -p rulesv3_explicit --context sum --label spatial
python run_models_spatial.py -m nebius-llama3.3-70b -p rulesv3_rag_t10 --context sum --label spatial

# Evaluate RAG performance
python evaluate_spatial.py -m nebius-llama3.3-70b -p rulesv3_rag_t10 --context sum --label spatial

# Analyze which rules were selected by RAG (check ../Rules/ for log files)
ls ../Rules/rag_rules_used_nebius-llama3.3-70b_prompt_rulesv3_rag_t10_*.txt
```

### 5. **Dynamic Proposition Generation Analysis**
```bash
# Test proposition-enhanced reasoning across different models (use parallel version for faster proposition generation)
python run_models_parallel.py -m nebius-llama3.3-70b -p prop_generated_explicit --context sum --label spatial --max_workers 25
python run_models_parallel.py -m nebius-qwen-32b -p prop_generated_explicit --context sum --label spatial --max_workers 25  
python run_models_parallel.py -m nebius-qwen3-32b -p prop_generated_explicit --context sum --label spatial --max_workers 25

# Alternative: Sequential processing (for debugging or limited resources)
python run_models_spatial.py -m nebius-llama3.3-70b -p prop_generated_explicit --context sum --label spatial

# Compare against static rule-based approaches
python run_models_spatial.py -m nebius-llama3.3-70b -p rulesv4_explicit --context sum --label spatial
python run_models_spatial.py -m nebius-llama3.3-70b -p base --context sum --label spatial

# Evaluate proposition generation performance
python evaluate_spatial.py -m nebius-llama3.3-70b -p prop_generated_explicit --context sum --label spatial
python evaluate_spatial.py -m nebius-qwen-32b -p prop_generated_explicit --context sum --label spatial

# Analyze generated propositions (check output directory for proposition logs)
ls ../output_spatial/nebius-llama3.3-70b_prompt_prop_generated_explicit_*/props_log_*.json
ls ../output_spatial/nebius-qwen-32b_prompt_prop_generated_explicit_*/props_log_*.json

# Compare proposition generation with different reasoning parameter settings
python run_models_spatial.py -m nebius-llama3.3-70b -p prop_generated_explicit --context sum --label spatial --reasoning full
python run_models_spatial.py -m nebius-llama3.3-70b -p prop_generated_explicit --context sum --label spatial --reasoning props
```

## Advanced Configuration

### Model Configuration
The system supports OpenAI and Nebius models through the unified `model_loader.py`:
- **OpenAI models**: `gpt-*`, `o3-*`, `o4-*` (GPT-4, GPT-3.5, O3, O4 variants)
- **Nebius models**: `nebius-*` (Nebius Llama, Qwen, and other variants)

**Environment Setup:**
Create a `.env` file in the project root with your API keys:
```
OPENAI_API_KEY=your_openai_api_key_here
NEBIUS_API_KEY=your_nebius_api_key_here
```

**Note:** DeepSeek and local HuggingFace models are no longer supported in the current version.

### Prompt Customization
Create custom prompts by following the established JSON format:
```json
{
    "prefix": "Instructions and rules (if applicable)...",
    "suffix": "Output format and requirements..."
}
```

### RAG System Configuration

#### RAG-Enabled Prompt Creation
To create RAG-enabled prompts, include the `{dynamic_rules}` placeholder in the prefix:
```json
{
    "prefix": "You are provided with characters, evidences and testimonies.\n\nRelevant Spatial Reasoning Rules:\n{dynamic_rules}\n\n",
    "suffix": "Analyze the spatial contradiction and provide your answer..."
}
```

#### Custom Top-K Values
Control the number of retrieved rules by including `_t{number}` in the prompt filename:
- `custom_rag_t3.json` → retrieves 3 rules
- `custom_rag_t12.json` → retrieves 12 rules
- `custom_rag.json` → uses default (5 rules)

#### RAG Dependencies
The RAG system requires additional Python packages:
```bash
pip install sentence-transformers scikit-learn
```

#### RAG Logging
The system automatically logs rule selection to `../Rules/rag_rules_used_*.txt` files for analysis and debugging.

### Rule Set Creation (Spatial Reasoning)
Design custom spatial rule sets by creating text files with one rule per line:
```
If XXX is above YYY then YYY is below XXX
If XXX is inside YYY then YYY contains XXX
...
```

For legacy documentation, see `README_legacy.md`. 