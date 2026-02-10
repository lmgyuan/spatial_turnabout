#!/usr/bin/env python3
"""
Combined script to extract evaluation metrics from Turnabout and/or SPARTUN reports.

Usage:
    python extract_all_results.py              # Extract both (default)
    python extract_all_results.py --turnabout  # Extract Turnabout only
    python extract_all_results.py --spartun    # Extract SPARTUN only

Outputs:
    eval/turnabout_evaluation_summary.csv
    eval_spurtun/spartun_evaluation_summary.csv
"""

import argparse
import json
import os
import glob
from pathlib import Path
import pandas as pd


def extract_turnabout_metrics(file_path: str) -> dict:
    """Extract key metrics from a Turnabout JSON report file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract filename and normalize
        filename = Path(file_path).stem
        # Remove provider prefixes
        for prefix in ['nebius-', 'deepinfra-', 'openai-']:
            if filename.startswith(prefix):
                filename = filename[len(prefix):]
                break
        # Remove _report suffix
        if filename.endswith('_report'):
            filename = filename[:-7]
        
        metrics = {
            'model_config': filename,
            'overall_accuracy': data.get('overall_accuracy', 0),
            'overall_evidence_accuracy': data.get('overall_evidence_accuracy', 0),
            'overall_testimony_accuracy': data.get('overall_testimony_accuracy', 0),
            'overall_correct': data.get('overall_correct', 0),
            'overall_evidence_correct': data.get('overall_evidence_correct', 0),
            'overall_testimony_correct': data.get('overall_testimony_correct', 0),
            'overall_total': data.get('overall_total', 0),
            'average_reasoning_tokens': data.get('average_reasoning_tokens', 0)
        }
        
        # Extract category accuracies
        categories_accuracy = data.get('categories_accuracy', {})
        for category in ['spatial', 'causal', 'physical', 'temporal', 'behavioral', 'numerical']:
            if category in categories_accuracy:
                metrics[f'{category}_accuracy'] = categories_accuracy[category].get('accuracy', 0)
                metrics[f'{category}_total'] = categories_accuracy[category].get('total', 0)
            else:
                metrics[f'{category}_accuracy'] = 0
                metrics[f'{category}_total'] = 0
        
        return metrics
    
    except Exception as e:
        print(f"  Error processing {file_path}: {e}")
        return None


def extract_spartun_metrics(file_path: str) -> dict:
    """Extract key metrics from a SPARTUN JSON report file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Derive config name from filename
        filename = Path(file_path).stem
        # Remove provider prefixes
        for prefix in ['nebius-', 'deepinfra-', 'openai-']:
            if filename.startswith(prefix):
                filename = filename[len(prefix):]
                break
        # Remove _report suffix
        if filename.endswith('_report'):
            filename = filename[:-7]
        
        metrics = {
            'model_prompt': filename,
            'overall_total_questions': data.get('overall_total_questions', 0),
            'overall_correct': data.get('overall_correct', 0),
            'overall_accuracy': data.get('overall_accuracy', 0.0),
        }
        return metrics
    
    except Exception as e:
        print(f"  Error processing {file_path}: {e}")
        return None


def process_turnabout(eval_dir: Path) -> None:
    """Process all Turnabout report files and generate CSV."""
    print("\n" + "="*60)
    print("📊 TURNABOUT EXTRACTION")
    print("="*60)
    
    # Find all report files (any provider)
    pattern = str(eval_dir / '*_report.json')
    report_files = glob.glob(pattern)
    
    # Filter out unwanted files
    # Note: 'reasoning_props' is allowed (ground truth props), but other reasoning types are excluded
    excluded_patterns = ['llama-8b', 'oss-20b', '_et_']
    filtered_files = [
        f for f in report_files 
        if not any(excl in f for excl in excluded_patterns)
    ]
    
    print(f"Found {len(filtered_files)} Turnabout report files")
    
    all_metrics = []
    for file_path in sorted(filtered_files):
        print(f"  Processing: {os.path.basename(file_path)}")
        metrics = extract_turnabout_metrics(file_path)
        if metrics:
            all_metrics.append(metrics)
    
    if not all_metrics:
        print("❌ No valid Turnabout metrics extracted!")
        return
    
    df = pd.DataFrame(all_metrics)
    
    # Order columns
    primary_cols = [
        'model_config', 
        'overall_accuracy', 
        'overall_evidence_accuracy', 
        'overall_testimony_accuracy',
        'overall_correct',
        'overall_evidence_correct', 
        'overall_testimony_correct',
        'overall_total',
        'average_reasoning_tokens'
    ]
    category_cols = [col for col in df.columns if col.endswith('_accuracy') and col not in primary_cols]
    total_cols = [col for col in df.columns if col.endswith('_total') and col != 'overall_total']
    ordered_cols = primary_cols + sorted(category_cols) + sorted(total_cols)
    df = df[ordered_cols]
    df = df.sort_values('model_config')
    
    # Save CSV
    output_file = eval_dir / 'turnabout_evaluation_summary.csv'
    df.to_csv(output_file, index=False, float_format='%.4f')
    
    print(f"\n✅ Turnabout results saved to: {output_file}")
    print(f"📊 Summary: {len(df)} configurations analyzed")
    print(f"\n📈 Overall Accuracy Statistics:")
    print(f"   Mean: {df['overall_accuracy'].mean():.4f}")
    print(f"   Min:  {df['overall_accuracy'].min():.4f}")
    print(f"   Max:  {df['overall_accuracy'].max():.4f}")
    
    # Show unique models
    models = sorted(set(cfg.split('_prompt_')[0] for cfg in df['model_config']))
    print(f"\n🤖 Models found: {models}")


def process_spartun(eval_dir: Path) -> None:
    """Process all SPARTUN report files and generate CSV."""
    print("\n" + "="*60)
    print("📊 SPARTUN EXTRACTION")
    print("="*60)
    
    pattern = str(eval_dir / '*_report.json')
    report_files = glob.glob(pattern)
    
    print(f"Found {len(report_files)} SPARTUN report files")
    
    all_metrics = []
    for file_path in sorted(report_files):
        print(f"  Processing: {os.path.basename(file_path)}")
        metrics = extract_spartun_metrics(file_path)
        if metrics:
            all_metrics.append(metrics)
    
    if not all_metrics:
        print("❌ No valid SPARTUN metrics extracted!")
        return
    
    df = pd.DataFrame(all_metrics)
    cols = ['model_prompt', 'overall_accuracy', 'overall_correct', 'overall_total_questions']
    df = df[cols]
    df = df.sort_values('model_prompt')
    
    # Save CSV
    output_file = eval_dir / 'spartun_evaluation_summary.csv'
    df.to_csv(output_file, index=False, float_format='%.4f')
    
    print(f"\n✅ SPARTUN results saved to: {output_file}")
    print(f"📊 Summary: {len(df)} configurations analyzed")
    print(f"\n📈 Overall Accuracy Statistics:")
    print(f"   Mean: {df['overall_accuracy'].mean():.4f}")
    print(f"   Min:  {df['overall_accuracy'].min():.4f}")
    print(f"   Max:  {df['overall_accuracy'].max():.4f}")
    
    # Show unique models
    models = sorted(set(cfg.split('_prompt_')[0] for cfg in df['model_prompt']))
    print(f"\n🤖 Models found: {models}")


def main():
    parser = argparse.ArgumentParser(
        description='Extract evaluation metrics from Turnabout and/or SPARTUN reports.'
    )
    parser.add_argument('--turnabout', action='store_true', 
                        help='Extract Turnabout results only')
    parser.add_argument('--spartun', action='store_true', 
                        help='Extract SPARTUN results only')
    args = parser.parse_args()
    
    # If neither flag specified, do both
    do_turnabout = args.turnabout or (not args.turnabout and not args.spartun)
    do_spartun = args.spartun or (not args.turnabout and not args.spartun)
    
    # Resolve directories
    src_dir = Path(__file__).resolve().parent
    project_root = src_dir.parent
    eval_turnabout = project_root / 'eval'
    eval_spartun = project_root / 'eval_spurtun'
    
    if do_turnabout:
        if eval_turnabout.exists():
            process_turnabout(eval_turnabout)
        else:
            print(f"❌ Turnabout eval directory not found: {eval_turnabout}")
    
    if do_spartun:
        if eval_spartun.exists():
            process_spartun(eval_spartun)
        else:
            print(f"❌ SPARTUN eval directory not found: {eval_spartun}")
    
    print("\n" + "="*60)
    print("✅ EXTRACTION COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()

