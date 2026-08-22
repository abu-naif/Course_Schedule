@echo off
cd /d "%~dp0"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python 3 is not installed or not added to PATH.
    echo Please download Python from https://www.python.org and check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

if not exist venv (
    echo Setting up Python virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
)

echo Starting Schedule Combinator...
venv\Scripts\python.exe schedule_gui.py
