#!/bin/bash

echo "FreshService User Management Toolkit - Launcher"
echo "============================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed or not in PATH."
    echo "Please install Python 3.6 or higher from https://www.python.org/downloads/"
    exit 1
fi

# Check if venv exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Verify and install critical dependencies if missing
python3 -c "import requests" 2>/dev/null || {
    echo "Installing missing 'requests' package..."
    pip install requests
}

# Check for Levenshtein package
python3 -c "import Levenshtein" 2>/dev/null || {
    echo "Installing missing 'Levenshtein' package..."
    # Try the macOS-compatible wheel first, then fallback to standard package, then basic Levenshtein
    pip install python-Levenshtein-wheels || pip install python-Levenshtein || pip install Levenshtein || {
        echo "Warning: Could not install any Levenshtein package. Some functionality may be limited."
    }
}

# Check for other important dependencies
python3 -c "import colorama" 2>/dev/null || pip install colorama
python3 -c "import tabulate" 2>/dev/null || pip install tabulate

# Run the toolkit
echo "Starting the toolkit..."
python3 freshservice_toolkit.py "$@" 

# Provide info on exit
echo ""
echo "Toolkit session ended. Run again with ./run_toolkit.sh" 