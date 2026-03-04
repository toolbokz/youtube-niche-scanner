#!/usr/bin/env bash
# Quick setup script for Growth Strategist
set -e

echo "=== Growth Strategist Setup ==="

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create data directories
mkdir -p data/cache data/reports data/db

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Activate the virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "Run analysis:"
echo "  python main.py analyze \"ai tools\" \"passive income\" \"health tips\""
echo ""
echo "Start API server:"
echo "  python main.py serve"
echo ""
echo "Run tests:"
echo "  pytest tests/ -v"
