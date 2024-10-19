#!/bin/bash

# Run "conda activate turnabout-llm" before running this script

echo "Starting running closed LLM on 1-2-2_Turnabout_Sisters_Parsed2"
#echo "Model used: gpt-4o, prmopt: default"
#python simulator_closedLLM.py --model gpt-4o --prompt default --case 1-2-2_Turnabout_Sisters_Parsed2
#python evaluate_output_close.py --model gpt-4o --prompt default --case 1-2-2_Turnabout_Sisters_Parsed2 --metric accuracy

echo "Model used: gpt-4o, prmopt: default cot_few_shot: Yes"
python simulator_closedLLM.py --model gpt-4o --prompt default --case 1-2-2_Turnabout_Sisters_Parsed2 --cot_few_shot
python evaluate_output_close.py --model gpt-4o --prompt default --case 1-2-2_Turnabout_Sisters_Parsed2 --metric accuracy --cot_few_shot


