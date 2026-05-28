#!/usr/bin/env python3
"""
Riemann / Integral Studio — High-quality educational visualization for MathForge.

Embeddable Tkinter Frame that demonstrates the definition of the definite integral
via Riemann sums and the Trapezoidal rule.

Key Features:
- Live f(x) entry with full MathEngine support (SymPy parsing, ^ power, implicit mult)
- Parameters (k, a, b, m, c, ...) auto-detected and given live dark sliders (independent of integral bounds)
- Bounds a (lower), b (upper) via synced sliders + entries
- Four classic summation methods with correct mathematics and beautiful shaded graphics
- Live n slider (1 to 220 partitions) — everything redraws instantly
- "Animate Convergence" button: n increases stepwise while you watch the shaded regions
  refine and approach the true area
- Side panel: symbolic exact integral (via MathEngine), current numeric approximation,
  absolute + relative error (when closed form exists)
- Matplotlib embedded with NavigationToolbar (pan/zoom/save)
- Perfect dark theme matching the rest of MathForge / Grapher2D
- Rich educational inline comments explaining *why* each method works and its error behavior

Mathematical Notes (for developers & curious users):
- All methods converge to ∫_a^b f(x) dx as n→∞ for continuous f (by definition of Riemann integral).
- Left/Right Riemann: O(1/n) error for smooth f; biased (under/over) on monotonic functions.
- Midpoint: O(1/n²) — usually much better than left/right for same n.
- Trapezoidal: O(1/n²) composite rule; equivalent to averaging left + right.
- The visual patches (rectangles vs. slanted trapezoids) make the convergence and bias visceral.

Usage (embeddable):
    from app.core.math_engine import MathEngine
    from app.calculus.riemann_studio import RiemannStudio, RiemannStudioFrame

    engine = MathEngine()
    studio = RiemannStudio(parent_frame, engine)
    # or
    container = RiemannStudioFrame(parent, engine)
    container.pack(...)

Run directly for instant demo:
    python -m app.calculus.riemann_studio
    # or from project root: python app/calculus/riemann_studio.py (with path fix)

Part of MathForge — making calculus click visually.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Callable

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Polygon

# Use the single source of truth for all symbolic + numeric math
from app.core.math_engine import MathEngine, MathEngineError


# =============================================================================
# DARK THEME — identical to Grapher2D and the rest of MathForge for consistency
# =============================================================================
DARK = {
    "bg": "#202020",
    "panel": "#1A1A1A",
    "display": "#2D2D2D",
    "btn": "#3A3A3A",
    "btn_hover": "#4A4A4A",
    "accent": "#0078D4",
    "text": "#FFFFFF",
    "secondary": "#B0B0B0",
    "success": "#4ADE80",
    "warning": "#FACC15",
    "error": "#F87171",
    "grid": "#444444",
    "spine": "#555555",
}

# Visual constants for the integral visualization (high contrast on dark)
RIEMANN_FILL = "#00D4FF"      # bright cyan — the "area under construction"
CURVE_COLOR = "#7CFC00"       # vivid green for f(x)
PARTITION_COLOR = "#888888"   # subtle vertical lines
SAMPLE_POINT_COLOR = "#FFEB3B"  # yellow dots for the chosen sample points (left/right/mid)
TRAP_EDGE = "#FF79C6"         # pinkish for trapezoid emphasis


# =============================================================================
# THE MAIN EMBEDDABLE COMPONENT
# =============================================================================
class RiemannStudio(tk.Frame):
    """
    The core reusable Riemann / Integral Studio widget.

    This is a complete self-contained educational laboratory for understanding
    how finite sums become the definite integral.

    All heavy lifting (parsing, symbolic integration, fast vectorized evaluation)
    is delegated to the injected MathEngine instance.
    """

    # Method labels (order matters for radiobuttons)
    METHODS = ["Left Riemann", "Right Riemann", "Midpoint", "Trapezoidal"]

    def __init__(self, parent: tk.Misc, engine: MathEngine) -> None:
        super().__init__(parent, bg=DARK["bg"])
        self.engine = engine

        # ------------------------------------------------------------------
        # Core mathematical state
        # ------------------------------------------------------------------
        self.func_str: str = "x**2"          # current f(x) expression
        self.a: float = 0.0                   # lower limit
        self.b: float = 2.0                   # upper limit
        self.n: int = 10                      # number of partitions
        self.method: str = "Left Riemann"

        # Dynamic parameters discovered from the expression (e.g. k, m, c)
        # These are completely independent of the integration bounds a/b
        self.params: dict[str, float] = {}
        self.param_vars: dict[str, tk.DoubleVar] = {}
        self.param_scales: dict[str, tk.Scale] = {}

        # Tk variables (two-way binding where possible)
        self.func_var = tk.StringVar(value=self.func_str)
        self.a_var = tk.DoubleVar(value=self.a)
        self.b_var = tk.DoubleVar(value=self.b)
        self.n_var = tk.IntVar(value=self.n)
        self.method_var = tk.StringVar(value=self.method)

        # For debounced updates from text entries
        self._update_after_id: str | None = None

        # Matplotlib persistent references
        self.fig: Figure | None = None
        self.ax = None
        self.canvas: FigureCanvasTkAgg | None = None
        self.toolbar = None

        # Build everything
        self._build_ui()
        self._setup_plot()

        # Initial render
        self._on_settings_change(full_rebuild=True)

    # -------------------------------------------------------------------------
    # UI CONSTRUCTION — clean, dense, educational, dark-themed
    # -------------------------------------------------------------------------
    def _build_ui(self) -> None:
        # === HEADER ===
        header = tk.Frame(self, bg=DARK["panel"], height=38)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Riemann / Integral Studio",
            bg=DARK["panel"],
            fg=DARK["text"],
            font=("Segoe UI", 15, "bold"),
        ).pack(side="left", padx=14, pady=6)

        tk.Label(
            header,
            text="Watch finite sums converge to the exact area under the curve",
            bg=DARK["panel"],
            fg=DARK["secondary"],
            font=("Segoe UI", 9),
        ).pack(side="left", padx=8)

        # === FUNCTION + BOUNDS ROW ===
        top_controls = tk.Frame(self, bg=DARK["bg"])
        top_controls.pack(fill="x", padx=8, pady=(6, 3))

        # Function entry (primary input)
        func_frame = tk.Frame(top_controls, bg=DARK["bg"])
        func_frame.pack(side="left", fill="x", expand=True)

        tk.Label(
            func_frame, text="f(x) =", bg=DARK["bg"], fg=DARK["text"],
            font=("Segoe UI", 10, "bold")
        ).pack(side="left", padx=(0, 4))

        func_entry = ttk.Entry(
            func_frame, textvariable=self.func_var, width=42,
            font=("Consolas", 11)
        )
        func_entry.pack(side="left", fill="x", expand=True, padx=2)
        func_entry.bind("<Return>", lambda e: self._schedule_update(full_rebuild=True))
        func_entry.bind("<FocusOut>", lambda e: self._schedule_update(full_rebuild=True))

        # Presets (educational quick starts)
        preset_frame = tk.Frame(top_controls, bg=DARK["bg"])
        preset_frame.pack(side="left", padx=8)

        presets = [
            ("x² [0,2]", "x**2", 0.0, 2.0),
            ("sin(x) [0,π]", "sin(x)", 0.0, np.pi),
            ("e^{-x} [0,3]", "exp(-x)", 0.0, 3.0),
            ("k·x² [0,2]", "k*x**2", 0.0, 2.0),
            ("cos(2x)+0.5 [−π,π]", "cos(2*x)+0.5", -np.pi, np.pi),
        ]
        for label, fstr, lo, hi in presets:
            b = ttk.Button(
                preset_frame, text=label, width=14,
                command=lambda fs=fstr, l=lo, h=hi: self._apply_preset(fs, l, h)
            )
            b.pack(side="left", padx=1)

        # === BOUNDS + METHOD + n (main interactive controls) ===
        ctrl_row = tk.Frame(self, bg=DARK["bg"])
        ctrl_row.pack(fill="x", padx=8, pady=2)

        # Bounds (a / b) — sliders + entries for "text or sliders"
        bounds_frame = tk.Frame(ctrl_row, bg=DARK["panel"])
        bounds_frame.pack(side="left", padx=(0, 12), fill="x")

        tk.Label(
            bounds_frame, text="Bounds", bg=DARK["panel"], fg=DARK["secondary"],
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=6, pady=(2, 0))

        # Lower a
        a_row = tk.Frame(bounds_frame, bg=DARK["panel"])
        a_row.pack(fill="x", padx=4, pady=1)
        tk.Label(a_row, text="a (lower)", bg=DARK["panel"], fg=DARK["text"], width=8,
                 font=("Segoe UI", 9)).pack(side="left")
        self.a_scale = tk.Scale(
            a_row, from_=-10, to=10, resolution=0.01, orient="horizontal",
            length=150, variable=self.a_var,
            command=lambda v: self._on_bound_change(),
            bg=DARK["panel"], fg=DARK["text"], troughcolor=DARK["btn"],
            highlightthickness=0, activebackground=DARK["accent"]
        )
        self.a_scale.pack(side="left", padx=3)
        a_entry = ttk.Entry(a_row, textvariable=self.a_var, width=7, font=("Consolas", 9))
        a_entry.pack(side="left", padx=2)
        a_entry.bind("<Return>", lambda e: self._on_bound_change())

        # Upper b
        b_row = tk.Frame(bounds_frame, bg=DARK["panel"])
        b_row.pack(fill="x", padx=4, pady=1)
        tk.Label(b_row, text="b (upper)", bg=DARK["panel"], fg=DARK["text"], width=8,
                 font=("Segoe UI", 9)).pack(side="left")
        self.b_scale = tk.Scale(
            b_row, from_=-10, to=10, resolution=0.01, orient="horizontal",
            length=150, variable=self.b_var,
            command=lambda v: self._on_bound_change(),
            bg=DARK["panel"], fg=DARK["text"], troughcolor=DARK["btn"],
            highlightthickness=0, activebackground=DARK["accent"]
        )
        self.b_scale.pack(side="left", padx=3)
        b_entry = ttk.Entry(b_row, textvariable=self.b_var, width=7, font=("Consolas", 9))
        b_entry.pack(side="left", padx=2)
        b_entry.bind("<Return>", lambda e: self._on_bound_change())

        # Method selection — classic radio buttons (very clear for teaching)
        method_frame = tk.Frame(ctrl_row, bg=DARK["panel"])
        method_frame.pack(side="left", padx=8, fill="y")

        tk.Label(
            method_frame, text="Summation Method", bg=DARK["panel"], fg=DARK["secondary"],
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=6, pady=(2, 1))

        for m in self.METHODS:
            rb = tk.Radiobutton(
                method_frame,
                text=m,
                variable=self.method_var,
                value=m,
                bg=DARK["panel"],
                fg=DARK["text"],
                selectcolor=DARK["display"],
                activebackground=DARK["panel"],
                font=("Segoe UI", 9),
                command=self._on_method_change,
            )
            rb.pack(anchor="w", padx=8, pady=0)

        # n (partitions) — the star control, huge visual impact
        n_frame = tk.Frame(ctrl_row, bg=DARK["panel"])
        n_frame.pack(side="left", padx=8, fill="x", expand=True)

        n_header = tk.Frame(n_frame, bg=DARK["panel"])
        n_header.pack(fill="x")
        tk.Label(n_header, text="Partitions  n", bg=DARK["panel"], fg=DARK["secondary"],
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=6)
        self.n_label = tk.Label(
            n_header, text="10", bg=DARK["panel"], fg=DARK["accent"],
            font=("Consolas", 12, "bold"), width=5
        )
        self.n_label.pack(side="left")

        self.n_scale = tk.Scale(
            n_frame,
            from_=1, to=220, resolution=1, orient="horizontal",
            length=260, variable=self.n_var,
            command=self._on_n_change,
            bg=DARK["panel"], fg=DARK["text"], troughcolor=DARK["btn"],
            highlightthickness=0, activebackground=DARK["accent"]
        )
        self.n_scale.pack(fill="x", padx=6, pady=(0, 2))

        # Action buttons
        btn_frame = tk.Frame(n_frame, bg=DARK["panel"])
        btn_frame.pack(fill="x", padx=4, pady=2)

        ttk.Button(
            btn_frame, text="▶ Animate n → 220", width=16,
            command=self.animate_convergence
        ).pack(side="left", padx=2)
        ttk.Button(
            btn_frame, text="Reset", width=8,
            command=self._reset_all
        ).pack(side="left", padx=2)
        ttk.Button(
            btn_frame, text="Recompute", width=10,
            command=lambda: self._on_settings_change(full_rebuild=True)
        ).pack(side="left", padx=2)

        # === DYNAMIC PARAMETER SLIDERS (rebuilt when f(x) changes) ===
        self.param_section = tk.Frame(self, bg=DARK["bg"])
        self.param_section.pack(fill="x", padx=8, pady=(2, 4))

        param_header = tk.Frame(self.param_section, bg=DARK["bg"])
        param_header.pack(fill="x")
        tk.Label(
            param_header, text="Live Parameters (discovered automatically from f(x))",
            bg=DARK["bg"], fg=DARK["secondary"], font=("Segoe UI", 9)
        ).pack(side="left")
        ttk.Button(
            param_header, text="Reset params → 1.0", width=16,
            command=self._reset_params
        ).pack(side="right")

        self.param_container = tk.Frame(self.param_section, bg=DARK["bg"])
        self.param_container.pack(fill="x", pady=2)

        # === MAIN CONTENT: PLOT + SIDE PANEL ===
        content = tk.Frame(self, bg=DARK["bg"])
        content.pack(fill="both", expand=True, padx=6, pady=4)

        # Plot takes most space
        plot_container = tk.Frame(content, bg=DARK["bg"])
        plot_container.pack(side="left", fill="both", expand=True)

        self.fig = Figure(figsize=(8.8, 5.6), dpi=100, facecolor=DARK["bg"])
        self.ax = self.fig.add_subplot(111, facecolor=DARK["display"])

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_container)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas, plot_container, pack_toolbar=False)
        self.toolbar.pack(fill="x")

        # === RIGHT SIDE PANEL — numbers + education ===
        side = tk.Frame(content, bg=DARK["panel"], width=260)
        side.pack(side="right", fill="y", padx=(6, 0))
        side.pack_propagate(False)

        tk.Label(
            side, text="RESULTS & ANALYSIS", bg=DARK["panel"], fg=DARK["accent"],
            font=("Segoe UI", 10, "bold")
        ).pack(fill="x", padx=8, pady=(6, 2))

        # Approximation block
        self.approx_label = tk.Label(
            side, text="Riemann Sum ≈ —", bg=DARK["panel"], fg=DARK["success"],
            font=("Consolas", 13, "bold"), anchor="w"
        )
        self.approx_label.pack(fill="x", padx=8, pady=2)

        self.dx_label = tk.Label(
            side, text="Δx = —   •   n = —", bg=DARK["panel"], fg=DARK["secondary"],
            font=("Consolas", 9), anchor="w"
        )
        self.dx_label.pack(fill="x", padx=8)

        # Exact / symbolic block
        tk.Label(
            side, text="EXACT INTEGRAL (SymPy)", bg=DARK["panel"], fg=DARK["warning"],
            font=("Segoe UI", 9, "bold")
        ).pack(fill="x", padx=8, pady=(8, 1))

        self.exact_label = tk.Label(
            side, text="∫ f(x) dx = —", bg=DARK["panel"], fg=DARK["text"],
            font=("Consolas", 9), anchor="w", wraplength=240, justify="left"
        )
        self.exact_label.pack(fill="x", padx=8, pady=1)

        self.error_label = tk.Label(
            side, text="Error vs exact: —", bg=DARK["panel"], fg=DARK["secondary"],
            font=("Consolas", 9), anchor="w"
        )
        self.error_label.pack(fill="x", padx=8, pady=(0, 4))

        # Educational method explanation (updates with selection)
        tk.Label(
            side, text="METHOD EXPLAINED", bg=DARK["panel"], fg=DARK["accent"],
            font=("Segoe UI", 9, "bold")
        ).pack(fill="x", padx=8, pady=(6, 1))

        self.method_explain = tk.Label(
            side,
            text="",
            bg=DARK["panel"],
            fg=DARK["secondary"],
            font=("Segoe UI", 8),
            anchor="nw",
            justify="left",
            wraplength=238,
        )
        self.method_explain.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        # Footer hint
        tk.Label(
            side,
            text="Tip: Drag/zoom the plot • Change n live • Animate to see convergence in action",
            bg=DARK["panel"], fg="#666666", font=("Segoe UI", 7), wraplength=240
        ).pack(fill="x", padx=8, pady=(0, 6))

        # Global status
        self.status = tk.Label(
            self, text="", bg=DARK["bg"], fg=DARK["success"],
            font=("Consolas", 9), anchor="w"
        )
        self.status.pack(fill="x", padx=8, pady=(0, 4))

        # Wire var traces for extra live feedback
        self.n_var.trace_add("write", lambda *a: self._update_n_label())
        self.a_var.trace_add("write", lambda *a: self._on_bound_change(from_trace=True))
        self.b_var.trace_add("write", lambda *a: self._on_bound_change(from_trace=True))

    def _update_n_label(self) -> None:
        self.n_label.config(text=str(self.n_var.get()))

    # -------------------------------------------------------------------------
    # EVENT HANDLERS & STATE MANAGEMENT
    # -------------------------------------------------------------------------
    def _schedule_update(self, full_rebuild: bool = False, delay: int = 180) -> None:
        """Debounce rapid typing in the function entry."""
        if self._update_after_id:
            self.after_cancel(self._update_after_id)
        self._update_after_id = self.after(
            delay, lambda: self._on_settings_change(full_rebuild=full_rebuild)
        )

    def _on_settings_change(self, full_rebuild: bool = False) -> None:
        """Central refresh point. Called after any significant user change."""
        self.func_str = self.func_var.get().strip()
        self.a = float(self.a_var.get())
        self.b = float(self.b_var.get())
        self.n = int(self.n_var.get())
        self.method = self.method_var.get()

        if full_rebuild:
            self._prepare_parameters()
            self._rebuild_param_sliders()

        self._update_plot()
        self._update_info_panel()

    def _on_bound_change(self, from_trace: bool = False) -> None:
        """Bounds changed via slider or entry."""
        self.a = float(self.a_var.get())
        self.b = float(self.b_var.get())
        # No need to rebuild params; just replot + info (cheap)
        self._update_plot()
        self._update_info_panel()

    def _on_n_change(self, val: str) -> None:
        self.n = int(float(val))
        self._update_plot()
        self._update_info_panel()

    def _on_method_change(self) -> None:
        self.method = self.method_var.get()
        self._update_method_explanation()
        self._update_plot()
        self._update_info_panel()

    def _apply_preset(self, fstr: str, a: float, b: float) -> None:
        """Load a curated educational example instantly."""
        self.func_var.set(fstr)
        self.a_var.set(a)
        self.b_var.set(b)
        self.n_var.set(12)  # nice starting n for demos
        self._on_settings_change(full_rebuild=True)

    def _reset_all(self) -> None:
        """Return to a clean, simple starting state."""
        self.func_var.set("x**2")
        self.a_var.set(0.0)
        self.b_var.set(2.0)
        self.n_var.set(10)
        self.method_var.set("Left Riemann")
        self._reset_params(silent=True)
        self._on_settings_change(full_rebuild=True)
        self.status.config(text="Reset to default educational example (x² on [0,2])", fg=DARK["secondary"])
        self.after(1600, lambda: self.status.config(text=""))

    def _reset_params(self, silent: bool = False) -> None:
        for p in list(self.params.keys()):
            self.params[p] = 1.0
            if p in self.param_vars:
                self.param_vars[p].set(1.0)
        if not silent:
            self._update_plot()
            self._update_info_panel()

    # -------------------------------------------------------------------------
    # PARAMETER DISCOVERY (identical philosophy to Grapher2D)
    # -------------------------------------------------------------------------
    def _prepare_parameters(self) -> None:
        """Discover free symbols besides 'x'. These become live parameter sliders."""
        try:
            expr = self.engine.parse(self.func_str)
            free = self.engine.get_free_symbols(expr)
            new_params = sorted([s for s in free if s != "x"])
        except Exception:
            new_params = []

        # Preserve previous values when possible
        for p in new_params:
            if p not in self.params:
                self.params[p] = 1.0

        # Drop stale
        for p in list(self.params.keys()):
            if p not in new_params:
                self.params.pop(p, None)

        self.current_param_list = new_params

    def _rebuild_param_sliders(self) -> None:
        """Dynamically create or destroy parameter sliders. Called on function change."""
        for w in self.param_container.winfo_children():
            w.destroy()
        self.param_vars.clear()
        self.param_scales.clear()

        if not self.current_param_list:
            tk.Label(
                self.param_container,
                text="No extra parameters — pure function of x only",
                bg=DARK["bg"], fg=DARK["secondary"], font=("Segoe UI", 9, "italic")
            ).pack(anchor="w", padx=4)
            return

        row = tk.Frame(self.param_container, bg=DARK["bg"])
        row.pack(fill="x")

        for p in self.current_param_list:
            col = tk.Frame(row, bg=DARK["bg"])
            col.pack(side="left", padx=6, fill="x", expand=True)

            val = self.params.get(p, 1.0)
            var = tk.DoubleVar(value=val)
            self.param_vars[p] = var

            tk.Label(col, text=f"{p} =", bg=DARK["bg"], fg=DARK["text"],
                     font=("Segoe UI", 9)).pack(side="left")

            val_lbl = tk.Label(
                col, text=f"{val:.3f}", bg=DARK["bg"], fg=DARK["accent"],
                font=("Consolas", 9, "bold"), width=6
            )
            val_lbl.pack(side="left", padx=3)

            # Reasonable slider ranges per common parameter names
            if p in ("k", "a", "b", "c", "m"):
                lo, hi, res = -6.0, 6.0, 0.05
            elif p in ("freq", "omega", "r"):
                lo, hi, res = 0.1, 10.0, 0.05
            else:
                lo, hi, res = -4.0, 4.0, 0.05

            scale = tk.Scale(
                col, from_=lo, to=hi, resolution=res, orient="horizontal",
                length=110, variable=var,
                command=lambda v, pp=p, lbl=val_lbl: self._on_param_change(pp, v, lbl),
                bg=DARK["bg"], fg=DARK["text"], troughcolor=DARK["btn"],
                highlightthickness=0, activebackground=DARK["accent"]
            )
            scale.pack(side="left", fill="x", expand=True)
            self.param_scales[p] = scale

            # Live label update
            var.trace_add(
                "write",
                lambda *_, pp=p, lbl=val_lbl, vv=var: lbl.config(text=f"{vv.get():.3f}")
            )

    def _on_param_change(self, p: str, val: str, value_label: tk.Label) -> None:
        try:
            self.params[p] = float(val)
        except Exception:
            self.params[p] = 1.0
        # Light update — params affect heights but not structure
        self._update_plot(full=False)
        self._update_info_panel()

    # -------------------------------------------------------------------------
    # CORE MATHEMATICS — the four methods with excellent comments
    # -------------------------------------------------------------------------
    def _get_callable(self) -> Callable:
        """
        Return a fast vectorized function f(*param_values, x_array) → y_array
        using the MathEngine's lambdify (NumPy backend).
        """
        try:
            expr = self.engine.parse(self.func_str)
            free = self.engine.get_free_symbols(expr)
            param_names = [s for s in sorted(free) if s != "x"]
            variables = param_names + ["x"]
            return self.engine.lambdify(self.func_str, variables=variables)
        except MathEngineError as e:
            raise MathEngineError(f"Could not prepare f(x): {e}") from e

    def _compute_approx(self) -> float:
        """
        Compute the chosen Riemann / Trapezoidal sum for current state.

        All implementations are mathematically correct and vectorized.
        """
        if abs(self.a - self.b) < 1e-12:
            return 0.0

        lo, hi = min(self.a, self.b), max(self.a, self.b)
        sign = 1.0 if self.a <= self.b else -1.0
        dx = (hi - lo) / self.n

        # Get the vectorized callable
        f = self._get_callable()
        param_names = sorted([p for p in self.params.keys()])  # deterministic
        param_vals = [self.params.get(p, 1.0) for p in param_names]

        # Partition points
        x = np.linspace(lo, hi, self.n + 1)

        if self.method == "Left Riemann":
            # Uses the LEFT endpoint of every subinterval [x_i, x_{i+1}]
            # Classic introductory method. Underestimates increasing positive functions.
            heights = f(*(param_vals + [x[:-1]]))
            total = np.sum(heights) * dx

        elif self.method == "Right Riemann":
            # Uses the RIGHT endpoint of every subinterval
            # Overestimates increasing positive functions. Same O(1/n) convergence.
            heights = f(*(param_vals + [x[1:]]))
            total = np.sum(heights) * dx

        elif self.method == "Midpoint":
            # Uses the midpoint of every subinterval — dramatically better accuracy
            # for the same n. The error term involves f'' and is O(1/n²).
            x_mid = (x[:-1] + x[1:]) / 2.0
            heights = f(*(param_vals + [x_mid]))
            total = np.sum(heights) * dx

        elif self.method == "Trapezoidal":
            # Composite trapezoidal rule.
            # Connects consecutive sample points with straight lines (trapezoids).
            # Error O(1/n²). Mathematically the average of left + right sums.
            y = f(*(param_vals + [x]))
            total = (dx / 2.0) * (y[0] + 2.0 * np.sum(y[1:-1]) + y[-1])
        else:
            total = 0.0

        return sign * float(total)

    # -------------------------------------------------------------------------
    # PLOTTING — beautiful, instantly updating shaded visualization
    # -------------------------------------------------------------------------
    def _setup_plot(self) -> None:
        if self.ax is None:
            return
        self.ax.set_xlabel("x", color=DARK["secondary"])
        self.ax.set_ylabel("f(x)", color=DARK["secondary"])
        self.ax.tick_params(colors=DARK["secondary"])
        for spine in self.ax.spines.values():
            spine.set_color(DARK["spine"])
        self.ax.grid(True, alpha=0.25, color=DARK["grid"], linestyle="-")

    def _update_plot(self, full: bool = True) -> None:
        """Redraw the function curve + the current approximation shading."""
        if self.ax is None or self.canvas is None:
            return

        try:
            self.ax.clear()
            self.ax.set_facecolor(DARK["display"])
            self.ax.tick_params(colors=DARK["secondary"])
            for spine in self.ax.spines.values():
                spine.set_color(DARK["spine"])
            self.ax.set_xlabel("x", color=DARK["secondary"])
            self.ax.set_ylabel("f(x)", color=DARK["secondary"])
            self.ax.grid(True, alpha=0.22, color=DARK["grid"])

            # Dense curve for reference (always beautiful)
            lo, hi = min(self.a, self.b), max(self.a, self.b)
            if abs(hi - lo) < 1e-9:
                hi = lo + 1.0

            x_dense = np.linspace(lo, hi, 650)
            f = self._get_callable()
            param_names = sorted(p for p in self.params.keys())
            param_vals = [self.params.get(p, 1.0) for p in param_names]

            y_dense = np.asarray(f(*(param_vals + [x_dense])), dtype=float)
            mask = np.isfinite(y_dense)
            if np.any(mask):
                self.ax.plot(
                    x_dense[mask], y_dense[mask],
                    color=CURVE_COLOR, linewidth=2.4, label=f"f(x) = {self.func_str[:42]}",
                    zorder=5
                )

            # === THE VISUAL RIEMANN / TRAPEZOIDAL SHADING ===
            dx = (hi - lo) / max(1, self.n)
            x_parts = np.linspace(lo, hi, self.n + 1)
            y_parts = np.asarray(f(*(param_vals + [x_parts])), dtype=float)

            fill_alpha = 0.38
            edge_alpha = 0.85

            if self.method in ("Left Riemann", "Right Riemann", "Midpoint"):
                # Rectangle patches
                for i in range(self.n):
                    if self.method == "Left Riemann":
                        x0 = x_parts[i]
                        height = y_parts[i]
                        sample_x = x0
                    elif self.method == "Right Riemann":
                        x0 = x_parts[i + 1] - dx
                        height = y_parts[i + 1]
                        sample_x = x_parts[i + 1]
                    else:  # Midpoint
                        x0 = x_parts[i]
                        height = y_parts[i] if i + 1 < len(y_parts) else 0.0
                        # recompute midpoint height for accuracy
                        x_mid = x0 + dx * 0.5
                        height = float(f(*(param_vals + [np.array([x_mid])]))[0])

                    rect = Rectangle(
                        (x0, 0), dx, height,
                        facecolor=RIEMANN_FILL,
                        edgecolor=PARTITION_COLOR,
                        linewidth=0.7,
                        alpha=fill_alpha,
                        zorder=2
                    )
                    self.ax.add_patch(rect)

                    # Small marker at the sample point used by the method
                    self.ax.plot(
                        sample_x if self.method != "Midpoint" else (x0 + dx * 0.5),
                        height,
                        "o",
                        color=SAMPLE_POINT_COLOR,
                        markersize=3.5,
                        zorder=4,
                        alpha=0.9
                    )

            elif self.method == "Trapezoidal":
                # Slanted trapezoids as polygons — visually distinct and correct
                for i in range(self.n):
                    x0, x1 = x_parts[i], x_parts[i + 1]
                    y0, y1 = y_parts[i], y_parts[i + 1]
                    # Polygon vertices: bottom-left, top-left, top-right, bottom-right
                    verts = [(x0, 0), (x0, y0), (x1, y1), (x1, 0)]
                    poly = Polygon(
                        verts,
                        facecolor=RIEMANN_FILL,
                        edgecolor=TRAP_EDGE,
                        linewidth=1.1,
                        alpha=fill_alpha,
                        zorder=2
                    )
                    self.ax.add_patch(poly)

                    # Sample points at both ends (characteristic of trapezoidal)
                    self.ax.plot([x0, x1], [y0, y1], "o", color=SAMPLE_POINT_COLOR,
                                 markersize=3.2, zorder=4, alpha=0.85)

            # Vertical partition lines (subtle but informative)
            for xv in x_parts:
                self.ax.axvline(xv, color=PARTITION_COLOR, linewidth=0.6, alpha=0.45, zorder=1)

            # Auto y limits with generous padding (important when function goes negative)
            y_all = y_dense[mask] if np.any(mask) else np.array([0.0])
            y_min, y_max = float(np.min(y_all)), float(np.max(y_all))
            y_pad = max(0.6, (y_max - y_min) * 0.18) if y_max > y_min else 1.0
            self.ax.set_ylim(y_min - y_pad, y_max + y_pad)
            self.ax.set_xlim(lo - dx * 0.5, hi + dx * 0.5)

            # Title with live info
            approx = self._compute_approx()
            title = f"{self.method}  •  n = {self.n}  •  Δx = {dx:.5g}  •  Sum ≈ {approx:.6g}"
            self.ax.set_title(title, color=DARK["text"], fontsize=10, pad=6)

            # Legend
            self.ax.legend(
                loc="upper right", fontsize=8,
                facecolor=DARK["panel"], edgecolor="#555555", labelcolor="#DDDDDD"
            )

            self.canvas.draw_idle()

            # Clear any previous transient error
            if "Error" in self.status.cget("text"):
                self.status.config(text="")

        except MathEngineError as me:
            self.status.config(text=f"Math error: {me}", fg=DARK["error"])
            self.ax.clear()
            self.ax.text(0.5, 0.5, "Invalid expression or parameters",
                         ha="center", va="center", color=DARK["error"], transform=self.ax.transAxes)
            self.canvas.draw_idle()
        except Exception as e:
            self.status.config(text=f"Plot error: {str(e)[:80]}", fg=DARK["error"])

    # -------------------------------------------------------------------------
    # INFO PANEL — symbolic + numeric + pedagogy
    # -------------------------------------------------------------------------
    def _update_info_panel(self) -> None:
        """Update the right-hand analysis panel with exact vs approximate values."""
        try:
            approx = self._compute_approx()
            dx = abs(self.b - self.a) / max(1, self.n)

            self.approx_label.config(text=f"{self.method} ≈ {approx:.8g}")
            self.dx_label.config(text=f"Δx = {dx:.6g}   •   n = {self.n}")

            # Symbolic definite integral via MathEngine (the star feature)
            expr = self.engine.parse(self.func_str)
            integ = self.engine.symbolic_integral(
                expr, var="x", definite=True,
                lower=self.a, upper=self.b
            )
            sym_pretty = self.engine.pretty(integ, use_unicode=True)
            if len(sym_pretty) > 68:
                sym_pretty = sym_pretty[:65] + "…"

            self.exact_label.config(text=f"∫_a^b f(x) dx = {sym_pretty}")

            # Try to get a numeric value for error calculation (handles parameters)
            numeric_exact = None
            try:
                # evaluate_numeric works on the result expression (may contain params)
                param_names = sorted(self.params.keys())
                if param_names:
                    numeric_exact = float(
                        self.engine.evaluate_numeric(integ, {p: self.params[p] for p in param_names})
                    )
                else:
                    numeric_exact = float(self.engine.evaluate_at(integ))
            except Exception:
                pass

            if numeric_exact is not None and np.isfinite(numeric_exact):
                err = abs(approx - numeric_exact)
                rel = (err / abs(numeric_exact)) * 100 if abs(numeric_exact) > 1e-12 else 0.0
                self.error_label.config(
                    text=f"Error = {err:.6g}   ({rel:.2f}%)",
                    fg=DARK["success"] if err < 0.05 * abs(numeric_exact) + 1e-6 else DARK["warning"]
                )
            else:
                self.error_label.config(
                    text="Error vs exact: (no closed form — numerical only)",
                    fg=DARK["secondary"]
                )

            self._update_method_explanation()

        except Exception as e:
            self.exact_label.config(text="Exact integral: (could not compute)")
            self.error_label.config(text=f"Error: {str(e)[:50]}", fg=DARK["error"])

    def _update_method_explanation(self) -> None:
        """Update the live educational blurb for the selected method."""
        explanations = {
            "Left Riemann": "Uses height at LEFT endpoint of each subinterval.\n\n"
                            "Simple to understand. For increasing f > 0 this underestimates "
                            "the true area. Convergence rate is O(1/n).",
            "Right Riemann": "Uses height at RIGHT endpoint of each subinterval.\n\n"
                             "Symmetric to Left. Overestimates increasing positive functions. "
                             "Same first-order convergence.",
            "Midpoint": "Uses height at the MIDPOINT of every subinterval.\n\n"
                        "Dramatically more accurate than left/right for the same n. "
                        "Error involves second derivative → O(1/n²) convergence.",
            "Trapezoidal": "Connects sample points with straight line segments (trapezoids).\n\n"
                           "Equivalent to (Left + Right)/2. Also O(1/n²). Excellent all-rounder "
                           "and the basis for many advanced quadrature rules."
        }
        text = explanations.get(self.method, "")
        self.method_explain.config(text=text)

    # -------------------------------------------------------------------------
    # ANIMATION — the pedagogical money shot
    # -------------------------------------------------------------------------
    def animate_convergence(self) -> None:
        """
        Animate n increasing from current value up to 220.

        This is the single most powerful teaching moment: students literally watch
        the rectangles/trapezoids refine and the numerical value stabilize at the
        exact integral.
        """
        if abs(self.a - self.b) < 1e-9:
            self.status.config(text="Set a ≠ b first", fg=DARK["warning"])
            return

        start_n = max(1, int(self.n_var.get()))
        target = 220
        if start_n >= target:
            start_n = 4

        # Smooth sequence of n values (more steps at beginning for drama)
        n_vals = np.unique(np.linspace(start_n, target, 38).astype(int))

        self.status.config(
            text="▶ Animating convergence... watch the shaded regions approach the exact area",
            fg=DARK["warning"]
        )

        def step(idx: int = 0) -> None:
            if idx >= len(n_vals):
                self.status.config(
                    text="✓ Convergence complete — the sum now matches the integral (within rounding)",
                    fg=DARK["success"]
                )
                self.after(2200, lambda: self.status.config(text=""))
                return

            new_n = int(n_vals[idx])
            self.n_var.set(new_n)
            self.n = new_n
            self._update_plot()
            self._update_info_panel()
            self.canvas.draw_idle()

            # Variable speed: slower at low n so you can see the big rectangles disappear
            delay = 58 if new_n < 35 else (38 if new_n < 90 else 22)
            self.after(delay, lambda: step(idx + 1))

        step(0)

    # -------------------------------------------------------------------------
    # PUBLIC API (for embedding & future scripting)
    # -------------------------------------------------------------------------
    def set_function(self, expr: str, a: float | None = None, b: float | None = None) -> None:
        self.func_var.set(expr)
        if a is not None:
            self.a_var.set(a)
        if b is not None:
            self.b_var.set(b)
        self._on_settings_change(full_rebuild=True)

    def set_method(self, method: str) -> None:
        if method in self.METHODS:
            self.method_var.set(method)
            self._on_method_change()

    def set_partitions(self, n: int) -> None:
        self.n_var.set(max(1, min(220, int(n))))
        self._on_n_change(str(self.n_var.get()))


# =============================================================================
# CONTAINER FRAME (easy drop-in for tabs/notebooks)
# =============================================================================
class RiemannStudioFrame(tk.Frame):
    """
    Ready-to-use titled container. Drop this into any MathForge tab or window.
    """

    def __init__(self, parent: tk.Misc, engine: MathEngine) -> None:
        super().__init__(parent, bg=DARK["bg"])

        header = tk.Frame(self, bg=DARK["panel"])
        header.pack(fill="x")
        tk.Label(
            header,
            text="Riemann Sums & The Definite Integral — Visual Calculus Laboratory",
            bg=DARK["panel"], fg=DARK["text"], font=("Segoe UI", 13, "bold")
        ).pack(pady=6, padx=12, anchor="w")

        self.studio = RiemannStudio(self, engine)
        self.studio.pack(fill="both", expand=True)


# =============================================================================
# STANDALONE DEMO (run this file directly)
# =============================================================================
if __name__ == "__main__":
    # Robust path handling so "python app/calculus/riemann_studio.py" works
    # even when the current working directory is not the project root.
    here = Path(__file__).resolve()
    # Go up three levels: .../calculus/ -> app/ -> windows-calculator/ (contains 'app' package)
    project_root = here.parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    print("Launching Riemann / Integral Studio standalone demo...")
    print("  Using MathEngine for symbolic integrals + fast numeric evaluation")

    root = tk.Tk()
    root.title("Riemann / Integral Studio — MathForge Educational Demo")
    root.geometry("1280x820")
    root.minsize(1080, 680)
    root.configure(bg=DARK["bg"])

    engine = MathEngine(use_numpy=True)

    frame = RiemannStudioFrame(root, engine)
    frame.pack(fill="both", expand=True, padx=4, pady=4)

    # Extra standalone footer
    footer = tk.Label(
        root,
        text="EDUCATIONAL TIP: Try the different methods on x² [0,2]. Then hit 'Animate n → 220' and watch the error drop. "
             "Midpoint and Trapezoidal converge visibly faster than Left/Right. Change parameters with the k-slider on the 'k·x²' preset.",
        bg=DARK["panel"], fg=DARK["secondary"], font=("Segoe UI", 9),
        wraplength=1250, justify="left"
    )
    footer.pack(fill="x", pady=(0, 3))

    root.mainloop()
