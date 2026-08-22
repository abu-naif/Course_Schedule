#!/usr/bin/env bash
# Schedule Combinator Launcher (macOS / Linux)
cd "$(dirname "$0")"

if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "Error: Python 3 is not installed or not added to PATH."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "Setting up virtual environment..."
    $PYTHON -m venv venv
    ./venv/bin/pip install -r requirements.txt
fi

echo "Starting Schedule Combinator..."
./venv/bin/python schedule_gui.py
