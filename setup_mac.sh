#!/bin/bash
# Setup script for macOS

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
pip install requests fuzzywuzzy python-Levenshtein-wheels colorama

echo "Setup complete! Run the toolkit with:"
echo "./run_toolkit.sh"

# Create run script if it doesn't exist
if [ ! -f "run_toolkit.sh" ]; then
    echo "Creating run script..."
    echo '#!/bin/bash
source venv/bin/activate
python freshservice_toolkit.py
' > run_toolkit.sh
    chmod +x run_toolkit.sh
fi

echo "Installation complete!" 