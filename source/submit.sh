#!/bin/bash
#
#SBATCH --partition=p_nlp
#SBATCH --nodelist=nlpgpu04  # To ensure we run on the same node each time
#SBATCH --job-name=simulator_kani
#SBATCH --output=logs/%j.%x.log
#SBATCH --error=logs/%j.%x.log
#SBATCH --time=02:00:00  # 2 hour
#SBATCH -c 16
#SBATCH --mem=128G
#SBATCH --gpus=3
#SBATCH --constraint=48GBgpu

# Run the Python script
python simulator_closedLLM.py --model gpt-4o --prompt default --case 1-2-4_Turnabout_Sisters --cot_few_shot --log_file text_log_new_cot2
