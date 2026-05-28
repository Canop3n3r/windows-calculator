# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification for MathForge — High-Tier Scientific & Visual Mathematics Tool.

Build the standalone executable with:

    pyinstaller mathforge.spec

Outputs:
    dist/MathForge/          (recommended onedir layout — fast startup with large scientific stack)
    dist/MathForge/MathForge.exe   (or MathForge on POSIX)

For a single-file executable (larger, slower startup):
    Change the EXE block to include a.scripts + a.binaries + ... and remove COLLECT,
    then set --onefile behavior via the block.

This spec targets the official MathForge launcher (launch_mathforge.py)
which correctly bootstraps the high-tier tabbed application (Grapher + Derivative Explorer + preserved classic calculator).

Requirements:
    pip install pyinstaller
    (or pip install -e ".[packaging]" once configured)

Notes for SymPy + NumPy + Matplotlib:
- These packages are large and use heavy dynamic imports / C extensions.
- We explicitly list critical hiddenimports and backend modules.
- onedir layout is strongly preferred for this class of application.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import sys
from pathlib import Path

block_cipher = None

# -----------------------------------------------------------------------------
# Project layout
# -----------------------------------------------------------------------------
ROOT = Path.cwd()
LAUNCHER = ROOT / "launch_mathforge.py"
CALCULATOR = ROOT / "calculator.py"

# -----------------------------------------------------------------------------
# Analysis — entry point is the documented MathForge launcher
# -----------------------------------------------------------------------------
a = Analysis(
    [str(LAUNCHER)],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Include the original simple calculator (imported via runtime path hack in app/main.py)
        (str(CALCULATOR), "."),
        # Future: add icons, example expressions, etc.
        # (str(ROOT / "assets"), "assets"),
    ],
    hiddenimports=[
        # --- Core scientific stack ---
        "sympy",
        "sympy.*",
        "numpy",
        "numpy.*",
        "matplotlib",
        "matplotlib.*",
        "matplotlib.backends.backend_tkagg",
        "matplotlib.backends._tkagg",
        "matplotlib.figure",
        "matplotlib.pyplot",
        "matplotlib.backends",
        # --- Tkinter (stdlib but PyInstaller sometimes needs explicit help on Windows) ---
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
        "_tkinter",
        # --- SymPy parsing & calculus internals (very dynamic) ---
        "sympy.parsing",
        "sympy.parsing.sympy_parser",
        "sympy.core",
        "sympy.functions",
        "sympy.matrices",
        "sympy.printing",
        "sympy.solvers",
        "sympy.series",
        "sympy.calculus",
        "sympy.polys",
        # --- NumPy / SciPy-adjacent that SymPy lambdify may touch ---
        "numpy.core._multiarray_umath",
        "numpy.random",
        "numpy.linalg",
        # --- Other common runtime needs ---
        "pkg_resources",  # sometimes pulled by matplotlib or setuptools remnants
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy optional scientific libs not used (keeps size down)
        "scipy",
        "pandas",
        "PIL",
        "PySide6",
        "PyQt6",
        "pyvista",
        "notebook",
        "jupyter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# -----------------------------------------------------------------------------
# Python zip archive
# -----------------------------------------------------------------------------
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# -----------------------------------------------------------------------------
# Executable (GUI application — no console window in release builds)
# -----------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MathForge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                    # Good compression for Windows; harmless if UPX not installed
    console=False,               # Pure GUI app (set True temporarily for debugging)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                   # TODO: Add 'assets/mathforge.ico' when available
)

# -----------------------------------------------------------------------------
# Collection (onedir layout — strongly recommended)
# Produces dist/MathForge/ folder containing the .exe + all dependencies.
# Much faster startup than onefile for SymPy-sized payloads.
# -----------------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MathForge",
)

# -----------------------------------------------------------------------------
# Optional onefile variant (commented)
# -----------------------------------------------------------------------------
# To produce a single MathForge.exe instead, replace the above EXE + COLLECT with:
#
# exe = EXE(
#     pyz,
#     a.scripts,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     name="MathForge",
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     console=False,
#     icon=None,
# )
#
# And remove the COLLECT block entirely.
# -----------------------------------------------------------------------------

print("\n[mathforge.spec] Analysis complete.")
print(f"  Entry script : {LAUNCHER}")
print(f"  Collected datas include calculator.py for legacy tab compatibility")
print("  Recommended build command:  pyinstaller mathforge.spec")
print("  Output will be in: dist/MathForge/")
