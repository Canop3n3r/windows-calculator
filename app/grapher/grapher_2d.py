"""
Interactive 2D Grapher + Calculus Visualizations

High-impact educational components:
- Live parameter sliders
- Derivative Explorer (the limit definition of derivative made visual)
- Clean dark theme matching the calculator
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch
import matplotlib.animation as animation

from app.core.math_engine import MathEngine


class DerivativeExplorer(tk.Frame):
    """
    One of the killer features: Makes the definition of the derivative visceral.

    Features:
    - Plot f(x) with parameter sliders
    - Movable point x0 with tangent line
    - Secant line for h that can be animated shrinking toward 0
    - Shows both symbolic derivative and numeric slope
    - This is the kind of thing that makes calculus finally click for students
    """

    def __init__(self, parent, engine: MathEngine):
        super().__init__(parent, bg="#202020")
        self.engine = engine
        self.parent = parent

        self.fig = Figure(figsize=(9, 6), dpi=100, facecolor="#202020")
        self.ax = self.fig.add_subplot(111, facecolor="#2D2D2D")
        self._style_axes()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=4)

        self.toolbar = NavigationToolbar2Tk(self.canvas, self, pack_toolbar=False)
        self.toolbar.pack(fill="x")

        self._create_controls()
        self._init_plot()

        # State
        self.current_expr = "sin(x)"
        self.params = {"a": 1.0, "b": 1.0}  # example parameters
        self.x0 = 0.5
        self.h = 0.3

        self.line_f = None
        self.line_tangent = None
        self.line_secant = None
        self.point = None

    def _style_axes(self):
        self.ax.tick_params(colors="#CCCCCC")
        for spine in self.ax.spines.values():
            spine.set_color("#555555")
        self.ax.set_xlabel("x", color="#AAAAAA")
        self.ax.set_ylabel("f(x)", color="#AAAAAA")
        self.ax.grid(True, alpha=0.2, color="#555555")

    def _create_controls(self):
        ctrl = tk.Frame(self, bg="#202020")
        ctrl.pack(fill="x", padx=8, pady=6)

        # Expression
        tk.Label(ctrl, text="f(x) =", bg="#202020", fg="#FFFFFF", font=("Segoe UI", 11)).pack(side="left")
        self.expr_var = tk.StringVar(value="sin(x)")
        entry = ttk.Entry(ctrl, textvariable=self.expr_var, width=30)
        entry.pack(side="left", padx=6)
        entry.bind("<Return>", lambda e: self.update_all())

        ttk.Button(ctrl, text="Update", command=self.update_all).pack(side="left", padx=4)

        # Sliders frame
        self.slider_frame = tk.Frame(ctrl, bg="#202020")
        self.slider_frame.pack(side="left", padx=12)

        # x0 slider
        self.x0_var = tk.DoubleVar(value=0.5)
        tk.Label(ctrl, text="x₀", bg="#202020", fg="#FFFFFF").pack(side="left", padx=(12, 2))
        self.x0_scale = tk.Scale(ctrl, from_=-4, to=4, resolution=0.01,
                                 orient="horizontal", length=180, variable=self.x0_var,
                                 command=self._on_x0_change, bg="#202020", fg="#FFFFFF",
                                 troughcolor="#3A3A3A", highlightthickness=0)
        self.x0_scale.pack(side="left")

        # h slider (for secant)
        self.h_var = tk.DoubleVar(value=0.4)
        tk.Label(ctrl, text="h", bg="#202020", fg="#FFFFFF").pack(side="left", padx=(12, 2))
        self.h_scale = tk.Scale(ctrl, from_=0.01, to=2.0, resolution=0.01,
                                orient="horizontal", length=140, variable=self.h_var,
                                command=self._on_h_change, bg="#202020", fg="#FFFFFF",
                                troughcolor="#3A3A3A", highlightthickness=0)
        self.h_scale.pack(side="left")

        # Animation button
        self.anim_btn = ttk.Button(ctrl, text="▶ Animate h → 0", command=self.animate_limit)
        self.anim_btn.pack(side="left", padx=12)

        self.status = tk.Label(ctrl, text="", bg="#202020", fg="#00FFAA", font=("Consolas", 10))
        self.status.pack(side="right", padx=10)

    def _init_plot(self):
        self.ax.set_xlim(-5, 5)
        self.ax.set_ylim(-3, 3)
        self.ax.set_title("Derivative Explorer — The limit definition of f'(x)", color="#FFFFFF", pad=10)

        self.line_f, = self.ax.plot([], [], color="#4FC3F7", linewidth=2.2, label="f(x)")
        self.line_tangent, = self.ax.plot([], [], color="#FF7043", linewidth=1.8, linestyle="--", label="tangent")
        self.line_secant, = self.ax.plot([], [], color="#FFEB3B", linewidth=1.5, alpha=0.85, label="secant (h)")
        self.point, = self.ax.plot([], [], 'o', color="#FFEB3B", markersize=8, zorder=5)

        self.ax.legend(loc="upper right", facecolor="#2D2D2D", edgecolor="#555", labelcolor="#CCCCCC")

    def update_all(self, *args):
        expr_str = self.expr_var.get().strip()
        if not expr_str:
            return

        try:
            expr = self.engine.parse(expr_str)
            free = self.engine.get_free_symbols(expr)

            # For demo we support x + optional a, b parameters
            x = sp.Symbol('x')
            self.current_expr = expr

            # Create numeric function
            vars_needed = ['x'] + [p for p in ['a', 'b'] if p in free]
            self.func = self.engine.numeric_function(expr, vars_needed)

            self._redraw()

            # Update symbolic derivative in status
            deriv = self.engine.symbolic_derivative(expr_str)
            self.status.config(text=f"f'(x) = {deriv}")

        except Exception as e:
            self.status.config(text=f"Error: {str(e)[:80]}", fg="#FF5252")

    def _redraw(self):
        try:
            x_vals = np.linspace(-5, 5, 600)

            # Evaluate f
            y_vals = self.func(x_vals, **self._get_param_values())

            self.line_f.set_data(x_vals, y_vals)

            # Current point
            x0 = self.x0_var.get()
            try:
                y0 = float(self.func(x0, **self._get_param_values()))
            except Exception:
                y0 = 0

            self.point.set_data([x0], [y0])

            # Tangent line
            try:
                slope = self.engine.evaluate_at_point(
                    str(self.current_expr),
                    'x', x0
                )
                # Better: use symbolic derivative evaluated at x0
                deriv_expr = self.engine.symbolic_derivative(str(self.current_expr))
                slope_sym = float(deriv_expr.subs(sp.Symbol('x'), x0))
            except Exception:
                slope_sym = 0.0

            dx = 1.2
            self.line_tangent.set_data(
                [x0 - dx, x0 + dx],
                [y0 - slope_sym * dx, y0 + slope_sym * dx]
            )

            # Secant line
            h = self.h_var.get()
            try:
                y1 = float(self.func(x0 + h, **self._get_param_values()))
                slope_sec = (y1 - y0) / h if abs(h) > 1e-9 else slope_sym
            except Exception:
                slope_sec = slope_sym
                y1 = y0

            self.line_secant.set_data(
                [x0, x0 + h],
                [y0, y1]
            )

            self.canvas.draw_idle()

        except Exception as e:
            self.status.config(text=f"Plot error: {e}", fg="#FF5252")

    def _get_param_values(self):
        """Return current parameter values for lambdified function."""
        # Extend this later for dynamic parameters
        return {"a": 1.0, "b": 1.0}

    def _on_x0_change(self, val):
        self._redraw()

    def _on_h_change(self, val):
        self._redraw()

    def animate_limit(self):
        """Beautiful animation showing secant → tangent as h shrinks."""
        h_values = np.linspace(self.h_var.get(), 0.001, 35)

        def update(frame):
            h = h_values[frame]
            self.h_var.set(h)
            self._redraw()
            return self.line_secant,

        self.anim = animation.FuncAnimation(
            self.fig, update, frames=len(h_values),
            interval=65, repeat=False, blit=False
        )
        self.canvas.draw()


class Grapher2DFrame(tk.Frame):
    """
    Main container for 2D graphing capabilities.
    Currently hosts the Derivative Explorer as the flagship demo.
    """

    def __init__(self, parent, engine: MathEngine):
        super().__init__(parent, bg="#202020")
        self.engine = engine

        # Header
        header = tk.Frame(self, bg="#1A1A1A")
        header.pack(fill="x")
        tk.Label(header, text="2D Grapher & Calculus Visualizations",
                 bg="#1A1A1A", fg="#FFFFFF", font=("Segoe UI", 14, "bold")).pack(pady=6)

        # Currently we lead with the Derivative Explorer — the highest educational value
        self.derivative_explorer = DerivativeExplorer(self, engine)
        self.derivative_explorer.pack(fill="both", expand=True)

        # Future tabs / modes can be added here (Riemann Studio, Taylor Playground, etc.)
