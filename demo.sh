#!/bin/bash
# Quick Demo Script - Run the DAQ system in simulation mode

echo "======================================"
echo "BMW M3 DAQ System - Quick Demo"
echo "======================================"
echo ""
echo "This demo will:"
echo "1. Generate test data (60 seconds)"
echo "2. Analyze the session"
echo "3. Show you the results"
echo ""

# Check if we're in the project directory
if [ ! -f "requirements.txt" ]; then
    echo "Error: Please run this script from the bmw_m3_daq directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Installing dependencies..."
    venv/bin/pip install -q --upgrade pip
    venv/bin/pip install -q -r requirements.txt
fi

echo "Step 1: Generating 60 seconds of test data..."
echo ""
SESSION=$(venv/bin/python scripts/generate_test_data.py 60 50 | grep "Session created:" | awk '{print $3}')

if [ -z "$SESSION" ]; then
    echo "Error: Failed to generate test data"
    exit 1
fi

echo ""
echo "Step 2: Analyzing session..."
echo ""
venv/bin/python scripts/analyze_session.py "$SESSION"

echo ""
echo "======================================"
echo "Demo Complete!"
echo "======================================"
echo ""
echo "Check out the results in: $SESSION"
echo ""
echo "Files created:"
echo "  - data.csv (raw data)"
echo "  - performance_report.json (metrics)"
echo "  - data.xlsx (Excel export)"
echo "  - track.kml (GPS track for Google Earth)"
echo "  - plots/ (all visualizations)"
echo ""
echo "To view plots, open: $SESSION/plots/"
echo ""
