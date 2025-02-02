#!/bin/bash
#
#SBATCH --partition=p_nlp
#SBATCH --nodelist=nlpgpu04  # To ensure we run on the same node each time
#SBATCH --job-name=kani-mixtral
#SBATCH --output=logs/%j.%x.log
#SBATCH --error=logs/%j.%x.log
#SBATCH --time=01:00:00  # 1 hour
#SBATCH -c 16
#SBATCH --mem=128G
#SBATCH --gpus=3
#SBATCH --constraint=48GBgpu

# Run the Python script
srun python kani_mixtral.py --case Turnabout_Goodbyes_Parsed2 --player human
