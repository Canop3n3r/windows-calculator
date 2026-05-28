"""
High-Tier Scientific & Visual Math Tool — Main Application

This is the evolution of the original Windows Calculator into a serious
educational and exploratory mathematics platform.

All tabs load with graceful error handling.
Tabs:
- Simple (classic preserved)
- 2D Grapher (flagship interactive)
- Scientific (SymPy-powered)
- Calculus Lab (Riemann + Taylor)
- 3D Surfaces
- 📓 Notebook / History (cross-tool persistent scratchpad)
"""

import tkinter as tk
from tkinter import ttk

from app.core.math_engine import MathEngine
from app.grapher.grapher_2d import Grapher2DFrame
from app.grapher.plot3d import Plot3DFrame
from app.calculator.scientific import ScientificCalculatorFrame
from app.calculus.riemann_studio import RiemannStudioFrame
from app.calculus.taylor_playground import TaylorPlaygroundFrame
from app.ui.history_notebook import HistoryNotebook

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

        # Start on the Scientific Calculator (the actually useful modern one)
        self.notebook.select(0)

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
        """Create the main tabbed notebook with graceful loading for every tab."""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=6)

        # Tab 0: Simple Calculator (original preserved, graceful fallback)
        try:
            self.simple_frame = tk.Frame(self.notebook, bg="#202020")
            self.notebook.add(self.simple_frame, text="  Simple  ")
            self._embed_simple_calculator()
        except Exception as exc:
            self.simple_frame = tk.Frame(self.notebook, bg="#202020")
            tk.Label(self.simple_frame, text=f"Simple Calculator failed to load:\n{exc}",
                     bg="#202020", fg="#F87171", font=("Segoe UI", 11)).pack(expand=True, pady=30)
            self.notebook.add(self.simple_frame, text="  Simple  ")

        # Tab 1: Scientific (SymPy expression mode with history & calculus actions) — primary powerful tool
        try:
            self.sci_frame = ScientificCalculatorFrame(self.notebook, self.engine)
        except Exception as exc:
            self.sci_frame = tk.Frame(self.notebook, bg="#202020")
            tk.Label(self.sci_frame, text=f"Scientific Calculator failed to load:\n{exc}",
                     bg="#202020", fg="#F87171", font=("Segoe UI", 11)).pack(expand=True, pady=30)
        self.notebook.add(self.sci_frame, text="  Scientific  ")

        # Tab 3: Visual Math Lab — grouped advanced visualizations (much cleaner)
        try:
            visual_container = tk.Frame(self.notebook, bg="#202020")
            
            # Add a short explanation at the top of the Visual Math Lab so it's not confusing
            header = tk.Frame(visual_container, bg="#202020")
            header.pack(fill="x", padx=8, pady=(4, 0))
            tk.Label(header, 
                     text="Interactive visualizations to help you actually understand calculus concepts.",
                     bg="#202020", fg="#AAAAAA", font=("Segoe UI", 10)).pack(anchor="w")

            inner = ttk.Notebook(visual_container)
            inner.pack(fill="both", expand=True, padx=4, pady=4)

            # Derivative Explorer (most educational single feature)
            try:
                deriv_tab = Grapher2DFrame(inner, self.engine)  # reuse the powerful one
            except Exception as exc:
                deriv_tab = tk.Frame(inner, bg="#202020")
                tk.Label(deriv_tab, text=f"Derivative Explorer failed to load:\n{exc}",
                         bg="#202020", fg="#F87171", font=("Segoe UI", 11)).pack(expand=True, pady=30)
            inner.add(deriv_tab, text="  Derivative Explorer  ")

            # Riemann Studio
            try:
                riemann_tab = RiemannStudioFrame(inner, self.engine)
            except Exception as exc:
                riemann_tab = tk.Frame(inner, bg="#202020")
                tk.Label(riemann_tab, text=f"Riemann Studio failed to load:\n{exc}",
                         bg="#202020", fg="#F87171", font=("Segoe UI", 11)).pack(expand=True, pady=30)
            inner.add(riemann_tab, text="  Riemann / Integrals  ")

            # Taylor Playground
            try:
                taylor_tab = TaylorPlaygroundFrame(inner, self.engine)
            except Exception as exc:
                taylor_tab = tk.Frame(inner, bg="#202020")
                tk.Label(taylor_tab, text=f"Taylor Series failed to load:\n{exc}",
                         bg="#202020", fg="#F87171", font=("Segoe UI", 11)).pack(expand=True, pady=30)
            inner.add(taylor_tab, text="  Taylor Series  ")

            inner.select(0)  # Start on Derivative Explorer (easiest "wow" moment)

            self.notebook.add(visual_container, text="  Visual Math Lab  ")
        except Exception as exc:
            visual_container = tk.Frame(self.notebook, bg="#202020")
            tk.Label(visual_container, text=f"Visual Math Lab failed to load:\n{exc}",
                     bg="#202020", fg="#F87171", font=("Segoe UI", 11)).pack(expand=True, pady=30)
            self.notebook.add(visual_container, text="  Visual Math Lab  ")

        # Tab 4: 3D Surfaces
        try:
            self.three_d_frame = Plot3DFrame(self.notebook, self.engine)
        except Exception as exc:
            self.three_d_frame = tk.Frame(self.notebook, bg="#202020")
            tk.Label(self.three_d_frame, text=f"3D viewer failed to load:\n{exc}",
                     bg="#202020", fg="#F87171", font=("Segoe UI", 11)).pack(expand=True, pady=30)
        self.notebook.add(self.three_d_frame, text="  3D  ")

        # Final tab: Cross-tool History / Notebook (lightweight persistent scratchpad)
        try:
            self.history_frame = HistoryNotebook(
                self.notebook,
                self.engine,
                callbacks={
                    "load_scientific": self._load_expr_in_scientific,
                    "plot_grapher": self._plot_expr_in_grapher,
                },
            )
        except Exception as exc:
            self.history_frame = tk.Frame(self.notebook, bg="#202020")
            tk.Label(
                self.history_frame,
                text=f"History Notebook failed to load:\n{exc}",
                bg="#202020",
                fg="#F87171",
                font=("Segoe UI", 11),
            ).pack(expand=True, pady=30)
        self.notebook.add(self.history_frame, text="  📓 Notebook / History  ")

    def _embed_simple_calculator(self):
        """Legacy simple calculator — made painfully clear because the old design was confusing."""
        container = tk.Frame(self.simple_frame, bg="#202020")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(container, 
                 text="Legacy Simple Calculator",
                 bg="#202020", fg="#FFFFFF", font=("Segoe UI", 16, "bold")).pack(pady=(0, 10))

        tk.Label(container,
                 text="WARNING: This tab does NOT contain a working calculator.\nClicking the button below will try to open the old basic calculator\nin a completely separate window.",
                 bg="#202020", fg="#F87171", font=("Segoe UI", 11), justify="center").pack(pady=8)

        ttk.Button(
            container,
            text="Open Legacy Calculator in New Window",
            command=self._launch_classic_separate
        ).pack(pady=15)

        tk.Label(container,
                 text="This exists only for historical reasons.\nFor actual use, please use the 'Scientific Calculator' tab (the second tab).",
                 bg="#202020", fg="#4ADE80", font=("Segoe UI", 10), justify="center").pack(pady=10)

    def _launch_classic_separate(self):
        """Launch the original calculator in its own window so it keeps working perfectly."""
        import threading
        def run_classic():
            app = OriginalSimpleCalculator()
            app.mainloop()
        threading.Thread(target=run_classic, daemon=True).start()

    # -------------------------------------------------------------------------
    # HISTORY NOTEBOOK CALLBACKS (robust tab switching + tool integration)
    # -------------------------------------------------------------------------
    def _load_expr_in_scientific(self, expr: str):
        """Switch to Scientific tab and load/evaluate the expression."""
        try:
            sci_idx = self.notebook.index(self.sci_frame)
            self.notebook.select(sci_idx)
            if hasattr(self, "sci_frame") and hasattr(self.sci_frame, "calculator"):
                self.sci_frame.calculator.set_expression(expr, evaluate_immediately=True)
            if hasattr(self, "history_frame"):
                self.history_frame.status_label.config(
                    text="Loaded in Scientific", fg="#4ADE80"
                )
                self.after(
                    1400,
                    lambda: (
                        self.history_frame.status_label.config(text="Ready", fg="#B0B0B0")
                        if hasattr(self, "history_frame")
                        else None
                    ),
                )
        except Exception as exc:
            from tkinter import messagebox
            messagebox.showinfo("MathForge Notebook", f"Could not load into Scientific:\n{exc}")

    def _plot_expr_in_grapher(self, expr: str):
        """Switch to 2D Grapher and plot the expression in the first function slot."""
        try:
            grapher_idx = self.notebook.index(self.grapher_frame)
            self.notebook.select(grapher_idx)
            if hasattr(self, "grapher_frame") and hasattr(self.grapher_frame, "grapher"):
                g = self.grapher_frame.grapher
                g.set_function(0, expr, visible=True)
                g.set_active(0)
            if hasattr(self, "history_frame"):
                self.history_frame.status_label.config(
                    text="Plotted in Grapher", fg="#4ADE80"
                )
                self.after(
                    1400,
                    lambda: (
                        self.history_frame.status_label.config(text="Ready", fg="#B0B0B0")
                        if hasattr(self, "history_frame")
                        else None
                    ),
                )
        except Exception as exc:
            from tkinter import messagebox
            messagebox.showinfo("MathForge Notebook", f"Could not plot in Grapher:\n{exc}")

def main():
    app = HighTierMathApp()
    app.mainloop()


if __name__ == "__main__":
    main()
