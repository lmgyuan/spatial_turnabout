#!/usr/bin/env python3
"""
Generate Meeting 20 plots for both Turnabout and SPARTUN benchmarks.

Based on meeting 18 plots with the following improvements:
- Clean white background with light gray gridlines (no seaborn theme)
- ColorBrewer-inspired colorblind-safe palette
- Fixed label names to match paper tables (C0 Spatial Cue, not Priming)
- SpaRTUN best-system labels use map_prompt_to_label() for consistency
- Value labels use 2 decimal places, non-bold for readability

Reads:
    eval/turnabout_evaluation_summary.csv
    eval_spurtun/spartun_evaluation_summary.csv

Outputs (to eval/, eval_spurtun/, and LATEX/):
    Turnabout plots:
        - turnabout_b0_baseline_meeting20.png
        - turnabout_b0_c0_rc_static_meeting20.png
        - turnabout_rc_rag_comparison_meeting20.png
        - turnabout_pa_comparison_meeting20.png
        - turnabout_rc_pa_rag_comparison_meeting20.png
        - turnabout_ar_comparison_meeting20.png
        - turnabout_b0_vs_best_meeting20.png
    
    SPARTUN plots:
        - spartun_base_vs_gold_rules_meeting20.png
        - spartun_base_rc_static_rag_meeting20.png
        - spartun_base_rc_static_pa_meeting20.png
        - spartun_base_rc_static_rag_pa_meeting20.png
        - spartun_base_vs_ar_meeting20.png
        - spartun_base_vs_best_meeting20.png
"""

import os
import re
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

# ---------------------------------------------------------------------------
# Style: clean white background, light gridlines, no seaborn dependency
# ---------------------------------------------------------------------------
mpl.rcParams.update({
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'axes.edgecolor': '#cccccc',
    'axes.grid': True,
    'axes.axisbelow': True,           # grid behind bars
    'grid.color': '#e0e0e0',
    'grid.linewidth': 0.6,
    'grid.alpha': 0.7,
    'axes.grid.axis': 'y',           # horizontal gridlines only
    'xtick.color': '#333333',
    'ytick.color': '#333333',
    'text.color': '#333333',
    'font.family': 'sans-serif',
    'font.size': 10,
})

# ---------------------------------------------------------------------------
# Colorblind-safe palette (ColorBrewer-inspired)
# ---------------------------------------------------------------------------
METHOD_COLORS = {
    # Baselines
    'B0': '#A8C5E3',               # Light blue (updated for better print visibility)
    'Base': '#A8C5E3',             # Light blue (SPARTUN naming)
    'C0': '#6DB388',               # Sage green
    # Static rules
    'RC-Static': '#E8913A',        # Warm amber
    # RAG variants (teal shades)
    'RC-RAG@5': '#a6d8d4',         # Light teal
    'RC-RAG@10': '#4bafa8',        # Teal
    'RC-RAG@15': '#2a7f7a',        # Dark teal
    # Proposition augmentation (coral shades)
    'PA@5': '#f4a6a0',             # Light coral
    'PA@10': '#d65f56',            # Coral
    'PA@15': '#a83028',            # Dark coral
    # Auto-generated rules (purple shades)
    'AR@5': '#c4aad0',             # Light lavender
    'AR@10': '#8b6aae',            # Purple
    'AR@15': '#5e3d8f',            # Dark purple
    # Combined methods (rose shades)
    'RC+PA-RAG@(15,5)': '#f0b8cb',    # Light rose
    'RC+PA-RAG@(15,10)': '#d87fa2',   # Rose
    'RC+PA-RAG@(15,15)': '#b04572',   # Dark rose
    'RC+PA-RAG@(10,10)': '#d87fa2',   # Rose (SPARTUN)
    # Oracle
    'Gold': '#DAA520',             # Goldenrod
    'Gold Rules': '#DAA520',       # Goldenrod
    # Best system comparison
    'Best': '#5E3D8F',             # Dark purple (updated for better contrast and print visibility)
    'Best System': '#5E3D8F',      # Dark purple
}


def shorten_model_name(name: str) -> str:
    """Shorten model names for cleaner plot labels."""
    for prefix in ['deepinfra-', 'nebius-', 'openai-']:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return name


def extract_model_base(config: str) -> str:
    """Extract base model id from a model_config string."""
    return config.split('_prompt_')[0]


def add_value_labels(ax, bars, fmt='{:.2f}'):
    """Add value labels on top of bars."""
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2.0, h + 0.005, fmt.format(h),
                    ha='center', va='bottom', fontsize=14, fontweight='bold', color='#444444')


def save_plot(output_dirs: list, filename: str):
    """Save plot to multiple directories."""
    for d in output_dirs:
        d.mkdir(exist_ok=True)
        plt.savefig(d / filename, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()


def map_prompt_to_label(prompt_fragment: str) -> str:
    """Map a prompt fragment to a readable system label."""
    frag = prompt_fragment
    if frag.startswith('base_spatial_ablation'):
        return 'C0'
    if frag.startswith('base'):
        return 'B0'
    if frag.startswith('rulesv5_improved') or frag == 'rulesv5':
        return 'RC-Static'
    m = re.match(r'rulesv5_rag_t(\d+)(?:_improved(?:_v2)?)?$', frag)
    if m:
        return f'RC-RAG@{m.group(1)}'
    m = re.match(r'prop_generated_p(\d+)(?:_improved(?:_v2)?)?$', frag)
    if m:
        return f'PA@{m.group(1)}'
    m = re.match(r'rulesv5_rag_prop_t(\d+)_p(\d+)(?:_improved(?:_v2)?)?$', frag)
    if m:
        return f'RC+PA-RAG@({m.group(1)},{m.group(2)})'
    m = re.match(r'rag_prop_generated_t(\d+)_p(\d+)(?:_improved(?:_v2)?)?$', frag)
    if m:
        return f'RC+PA-RAG@({m.group(1)},{m.group(2)})'
    m = re.match(r'rules_generated_r(\d+)(?:_improved(?:_v2)?)?$', frag)
    if m:
        return f'AR@{m.group(1)}'
    if frag.startswith('gold_rules'):
        return 'Gold Rules'
    return frag


def style_axes(ax, title, xlabel='Model', ylabel='Accuracy'):
    """Apply consistent styling to axes."""
    ax.set_title(title, fontsize=13, fontweight='bold', color='#222222', pad=12)
    ax.set_xlabel(xlabel, fontsize=11, fontweight='bold', color='#333333')
    ax.set_ylabel(ylabel, fontsize=11, fontweight='bold', color='#333333')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#cccccc')
    ax.spines['bottom'].set_color('#cccccc')


# =============================================================================
# TURNABOUT PLOTS
# =============================================================================

def get_turnabout_acc(df: pd.DataFrame, model: str, prompt_pattern: str) -> float:
    """Get accuracy for a Turnabout model+prompt combination."""
    full_pattern = f"{model}_prompt_{prompt_pattern}"
    m = df[df['model_config'].str.contains(full_pattern, na=False)]
    return float(m.iloc[0]['overall_accuracy']) if not m.empty else 0.0


def generate_turnabout_plots(df: pd.DataFrame, output_dirs: list):
    """Generate all Turnabout plots."""
    print("\nGenerating Turnabout plots...")
    
    all_models = sorted(set(extract_model_base(c) for c in df['model_config']))
    models = [m for m in all_models if get_turnabout_acc(df, m, 'base_context_sum_label_spatial') > 0]
    models = [m for m in models if m != 'qwen-32b']
    display_names = [shorten_model_name(m) for m in models]
    
    print(f"   Models: {display_names}")
    
    # --- Plot 1: B0 Baseline ---
    fig, ax = plt.subplots(figsize=(12, 6))
    accs = [get_turnabout_acc(df, m, 'base_context_sum_label_spatial') for m in models]
    # Use a single color for all bars (baseline identity)
    bars = ax.bar(display_names, accs, color=METHOD_COLORS['B0'], edgecolor='white', linewidth=0.8)
    style_axes(ax, 'Turnabout: Baseline (B0) Accuracy Across Models')
    ax.set_ylim(0, max(accs) * 1.15 if accs else 1)
    add_value_labels(ax, bars)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    save_plot(output_dirs, 'turnabout_b0_baseline_meeting20.png')
    print("   - turnabout_b0_baseline_meeting20.png")
    
    # --- Plot 2: B0 vs C0 vs RC-Static ---
    fig, ax = plt.subplots(figsize=(14, 7))
    x = np.arange(len(models))
    width = 0.25
    b0 = [get_turnabout_acc(df, m, 'base_context_sum_label_spatial') for m in models]
    c0 = [get_turnabout_acc(df, m, 'base_spatial_ablation_context_sum_label_spatial') for m in models]
    rc = [get_turnabout_acc(df, m, 'rulesv5_improved_context_sum_label_spatial') for m in models]
    
    bars1 = ax.bar(x - width, b0, width, label='B0', color='#4878A8', edgecolor='white', linewidth=0.8)
    bars2 = ax.bar(x, c0, width, label='C0 (Spatial Cue)', color=METHOD_COLORS['C0'], edgecolor='white', linewidth=0.8)
    bars3 = ax.bar(x + width, rc, width, label='RC-Static', color=METHOD_COLORS['RC-Static'], edgecolor='white', linewidth=0.8)
    
    style_axes(ax, 'Turnabout: B0 vs C0 (Spatial Cue) vs RC-Static')
    ax.set_xticks(x)
    ax.set_xticklabels(display_names, rotation=45, ha='right', fontsize=14)
    ax.legend(frameon=True, fancybox=False, edgecolor='#cccccc', fontsize=10)
    all_vals = b0 + c0 + rc
    ax.set_ylim(0, max(all_vals) * 1.15 if all_vals else 1)
    for bars in [bars1, bars2, bars3]:
        add_value_labels(ax, bars)
    plt.tight_layout()
    save_plot(output_dirs, 'turnabout_b0_c0_rc_static_meeting20.png')
    print("   - turnabout_b0_c0_rc_static_meeting20.png")
    
    # --- Plot 3: RC-RAG Comparison ---
    fig, ax = plt.subplots(figsize=(16, 7))
    width = 0.15
    rag5 = [get_turnabout_acc(df, m, 'rulesv5_rag_t5_improved_context_sum_label_spatial') for m in models]
    rag10 = [get_turnabout_acc(df, m, 'rulesv5_rag_t10_improved_context_sum_label_spatial') for m in models]
    rag15 = [get_turnabout_acc(df, m, 'rulesv5_rag_t15_improved_context_sum_label_spatial') for m in models]
    
    bars1 = ax.bar(x - 2*width, b0, width, label='B0', color=METHOD_COLORS['B0'], edgecolor='white', linewidth=0.8)
    bars2 = ax.bar(x - width, rc, width, label='RC-Static', color=METHOD_COLORS['RC-Static'], edgecolor='white', linewidth=0.8)
    bars3 = ax.bar(x, rag5, width, label='RC-RAG@5', color=METHOD_COLORS['RC-RAG@5'], edgecolor='white', linewidth=0.8)
    bars4 = ax.bar(x + width, rag10, width, label='RC-RAG@10', color=METHOD_COLORS['RC-RAG@10'], edgecolor='white', linewidth=0.8)
    bars5 = ax.bar(x + 2*width, rag15, width, label='RC-RAG@15', color=METHOD_COLORS['RC-RAG@15'], edgecolor='white', linewidth=0.8)
    
    style_axes(ax, 'Turnabout: B0 vs RC-Static vs RC-RAG@k')
    ax.set_xticks(x)
    ax.set_xticklabels(display_names, rotation=45, ha='right', fontsize=14)
    ax.legend(frameon=True, fancybox=False, edgecolor='#cccccc', fontsize=10)
    all_vals = b0 + rc + rag5 + rag10 + rag15
    ax.set_ylim(0, max(all_vals) * 1.15 if all_vals else 1)
    for bars in [bars1, bars2, bars3, bars4, bars5]:
        add_value_labels(ax, bars)
    plt.tight_layout()
    save_plot(output_dirs, 'turnabout_rc_rag_comparison_meeting20.png')
    print("   - turnabout_rc_rag_comparison_meeting20.png")
    
    # --- Plot 4: PA Comparison ---
    fig, ax = plt.subplots(figsize=(16, 7))
    pa5 = [get_turnabout_acc(df, m, 'prop_generated_p5_improved_v2_context_sum_label_spatial') for m in models]
    pa10 = [get_turnabout_acc(df, m, 'prop_generated_p10_improved_v2_context_sum_label_spatial') for m in models]
    pa15 = [get_turnabout_acc(df, m, 'prop_generated_p15_improved_v2_context_sum_label_spatial') for m in models]
    
    bars1 = ax.bar(x - 2*width, b0, width, label='B0', color=METHOD_COLORS['B0'], edgecolor='white', linewidth=0.8)
    bars2 = ax.bar(x - width, rc, width, label='RC-Static', color=METHOD_COLORS['RC-Static'], edgecolor='white', linewidth=0.8)
    bars3 = ax.bar(x, pa5, width, label='PA@5', color=METHOD_COLORS['PA@5'], edgecolor='white', linewidth=0.8)
    bars4 = ax.bar(x + width, pa10, width, label='PA@10', color=METHOD_COLORS['PA@10'], edgecolor='white', linewidth=0.8)
    bars5 = ax.bar(x + 2*width, pa15, width, label='PA@15', color=METHOD_COLORS['PA@15'], edgecolor='white', linewidth=0.8)
    
    style_axes(ax, 'Turnabout: B0 vs RC-Static vs PA@p')
    ax.set_xticks(x)
    ax.set_xticklabels(display_names, rotation=45, ha='right', fontsize=14)
    ax.legend(frameon=True, fancybox=False, edgecolor='#cccccc', fontsize=10)
    all_vals = b0 + rc + pa5 + pa10 + pa15
    ax.set_ylim(0, max(all_vals) * 1.15 if all_vals else 1)
    for bars in [bars1, bars2, bars3, bars4, bars5]:
        add_value_labels(ax, bars)
    plt.tight_layout()
    save_plot(output_dirs, 'turnabout_pa_comparison_meeting20.png')
    print("   - turnabout_pa_comparison_meeting20.png")
    
    # --- Plot 5: RC+PA-RAG Comparison ---
    fig, ax = plt.subplots(figsize=(16, 7))
    width = 0.12
    rp5 = [get_turnabout_acc(df, m, 'rulesv5_rag_prop_t15_p5_improved_v2_context_sum_label_spatial') for m in models]
    rp10 = [get_turnabout_acc(df, m, 'rulesv5_rag_prop_t15_p10_improved_v2_context_sum_label_spatial') for m in models]
    rp15 = [get_turnabout_acc(df, m, 'rulesv5_rag_prop_t15_p15_improved_v2_context_sum_label_spatial') for m in models]
    
    bars1 = ax.bar(x - 2*width, b0, width, label='B0', color=METHOD_COLORS['B0'], edgecolor='white', linewidth=0.8)
    bars2 = ax.bar(x - width, rc, width, label='RC-Static', color=METHOD_COLORS['RC-Static'], edgecolor='white', linewidth=0.8)
    bars3 = ax.bar(x, rp5, width, label='RC+PA-RAG@(15,5)', color=METHOD_COLORS['RC+PA-RAG@(15,5)'], edgecolor='white', linewidth=0.8)
    bars4 = ax.bar(x + width, rp10, width, label='RC+PA-RAG@(15,10)', color=METHOD_COLORS['RC+PA-RAG@(15,10)'], edgecolor='white', linewidth=0.8)
    bars5 = ax.bar(x + 2*width, rp15, width, label='RC+PA-RAG@(15,15)', color=METHOD_COLORS['RC+PA-RAG@(15,15)'], edgecolor='white', linewidth=0.8)
    
    style_axes(ax, 'Turnabout: B0 vs RC-Static vs RC+PA-RAG@(15,p)')
    ax.set_xticks(x)
    ax.set_xticklabels(display_names, rotation=45, ha='right', fontsize=14)
    ax.legend(frameon=True, fancybox=False, edgecolor='#cccccc', fontsize=10)
    all_vals = b0 + rc + rp5 + rp10 + rp15
    ax.set_ylim(0, max(all_vals) * 1.15 if all_vals else 1)
    for bars in [bars1, bars2, bars3, bars4, bars5]:
        add_value_labels(ax, bars)
    plt.tight_layout()
    save_plot(output_dirs, 'turnabout_rc_pa_rag_comparison_meeting20.png')
    print("   - turnabout_rc_pa_rag_comparison_meeting20.png")
    
    # --- Plot 6: AR Comparison ---
    fig, ax = plt.subplots(figsize=(16, 7))
    width = 0.15
    ar5 = [get_turnabout_acc(df, m, 'rules_generated_r5_improved_v2_context_sum_label_spatial') for m in models]
    ar10 = [get_turnabout_acc(df, m, 'rules_generated_r10_improved_v2_context_sum_label_spatial') for m in models]
    ar15 = [get_turnabout_acc(df, m, 'rules_generated_r15_improved_v2_context_sum_label_spatial') for m in models]
    
    bars1 = ax.bar(x - 2*width, b0, width, label='B0', color=METHOD_COLORS['B0'], edgecolor='white', linewidth=0.8)
    bars2 = ax.bar(x - width, rc, width, label='RC-Static', color=METHOD_COLORS['RC-Static'], edgecolor='white', linewidth=0.8)
    bars3 = ax.bar(x, ar5, width, label='AR@5', color=METHOD_COLORS['AR@5'], edgecolor='white', linewidth=0.8)
    bars4 = ax.bar(x + width, ar10, width, label='AR@10', color=METHOD_COLORS['AR@10'], edgecolor='white', linewidth=0.8)
    bars5 = ax.bar(x + 2*width, ar15, width, label='AR@15', color=METHOD_COLORS['AR@15'], edgecolor='white', linewidth=0.8)
    
    style_axes(ax, 'Turnabout: B0 vs RC-Static vs AR@k')
    ax.set_xticks(x)
    ax.set_xticklabels(display_names, rotation=45, ha='right', fontsize=14)
    ax.legend(frameon=True, fancybox=False, edgecolor='#cccccc', fontsize=10)
    all_vals = b0 + rc + ar5 + ar10 + ar15
    ax.set_ylim(0, max(all_vals) * 1.15 if all_vals else 1)
    for bars in [bars1, bars2, bars3, bars4, bars5]:
        add_value_labels(ax, bars)
    plt.tight_layout()
    save_plot(output_dirs, 'turnabout_ar_comparison_meeting20.png')
    print("   - turnabout_ar_comparison_meeting20.png")
    
    # --- Plot 7: B0 vs Best ---
    fig, ax = plt.subplots(figsize=(12, 7))
    width = 0.35
    best_vals, best_labels = [], []
    for m in models:
        model_runs = df[df['model_config'].str.startswith(m + '_prompt_')]
        # Exclude oracle/gold runs (reasoning_props = gold propositions)
        model_runs = model_runs[~model_runs['model_config'].str.contains('reasoning_props|gold', na=False)]
        if model_runs.empty:
            best_vals.append(0.0)
            best_labels.append('')
            continue
        best_run = model_runs.loc[model_runs['overall_accuracy'].idxmax()]
        best_vals.append(float(best_run['overall_accuracy']))
        frag = best_run['model_config'].split('_prompt_', 1)[-1]
        frag = frag.replace('_context_sum_label_spatial_reasoning_props', '')
        frag = frag.replace('_context_sum_label_spatial', '')
        frag = frag.replace('_improved_v2', '').replace('_improved', '')
        best_labels.append(map_prompt_to_label(frag))
    
    bars1 = ax.bar(x - width/2, b0, width, label='B0', color=METHOD_COLORS['B0'], edgecolor='white', linewidth=0.8)
    bars2 = ax.bar(x + width/2, best_vals, width, label='Best System', color=METHOD_COLORS['Best System'], edgecolor='white', linewidth=0.8)
    
    style_axes(ax, 'Turnabout: B0 vs Best System per Model')
    ax.set_xticks(x)
    ax.set_xticklabels(display_names, rotation=45, ha='right', fontsize=14)
    ax.legend(frameon=True, fancybox=False, edgecolor='#cccccc', fontsize=10)
    all_vals = b0 + best_vals
    ax.set_ylim(0, max(all_vals) * 1.15 if all_vals else 1)
    add_value_labels(ax, bars1)
    add_value_labels(ax, bars2)
    # Annotate best system names
    for i, lbl in enumerate(best_labels):
        if lbl:
            ax.text(i + width/2, best_vals[i] - 0.02, lbl, ha='center', va='top',
                    fontsize=12, rotation=90, color='white', fontweight='bold')
    plt.tight_layout()
    save_plot(output_dirs, 'turnabout_b0_vs_best_meeting20.png')
    print("   - turnabout_b0_vs_best_meeting20.png")


# =============================================================================
# SPARTUN PLOTS
# =============================================================================

def get_spartun_acc(df: pd.DataFrame, model: str, prompt_fragment: str) -> float:
    """Get accuracy for a SPARTUN model+prompt combination."""
    pat = f"{model}_prompt_{prompt_fragment}"
    m = df[df['model_prompt'] == pat]
    return float(m.iloc[0]['overall_accuracy']) if not m.empty else 0.0


def generate_spartun_plots(df: pd.DataFrame, output_dirs: list):
    """Generate all SPARTUN plots."""
    print("\nGenerating SPARTUN plots...")
    
    all_models = sorted(set(m.split('_prompt_')[0] for m in df['model_prompt']))
    models = [m for m in all_models if get_spartun_acc(df, m, 'base') > 0]
    display_names = [shorten_model_name(m) for m in models]
    
    print(f"   Models: {display_names}")
    
    x = np.arange(len(models))
    base_vals = [get_spartun_acc(df, m, 'base') for m in models]
    rs_vals = [get_spartun_acc(df, m, 'rulesv5_improved') for m in models]
    
    # --- Plot 1: Base vs Gold Rules ---
    fig, ax = plt.subplots(figsize=(12, 6))
    gold_vals = [get_spartun_acc(df, m, 'gold_rules_improved') for m in models]
    width = 0.35
    
    bars1 = ax.bar(x - width/2, base_vals, width, label='B0', color=METHOD_COLORS['Base'], edgecolor='white', linewidth=0.8)
    bars2 = ax.bar(x + width/2, gold_vals, width, label='Gold Rules', color=METHOD_COLORS['Gold Rules'], edgecolor='white', linewidth=0.8)
    
    style_axes(ax, 'SpaRTUN: B0 vs Gold Rules (Oracle)')
    ax.set_xticks(x)
    ax.set_xticklabels(display_names, rotation=45, ha='right', fontsize=14)
    ax.legend(frameon=True, fancybox=False, edgecolor='#cccccc', fontsize=10)
    all_vals = base_vals + gold_vals
    ax.set_ylim(0, max(all_vals) * 1.15 if all_vals else 1)
    add_value_labels(ax, bars1)
    add_value_labels(ax, bars2)
    plt.tight_layout()
    save_plot(output_dirs, 'spartun_base_vs_gold_rules_meeting20.png')
    print("   - spartun_base_vs_gold_rules_meeting20.png")
    
    # --- Plot 2: Base vs RC-Static vs RC-RAG@10 ---
    fig, ax = plt.subplots(figsize=(14, 7))
    rag10 = [get_spartun_acc(df, m, 'rulesv5_rag_t10_improved') for m in models]
    width = 0.25
    
    bars1 = ax.bar(x - width, base_vals, width, label='B0', color=METHOD_COLORS['Base'], edgecolor='white', linewidth=0.8)
    bars2 = ax.bar(x, rs_vals, width, label='RC-Static', color=METHOD_COLORS['RC-Static'], edgecolor='white', linewidth=0.8)
    bars3 = ax.bar(x + width, rag10, width, label='RC-RAG@10', color=METHOD_COLORS['RC-RAG@10'], edgecolor='white', linewidth=0.8)
    
    style_axes(ax, 'SpaRTUN: B0 vs RC-Static vs RC-RAG@10')
    ax.set_xticks(x)
    ax.set_xticklabels(display_names, rotation=45, ha='right', fontsize=14)
    ax.legend(frameon=True, fancybox=False, edgecolor='#cccccc', fontsize=10)
    all_vals = base_vals + rs_vals + rag10
    ax.set_ylim(0, max(all_vals) * 1.15 if all_vals else 1)
    for bars in [bars1, bars2, bars3]:
        add_value_labels(ax, bars)
    plt.tight_layout()
    save_plot(output_dirs, 'spartun_base_rc_static_rag_meeting20.png')
    print("   - spartun_base_rc_static_rag_meeting20.png")
    
    # --- Plot 3: Base vs RC-Static vs PA@10 ---
    fig, ax = plt.subplots(figsize=(14, 7))
    pa10 = [get_spartun_acc(df, m, 'prop_generated_p10_improved_v2') for m in models]
    
    bars1 = ax.bar(x - width, base_vals, width, label='B0', color=METHOD_COLORS['Base'], edgecolor='white', linewidth=0.8)
    bars2 = ax.bar(x, rs_vals, width, label='RC-Static', color=METHOD_COLORS['RC-Static'], edgecolor='white', linewidth=0.8)
    bars3 = ax.bar(x + width, pa10, width, label='PA@10', color=METHOD_COLORS['PA@10'], edgecolor='white', linewidth=0.8)
    
    style_axes(ax, 'SpaRTUN: B0 vs RC-Static vs PA@10')
    ax.set_xticks(x)
    ax.set_xticklabels(display_names, rotation=45, ha='right', fontsize=14)
    ax.legend(frameon=True, fancybox=False, edgecolor='#cccccc', fontsize=10)
    all_vals = base_vals + rs_vals + pa10
    ax.set_ylim(0, max(all_vals) * 1.15 if all_vals else 1)
    for bars in [bars1, bars2, bars3]:
        add_value_labels(ax, bars)
    plt.tight_layout()
    save_plot(output_dirs, 'spartun_base_rc_static_pa_meeting20.png')
    print("   - spartun_base_rc_static_pa_meeting20.png")
    
    # --- Plot 4: Base vs RC-Static vs RC+PA-RAG@(10,10) ---
    fig, ax = plt.subplots(figsize=(14, 7))
    rp1010 = [get_spartun_acc(df, m, 'rag_prop_generated_t10_p10_improved_v2') for m in models]
    
    bars1 = ax.bar(x - width, base_vals, width, label='B0', color=METHOD_COLORS['Base'], edgecolor='white', linewidth=0.8)
    bars2 = ax.bar(x, rs_vals, width, label='RC-Static', color=METHOD_COLORS['RC-Static'], edgecolor='white', linewidth=0.8)
    bars3 = ax.bar(x + width, rp1010, width, label='RC+PA-RAG@(10,10)', color=METHOD_COLORS['RC+PA-RAG@(10,10)'], edgecolor='white', linewidth=0.8)
    
    style_axes(ax, 'SpaRTUN: B0 vs RC-Static vs RC+PA-RAG@(10,10)')
    ax.set_xticks(x)
    ax.set_xticklabels(display_names, rotation=45, ha='right', fontsize=14)
    ax.legend(frameon=True, fancybox=False, edgecolor='#cccccc', fontsize=10)
    all_vals = base_vals + rs_vals + rp1010
    ax.set_ylim(0, max(all_vals) * 1.15 if all_vals else 1)
    for bars in [bars1, bars2, bars3]:
        add_value_labels(ax, bars)
    plt.tight_layout()
    save_plot(output_dirs, 'spartun_base_rc_static_rag_pa_meeting20.png')
    print("   - spartun_base_rc_static_rag_pa_meeting20.png")
    
    # --- Plot 5: Base vs AR@10 ---
    fig, ax = plt.subplots(figsize=(12, 6))
    ar10 = [get_spartun_acc(df, m, 'rules_generated_r10_improved_v2') for m in models]
    width = 0.35
    
    bars1 = ax.bar(x - width/2, base_vals, width, label='B0', color=METHOD_COLORS['Base'], edgecolor='white', linewidth=0.8)
    bars2 = ax.bar(x + width/2, ar10, width, label='AR@10', color=METHOD_COLORS['AR@10'], edgecolor='white', linewidth=0.8)
    
    style_axes(ax, 'SpaRTUN: B0 vs AR@10 (Auto-Generated Rules)')
    ax.set_xticks(x)
    ax.set_xticklabels(display_names, rotation=45, ha='right', fontsize=14)
    ax.legend(frameon=True, fancybox=False, edgecolor='#cccccc', fontsize=10)
    all_vals = base_vals + ar10
    ax.set_ylim(0, max(all_vals) * 1.15 if all_vals else 1)
    add_value_labels(ax, bars1)
    add_value_labels(ax, bars2)
    plt.tight_layout()
    save_plot(output_dirs, 'spartun_base_vs_ar_meeting20.png')
    print("   - spartun_base_vs_ar_meeting20.png")
    
    # --- Plot 6: Base vs Best System ---
    fig, ax = plt.subplots(figsize=(12, 7))
    best_vals, best_labels = [], []
    for m in models:
        mdf = df[df['model_prompt'].str.startswith(m + '_prompt_')]
        mdf = mdf[~mdf['model_prompt'].str.contains('gold')]
        if mdf.empty:
            best_vals.append(0.0)
            best_labels.append('')
            continue
        best_row = mdf.loc[mdf['overall_accuracy'].idxmax()]
        best_vals.append(float(best_row['overall_accuracy']))
        frag = best_row['model_prompt'].split('_prompt_', 1)[-1]
        frag = frag.replace('_improved_v2', '').replace('_improved', '')
        best_labels.append(map_prompt_to_label(frag))
    
    bars1 = ax.bar(x - width/2, base_vals, width, label='B0', color=METHOD_COLORS['Base'], edgecolor='white', linewidth=0.8)
    bars2 = ax.bar(x + width/2, best_vals, width, label='Best System', color=METHOD_COLORS['Best System'], edgecolor='white', linewidth=0.8)
    
    style_axes(ax, 'SpaRTUN: B0 vs Best System per Model')
    ax.set_xticks(x)
    ax.set_xticklabels(display_names, rotation=45, ha='right', fontsize=14)
    ax.legend(frameon=True, fancybox=False, edgecolor='#cccccc', fontsize=10)
    all_vals = base_vals + best_vals
    ax.set_ylim(0, max(all_vals) * 1.15 if all_vals else 1)
    add_value_labels(ax, bars1)
    add_value_labels(ax, bars2)
    # Annotate best system names (now using map_prompt_to_label for consistency)
    for i, lbl in enumerate(best_labels):
        if lbl:
            ax.text(i + width/2, best_vals[i] - 0.02, lbl, ha='center', va='top',
                    fontsize=12, rotation=90, color='white', fontweight='bold')
    plt.tight_layout()
    save_plot(output_dirs, 'spartun_base_vs_best_meeting20.png')
    print("   - spartun_base_vs_best_meeting20.png")


def main():
    src_dir = Path(__file__).resolve().parent
    project_root = src_dir.parent
    
    eval_turnabout = project_root / 'eval'
    eval_spartun = project_root / 'eval_spurtun'
    latex_dir = project_root / 'LATEX'
    
    turnabout_csv = eval_turnabout / 'turnabout_evaluation_summary.csv'
    spartun_csv = eval_spartun / 'spartun_evaluation_summary.csv'
    
    print("="*60)
    print("MEETING 20 PLOT GENERATION")
    print("="*60)
    
    if turnabout_csv.exists():
        df_turnabout = pd.read_csv(turnabout_csv)
        print(f"\nLoaded {len(df_turnabout)} Turnabout configurations")
        output_dirs = [eval_turnabout, latex_dir]
        generate_turnabout_plots(df_turnabout, output_dirs)
    else:
        print(f"\nTurnabout CSV not found: {turnabout_csv}")
        print("   Run: python extract_all_results.py --turnabout")
    
    if spartun_csv.exists():
        df_spartun = pd.read_csv(spartun_csv)
        print(f"\nLoaded {len(df_spartun)} SPARTUN configurations")
        output_dirs = [eval_spartun, latex_dir]
        generate_spartun_plots(df_spartun, output_dirs)
    else:
        print(f"\nSPARTUN CSV not found: {spartun_csv}")
        print("   Run: python extract_all_results.py --spartun")
    
    print("\n" + "="*60)
    print("MEETING 20 PLOT GENERATION COMPLETE")
    print("="*60)
    print(f"\nOutputs saved to:")
    print(f"   - {eval_turnabout}")
    print(f"   - {eval_spartun}")
    print(f"   - {latex_dir}")


if __name__ == '__main__':
    main()
