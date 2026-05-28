# MathForge

**High-Tier Symbolic & Visual Mathematics Tool**

*Powerful interactive visualizations for calculus, paired with a full SymPy-powered scientific calculator. Built for students, educators, and anyone who wants to truly **see** mathematics.*

MathForge transforms abstract concepts into vivid, manipulable experiences. Drag a point along a curve and watch the definition of the derivative unfold in real time. Animate Riemann partitions and witness convergence. Explore Taylor approximations order-by-order with live error plots. All powered by a robust symbolic engine and rendered with publication-quality graphics in a polished dark interface.

---

## Features

### Symbolic Math Engine
- Full-featured `MathEngine` built on SymPy and NumPy
- Symbolic differentiation, indefinite & definite integration, limits (one- and two-sided), Taylor/Laurent series
- Algebraic operations: simplify, expand, factor
- Calculator-friendly parsing (`^` for power, implicit multiplication like `2x` or `3sin(x)`)
- High-precision numeric evaluation with support for live parameters across every tool

### Flagship Visual Explorers
- **2D Grapher + Derivative Explorer** — Plot up to three functions simultaneously with live parameter sliders. The standout Derivative Explorer features a draggable exploration point, real-time tangent line, adjustable secant, and a one-click animation that demonstrates the limit definition of the derivative (`h → 0`) with converging slopes and symbolic derivative display.
- **Riemann / Integral Studio** — Four summation methods (Left, Right, Midpoint, Trapezoidal) with live partition count (n = 1–220), automatic parameter detection, symbolic exact integral, numeric approximation, and absolute/relative error. Includes a beautiful "Animate Convergence" mode.
- **Taylor Series Playground** — Interactive polynomial approximations of any order. Adjustable expansion point (set by clicking the plot!), parameter sliders, symbolic polynomial display, smooth "build order by order" animation, and a dedicated remainder/error subplot.
- **3D Surface Viewer** — Live surfaces `z = f(x, y, ...)` with dynamic parameters. Optional symbolic gradient vector field overlay computed via partial derivatives. Full mouse-driven 3D navigation (rotate, zoom, pan) with toolbar.

### Scientific Expression Calculator
- Large input supporting complete SymPy syntax
- One-click actions: Derivative, Indefinite/Definite Integral, Limit, Taylor series, Simplify, Expand, Factor
- Live parameter editing panel for instant numeric feedback
- Clickable 20-entry history
- Beautiful multi-format results: pretty-printed, LaTeX, and high-precision numeric
- Curated example gallery and smart token insertion buttons

### Professional Experience & Distribution
- Elegant, consistent dark theme inspired by modern Windows design across all components
- Fully preserved original simple calculator (basic arithmetic, memory, keyboard support) — launchable independently
- Comprehensive test suite for the math engine
- **True standalone distribution**: Professional PyInstaller packaging produces a self-contained Windows executable and folder. No Python installation required on target machines.

---

## Getting Started

### Development (from Source)

```powershell
# 1. Navigate to the project root
cd C:\path\to\windows-calculator

# 2. Install scientific dependencies (SymPy, NumPy, Matplotlib)
pip install -r requirements.txt

# 3. Launch the full high-tier MathForge experience
python launch_mathforge.py

# Windows convenience launcher (auto-installs deps on first run)
# .\launch_mathforge.bat
```

The app opens with the powerful **2D Grapher + Calculus** tab front and center (you can switch freely between all tools).

### Building & Running the Standalone App

MathForge ships as a completely self-contained Windows application:

```powershell
# Build the executable (one-time step)
python build_exe.py

# Recommended options for different use cases:
#   python build_exe.py --clean           # Remove previous build artifacts first
#   python build_exe.py --onefile         # Produce a single .exe (larger file, slower startup)
```

After a successful build:
- The recommended **onedir** distribution is at `dist/MathForge/`
- Run `MathForge.exe` directly

The resulting folder is portable — copy it to any Windows machine and it runs with **zero Python installation or additional dependencies**. Ideal for classrooms, labs, offline use, or sharing with others.

### Classic Simple Calculator (Preserved)

For the original lightweight experience:

```powershell
python calculator.py
# or
.\launch.bat
```

---

## Usage Examples

### Derivative Explorer — The Limit Definition, Visualized

1. Open the **2D Grapher + Calculus** tab.
2. Enter a function such as `sin(x)^2` (or try the parametric form `a*sin(b*x)`).
3. Drag the white exploration point directly on the curve, or use the **x₀** slider.
4. Enable the tangent and secant checkboxes.
5. Click the prominent **▶ Animate h → 0 (limit demo)** button.

Watch the yellow secant line collapse onto the orange tangent in real time while the numeric slopes converge to the displayed symbolic derivative. This is one of the most effective visualizations available for internalizing the definition of the derivative.

**Great expressions to try**: `exp(-x)*cos(3x)`, `x**2 * exp(-0.1*x)`, `cos(2*x) + 0.5*sin(3*x)`.

### Riemann / Integral Studio — See Convergence Happen

1. Switch to the **Calculus Lab • Riemann** tab.
2. Load an educational preset (`x² [0,2]`, `sin(x) [0,π]`, or `e^{-x} [0,3]`) or type your own expression.
3. Slide the partition count **n** and watch the shaded rectangles or trapezoids update instantly.
4. Press **▶ Animate n → 220** to watch the approximation refine smoothly.

The panel on the right shows the exact symbolic integral (via SymPy), the current Riemann/Trapezoidal approximation, and precise error values. Switch methods to compare their visual and numerical behavior side-by-side.

### Taylor Series Playground — Approximations You Can Explore

1. Go to the **Taylor Series** tab.
2. Select a preset such as `eˣ`, `sin(x)`, or `1/(1+x²)`.
3. Use the order slider (0–12+) or click the animation control to build the approximating polynomial term by term.
4. Click anywhere on the plot or edit the expansion point `a` — observe how dramatically the fit changes with distance from the center.
5. Study the live error subplot below.

Perfect for developing intuition about convergence, the importance of the expansion point, and where series approximations succeed or fail.

### Scientific Calculator — Symbolic Power at Your Fingertips

1. Open the **Scientific** tab.
2. Type an expression: `x^2 * sin(x) + exp(-x/2)`, `(1 + x)^(1/x)`, or `sin(x)/x`.
3. Use the one-click action buttons:
   - **Derivative** or **∫ Indefinite/Definite**
   - **Limit**, **Taylor**, **Simplify**, **Expand**, **Factor**
4. Discovered parameters appear in an editable panel — change their values and see high-precision numeric results update live.
5. Click any entry in the history list to reload it instantly and chain further operations.

Results appear simultaneously in pretty-printed, LaTeX, and numeric forms.

---

## Project Structure

```
windows-calculator/
├── app/
│   ├── core/
│   │   └── math_engine.py          # The symbolic + numeric heart (SymPy + NumPy)
│   ├── calculator/
│   │   └── scientific.py           # Professional expression scientific calculator
│   ├── calculus/
│   │   ├── riemann_studio.py       # Riemann sums & integral visualization studio
│   │   └── taylor_playground.py    # Taylor series explorer with error visualization
│   ├── grapher/
│   │   ├── grapher_2d.py           # 2D grapher + flagship Derivative Explorer
│   │   └── plot3d.py               # 3D surfaces + symbolic gradient fields
│   └── main.py                     # Main tabbed high-tier application
├── calculator.py                   # Original simple calculator (fully preserved)
├── launch_mathforge.py             # Primary launcher (entry point for PyInstaller too)
├── build_exe.py                    # Professional standalone Windows builder
├── mathforge.spec                  # Carefully tuned PyInstaller specification
├── requirements.txt
├── pyproject.toml
├── tests/
│   └── test_math_engine.py
└── README.md
```

## Technology

- **Python 3.11+** with Tkinter (maximum compatibility, zero extra GUI dependencies)
- **SymPy** — full-featured computer algebra system for all symbolic operations
- **NumPy + Matplotlib** — high-performance numeric evaluation and interactive, beautifully styled plots
- **PyInstaller** — robust creation of truly standalone Windows distributions

## License

MIT License

---

**MathForge** brings the beauty and intuition of mathematics to life.

Whether you are teaching the definition of the derivative, exploring series convergence for the first time, or rapidly prototyping symbolic calculations, MathForge is designed to delight, educate, and accelerate understanding.

Built with care, precision, and high standards.
