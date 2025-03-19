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

# Activate the virtual environment and run the script
echo "Starting the toolkit..."
source venv/bin/activate
python3 freshservice_toolkit.py "$@" 