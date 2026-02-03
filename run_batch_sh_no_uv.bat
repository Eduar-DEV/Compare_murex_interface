#!/bin/bash
set -euo pipefail

# -----------------------------
# Configuration
# -----------------------------
DIR_A="./tests/batch_data/server_a"
DIR_B="./tests/batch_data/server_b"
OUTPUT_DIR="./results/batch_$(date +%Y%m%d_%H%M%S)"
KEYS="id"                 # Fallback key if config doesn't match
CONFIG="batch_config.json"
IGNORE=""                 # e.g. "col1,col2"

# -----------------------------
# Move to project root (folder of this script)
# -----------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# -----------------------------
# Basic checks
# -----------------------------
if [ ! -d "$DIR_A" ]; then
  echo "Error: Directory A '$DIR_A' does not exist."
  exit 1
fi

if [ ! -d "$DIR_B" ]; then
  echo "Error: Directory B '$DIR_B' does not exist."
  exit 1
fi

if [ ! -f "src/batch/orchestrator.py" ]; then
  echo "Error: src/batch/orchestrator.py not found. Run from project root."
  exit 1
fi

# -----------------------------
# Pick Python (prefer local venv if present)
# -----------------------------
PY=""

if [ -x "./.venv/bin/python" ]; then
  PY="./.venv/bin/python"
elif [ -x "./venv/bin/python" ]; then
  PY="./venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
else
  echo "Error: Python not found (python3/python). Install Python 3 and/or activate your venv."
  exit 1
fi

# -----------------------------
# Info
# -----------------------------
echo "Starting Batch Comparison..."
echo "Python:   $($PY -c 'import sys; print(sys.executable)')"
echo "Source A: $DIR_A"
echo "Source B: $DIR_B"
echo "Output:   $OUTPUT_DIR"
echo "Config:   $CONFIG"
echo "-----------------------------------"

mkdir -p "$OUTPUT_DIR"

# -----------------------------
# Build args safely (no eval)
# -----------------------------
ARGS=( -m src.batch.orchestrator
  --dir-a "$DIR_A"
  --dir-b "$DIR_B"
  --output "$OUTPUT_DIR"
)

if [ -n "${CONFIG:-}" ]; then
  ARGS+=( --config "$CONFIG" )
fi

if [ -n "${KEYS:-}" ]; then
  ARGS+=( --key "$KEYS" )
fi

if [ -n "${IGNORE:-}" ]; then
  ARGS+=( --ignore-columns "$IGNORE" )
fi

# -----------------------------
# Execute
# -----------------------------
"$PY" "${ARGS[@]}"
