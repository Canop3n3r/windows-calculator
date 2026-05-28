@echo off
REM MathForge — High-Tier Scientific & Visual Math Tool Launcher
cd /d "%~dp0"

echo Starting MathForge...
echo Installing/updating dependencies if needed (first run may take a minute)...

python -m pip install -r requirements.txt --quiet

python launch_mathforge.py

if errorlevel 1 (
    echo.
    echo Launch failed. Make sure you have Python 3.11+ and run:
    echo    pip install -r requirements.txt
    pause
)
