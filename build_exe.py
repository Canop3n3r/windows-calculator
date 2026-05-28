#!/usr/bin/env python3
"""
MathForge — PyInstaller Build Script

Professional one-command builder for the standalone MathForge executable.

Usage (from project root):

    python build_exe.py
    python build_exe.py --onefile          # single executable (slower startup)
    python build_exe.py --clean            # clean previous builds first
    python build_exe.py --debug            # keep console window for debugging

Requirements:
    pip install pyinstaller
    # or
    pip install -e ".[packaging]"

The script uses the high-quality mathforge.spec by default (preferred onedir layout).
It also supports quick overrides for development.

After a successful build the executable lives in:
    dist/MathForge/MathForge.exe
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
SPEC_FILE = ROOT / "mathforge.spec"


def clean_build_artifacts() -> None:
    """Remove previous PyInstaller build and dist artifacts."""
    for path in (DIST_DIR, BUILD_DIR):
        if path.exists():
            print(f"  Removing {path}...")
            shutil.rmtree(path, ignore_errors=True)
    # Also clean any stray .spec generated files in some workflows
    for spec in ROOT.glob("*.spec"):
        # Keep our canonical mathforge.spec
        if spec.name.lower() != "mathforge.spec":
            spec.unlink(missing_ok=True)


def run_pyinstaller(args: list[str]) -> int:
    """Invoke PyInstaller with the provided arguments."""
    cmd = [sys.executable, "-m", "PyInstaller"] + args
    print(f"\n>>> {' '.join(cmd)}\n")
    return subprocess.call(cmd)


def build(default_spec: bool = True, onefile: bool = False, clean: bool = False, debug: bool = False) -> None:
    if clean:
        clean_build_artifacts()

    print("=" * 70)
    print("MathForge PyInstaller Builder")
    print("=" * 70)
    print(f"Project root : {ROOT}")
    print(f"Python       : {sys.version.split()[0]}")
    print(f"Target       : {'Onefile (single exe)' if onefile else 'Onedir (recommended folder layout)'}")
    print()

    if default_spec and SPEC_FILE.exists() and not onefile:
        # Preferred professional path: use the carefully tuned .spec
        pyinstaller_args = [str(SPEC_FILE)]
        if debug:
            # Force console for easier debugging when using spec
            # (the spec hardcodes console=False; we can override via --console here)
            pyinstaller_args.append("--console")
        print("Using canonical spec file: mathforge.spec")
    else:
        # Fallback / quick development build directly from launcher
        launcher = ROOT / "launch_mathforge.py"
        pyinstaller_args = [
            str(launcher),
            "--name=MathForge",
            "--paths", str(ROOT),
        ]

        if onefile:
            pyinstaller_args.append("--onefile")
        else:
            pyinstaller_args.append("--onedir")

        if not debug:
            pyinstaller_args.append("--windowed")  # GUI only
        else:
            pyinstaller_args.append("--console")

        # Mirror the important hidden imports from the spec
        hidden = [
            "sympy", "sympy.*",
            "numpy", "numpy.*",
            "matplotlib", "matplotlib.*", "matplotlib.backends.backend_tkagg",
            "tkinter", "tkinter.ttk",
        ]
        for h in hidden:
            pyinstaller_args.extend(["--hidden-import", h])

        # Include the classic calculator
        pyinstaller_args.extend(["--add-data", f"{ROOT / 'calculator.py'}{';.' if sys.platform == 'win32' else ':.'}"])

    exit_code = run_pyinstaller(pyinstaller_args)

    if exit_code == 0:
        print("\n" + "=" * 70)
        print("BUILD SUCCESSFUL")
        print("=" * 70)
        exe_name = "MathForge.exe" if sys.platform == "win32" else "MathForge"
        if onefile:
            print(f"Standalone executable: {DIST_DIR / exe_name}")
        else:
            print(f"Application folder   : {DIST_DIR / 'MathForge'}")
            print(f"Executable           : {DIST_DIR / 'MathForge' / exe_name}")
        print("\nTip: You can copy the entire 'MathForge' folder to any Windows machine.")
        print("     No Python installation is required on the target machine.")
    else:
        print("\n" + "=" * 70)
        print("BUILD FAILED")
        print("=" * 70)
        print("Check the output above for missing modules or hook errors.")
        print("Common fixes:")
        print("  - pip install --upgrade pyinstaller sympy numpy matplotlib")
        print("  - Try with --debug to keep the console window")
        print("  - Inspect build/MathForge/warn-MathForge.txt")
        sys.exit(exit_code)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a standalone MathForge executable using PyInstaller."
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Produce a single executable instead of a folder (slower startup, larger file)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete previous build/ and dist/ directories before building",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Build with console window visible (useful for seeing errors)",
    )
    parser.add_argument(
        "--no-spec",
        action="store_true",
        help="Ignore mathforge.spec and build directly from launch_mathforge.py (advanced)",
    )

    args = parser.parse_args()

    build(
        default_spec=not args.no_spec,
        onefile=args.onefile,
        clean=args.clean,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
