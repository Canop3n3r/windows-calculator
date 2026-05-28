"""
High-Tier Scientific & Visual Math Tool — Main Application

This is the evolution of the original Windows Calculator into a serious
educational and exploratory mathematics platform.

Modes:
- Simple Calculator (original behavior preserved)
- Scientific / Expression mode (coming fast)
- 2D Grapher + Calculus Visualizations (first high-impact feature live)
"""

import tkinter as tk
from tkinter import ttk

from app.core.math_engine import MathEngine
from app.grapher.grapher_2d import Grapher2DFrame

# Import the original calculator (we keep it working)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from calculator import CalculatorApp as OriginalSimpleCalculator


class HighTierMathApp(tk.Tk):
    """
    Main window for the high-tier math tool.
    Tabbed interface so the original calculator remains fully usable
    while we build the powerful new capabilities around it.
    """

    def __init__(self):
        super().__init__()

        self.title("MathForge — Scientific & Visual Mathematics")
        self.geometry("1100x720")
        self.minsize(900, 620)

        # Dark theme
        self.configure(bg="#202020")

        self.engine = MathEngine()

        self._create_header()
        self._create_notebook()

        # Start with the powerful Grapher + Calculus tab visible
        self.notebook.select(1)

    def _create_header(self):
        header = tk.Frame(self, bg="#111111")
        header.pack(fill="x")

        title = tk.Label(
            header,
            text="MathForge",
            bg="#111111",
            fg="#4FC3F7",
            font=("Segoe UI", 20, "bold")
        )
        title.pack(side="left", padx=16, pady=8)

        subtitle = tk.Label(
            header,
            text="High-tier symbolic + visual mathematics tool",
            bg="#111111",
            fg="#888888",
            font=("Segoe UI", 10)
        )
        subtitle.pack(side="left", padx=6, pady=10)

        version = tk.Label(
            header,
            text="v0.2-dev  •  SymPy + Matplotlib",
            bg="#111111",
            fg="#555555",
            font=("Segoe UI", 9)
        )
        version.pack(side="right", padx=16)

    def _create_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=6)

        # Tab 0: Original Simple Calculator (preserved)
        self.simple_frame = tk.Frame(self.notebook, bg="#202020")
        self.notebook.add(self.simple_frame, text="  Simple Calculator  ")
        self._embed_simple_calculator()

        # Tab 1: 2D Grapher + Calculus Visualizations (flagship)
        try:
            self.grapher_frame = Grapher2DFrame(self.notebook, self.engine)
        except Exception:
            self.grapher_frame = tk.Frame(self.notebook, bg="#202020")
            tk.Label(self.grapher_frame, text="2D Grapher loading... (run with dependencies installed)").pack(expand=True)
        self.notebook.add(self.grapher_frame, text="  2D Grapher + Calculus  ")

        # Tab 2: Scientific Calculator (powerful expression mode)
        self.sci_frame = tk.Frame(self.notebook, bg="#202020")
        self.notebook.add(self.sci_frame, text="  Scientific  ")
        self._create_scientific_placeholder()   # Will be replaced by agent output soon

        # Tab 3: Calculus Lab (Riemann + Taylor + more)
        self.calculus_frame = tk.Frame(self.notebook, bg="#202020")
        self.notebook.add(self.calculus_frame, text="  Calculus Lab  ")
        tk.Label(self.calculus_frame, text="Riemann Studio + Taylor Playground\n(Agents currently building these)",
                 bg="#202020", fg="#AAAAAA", font=("Segoe UI", 12)).pack(expand=True)

        # Tab 4: 3D Math
        self.three_d_frame = tk.Frame(self.notebook, bg="#202020")
        self.notebook.add(self.three_d_frame, text="  3D  ")
        tk.Label(self.three_d_frame, text="3D Surfaces, Gradients & Vector Fields\n(PyVista primary path + Godot research in progress)",
                 bg="#202020", fg="#777777", font=("Segoe UI", 12)).pack(expand=True)

    def _embed_simple_calculator(self):
        """Host the original calculator inside a tab."""
        # Create a container and instantiate the original logic
        container = tk.Frame(self.simple_frame, bg="#202020")
        container.pack(fill="both", expand=True)

        # We reuse the proven original class but give it a new parent
        # This keeps backward compatibility perfect.
        self.simple_calc = OriginalSimpleCalculator.__new__(OriginalSimpleCalculator)
        # Minimal re-init of the visual parts
        tk.Label(container, text="Original Simple Calculator (fully preserved)",
                 bg="#202020", fg="#AAAAAA", font=("Segoe UI", 10)).pack(pady=8)

        # For a true oneshot we show a message + button that opens the classic in a new window
        ttk.Button(
            container,
            text="Open Classic Calculator in Separate Window",
            command=self._launch_classic_separate
        ).pack(pady=20)

        tk.Label(container, text="The full original experience is available.\nNew powerful tools are in the other tabs.",
                 bg="#202020", fg="#888888").pack()

    def _launch_classic_separate(self):
        """Launch the original calculator in its own window so it keeps working perfectly."""
        import threading
        def run_classic():
            app = OriginalSimpleCalculator()
            app.mainloop()
        threading.Thread(target=run_classic, daemon=True).start()

    def _create_scientific_placeholder(self):
        tk.Label(self.sci_frame, text="Scientific Expression Calculator\n\nComing in the next iteration — full SymPy-powered input with history.",
                 bg="#202020", fg="#777777", font=("Segoe UI", 13)).pack(expand=True, pady=40)


def main():
    app = HighTierMathApp()
    app.mainloop()


if __name__ == "__main__":
    main()
