#!/usr/bin/env python3
"""
MathForge — High-Tier Scientific & Visual Mathematics Tool

Run this file to launch the evolved calculator + grapher + calculus visualizer.

Usage:
    python launch_mathforge.py

First time:
    pip install -r requirements.txt
"""

import sys
from pathlib import Path

# Make sure we can import from the app package
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from app.main import main

if __name__ == "__main__":
    print("Starting MathForge...")
    print("  - SymPy symbolic engine loaded")
    print("  - Matplotlib visualizations ready")
    main()
