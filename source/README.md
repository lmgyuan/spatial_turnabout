# Turnabout LLM: Multi-Dimensional Reasoning Benchmark for Large Language Models

A comprehensive benchmark for evaluating Large Language Models' (LLMs) **deductive reasoning** abilities across multiple cognitive dimensions using interactive detective novel games from the **Ace Attorney** and **Danganronpa** series.

## 🎯 Overview

This project transforms detective game scenarios into sophisticated multiple-choice reasoning tasks where models must:

1. **Read case backgrounds** and character descriptions
2. **Examine physical evidence** with various properties
3. **Analyze witness testimonies** containing claims
4. **Identify contradictions** using multi-dimensional reasoning
5. **Apply logical reasoning** across different cognitive domains

The benchmark evaluates models across **six major reasoning dimensions**: **spatial**, **temporal**, **behavioral**, **physical/object property**, **numerical**, and **causal** reasoning, with additional categories like **spelling** errors.

## 🧠 Reasoning Types Evaluated

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

## 🚀 Quick Start

### Basic Model Evaluation
```bash
# Run a model on spatial reasoning tasks
python run_models_spatial.py -m gpt-4 -p rulesv4_explicit --context sum --label spatial

# Run on temporal reasoning tasks  
python run_models_spatial.py -m gpt-4 -p base --context sum --label temporal

# Run on behavioral reasoning tasks
python run_models_spatial.py -m gpt-4 -p cot_one_shot --context sum --label behavioral

# Evaluate results
python evaluate_spatial.py output_spatial/gpt-4_prompt_rulesv4_explicit_context_sum_label_spatial
```

### Advanced Analysis
```bash
# Run with different rule sets (primarily for spatial reasoning)
python run_models_spatial.py -m claude-3 -p rulesa_explicit --label spatial
python run_models_spatial.py -m llama-70b -p rulesv3a_explicit --label physical

# Compare multiple models across reasoning types
python evaluate_spatial.py output_spatial/ --compare
```

## 📊 Core Components

### 1. **Enhanced Model Runner** (`run_models_spatial.py`)

**Note:** Despite the name "spatial", this script handles **all reasoning types** - it's an enhanced version of the original `run_models.py`.

**Key Features:**
- **Label-based filtering**: Target specific reasoning types (`--label spatial`, `--label temporal`, `--label behavioral`, `--label physical`, `--label numerical`, `--label causal`)
- **Multi-dimensional analysis**: Focus evaluation on particular cognitive skills
- **Flexible prompting**: Support for rule-based and standard prompts
- **Context management**: Multiple context strategies (full, summary, minimal)

**Usage:**
```bash
python run_models_spatial.py [OPTIONS]

Options:
  -m, --model TEXT          Model name (gpt-4, claude-3, llama-70b, etc.)
  -p, --prompt TEXT         Prompt type (base, rulesv4_explicit, cot_one_shot, etc.)
  --context TEXT            Context strategy (full, sum, min)
  --label TEXT              Reasoning type filter (spatial, temporal, behavioral, physical, numerical, causal)
  --max_cases INT           Maximum cases to process
  --output_dir TEXT         Custom output directory
```

### 2. **Advanced Evaluator** (`evaluate_spatial.py`)

**Note:** Also handles **all reasoning types** despite the name.

**Capabilities:**
- **Multi-dimensional analysis**: Accuracy by reasoning type, case difficulty, complexity
- **Statistical reporting**: Confidence intervals, significance testing
- **Comparative analysis**: Multi-model performance comparison
- **Error categorization**: Detailed failure mode analysis across reasoning types

### 3. **Rule Usage Analyzer** (`source/extract_rule_usage.py`)

**Features:**
- **Dynamic rule loading**: Works with any rule text file
- **Pattern recognition**: Detects explicit and implicit rule usage
- **Usage statistics**: Quantifies which rules are most/least used
- **Auto-naming**: Generates output filenames automatically

**Note:** Rule-based prompts are primarily designed for **spatial reasoning** tasks, but can be applied to other reasoning types as well.

## 🧠 Spatial Reasoning Rule System

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

## 🔧 Prompt Engineering System

### Prompt Types

| Prompt | File | Features | Best For |
|--------|------|----------|----------|
| **Base** | `base.json` | Simple contradiction detection | All reasoning types |
| **Chain-of-Thought** | `cot_one_shot.json` | Step-by-step reasoning | Complex multi-step reasoning |
| **Rule-based** | `rules.json`, `rulesv2.json`, etc. | Explicit spatial rules | Spatial reasoning tasks |
| **Explicit** | `*_explicit.json` | Enhanced rule reference instructions | Spatial reasoning with detailed analysis |

### Explicit Prompting (Spatial Focus)

The **explicit prompts** (`*_explicit.json`) are designed specifically for **spatial reasoning** and provide enhanced instructions that ask models to:

1. **Analyze spatial contradictions** systematically
2. **Check applicable spatial rules** from the provided list
3. **Explicitly cite rules** and explain their application
4. **Provide structured reasoning** in 5-step format
5. **Output structured JSON** responses

## 📈 Analysis and Evaluation

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

## 🏗️ Project Structure

```
source/
├── run_models_spatial.py          # Enhanced model evaluation (all reasoning types)
├── evaluate_spatial.py            # Advanced result analysis (all reasoning types)
├── source/extract_rule_usage.py    # Rule usage analysis (spatial rules)
├── prompts/                       # Prompt engineering
│   ├── base.json                  # Basic prompts (all reasoning types)
│   ├── cot_one_shot.json         # Chain-of-thought (all reasoning types)
│   ├── rules*.json               # Rule-based prompts (spatial focus)
│   ├── *_explicit.json           # Enhanced explicit prompts (spatial focus)
│   └── ...
├── README.md                      # This documentation
└── README_legacy.md               # Original documentation

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
│   └── *_rules_analysis.txt      # Generated rule usage analyses
```

## 🎮 Data Format

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

## 🔬 Research Applications

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

## 📊 Example Workflows

### 1. **Comprehensive Multi-Reasoning Evaluation**
```bash
# Test across different reasoning types
python run_models_spatial.py -m gpt-4 -p base --label spatial
python run_models_spatial.py -m gpt-4 -p base --label temporal
python run_models_spatial.py -m gpt-4 -p base --label behavioral
python run_models_spatial.py -m gpt-4 -p base --label physical
python run_models_spatial.py -m gpt-4 -p base --label numerical

# Analyze and compare
python evaluate_spatial.py output_spatial/ --compare
```

### 2. **Spatial Reasoning Rule Optimization** 
```bash
# Test original vs. filtered spatial rules
python run_models_spatial.py -m claude-3 -p rulesv4_explicit --label spatial
python run_models_spatial.py -m claude-3 -p rulesv4a_explicit --label spatial

# Compare spatial rule usage
python source/extract_rule_usage.py -r Rules/RuleText4.txt -i output_spatial/claude-3_prompt_rulesv4_explicit_*
python source/extract_rule_usage.py -r Rules/RuleText4a.txt -i output_spatial/claude-3_prompt_rulesv4a_explicit_*
```

### 3. **Cross-Reasoning Type Analysis**
```bash
# Focus on multi-dimensional cases
python run_models_spatial.py -m llama-70b -p cot_one_shot --label spatial
python run_models_spatial.py -m llama-70b -p cot_one_shot --label behavioral  
python run_models_spatial.py -m llama-70b -p cot_one_shot --label causal

# Comparative analysis
python evaluate_spatial.py output_spatial/llama-70b_* --by_label
```

## 🛠️ Advanced Configuration

### Model Configuration
The system supports various LLM providers through flexible configuration:
- **OpenAI models**: GPT-4, GPT-3.5, etc.
- **Anthropic models**: Claude-3, Claude-2, etc.  
- **Open source models**: Llama, Qwen, Nebius, etc.
- **Custom endpoints**: Any OpenAI-compatible API

### Prompt Customization
Create custom prompts by following the established JSON format:
```json
{
    "prefix": "Instructions and rules (if applicable)...",
    "suffix": "Output format and requirements..."
}
```

### Rule Set Creation (Spatial Reasoning)
Design custom spatial rule sets by creating text files with one rule per line:
```
If XXX is above YYY then YYY is below XXX
If XXX is inside YYY then YYY contains XXX
...
```

## 📝 Citation

If you use this benchmark in your research, please cite:

```bibtex
@article{turnabout_llm_2024,
    title={Turnabout LLM: Multi-Dimensional Reasoning Benchmark for Large Language Models},
    author={[Authors]},
    journal={[Journal]},
    year={2024}
}
```

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- **New reasoning types**: Additional cognitive dimensions
- **Rule systems**: Extend beyond spatial to other reasoning types
- **Prompt engineering**: Better instruction formats for different reasoning types
- **Analysis tools**: Enhanced evaluation metrics across reasoning dimensions
- **Data expansion**: Additional detective game cases
- **Model support**: Integration with new LLM providers

## 📄 License

[License information]

---

For legacy documentation, see `README_legacy.md`. 