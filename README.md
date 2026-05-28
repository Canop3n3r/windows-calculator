# Windows Calculator

A clean, modern desktop calculator app for Windows built with Python and Tkinter.

No external dependencies required — uses only Python's standard library.

## Features

- Full arithmetic: +, −, ×, ÷
- Advanced functions: square (x²), square root (√x), reciprocal (1/x), percentage (%)
- Memory functions: MC, MR, MS, M+, M−
- Parentheses-friendly chaining and immediate calculation mode
- Full keyboard support (numpad friendly)
- Dark theme inspired by Windows 11
- Copy result (Ctrl+C) and paste numbers (Ctrl+V)
- Clean error handling and backspace support

## Running the App

### Option 1: Direct (Recommended for development)

```powershell
cd C:\Users\Myers\dev\windows-calculator
python calculator.py
```

### Option 2: Double-click launcher (Windows)

1. Run `launch.bat` (created automatically or manually)

## Creating a Standalone .exe (No Python needed to run)

You can turn this into a real Windows application (.exe) using PyInstaller.

### One-time setup

```powershell
pip install pyinstaller
```

### Build the executable

From the project folder:

```powershell
pyinstaller --onefile --windowed --name "Windows Calculator" --icon=NONE calculator.py
```

The finished app will appear in the `dist` folder:

```
dist\Windows Calculator.exe
```

You can copy that `.exe` anywhere and run it without installing Python.

Optional nicer build flags:

```powershell
pyinstaller --onefile --windowed --clean --name "Calculator" calculator.py
```

## Keyboard Shortcuts

| Key            | Action                  |
|----------------|-------------------------|
| 0-9 / Numpad   | Enter digits            |
| .              | Decimal point           |
| + - * /        | Operators               |
| Enter / =      | Calculate result        |
| Backspace      | Delete last digit       |
| Delete         | Clear entry (CE)        |
| Esc / C        | Clear all (C)           |
| %              | Percentage              |
| Ctrl+C         | Copy displayed result   |
| Ctrl+V         | Paste number            |
| M / m          | Memory store / recall   |

## Project Structure

```
windows-calculator/
├── calculator.py     # Main application
├── README.md
├── .gitignore
└── launch.bat        # Optional convenience launcher
```

## License

MIT — Free to use and modify.

---

Made for Windows. Enjoy!
