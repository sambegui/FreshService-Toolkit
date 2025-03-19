# PowerShell setup script for FreshService Toolkit

# Check if script is running as admin, which might be needed for some systems
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "This script is not running as Administrator. If you encounter permission issues, try running as Administrator."
}

# Check if Python is installed
try {
    $pythonVersion = (python --version 2>&1).ToString()
    Write-Host "Found $pythonVersion"
} catch {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.6+ and try again."
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Green
    python -m venv venv
    if (-not $?) {
        Write-Error "Failed to create virtual environment. Please check your Python installation."
        exit 1
    }
}

# Activate virtual environment and install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Green
& .\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# Create run script if it doesn't exist
if (-not (Test-Path "run_toolkit.ps1")) {
    Write-Host "Creating run script..." -ForegroundColor Green
    @"
# PowerShell script to run FreshService Toolkit
& .\venv\Scripts\Activate.ps1
python freshservice_toolkit.py
"@ | Out-File -FilePath "run_toolkit.ps1" -Encoding utf8
}

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "To run the toolkit:" -ForegroundColor Yellow
Write-Host "  PowerShell: .\run_toolkit.ps1" -ForegroundColor Cyan
Write-Host "  Command Prompt: run_toolkit.bat" -ForegroundColor Cyan
Write-Host "`nNote: If you have execution policy restrictions, you may need to run:" -ForegroundColor Yellow
Write-Host "  Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process" -ForegroundColor Cyan 