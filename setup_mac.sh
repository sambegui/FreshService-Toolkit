#!/bin/bash
# Setup script for macOS

echo "FreshService User Management Toolkit - Setup for macOS"
echo "===================================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed or not in PATH."
    echo "Please install Python 3.6 or higher from https://www.python.org/downloads/"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip

# Install required packages with error handling
echo "Installing requests..."
pip install requests || echo "Warning: Could not install requests package"

echo "Installing python-Levenshtein-wheels (macOS compatible)..."
pip install python-Levenshtein-wheels || { 
    echo "Warning: Could not install python-Levenshtein-wheels"
    echo "Trying alternate Levenshtein package..."
    pip install python-Levenshtein || {
        echo "Warning: Could not install python-Levenshtein"
        echo "Trying basic Levenshtein package..."
        pip install Levenshtein || echo "Warning: Could not install any Levenshtein package"
    }
}

echo "Installing other dependencies..."
pip install fuzzywuzzy colorama tabulate keyring || echo "Warning: Some dependencies could not be installed"

# Check if requirements.txt exists and install from it
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt || echo "Warning: Some dependencies from requirements.txt could not be installed"
fi

# Create run script if it doesn't exist
if [ ! -f "run_toolkit.sh" ]; then
    echo "Creating run script..."
    echo '#!/bin/bash
source venv/bin/activate
python3 freshservice_toolkit.py "$@"
' > run_toolkit.sh
    chmod +x run_toolkit.sh
fi

echo "Setup complete! Run the toolkit with:"
echo "./run_toolkit.sh"
echo ""
echo "If you encounter any issues, you may need to manually install dependencies:"
echo "source venv/bin/activate"
echo "pip install requests"
echo "pip install python-Levenshtein-wheels"
echo ""
echo "Installation complete!" 