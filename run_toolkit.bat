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

REM Activate the virtual environment and install dependencies
call venv\Scripts\activate.bat

REM Install required packages
echo Installing required packages...
pip install colorama tabulate keyring > NUL 2>&1
if %errorlevel% neq 0 (
    echo Warning: Some dependencies could not be installed automatically.
    echo The toolkit will try to run with limited functionality.
    timeout /t 3 > NUL
)

REM Run the script
echo Starting the toolkit...
python freshservice_toolkit.py %*
pause 