#!/usr/bin/env python3
"""
Taylor Series Playground — Interactive educational visualization.

Embeddable Tkinter + Matplotlib component for the MathForge / Windows Calculator ecosystem.

Key Features (as specified):
- User inputs f(x) with full MathEngine parsing (^, implicit *, sin, exp, etc.)
- Slider + buttons + quick-picks for approximation order n = 0..12
- Live-updating plot: original f(x) + current Taylor polynomial T_n(x)
- Expansion point a (editable, clickable on plot to set!)
- Dynamic parameter sliders when f(x) contains free symbols (a, b, k, ...)
- Symbolic polynomial display (pretty-printed)
- Animation: "Build up order by order" with smooth stepping
- Dedicated remainder / error visualization (bottom subplot + max |error| readout)
- Fully powered by MathEngine.symbolic_series + evaluate_numeric (vectorized)
- Professional dark theme matching the rest of the app
- Educational: presets, explanations, click-to-set-center, convergence hints

Usage (embeddable Frame):
    from app.core.math_engine import MathEngine
    from app.calculus.taylor_playground import TaylorPlayground, TaylorPlaygroundFrame

    engine = MathEngine()
    playground = TaylorPlayground(parent, engine)
    playground.pack(fill="both", expand=True)

Or drop the ready-made titled container:
    frame = TaylorPlaygroundFrame(parent, engine)

Standalone demo: python -m app.calculus.taylor_playground
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import time
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib import rcParams

# Shared powerful engine
from app.core.math_engine import MathEngine, MathEngineError


# =============================================================================
# DARK THEME (perfectly consistent with Grapher2D and main app)
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

# Plot colors (high contrast on dark)
FUNC_COLOR = "#00D4FF"        # bright cyan for original
TAYLOR_COLOR = "#FF6B6B"      # warm coral/red for approximation
ERROR_COLOR = "#FACC15"       # yellow/gold for error
CENTER_COLOR = "#A78BFA"      # purple for expansion point marker
GRID_COLOR = DARK["grid"]


class TaylorPlayground(tk.Frame):
    """
    The primary embeddable Taylor Series Playground component.

    Fully self-contained, uses only the injected MathEngine for all symbolic
    and numeric work (no direct SymPy outside engine).
    """

    def __init__(self, parent, engine: MathEngine):
        super().__init__(parent, bg=DARK["bg"])
        self.engine = engine

        # --------------------- Core state ---------------------
        self.func_str: str = "sin(x)"
        self.center: float = 0.0
        self.order: int = 5
        self.xmin: float = -6.0
        self.xmax: float = 6.0

        self.params: dict[str, float] = {}
        self.param_vars: dict[str, tk.DoubleVar] = {}
        self.param_scales: dict[str, tk.Scale] = {}
        self.current_param_list: list[str] = []

        # Current computed objects (for external access / debugging)
        self.current_poly = None
        self.current_f_str = ""
        self.last_max_error: float | None = None

        # Tk variables
        self.func_var = tk.StringVar(value=self.func_str)
        self.center_var = tk.StringVar(value="0")
        self.order_var = tk.IntVar(value=self.order)
        self.xmin_var = tk.StringVar(value=str(self.xmin))
        self.xmax_var = tk.StringVar(value=str(self.xmax))

        self.show_original_var = tk.BooleanVar(value=True)
        self.show_error_var = tk.BooleanVar(value=True)
        self.show_center_line_var = tk.BooleanVar(value=True)

        self.animating = False
        self._anim_after_id = None

        # UI references
        self.poly_text: tk.Text | None = None
        self.status_label: tk.Label | None = None
        self.error_label: tk.Label | None = None
        self.info_label: tk.Label | None = None
        self.order_label: tk.Label | None = None

        # Matplotlib
        self.fig: Figure | None = None
        self.ax1 = None
        self.ax2 = None
        self.canvas: FigureCanvasTkAgg | None = None
        self.toolbar = None

        # Artists (for fast redraws if desired)
        self.line_f = None
        self.line_taylor = None
        self.line_error = None
        self.center_vline = None
        self.center_marker = None

        # Build everything
        self._build_ui()
        self._setup_plot()
        self._connect_events()

        # Boot with nice initial state
        self._on_func_change(initial=True)

    # -------------------------------------------------------------------------
    # UI CONSTRUCTION
    # -------------------------------------------------------------------------
    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=DARK["panel"], height=38)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Taylor Series Playground",
            bg=DARK["panel"],
            fg=DARK["text"],
            font=("Segoe UI", 15, "bold"),
        ).pack(side="left", padx=14, pady=6)

        tk.Label(
            header,
            text="Watch polynomials converge to the true function • Click plot to set center a",
            bg=DARK["panel"],
            fg=DARK["secondary"],
            font=("Segoe UI", 9),
        ).pack(side="left", padx=12, pady=8)

        # ===================== INPUT CONTROLS =====================
        ctrl = tk.Frame(self, bg=DARK["bg"])
        ctrl.pack(fill="x", padx=8, pady=(6, 2))

        # Function row
        func_row = tk.Frame(ctrl, bg=DARK["bg"])
        func_row.pack(fill="x", pady=2)

        tk.Label(func_row, text="f(x) =", bg=DARK["bg"], fg=DARK["text"],
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=(2, 6))

        self.func_entry = ttk.Entry(func_row, textvariable=self.func_var, width=42,
                                    font=("Consolas", 11))
        self.func_entry.pack(side="left", fill="x", expand=True, padx=2)
        self.func_entry.bind("<Return>", lambda e: self._on_func_change())
        self.func_entry.bind("<FocusOut>", lambda e: self._on_func_change())

        ttk.Button(func_row, text="Update", command=self._on_func_change, width=9).pack(side="left", padx=4)

        # Center + Order row
        center_order = tk.Frame(ctrl, bg=DARK["bg"])
        center_order.pack(fill="x", pady=4)

        # Center a
        tk.Label(center_order, text="Expansion point  a =", bg=DARK["bg"], fg=DARK["text"],
                 font=("Segoe UI", 10)).pack(side="left")
        self.center_entry = ttk.Entry(center_order, textvariable=self.center_var, width=10,
                                      font=("Consolas", 10))
        self.center_entry.pack(side="left", padx=4)
        self.center_entry.bind("<Return>", lambda e: self._on_center_change())
        self.center_entry.bind("<FocusOut>", lambda e: self._on_center_change())

        ttk.Button(center_order, text="Set a=0", width=8,
                   command=lambda: self._set_center(0.0)).pack(side="left", padx=2)
        ttk.Button(center_order, text="a=π/2", width=7,
                   command=lambda: self._set_center(np.pi / 2)).pack(side="left", padx=2)
        ttk.Button(center_order, text="a=1", width=6,
                   command=lambda: self._set_center(1.0)).pack(side="left", padx=2)
        ttk.Button(center_order, text="a=-1", width=6,
                   command=lambda: self._set_center(-1.0)).pack(side="left", padx=2)

        # Order controls
        tk.Label(center_order, text="   Order n =", bg=DARK["bg"], fg=DARK["text"],
                 font=("Segoe UI", 10)).pack(side="left", padx=(12, 4))

        self.order_scale = tk.Scale(
            center_order, from_=0, to=12, resolution=1, orient="horizontal",
            length=210, variable=self.order_var,
            command=self._on_order_change,
            bg=DARK["bg"], fg=DARK["text"], troughcolor=DARK["btn"],
            highlightthickness=0, activebackground=DARK["accent"]
        )
        self.order_scale.pack(side="left", padx=2)

        self.order_label = tk.Label(center_order, text="n=5", bg=DARK["bg"],
                                    fg=DARK["accent"], font=("Consolas", 11, "bold"), width=5)
        self.order_label.pack(side="left", padx=4)

        # +/- buttons
        ttk.Button(center_order, text="−", width=3,
                   command=lambda: self._change_order(-1)).pack(side="left", padx=1)
        ttk.Button(center_order, text="+", width=3,
                   command=lambda: self._change_order(+1)).pack(side="left", padx=1)

        # Quick order buttons
        quick = tk.Frame(center_order, bg=DARK["bg"])
        quick.pack(side="left", padx=8)
        for q in [0, 1, 2, 3, 4, 5, 6, 8, 10, 12]:
            b = ttk.Button(quick, text=str(q), width=2,
                           command=lambda qq=q: self._set_order(qq))
            b.pack(side="left", padx=1)

        # ===================== PRESETS =====================
        preset_frame = tk.Frame(self, bg=DARK["bg"])
        preset_frame.pack(fill="x", padx=8, pady=2)

        tk.Label(preset_frame, text="Presets:", bg=DARK["bg"], fg=DARK["secondary"],
                 font=("Segoe UI", 9)).pack(side="left", padx=(2, 6))

        presets = [
            ("sin(x)", "sin(x)", 0),
            ("cos(x)", "cos(x)", 0),
            ("eˣ", "exp(x)", 0),
            ("eˣ @ a=2", "exp(x)", 2),
            ("1/(1+x²)", "1/(1+x^2)", 0),
            ("ln(1+x) @1", "ln(1+x)", 1),
            ("(1+x)^(-1/2)", "(1+x)^(-0.5)", 0),
            ("sin(x) @ π/4", "sin(x)", np.pi/4),
            ("Geometric 1/(1-x)", "1/(1-x)", 0),
        ]
        for label, fstr, a in presets:
            cmd = lambda f=fstr, aa=a: self._load_preset(f, aa)
            ttk.Button(preset_frame, text=label, width=16, command=cmd).pack(side="left", padx=1)

        # ===================== PARAMETER SLIDERS =====================
        self.param_section = tk.Frame(self, bg=DARK["bg"])
        self.param_section.pack(fill="x", padx=8, pady=(2, 4))

        ph = tk.Frame(self.param_section, bg=DARK["bg"])
        ph.pack(fill="x")
        tk.Label(ph, text="Live Parameters (coefficients & constants in f)", bg=DARK["bg"],
                 fg=DARK["secondary"], font=("Segoe UI", 9)).pack(side="left")
        ttk.Button(ph, text="Reset params → 1.0", command=self._reset_params, width=16).pack(side="right")

        self.param_container = tk.Frame(self.param_section, bg=DARK["bg"])
        self.param_container.pack(fill="x", pady=1)

        # ===================== RANGE CONTROLS =====================
        range_frame = tk.Frame(self, bg=DARK["bg"])
        range_frame.pack(fill="x", padx=8, pady=2)

        tk.Label(range_frame, text="x-range:", bg=DARK["bg"], fg=DARK["text"],
                 font=("Segoe UI", 9)).pack(side="left")

        ttk.Entry(range_frame, textvariable=self.xmin_var, width=7).pack(side="left", padx=2)
        tk.Label(range_frame, text="to", bg=DARK["bg"], fg=DARK["secondary"],
                 font=("Segoe UI", 9)).pack(side="left")
        ttk.Entry(range_frame, textvariable=self.xmax_var, width=7).pack(side="left", padx=2)

        ttk.Button(range_frame, text="Apply", command=self._apply_range, width=8).pack(side="left", padx=3)

        # Range presets + convenience
        for lbl, lo, hi in [
            ("[-π,π]", -np.pi, np.pi),
            ("[-2π,2π]", -2*np.pi, 2*np.pi),
            ("[-3,3]", -3.0, 3.0),
            ("[0,4π]", 0, 4*np.pi),
            ("Center on a", None, None),
        ]:
            if lbl == "Center on a":
                b = ttk.Button(range_frame, text=lbl, width=11,
                               command=self._center_range_on_a)
            else:
                b = ttk.Button(range_frame, text=lbl, width=9,
                               command=lambda l=lo, h=hi: self._set_range(l, h))
            b.pack(side="left", padx=1)

        ttk.Button(range_frame, text="Auto Y", command=self._update_plot, width=8).pack(side="left", padx=6)

        # Action buttons
        action = tk.Frame(self, bg=DARK["panel"])
        action.pack(fill="x", padx=8, pady=3)

        ttk.Button(action, text="▶  Animate Order 0 → 12", width=22,
                   command=self._start_animation).pack(side="left", padx=4)
        ttk.Button(action, text="Stop Anim", width=10,
                   command=self._stop_animation).pack(side="left", padx=2)

        ttk.Button(action, text="Recompute", command=self._update_plot, width=11).pack(side="left", padx=6)

        self.show_orig_chk = tk.Checkbutton(
            action, text="Show f(x)", variable=self.show_original_var,
            bg=DARK["panel"], fg=DARK["text"], selectcolor=DARK["display"],
            command=self._update_plot
        )
        self.show_orig_chk.pack(side="left", padx=6)

        self.show_err_chk = tk.Checkbutton(
            action, text="Show Error |f−Tₙ|", variable=self.show_error_var,
            bg=DARK["panel"], fg=DARK["text"], selectcolor=DARK["display"],
            command=self._update_plot
        )
        self.show_err_chk.pack(side="left", padx=2)

        self.show_center_chk = tk.Checkbutton(
            action, text="Show a", variable=self.show_center_line_var,
            bg=DARK["panel"], fg=DARK["text"], selectcolor=DARK["display"],
            command=self._update_plot
        )
        self.show_center_chk.pack(side="left", padx=2)

        self.status_label = tk.Label(action, text="", bg=DARK["panel"],
                                     fg=DARK["success"], font=("Consolas", 9))
        self.status_label.pack(side="right", padx=8)

        # ===================== MATPLOTLIB PLOT =====================
        plot_frame = tk.Frame(self, bg=DARK["bg"])
        plot_frame.pack(fill="both", expand=True, padx=6, pady=4)

        self.fig = Figure(figsize=(10.0, 6.8), dpi=100, facecolor=DARK["bg"])
        # Two stacked axes: top = functions, bottom = remainder error
        gs = self.fig.add_gridspec(2, 1, height_ratios=[2.6, 1.0], hspace=0.28)
        self.ax1 = self.fig.add_subplot(gs[0], facecolor=DARK["display"])
        self.ax2 = self.fig.add_subplot(gs[1], facecolor=DARK["display"], sharex=self.ax1)

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas, plot_frame, pack_toolbar=False)
        self.toolbar.pack(fill="x")

        # ===================== SYMBOLIC + ERROR INFO =====================
        info = tk.Frame(self, bg=DARK["panel"])
        info.pack(fill="x", padx=8, pady=(0, 6))

        # Symbolic polynomial
        sym_header = tk.Frame(info, bg=DARK["panel"])
        sym_header.pack(fill="x", padx=6, pady=(4, 1))
        tk.Label(sym_header, text="Symbolic Taylor Polynomial  Tₙ(x)  —  matches f and derivatives up to order n at x = a",
                 bg=DARK["panel"], fg=DARK["text"], font=("Segoe UI", 9, "bold")).pack(side="left")

        self.poly_text = tk.Text(
            info, height=2, wrap="word", font=("Consolas", 10),
            bg=DARK["display"], fg=DARK["warning"],
            relief="flat", bd=0, padx=6, pady=3
        )
        self.poly_text.pack(fill="x", padx=6, pady=(0, 3))
        self.poly_text.config(state="disabled")

        # Error readout + educational line
        bottom_row = tk.Frame(info, bg=DARK["panel"])
        bottom_row.pack(fill="x", padx=6, pady=(0, 4))

        self.error_label = tk.Label(
            bottom_row,
            text="Max |error| in view: —",
            bg=DARK["panel"], fg=DARK["success"], font=("Consolas", 9, "bold")
        )
        self.error_label.pack(side="left")

        self.info_label = tk.Label(
            bottom_row,
            text="",
            bg=DARK["panel"], fg=DARK["secondary"], font=("Segoe UI", 8)
        )
        self.info_label.pack(side="left", padx=16)

        tk.Label(
            info,
            text="EDUCATIONAL NOTE:  Tₙ(x) is the unique polynomial of degree ≤ n that agrees with f and its first n derivatives at the expansion point a. "
                 "Near a the approximation is excellent; farther away it may diverge (see error subplot).  Click anywhere on the top plot to instantly change a.",
            bg=DARK["panel"], fg=DARK["secondary"], font=("Segoe UI", 8), wraplength=980, justify="left"
        ).pack(fill="x", padx=6, pady=(2, 4))

    # -------------------------------------------------------------------------
    # PLOT SETUP + STYLING
    # -------------------------------------------------------------------------
    def _setup_plot(self):
        for ax in (self.ax1, self.ax2):
            ax.tick_params(colors=DARK["secondary"])
            for spine in ax.spines.values():
                spine.set_color(DARK["spine"])
            ax.grid(True, alpha=0.22, color=GRID_COLOR, linestyle="-")

        self.ax1.set_ylabel("y", color=DARK["secondary"])
        self.ax2.set_xlabel("x", color=DARK["secondary"])
        self.ax2.set_ylabel("|f(x) − Tₙ(x)|", color=DARK["secondary"])

        self.ax1.set_title("Original Function  vs  Taylor Approximation", color=DARK["text"], fontsize=11, pad=4)

        # Persistent artists (re-created on full clears for safety)
        self._reset_artists()

    def _reset_artists(self):
        self.line_f = None
        self.line_taylor = None
        self.line_error = None
        self.center_vline = None
        self.center_marker = None

    def _connect_events(self):
        # Click on top plot → set new expansion point (very powerful for learning!)
        self.canvas.mpl_connect("button_press_event", self._on_plot_click)

    def _on_plot_click(self, event):
        if event.inaxes != self.ax1 or event.xdata is None:
            return
        # Set center to clicked x, keep current order, update everything
        self._set_center(float(event.xdata))

    # -------------------------------------------------------------------------
    # CALLBACKS & STATE
    # -------------------------------------------------------------------------
    def _on_func_change(self, initial: bool = False):
        """Parse new function, discover parameters, rebuild UI, replot."""
        new_f = self.func_var.get().strip()
        if new_f:
            self.func_str = new_f

        self._prepare_parameters()
        self._rebuild_param_sliders()

        if not initial:
            self._update_plot(full=True)
        else:
            # First boot: set reasonable defaults
            self._update_plot(full=True)

    def _on_center_change(self):
        try:
            self.center = self._parse_point(self.center_var.get())
            self.center_var.set(f"{self.center:.6g}")  # normalize display
        except Exception:
            self.center_var.set("0")
            self.center = 0.0
        self._update_plot(full=True)

    def _set_center(self, val: float):
        self.center = float(val)
        self.center_var.set(f"{self.center:.6g}")
        self._update_plot(full=True)

    def _on_order_change(self, *args):
        self.order = int(self.order_var.get())
        if self.order_label:
            self.order_label.config(text=f"n={self.order}")
        self._update_plot(full=False)  # light update sufficient

    def _change_order(self, delta: int):
        new_o = max(0, min(12, self.order_var.get() + delta))
        self.order_var.set(new_o)
        self._on_order_change()

    def _set_order(self, n: int):
        self.order_var.set(max(0, min(12, n)))
        self._on_order_change()

    def _on_param_change(self, p: str, val):
        try:
            self.params[p] = float(val)
        except Exception:
            self.params[p] = 1.0
        self._update_plot(full=False)

    def _reset_params(self):
        for p in self.current_param_list:
            self.params[p] = 1.0
            if p in self.param_vars:
                self.param_vars[p].set(1.0)
        self._update_plot(full=True)

    def _apply_range(self):
        try:
            lo = float(self.xmin_var.get())
            hi = float(self.xmax_var.get())
            if lo >= hi:
                raise ValueError("xmin must be < xmax")
            self._set_range(lo, hi)
        except Exception as e:
            self._set_status(f"Bad range: {e}", error=True)

    def _set_range(self, lo: float, hi: float):
        self.xmin, self.xmax = float(lo), float(hi)
        self.xmin_var.set(f"{self.xmin:.4g}")
        self.xmax_var.set(f"{self.xmax:.4g}")
        self._update_plot(full=True)

    def _center_range_on_a(self):
        width = self.xmax - self.xmin
        if width <= 0:
            width = 6.0
        half = width / 2.0
        self._set_range(self.center - half, self.center + half)

    # -------------------------------------------------------------------------
    # PARAMETER HANDLING (adapted from grapher pattern)
    # -------------------------------------------------------------------------
    def _prepare_parameters(self):
        try:
            expr = self.engine.parse(self.func_str)
            free = self.engine.get_free_symbols(expr)
            params = sorted(p for p in free if p != "x")
        except Exception:
            params = []

        new_list = params[:5]  # cap

        # Preserve values for existing params
        for p in new_list:
            if p not in self.params:
                self.params[p] = 1.0

        self.current_param_list = new_list

        # Drop stale
        for p in list(self.params.keys()):
            if p not in self.current_param_list:
                self.params.pop(p, None)

    def _rebuild_param_sliders(self):
        for w in self.param_container.winfo_children():
            w.destroy()
        self.param_vars.clear()
        self.param_scales.clear()

        if not self.current_param_list:
            tk.Label(
                self.param_container,
                text="No extra parameters (pure function of x only)",
                bg=DARK["bg"], fg=DARK["secondary"], font=("Segoe UI", 9, "italic")
            ).pack(anchor="w", pady=1)
            return

        row = tk.Frame(self.param_container, bg=DARK["bg"])
        row.pack(fill="x")

        for p in self.current_param_list:
            col = tk.Frame(row, bg=DARK["bg"])
            col.pack(side="left", padx=10, fill="x", expand=True)

            val = self.params.get(p, 1.0)
            var = tk.DoubleVar(value=val)
            self.param_vars[p] = var

            tk.Label(col, text=f"{p} =", bg=DARK["bg"], fg=DARK["text"],
                     font=("Segoe UI", 9)).pack(side="left")

            val_lbl = tk.Label(col, text=f"{val:.3f}", bg=DARK["bg"], fg=DARK["accent"],
                               font=("Consolas", 9, "bold"), width=6)
            val_lbl.pack(side="left", padx=(3, 4))

            # Reasonable slider ranges per common param names
            if p in ("a", "b", "c", "k", "m", "alpha"):
                lo, hi, res = -5.0, 5.0, 0.02
            elif p in ("omega", "freq", "w"):
                lo, hi, res = 0.1, 12.0, 0.05
            else:
                lo, hi, res = -4.0, 4.0, 0.05

            scale = tk.Scale(
                col, from_=lo, to=hi, resolution=res, orient="horizontal",
                length=120, variable=var,
                command=lambda v, pp=p, lbl=val_lbl: self._on_param_change(pp, v),
                bg=DARK["bg"], fg=DARK["text"], troughcolor=DARK["btn"],
                highlightthickness=0, activebackground=DARK["accent"]
            )
            scale.pack(side="left", fill="x", expand=True)
            self.param_scales[p] = scale

            var.trace_add("write", lambda *_, pp=p, lbl=val_lbl, vv=var: lbl.config(text=f"{vv.get():.3f}"))

    # -------------------------------------------------------------------------
    # CORE UPDATE / PLOTTING
    # -------------------------------------------------------------------------
    def _parse_point(self, s: str) -> float:
        s = (s or "0").strip()
        try:
            return float(s)
        except ValueError:
            pass
        try:
            # Support pi, sqrt(2), 1/3 etc.
            return float(self.engine.evaluate_at(s))
        except Exception as exc:
            raise MathEngineError(f"Cannot interpret expansion point '{s}'") from exc

    def _update_plot(self, full: bool = True):
        """Recompute series via MathEngine and redraw everything."""
        try:
            self._stop_animation()  # safety

            f_str = self.func_var.get().strip() or "sin(x)"
            self.func_str = f_str

            a = self._parse_point(self.center_var.get())
            self.center = a
            self.center_var.set(f"{a:.6g}")

            n_order = int(self.order_var.get())
            self.order = n_order
            if self.order_label:
                self.order_label.config(text=f"n={n_order}")

            n = n_order + 1  # series(..., n) gives polynomial of degree < n

            # Compute symbolic Taylor polynomial (the star of the show)
            poly = self.engine.symbolic_series(f_str, var="x", point=a, n=n)
            self.current_poly = poly

            # Update symbolic display
            pretty = self.engine.pretty(poly, use_unicode=True)
            if self.poly_text:
                self.poly_text.config(state="normal")
                self.poly_text.delete("1.0", "end")
                self.poly_text.insert("1.0", pretty)
                self.poly_text.config(state="disabled")

            # Numeric grid
            x_vals = np.linspace(self.xmin, self.xmax, 650)

            # Evaluate original f and the polynomial (both support params)
            values = {"x": x_vals, **self.params}

            y_f = self.engine.evaluate_numeric(f_str, values)
            y_poly = self.engine.evaluate_numeric(poly, values)

            y_f = np.asarray(y_f, dtype=float)
            y_poly = np.asarray(y_poly, dtype=float)

            # Clean masks
            mask_f = np.isfinite(y_f)
            mask_p = np.isfinite(y_poly)
            mask = mask_f & mask_p

            if not np.any(mask):
                raise MathEngineError("No finite values to plot in the chosen range")

            x_plot = x_vals[mask]
            y_f_plot = y_f[mask]
            y_poly_plot = y_poly[mask]

            # Error (remainder visualization)
            y_err = np.abs(y_f_plot - y_poly_plot)
            self.last_max_error = float(np.max(y_err)) if len(y_err) else None

            # ---------- DRAW ----------
            self.ax1.clear()
            self.ax2.clear()

            # Re-apply dark styling (clear wipes it)
            for ax in (self.ax1, self.ax2):
                ax.set_facecolor(DARK["display"])
                ax.tick_params(colors=DARK["secondary"])
                for spine in ax.spines.values():
                    spine.set_color(DARK["spine"])
                ax.grid(True, alpha=0.22, color=GRID_COLOR)

            self.ax1.set_ylabel("y", color=DARK["secondary"])
            self.ax2.set_xlabel("x", color=DARK["secondary"])
            self.ax2.set_ylabel("| remainder |", color=DARK["secondary"])
            self.ax1.set_title("Original Function  vs  Taylor Approximation", color=DARK["text"], fontsize=11, pad=4)

            # Top plot: f(x) and T_n(x)
            if self.show_original_var.get():
                self.line_f, = self.ax1.plot(
                    x_plot, y_f_plot,
                    color=FUNC_COLOR, linewidth=2.3, label=f"f(x) = {f_str[:42]}"
                )

            self.line_taylor, = self.ax1.plot(
                x_plot, y_poly_plot,
                color=TAYLOR_COLOR, linewidth=2.1, linestyle="--",
                label=f"T_{n_order}(x)  (order {n_order})"
            )

            # Center marker + vertical line
            if self.show_center_line_var.get():
                # Vertical line at a
                self.center_vline = self.ax1.axvline(
                    a, color=CENTER_COLOR, linestyle=":", linewidth=1.6, alpha=0.85
                )
                # Marker at (a, f(a))
                try:
                    fa = float(self.engine.evaluate_numeric(f_str, {"x": a, **self.params}))
                    self.center_marker = self.ax1.scatter(
                        [a], [fa], s=95, c=CENTER_COLOR, zorder=25,
                        edgecolors="#111", linewidths=1.5, marker="o", label=f"a = {a:.4g}"
                    )
                except Exception:
                    pass

            self.ax1.legend(
                loc="upper right", fontsize=8,
                facecolor=DARK["panel"], edgecolor="#555555", labelcolor="#DDDDDD"
            )

            # Auto y limits with padding
            all_y = []
            if self.show_original_var.get():
                all_y.append(y_f_plot)
            all_y.append(y_poly_plot)
            if all_y:
                flat = np.concatenate(all_y)
                ymn, ymx = float(np.nanmin(flat)), float(np.nanmax(flat))
                if np.isfinite(ymn) and np.isfinite(ymx):
                    pad = max(0.4, (ymx - ymn) * 0.12)
                    self.ax1.set_ylim(ymn - pad, ymx + pad)

            self.ax1.set_xlim(self.xmin, self.xmax)

            # Bottom: remainder / error visualization
            if self.show_error_var.get() and len(y_err) > 0:
                self.line_error, = self.ax2.plot(
                    x_plot, y_err, color=ERROR_COLOR, linewidth=1.9, label="|f(x) − Tₙ(x)|"
                )
                self.ax2.fill_between(x_plot, 0, y_err, alpha=0.18, color=ERROR_COLOR)

                # Nice y limit for error
                emax = float(np.max(y_err))
                if emax > 0:
                    self.ax2.set_ylim(0, emax * 1.12)
                else:
                    self.ax2.set_ylim(0, 1)
            else:
                self.ax2.text(0.5, 0.5, "Error curve hidden", transform=self.ax2.transAxes,
                              ha="center", va="center", color=DARK["secondary"], fontsize=9)

            self.ax2.set_xlim(self.xmin, self.xmax)

            self.canvas.draw_idle()

            # Update status + error labels
            self._update_status_and_error(a, n_order, f_str)

            if self.status_label and "Error" in (self.status_label.cget("text") or ""):
                self._set_status("")

        except MathEngineError as me:
            self._set_status(f"Math error: {me}", error=True)
        except Exception as e:
            self._set_status(f"Plot error: {str(e)[:75]}", error=True)

    def _update_status_and_error(self, a: float, n: int, f_str: str):
        # Error readout
        if self.last_max_error is not None:
            err_str = f"Max |error| in view: {self.last_max_error:.3e}"
            if self.last_max_error > 1e6:
                err_str += "  (large — function may have singularity or slow convergence)"
            self.error_label.config(text=err_str, fg=DARK["success"] if self.last_max_error < 10 else DARK["warning"])
        else:
            self.error_label.config(text="Max |error| in view: —")

        # Info line
        try:
            fa = self.engine.evaluate_numeric(f_str, {"x": a, **self.params})
            info = f"a = {a:.5g}    |    f(a) ≈ {float(fa):.5g}    |    degree ≤ {n}"
            self.info_label.config(text=info)
        except Exception:
            self.info_label.config(text=f"a = {a:.5g}    |    degree ≤ {n}")

        self._set_status("")

    def _set_status(self, msg: str, error: bool = False):
        if self.status_label:
            color = DARK["error"] if error else DARK["success"]
            self.status_label.config(text=msg, fg=color)
            if msg:
                self.after(2600, lambda: self.status_label.config(text="") if self.status_label else None)

    # -------------------------------------------------------------------------
    # ANIMATION
    # -------------------------------------------------------------------------
    def _start_animation(self):
        if self.animating:
            return
        self.animating = True
        self._set_status("Animating order 0 → 12 ...")
        self._anim_step(0)

    def _anim_step(self, current: int):
        if not self.animating or current > 12:
            self._stop_animation()
            return

        self.order_var.set(current)
        self._on_order_change()

        # Schedule next
        delay = 165 if current < 8 else 240  # slow down at higher orders
        self._anim_after_id = self.after(delay, lambda: self._anim_step(current + 1))

    def _stop_animation(self):
        self.animating = False
        if self._anim_after_id is not None:
            try:
                self.after_cancel(self._anim_after_id)
            except Exception:
                pass
            self._anim_after_id = None
        if self.status_label and "Animat" in (self.status_label.cget("text") or ""):
            self.status_label.config(text="")

    # -------------------------------------------------------------------------
    # PRESETS
    # -------------------------------------------------------------------------
    def _load_preset(self, f_str: str, a: float):
        self.func_var.set(f_str)
        self.func_str = f_str
        self.center = float(a)
        self.center_var.set(f"{a:.6g}")

        # Nice starting order depending on function
        if "exp" in f_str.lower() or "1/(1" in f_str:
            start_order = 4
        elif "ln" in f_str:
            start_order = 3
        else:
            start_order = 5

        self.order_var.set(start_order)

        # Auto-adjust range to be interesting around a
        if abs(a) < 0.1:
            self._set_range(-6.5, 6.5)
        elif abs(a) < 2:
            self._set_range(a - 5.5, a + 5.5)
        else:
            self._set_range(a - 4, a + 4)

        self._on_func_change()

    # -------------------------------------------------------------------------
    # PUBLIC HELPERS (for embedding apps)
    # -------------------------------------------------------------------------
    def set_function(self, expr: str, center: float | None = None, order: int | None = None):
        """Convenience API for external control."""
        self.func_var.set(expr)
        if center is not None:
            self.center_var.set(str(center))
        if order is not None:
            self.order_var.set(max(0, min(12, order)))
        self._on_func_change()

    def get_current_polynomial(self):
        """Returns the current SymPy polynomial (or None)."""
        return self.current_poly

    def get_current_error_max(self) -> float | None:
        return self.last_max_error


class TaylorPlaygroundFrame(tk.Frame):
    """
    Ready-to-drop titled container Frame (matches Grapher2DFrame pattern).
    Use this when placing the playground inside a notebook tab or window.
    """

    def __init__(self, parent, engine: MathEngine):
        super().__init__(parent, bg=DARK["bg"])
        self.engine = engine

        header = tk.Frame(self, bg=DARK["panel"])
        header.pack(fill="x")
        tk.Label(
            header,
            text="Calculus Lab • Taylor Series Playground",
            bg=DARK["panel"], fg="#4FC3F7", font=("Segoe UI", 13, "bold")
        ).pack(pady=7, padx=14, anchor="w")

        self.playground = TaylorPlayground(self, engine)
        self.playground.pack(fill="both", expand=True)


# =============================================================================
# STANDALONE DEMO (run file directly)
# =============================================================================
if __name__ == "__main__":
    print("Launching Taylor Series Playground standalone demo...")

    root = tk.Tk()
    root.title("Taylor Series Playground — Educational Interactive Demo  •  MathForge")
    root.geometry("1180x860")
    root.minsize(980, 720)
    root.configure(bg=DARK["bg"])

    engine = MathEngine(use_numpy=True)

    container = TaylorPlaygroundFrame(root, engine)
    container.pack(fill="both", expand=True, padx=4, pady=4)

    hint = tk.Label(
        root,
        text="TIP: Type any expression (try  exp(-x^2),  sin(x)/x,  1/(1+x) ).  Drag the order slider or click the +/− buttons.  CLICK anywhere on the top graph to instantly move the expansion point a.  Use the animation button to see convergence build visually.  Watch the yellow error curve shrink near a.",
        bg=DARK["panel"], fg=DARK["secondary"], font=("Segoe UI", 9), wraplength=1100
    )
    hint.pack(fill="x", pady=(0, 3), padx=6)

    root.mainloop()
