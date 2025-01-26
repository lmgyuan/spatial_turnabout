#!/bin/bash
#
#SBATCH --partition=p_nlp
#SBATCH --job-name=simulator_kani
#SBATCH --output=logs/%j.%x.log
#SBATCH --error=logs/%j.%x.log
#SBATCH --time=02:00:00  # 2 hour
#SBATCH -c 16
#SBATCH --mem=128G
#SBATCH --gpus=8
#SBATCH --constraint=48GBgpu

# Run the Python script
#srun python llama_simulator_closedLLM.py --model meta-llama/Llama-3.1-8B-Instruct --prompt default --case 1-2-2_Turnabout_Sisters_Parsed2
#srun python test.py
srun python simulator_closedLLM.py --model google/gemma-2-9b-it --prompt default --case 1-2-2_Turnabout_Sisters_Parsed2 --cot_few_shot
