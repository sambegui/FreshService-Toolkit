@echo off
echo FreshService User Management Toolkit - Launcher
echo =============================================

REM Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.6 or higher from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if venv exists, create if not
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate the virtual environment and run the script
echo Starting the toolkit...
call venv\Scripts\activate.bat
python freshservice_toolkit.py %*
pause 