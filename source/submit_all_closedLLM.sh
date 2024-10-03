
# Set variables
MODEL="gpt-4o"
PROMPT="default"
METRIC="accuracy"
CASE_DIR="../case_data/generated/parsed"

echo "Starting batch evaluation for all cases"
echo "Model used: $MODEL, Prompt: $PROMPT"

# Initialize variables for average calculation
total_accuracy=0
case_count=0

# Loop through all JSON files in the specified directory
for case_file in "$CASE_DIR"/*.json; do
    # Extract the case name (filename without path and extension)
    case_name=$(basename "$case_file" .json)

    echo "Processing case: $case_name"
    # echo "Evaluating case: $case_name"

    # Run the simulation
    python simulator_closedLLM.py --model $MODEL --prompt $PROMPT --case "$case_name"

    # Run the evaluation and capture the output
    python evaluate_output_close.py --model $MODEL --prompt $PROMPT --case "$case_name" --metric $METRIC
    echo "----------------------------------------"
done

echo "Batch evaluation complete"