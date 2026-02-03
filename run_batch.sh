#!/bin/bash

# Configuration
DIR_A="./tests/stress_data/server_a"
DIR_B="./tests/stress_data/server_b"
OUTPUT_DIR="./results/batch_$(date +%Y%m%d_%H%M%S)"
KEYS="id"  # Fallback key if config doesn't match
SEPARATOR="" # Default is ';' in Python if empty, can set to ',' or ';'
CONFIG="batch_config.json"
IGNORE="" 

# Ensure directories exist (or change to your actual paths)
if [ ! -d "$DIR_A" ]; then
    echo "Error: Directory A '$DIR_A' does not exist."
    exit 1
fi

echo "Starting Batch Comparison..."
echo "Source A: $DIR_A"
echo "Source B: $DIR_B"
echo "Output:   $OUTPUT_DIR"
echo "Config:   $CONFIG"
echo "-----------------------------------"

# Build Command
CMD="uv run python -m src.batch.orchestrator --dir-a \"$DIR_A\" --dir-b \"$DIR_B\" --output \"$OUTPUT_DIR\""

if [ -n "$SEPARATOR" ]; then
    CMD="$CMD --separator \"$SEPARATOR\""
fi

if [ -n "$CONFIG" ]; then
    CMD="$CMD --config \"$CONFIG\""
fi

if [ -n "$KEYS" ]; then
     # Pass keys as default/fallback
    CMD="$CMD --key \"$KEYS\""
fi

if [ -n "$IGNORE" ]; then
    CMD="$CMD --ignore-columns \"$IGNORE\""
fi

# Execute

# -----------------------------------
# Header Validation
# -----------------------------------
echo "Running Header Validation..."
VALIDATE_CMD="uv run python -m src.batch.validate_headers --dir-a \"$DIR_A\" --dir-b \"$DIR_B\" --output \"$OUTPUT_DIR\""

if [ -n "$SEPARATOR" ]; then
    VALIDATE_CMD="$VALIDATE_CMD --separator \"$SEPARATOR\""
fi

if [ -n "$CONFIG" ]; then
    VALIDATE_CMD="$VALIDATE_CMD --config \"$CONFIG\""
fi

eval $VALIDATE_CMD

# -----------------------------------
# Execute Orchestrator
# -----------------------------------
eval $CMD
