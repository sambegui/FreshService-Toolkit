@echo off
echo Setting up FreshService Toolkit for Windows...

:: Check if Python is installed
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python is not installed or not in PATH. Please install Python 3.6+.
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment and install dependencies
echo Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

:: Create run script if it doesn't exist
if not exist run_toolkit.bat (
    echo Creating run script...
    echo @echo off > run_toolkit.bat
    echo call venv\Scripts\activate.bat >> run_toolkit.bat
    echo python freshservice_toolkit.py >> run_toolkit.bat
    echo pause >> run_toolkit.bat
)

echo.
echo Setup complete! Run the toolkit with:
echo run_toolkit.bat
echo. 