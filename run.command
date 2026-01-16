#!/bin/bash

# Shotbuddy Launcher for macOS
# Double-click this file to launch Shotbuddy

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Change to the script directory
cd "$SCRIPT_DIR"

# Check if a virtual environment exists and activate it
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run Shotbuddy (run.py handles browser opening automatically)
python run.py
