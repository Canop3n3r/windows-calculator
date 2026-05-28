@echo off
REM Windows Calculator Launcher
cd /d "%~dp0"
python calculator.py
if errorlevel 1 (
    echo.
    echo Failed to launch calculator.
    echo Make sure Python is installed and in your PATH.
    echo.
    pause
)
