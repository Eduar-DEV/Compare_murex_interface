#!/bin/bash

# Configuration
DIR_A="./tests/batch_data/server_a"
DIR_B="./tests/batch_data/server_b"
OUTPUT_DIR="./results/batch_$(date +%Y%m%d_%H%M%S)"
KEYS="id"  # Fallback key if config doesn't match
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
eval $CMD
