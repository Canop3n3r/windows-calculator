#!/usr/bin/env python3
"""
MathForge — High-Tier Scientific & Visual Mathematics Tool

Official launcher for the modern MathForge application
(2D Grapher + Derivative Explorer + preserved classic calculator).

Usage (development):
    python launch_mathforge.py

First time:
    pip install -r requirements.txt

Packaged executable:
    The same launcher is the entry point for PyInstaller builds
    (see mathforge.spec and build_exe.py).
"""

from __future__ import annotations

import sys
from pathlib import Path


def _get_root() -> Path:
    """
    Determine the project root whether running from source or as a
    frozen PyInstaller executable (onedir or onefile).
    """
    if getattr(sys, "frozen", False):
        # Running inside PyInstaller bundle
        # - onedir: sys.executable lives next to the supporting files
        # - onefile: sys._MEIPASS points at the temporary extraction dir
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        return Path(sys.executable).parent
    # Normal source execution
    return Path(__file__).parent.resolve()


ROOT = _get_root()

# Ensure both the project root and the app package are importable
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Some builds place the original calculator.py at the bundle root
if (ROOT / "calculator.py").exists() and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    """Entry point used by both direct execution and [project.scripts]."""
    print("Starting MathForge...")
    print("  - SymPy symbolic engine loaded")
    print("  - Matplotlib visualizations ready")

    # Import here so path setup has already happened
    from app.main import main as _app_main  # noqa: WPS433 (late import intended)

    _app_main()


if __name__ == "__main__":
    main()
