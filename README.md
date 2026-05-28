# MathForge — High-Tier Scientific & Visual Mathematics Tool

**The evolution of a simple Windows calculator into a powerful symbolic + visual math platform.**

This project started as a clean Tkinter calculator and is rapidly becoming a serious tool for exploration and teaching of advanced mathematics, with first-class support for interactive graphing and calculus visualizations that actually help people *understand*.

> "I can type a math concept and immediately see it, manipulate it, and understand it visually."

---

## Current Status (Rapid Development)

**Already delivered in this phase:**
- Full SymPy-powered math engine (symbolic derivatives, integrals, limits, series, etc.)
- Interactive **2D Grapher** with live parameter control
- **Derivative Explorer** — one of the highest-educational-value visualizations possible (movable point + tangent + animated secant → tangent limit demonstration)
- Original simple calculator preserved and launchable
- Modern project structure with proper separation of concerns

We are moving extremely fast on the most valuable parts (the visuals that make calculus click) while keeping the original experience intact.

## Features

- Full arithmetic: +, −, ×, ÷
- Advanced functions: square (x²), square root (√x), reciprocal (1/x), percentage (%)
- Memory functions: MC, MR, MS, M+, M−
- Parentheses-friendly chaining and immediate calculation mode
- Full keyboard support (numpad friendly)
- Dark theme inspired by Windows 11
- Copy result (Ctrl+C) and paste numbers (Ctrl+V)
- Clean error handling and backspace support

## Running the App (High-Tier Version)

### Quick Start

```powershell
cd C:\Users\Myers\dev\windows-calculator

# Install the scientific stack (one time)
pip install -r requirements.txt

# Launch the new high-tier tool
python launch_mathforge.py
```

This opens **MathForge** with the powerful 2D Grapher + Derivative Explorer front and center.

You can still open the original simple calculator from the first tab if you want the classic experience.

### Classic Simple Calculator Only

```powershell
python calculator.py
# or
.\launch.bat
```

## Current High-Impact Features (Phase 1)

- **MathEngine** — SymPy + NumPy brain for the whole app (symbolic calculus, fast numeric lambdify, safe parsing)
- **Derivative Explorer** (flagship visualization)
  - Enter almost any expression (`sin(x)^2`, `exp(-x)*cos(3x)`, etc.)
  - Move the point x₀ live
  - See the tangent line update in real time
  - Watch the secant line animate toward the tangent as h → 0 — this is the *definition of the derivative* made visceral
- Clean dark theme consistent with modern Windows tools
- Preserved original simple calculator (zero regression)

## Roadmap (Aggressive)

**Phase 1 (current — moving extremely fast)**
- Riemann / Integral Studio with live partition animation
- Full expression scientific calculator mode
- Taylor series convergence playground

**Phase 2**
- Multiple functions + area between curves
- 3D surfaces & vector fields (decision point: PyVista + PySide6 or advanced Godot integration)

**Phase 3**
- Notebook-style problem history
- Animation export (GIF/MP4)
- Standalone high-quality `.exe`

**Long-term vision**
- Best-in-class integrated 3D math visualization on Windows (potentially using Godot LibGodot for truly stunning scenes once the core value is proven)

## Godot 3D Note

We investigated embedding Godot 4 (via LibGodot) for seamless same-window 3D. It is technically possible (experimental in 2026) but high complexity and build cost. 

For now we are delivering **maximum educational value** using matplotlib + SymPy (already extremely powerful for 2D calculus). When the tool is already great, we will evaluate PyVista (excellent integrated 3D) and/or Godot for premium 3D scenes.

## Project Structure (Evolving Fast)

```
windows-calculator/
├── app/
│   ├── core/
│   │   └── math_engine.py       # The symbolic + numeric brain
│   ├── grapher/
│   │   └── grapher_2d.py        # 2D + calculus visualizations
│   ├── calculator/
│   ├── calculus/
│   └── main.py                  # New tabbed high-tier shell
├── calculator.py                # Original simple calculator (preserved)
├── launch_mathforge.py          # New recommended launcher
├── requirements.txt
└── README.md
```

## License

MIT

---

Built with urgency and high standards. This is becoming a genuinely excellent math tool.
