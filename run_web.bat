@echo off
cd /d "%~dp0"

echo ===================================================
echo     BracU Course Combinator - Web App Launcher
echo ===================================================
echo.

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
    echo Installing dependencies (fastapi, uvicorn, reportlab)...
    pip install -r requirements.txt
)

echo Starting Course Combinator Web Server...
echo Opening browser at http://localhost:8000 ...

start "" http://localhost:8000
venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000

if %errorlevel% neq 0 (
    echo.
    echo Web server exited with an error.
    pause
)
