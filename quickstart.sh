#!/bin/bash
# Quick Start Guide - Getting Started with Temporal Conflict RAG

echo "=================================================="
echo "Temporal Conflict Resolution RAG - Quick Start"
echo "=================================================="
echo

# Step 1: Python Check
echo "Step 1: Checking Python installation..."
python --version
if [ $? -ne 0 ]; then
    echo "ERROR: Python not found. Please install Python 3.8+"
    exit 1
fi
echo "✓ Python found"
echo

# Step 2: Virtual Environment
echo "Step 2: Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate venv (Windows vs Unix)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi
echo "✓ Virtual environment activated"
echo

# Step 3: Install Dependencies
echo "Step 3: Installing dependencies (this may take a few minutes)..."
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi
echo "✓ Dependencies installed"
echo

# Step 4: Verify Installation
echo "Step 4: Verifying installation..."
python -c "from rag_orchestrator import TemporalConflictRAG; print('✓ RAG system imported successfully')"
if [ $? -ne 0 ]; then
    echo "ERROR: Installation verification failed"
    exit 1
fi
echo "✓ Installation verified"
echo

# Step 5: Run Tests
echo "Step 5: Running test suite (optional, takes ~1 minute)..."
echo "To run tests, execute: pytest test_rag_system.py -v"
echo

# Step 6: Launch Application
echo "Step 6: Ready to launch!"
echo
echo "To start the Streamlit application, run:"
echo "  streamlit run app.py"
echo
echo "The app will open at: http://localhost:8501"
echo
echo "=================================================="
echo "Quick Start Complete!"
echo "=================================================="
