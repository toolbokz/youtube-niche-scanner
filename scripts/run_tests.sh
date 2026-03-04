#!/usr/bin/env bash
# Run the test suite
set -e

echo "Running Growth Strategist tests..."
python -m pytest tests/ -v --tb=short -x

echo ""
echo "All tests passed!"
