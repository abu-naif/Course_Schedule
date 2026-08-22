#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "==================================================="
echo "    BracU Course Combinator - Web App Launcher     "
echo "==================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed."
    echo "Please install Python 3.8 or higher."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    echo "Installing required packages..."
    ./venv/bin/pip install -r requirements.txt
fi

echo "Starting Course Combinator Web Server..."
echo "Web App URL: http://localhost:8000"

# Auto-open default browser
if command -v open &> /dev/null; then
    (sleep 1 && open http://localhost:8000) &
elif command -v xdg-open &> /dev/null; then
    (sleep 1 && xdg-open http://localhost:8000) &
fi

./venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
