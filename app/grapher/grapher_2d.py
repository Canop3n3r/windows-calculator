#!/usr/bin/env python3
"""
Grapher2D — High-quality interactive 2D function grapher + calculus visualizations
for the MathForge / Windows Calculator ecosystem.

Features (matches spec):
- Embeddable Grapher2D (tk.Frame) and Grapher2DFrame
- Up to 3 simultaneous functions with live toggles + one "active for calculus"
- Expressions with 1-3 parameters (e.g. "a*sin(b*x)", "x^2*exp(-c*x)") → live dark-themed Tk sliders
- Full Derivative Explorer (the killer educational visualization):
  * Draggable point + synced x0 slider (click or drag anywhere on plot to move)
  * Tangent line at the point (symbolic + numeric slope)
  * Secant line for adjustable h
  * "Animate h → 0" + preset h buttons to demonstrate the limit definition visually
  * Live numeric slopes + symbolic f'(x) from the shared MathEngine (SymPy)
- Dark theme perfectly matching the Windows Calculator (#202020 etc.)
- Matplotlib embedded with NavigationToolbar (zoom/pan/save)
- Responsive, clean, genuinely "wow, calculus just clicked"
- Self-contained runnable demo at bottom of file

Integration: Drop into any Tk app that has an instance of app.core.math_engine.MathEngine.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

# Reuse the powerful shared engine (parsing, symbolic diff, safe vectorized eval)
from app.core.math_engine import MathEngine, MathEngineError


# =============================================================================
# DARK THEME (matches the original Windows Calculator exactly)
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


FUNC_COLORS = ["#00D4FF", "#7CFC00", "#FF79C6"]  # cyan, green, pink — high contrast on dark
TANGENT_COLOR = "#FFB74D"                         # warm orange
SECANT_COLOR = "#FFEB3B"                          # bright yellow
POINT_COLOR = "#FFFFFF"


class Grapher2D(tk.Frame):
    """
    The primary embeddable component.

    Usage:
        engine = MathEngine()
        grapher = Grapher2D(parent, engine)
        grapher.pack(fill="both", expand=True)

    Or use Grapher2DFrame for a ready-made titled container.
    """

    def __init__(self, parent, engine: MathEngine):
        super().__init__(parent, bg=DARK["bg"])
        self.engine = engine

        # --- Core state ---
        self.func_strs = [
            "a*sin(b*x)",
            "x**2 * exp(-0.1*x)",
            "cos(2*x) + 0.5*sin(3*x)",
        ]
        self.visible = [True, True, False]
        self.active_idx = 0

        self.params: dict[str, float] = {}
        self.param_vars: dict[str, tk.DoubleVar] = {}
        self.param_scales: dict[str, tk.Scale] = {}

        self.xmin = -8.0
        self.xmax = 8.0
        self.x0 = 1.2
        self.h = 0.45

        self.show_tangent = True
        self.show_secant = True
        self.dragging = False

        # Matplotlib artists (persistent for buttery updates)
        self.func_artists = [None] * 3
        self.point_marker = None
        self.tangent_line = None
        self.secant_line = None

        self.current_param_list: list[str] = []

        # UI vars
        self.expr_vars: list[tk.StringVar] = []
        self.vis_vars: list[tk.BooleanVar] = []
        self.active_var = tk.IntVar(value=0)
        self.x0_var = tk.DoubleVar(value=self.x0)
        self.h_var = tk.DoubleVar(value=self.h)

        self._build_ui()
        self._setup_plot()
        self._connect_events()

        # Initial boot
        self._on_func_change()   # parses, builds sliders, plots everything

    # -------------------------------------------------------------------------
    # UI CONSTRUCTION
    # -------------------------------------------------------------------------
    def _build_ui(self):
        # Top header strip
        header = tk.Frame(self, bg=DARK["panel"], height=32)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="2D Grapher + Derivative Explorer",
            bg=DARK["panel"],
            fg=DARK["text"],
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left", padx=12, pady=4)

        tk.Label(
            header,
            text="Drag the point • Watch secant → tangent • Calculus that finally clicks",
            bg=DARK["panel"],
            fg=DARK["secondary"],
            font=("Segoe UI", 9),
        ).pack(side="left", padx=10)

        # === FUNCTIONS SECTION ===
        func_section = tk.Frame(self, bg=DARK["bg"])
        func_section.pack(fill="x", padx=8, pady=(6, 2))

        tk.Label(
            func_section, text="Functions (toggle visible • pick one for derivative)",
            bg=DARK["bg"], fg=DARK["secondary"], font=("Segoe UI", 9)
        ).pack(anchor="w", padx=2)

        self.expr_vars = []
        self.vis_vars = []

        for i in range(3):
            row = tk.Frame(func_section, bg=DARK["bg"])
            row.pack(fill="x", pady=2)

            # Visibility checkbox
            vis_var = tk.BooleanVar(value=self.visible[i])
            self.vis_vars.append(vis_var)
            chk = tk.Checkbutton(
                row,
                text="",
                variable=vis_var,
                bg=DARK["bg"],
                fg=DARK["text"],
                selectcolor=DARK["display"],
                activebackground=DARK["bg"],
                command=self._on_func_change,
            )
            chk.pack(side="left", padx=(0, 4))

            # Color swatch
            swatch = tk.Canvas(row, width=16, height=16, bg=DARK["bg"], highlightthickness=0)
            swatch.pack(side="left", padx=(0, 6))
            swatch.create_rectangle(2, 2, 14, 14, fill=FUNC_COLORS[i], outline="#111")

            # Expression entry
            evar = tk.StringVar(value=self.func_strs[i])
            self.expr_vars.append(evar)
            entry = ttk.Entry(row, textvariable=evar, width=38, font=("Consolas", 10))
            entry.pack(side="left", fill="x", expand=True, padx=2)
            entry.bind("<Return>", lambda e, idx=i: self._on_func_change())
            entry.bind("<FocusOut>", lambda e, idx=i: self._on_func_change())

            # Active radio
            rad = tk.Radiobutton(
                row,
                text="Explore derivative here",
                variable=self.active_var,
                value=i,
                bg=DARK["bg"],
                fg=DARK["text"],
                selectcolor=DARK["display"],
                activebackground=DARK["bg"],
                font=("Segoe UI", 9),
                command=self._on_active_change,
            )
            rad.pack(side="left", padx=8)

        # === PARAMETER SLIDERS (dynamic, rebuilt on expression changes) ===
        self.param_section = tk.Frame(self, bg=DARK["bg"])
        self.param_section.pack(fill="x", padx=8, pady=(4, 2))

        param_header = tk.Frame(self.param_section, bg=DARK["bg"])
        param_header.pack(fill="x")
        tk.Label(param_header, text="Live Parameters", bg=DARK["bg"], fg=DARK["secondary"], font=("Segoe UI", 9)).pack(side="left")
        ttk.Button(param_header, text="Reset to 1.0", command=self._reset_params, width=12).pack(side="right")

        self.param_container = tk.Frame(self.param_section, bg=DARK["bg"])
        self.param_container.pack(fill="x", pady=2)

        # === RANGE + PRESETS ===
        range_frame = tk.Frame(self, bg=DARK["bg"])
        range_frame.pack(fill="x", padx=8, pady=3)

        tk.Label(range_frame, text="x-range:", bg=DARK["bg"], fg=DARK["text"], font=("Segoe UI", 9)).pack(side="left")

        self.xmin_var = tk.StringVar(value=str(self.xmin))
        self.xmax_var = tk.StringVar(value=str(self.xmax))
        ttk.Entry(range_frame, textvariable=self.xmin_var, width=7).pack(side="left", padx=2)
        tk.Label(range_frame, text="to", bg=DARK["bg"], fg=DARK["secondary"], font=("Segoe UI", 9)).pack(side="left")
        ttk.Entry(range_frame, textvariable=self.xmax_var, width=7).pack(side="left", padx=2)

        ttk.Button(range_frame, text="Apply", command=self._apply_range, width=8).pack(side="left", padx=4)

        # Presets
        presets = [
            ("[-10,10]", -10, 10),
            ("[-2π,2π]", -2*np.pi, 2*np.pi),
            ("[-π,π]", -np.pi, np.pi),
            ("[0, 6π]", 0, 6*np.pi),
            ("[-5,5]", -5, 5),
        ]
        for label, lo, hi in presets:
            b = ttk.Button(range_frame, text=label, width=8,
                           command=lambda l=lo, h=hi: self._set_range(l, h))
            b.pack(side="left", padx=1)

        ttk.Button(range_frame, text="Auto Y", command=self._update_plot, width=8).pack(side="left", padx=6)

        # === EXPLORER CONTROLS ===
        explorer = tk.Frame(self, bg=DARK["panel"])
        explorer.pack(fill="x", padx=8, pady=4)

        # x0
        x0_frame = tk.Frame(explorer, bg=DARK["panel"])
        x0_frame.pack(fill="x", pady=1)
        tk.Label(x0_frame, text="Exploration point  x₀", bg=DARK["panel"], fg=DARK["text"], font=("Segoe UI", 9)).pack(side="left")
        self.x0_scale = tk.Scale(
            x0_frame, from_=-10, to=10, resolution=0.01, orient="horizontal",
            length=260, variable=self.x0_var,
            command=self._on_x0_scale,
            bg=DARK["panel"], fg=DARK["text"], troughcolor=DARK["btn"],
            highlightthickness=0, activebackground=DARK["accent"]
        )
        self.x0_scale.pack(side="left", padx=6)
        ttk.Button(x0_frame, text="Center", command=lambda: self._set_x0(0.0), width=7).pack(side="left", padx=2)

        # h
        h_frame = tk.Frame(explorer, bg=DARK["panel"])
        h_frame.pack(fill="x", pady=1)
        tk.Label(h_frame, text="Secant step  h", bg=DARK["panel"], fg=DARK["text"], font=("Segoe UI", 9)).pack(side="left")
        self.h_scale = tk.Scale(
            h_frame, from_=0.001, to=2.5, resolution=0.001, orient="horizontal",
            length=200, variable=self.h_var,
            command=self._on_h_scale,
            bg=DARK["panel"], fg=DARK["text"], troughcolor=DARK["btn"],
            highlightthickness=0, activebackground=DARK["accent"]
        )
        self.h_scale.pack(side="left", padx=6)

        # h preset buttons (educational gold)
        for val in [1.0, 0.5, 0.1, 0.05, 0.01, 0.001]:
            ttk.Button(h_frame, text=f"h={val}", width=6,
                       command=lambda v=val: self._set_h(v)).pack(side="left", padx=1)

        # Action buttons
        btn_row = tk.Frame(explorer, bg=DARK["panel"])
        btn_row.pack(fill="x", pady=3)

        self.tan_var = tk.BooleanVar(value=self.show_tangent)
        tk.Checkbutton(
            btn_row, text="Show Tangent", variable=self.tan_var,
            bg=DARK["panel"], fg=DARK["text"], selectcolor=DARK["display"],
            command=self._on_tangent_toggle
        ).pack(side="left", padx=4)

        self.sec_var = tk.BooleanVar(value=self.show_secant)
        tk.Checkbutton(
            btn_row, text="Show Secant", variable=self.sec_var,
            bg=DARK["panel"], fg=DARK["text"], selectcolor=DARK["display"],
            command=self._on_secant_toggle
        ).pack(side="left", padx=4)

        ttk.Button(btn_row, text="▶  Animate h → 0  (limit demo)", command=self.animate_limit).pack(side="left", padx=8)
        ttk.Button(btn_row, text="Reset h=0.45", command=lambda: self._set_h(0.45)).pack(side="left", padx=2)

        self.status = tk.Label(btn_row, text="", bg=DARK["panel"], fg=DARK["success"], font=("Consolas", 9))
        self.status.pack(side="right", padx=8)

        # === MATPLOTLIB PLOT ===
        plot_frame = tk.Frame(self, bg=DARK["bg"])
        plot_frame.pack(fill="both", expand=True, padx=6, pady=4)

        self.fig = Figure(figsize=(9.5, 5.8), dpi=100, facecolor=DARK["bg"])
        self.ax = self.fig.add_subplot(111, facecolor=DARK["display"])

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas, plot_frame, pack_toolbar=False)
        self.toolbar.pack(fill="x")

        # === EDUCATIONAL INFO PANEL (the "wow" closer) ===
        info = tk.Frame(self, bg=DARK["panel"])
        info.pack(fill="x", padx=8, pady=(0, 6))

        self.active_info = tk.Label(
            info, text="Active: —", bg=DARK["panel"], fg=DARK["text"],
            font=("Segoe UI", 10, "bold"), anchor="w"
        )
        self.active_info.pack(fill="x", padx=6, pady=(3, 0))

        self.deriv_info = tk.Label(
            info, text="f'(x) = —", bg=DARK["panel"], fg=DARK["warning"],
            font=("Consolas", 10), anchor="w"
        )
        self.deriv_info.pack(fill="x", padx=6)

        self.numeric_info = tk.Label(
            info, text="f(x₀) = —    |    f'(x₀) ≈ —    |    secant slope ≈ —",
            bg=DARK["panel"], fg=DARK["success"], font=("Consolas", 9), anchor="w"
        )
        self.numeric_info.pack(fill="x", padx=6, pady=(0, 2))

        tk.Label(
            info,
            text="DEFINITION  →  f'(x) = lim (h→0)  [f(x+h) − f(x)] / h     •     Drag the white point or use sliders. Watch the yellow secant line flatten onto the orange tangent as h shrinks.",
            bg=DARK["panel"], fg=DARK["secondary"], font=("Segoe UI", 8), wraplength=920, justify="left"
        ).pack(fill="x", padx=6, pady=(0, 4))

    # -------------------------------------------------------------------------
    # PLOT SETUP + ARTISTS
    # -------------------------------------------------------------------------
    def _setup_plot(self):
        self.ax.set_xlim(self.xmin, self.xmax)
        self.ax.tick_params(colors=DARK["secondary"])
        for spine in self.ax.spines.values():
            spine.set_color(DARK["spine"])
        self.ax.set_xlabel("x", color=DARK["secondary"])
        self.ax.set_ylabel("y", color=DARK["secondary"])
        self.ax.grid(True, alpha=0.25, color=DARK["grid"], linestyle="-")

        self._create_persistent_artists()
        self._style_legend_placeholder()

    def _create_persistent_artists(self):
        for i, color in enumerate(FUNC_COLORS):
            ln, = self.ax.plot([], [], color=color, linewidth=2.15, label=f"f{i+1}")
            self.func_artists[i] = ln

        self.point_marker, = self.ax.plot(
            [], [], "o", color=POINT_COLOR, markersize=11, zorder=20,
            markeredgecolor="#111111", markeredgewidth=2.0
        )
        self.tangent_line, = self.ax.plot(
            [], [], color=TANGENT_COLOR, linewidth=1.85, linestyle="--", label="tangent"
        )
        self.secant_line, = self.ax.plot(
            [], [], color=SECANT_COLOR, linewidth=1.7, linestyle=":", alpha=0.92, label="secant"
        )

    def _style_legend_placeholder(self):
        # Legend will be refreshed in updates
        pass

    # -------------------------------------------------------------------------
    # EVENT HANDLING (DRAGGABLE POINT — THE STAR FEATURE)
    # -------------------------------------------------------------------------
    def _connect_events(self):
        self.canvas.mpl_connect("button_press_event", self._on_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_drag)
        self.canvas.mpl_connect("button_release_event", self._on_release)

    def _on_press(self, event):
        if event.inaxes != self.ax or event.xdata is None:
            return
        self._set_x0(float(event.xdata))
        self.dragging = True

    def _on_drag(self, event):
        if not self.dragging or event.inaxes != self.ax or event.xdata is None:
            return
        self._set_x0(float(event.xdata))

    def _on_release(self, event):
        self.dragging = False

    # -------------------------------------------------------------------------
    # STATE MUTATORS + CALLBACKS
    # -------------------------------------------------------------------------
    def _on_func_change(self, *args):
        """Parse all expressions, detect parameters, (re)build sliders, replot."""
        changed = False
        for i in range(3):
            new_str = self.expr_vars[i].get().strip()
            if new_str != self.func_strs[i]:
                self.func_strs[i] = new_str
                changed = True
            self.visible[i] = self.vis_vars[i].get()

        self.active_idx = self.active_var.get()
        if self.active_idx >= 3 or not self.visible[self.active_idx]:
            # pick first visible
            for j in range(3):
                if self.visible[j]:
                    self.active_idx = j
                    self.active_var.set(j)
                    break

        self._prepare_parameters()
        self._rebuild_param_sliders()
        self._update_plot(full=True)

    def _on_active_change(self):
        self.active_idx = self.active_var.get()
        self._update_plot(full=True)  # need to refresh legend + tangent target

    def _prepare_parameters(self):
        """Discover all parameters across visible functions."""
        all_params: set[str] = set()
        for i in range(3):
            if not self.visible[i] or not self.func_strs[i]:
                continue
            try:
                expr = self.engine.parse(self.func_strs[i])
                free = self.engine.get_free_symbols(expr)
                for p in free:
                    if p != "x":
                        all_params.add(p)
            except Exception:
                pass  # bad expr handled later in plotting

        new_list = sorted(all_params)[:4]  # hard cap at 4 for sanity

        # Preserve existing values
        for p in new_list:
            if p not in self.params:
                self.params[p] = 1.0

        self.current_param_list = new_list

        # Drop stale params
        for p in list(self.params.keys()):
            if p not in self.current_param_list:
                self.params.pop(p, None)

    def _rebuild_param_sliders(self):
        """Dynamically create beautiful dark sliders for discovered parameters."""
        for w in self.param_container.winfo_children():
            w.destroy()
        self.param_vars.clear()
        self.param_scales.clear()

        if not self.current_param_list:
            tk.Label(
                self.param_container, text="No parameters detected (pure function of x)",
                bg=DARK["bg"], fg=DARK["secondary"], font=("Segoe UI", 9, "italic")
            ).pack(anchor="w", pady=2)
            return

        row = tk.Frame(self.param_container, bg=DARK["bg"])
        row.pack(fill="x")

        for p in self.current_param_list:
            col = tk.Frame(row, bg=DARK["bg"])
            col.pack(side="left", padx=8, fill="x", expand=True)

            # Label + live value
            val = self.params.get(p, 1.0)
            var = tk.DoubleVar(value=val)
            self.param_vars[p] = var

            label = tk.Label(col, text=f"{p} =", bg=DARK["bg"], fg=DARK["text"], font=("Segoe UI", 9))
            label.pack(side="left")

            value_lbl = tk.Label(col, text=f"{val:.3f}", bg=DARK["bg"], fg=DARK["accent"], font=("Consolas", 9, "bold"), width=7)
            value_lbl.pack(side="left", padx=(2, 6))

            # Sensible per-parameter ranges
            if p in ("a", "b", "c", "k", "m"):
                lo, hi, res = (-5.0, 5.0, 0.02)
            elif p in ("freq", "omega"):
                lo, hi, res = (0.1, 8.0, 0.05)
            else:
                lo, hi, res = (-4.0, 4.0, 0.05)

            scale = tk.Scale(
                col, from_=lo, to=hi, resolution=res, orient="horizontal",
                length=130, variable=var,
                command=lambda v, pp=p, lbl=value_lbl: self._on_param_change(pp, v, lbl),
                bg=DARK["bg"], fg=DARK["text"], troughcolor=DARK["btn"],
                highlightthickness=0, activebackground=DARK["accent"]
            )
            scale.pack(side="left", fill="x", expand=True)
            self.param_scales[p] = scale

            # initialize value label
            var.trace_add("write", lambda *_, pp=p, lbl=value_lbl, vv=var: lbl.config(text=f"{vv.get():.3f}"))

    def _on_param_change(self, p: str, val, value_label=None):
        try:
            self.params[p] = float(val)
        except Exception:
            self.params[p] = 1.0
        if value_label:
            value_label.config(text=f"{self.params[p]:.3f}")
        self._update_plot(full=False)  # light — only need deriv artists + info

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
                raise ValueError
            self._set_range(lo, hi)
        except Exception:
            self.status.config(text="Invalid range", fg=DARK["error"])
            self.after(1400, lambda: self.status.config(text=""))

    def _set_range(self, lo: float, hi: float):
        self.xmin, self.xmax = float(lo), float(hi)
        self.xmin_var.set(f"{self.xmin:.3g}")
        self.xmax_var.set(f"{self.xmax:.3g}")
        # keep x0 inside
        self.x0 = max(self.xmin, min(self.xmax, self.x0))
        self.x0_var.set(self.x0)
        self._update_plot(full=True)

    def _on_x0_scale(self, val):
        self._set_x0(float(val), from_scale=True)

    def _set_x0(self, val: float, from_scale=False):
        self.x0 = max(self.xmin, min(self.xmax, float(val)))
        if not from_scale:
            self.x0_var.set(self.x0)
        self._update_derivative_artists()
        self._update_info_panel()

    def _on_h_scale(self, val):
        self.h = max(0.0005, min(3.0, float(val)))
        self.h_var.set(self.h)  # keep in sync
        self._update_derivative_artists()
        self._update_info_panel()

    def _set_h(self, val: float):
        self.h = max(0.0005, min(3.0, float(val)))
        self.h_var.set(self.h)
        self._update_derivative_artists()
        self._update_info_panel()

    def _on_tangent_toggle(self):
        self.show_tangent = self.tan_var.get()
        self._update_derivative_artists()

    def _on_secant_toggle(self):
        self.show_secant = self.sec_var.get()
        self._update_derivative_artists()

    # -------------------------------------------------------------------------
    # CORE PLOTTING (full vs light)
    # -------------------------------------------------------------------------
    def _update_plot(self, full: bool = True):
        """full=True when functions, range, or params (that affect all curves) change."""
        try:
            self.ax.clear()
            self.ax.set_facecolor(DARK["display"])
            self.ax.tick_params(colors=DARK["secondary"])
            for spine in self.ax.spines.values():
                spine.set_color(DARK["spine"])
            self.ax.set_xlabel("x", color=DARK["secondary"])
            self.ax.set_ylabel("f(x)", color=DARK["secondary"])
            self.ax.grid(True, alpha=0.22, color=DARK["grid"])

            x_vals = np.linspace(self.xmin, self.xmax, 520)
            all_y = []

            # Re-create artists after clear
            self.func_artists = [None] * 3
            for i in range(3):
                if not self.visible[i]:
                    continue
                try:
                    y = self.engine.evaluate_numeric(
                        self.func_strs[i], {"x": x_vals, **self.params}
                    )
                    y = np.asarray(y, dtype=float)
                    mask = np.isfinite(y)
                    if not np.any(mask):
                        continue
                    ln, = self.ax.plot(
                        x_vals[mask], y[mask],
                        color=FUNC_COLORS[i], linewidth=2.2,
                        label=f"f{i+1}: {self.func_strs[i][:32]}"
                    )
                    self.func_artists[i] = ln
                    all_y.append(y[mask])
                except Exception as e:
                    # Plot nothing for this curve; status will reflect
                    pass

            # Recreate derivative artists
            self._create_persistent_artists()

            self.ax.set_xlim(self.xmin, self.xmax)

            if all_y:
                flat = np.concatenate(all_y)
                ymin, ymax = float(np.min(flat)), float(np.max(flat))
                pad = max(0.6, (ymax - ymin) * 0.13)
                self.ax.set_ylim(ymin - pad, ymax + pad)

            self._update_derivative_artists(force=True)

            # Legend
            handles = [a for a in self.func_artists if a is not None] + \
                      ([self.tangent_line] if self.show_tangent else []) + \
                      ([self.secant_line] if self.show_secant else [])
            labels = [h.get_label() for h in handles if h is not None]
            if handles:
                self.ax.legend(
                    handles, labels,
                    loc="upper right", fontsize=8,
                    facecolor=DARK["panel"], edgecolor="#555555", labelcolor="#DDDDDD"
                )

            self.canvas.draw_idle()
            self._update_info_panel()

            if self.status.cget("text") and "Error" in self.status.cget("text"):
                self.status.config(text="")

        except Exception as e:
            self.status.config(text=f"Plot error: {str(e)[:70]}", fg=DARK["error"])

    def _update_derivative_artists(self, force: bool = False):
        """Fast path: only move the point, tangent, and secant (ideal for dragging + h animation)."""
        if not any(self.visible):
            return

        active = self.active_idx
        if not self.visible[active] or self.func_artists[active] is None:
            self.point_marker.set_visible(False)
            self.tangent_line.set_visible(False)
            self.secant_line.set_visible(False)
            self.canvas.draw_idle()
            return

        try:
            x0 = float(self.x0)
            h = float(self.h)

            # f(x0)
            y0 = float(self.engine.evaluate_numeric(
                self.func_strs[active], {"x": x0, **self.params}
            ))

            # Point
            self.point_marker.set_data([x0], [y0])
            self.point_marker.set_visible(True)

            # Tangent
            if self.show_tangent:
                try:
                    deriv_expr = self.engine.symbolic_derivative(self.func_strs[active])
                    slope = float(self.engine.evaluate_numeric(
                        deriv_expr, {"x": x0, **self.params}
                    ))
                    dx = (self.xmax - self.xmin) * 0.20
                    self.tangent_line.set_data(
                        [x0 - dx, x0 + dx],
                        [y0 - slope * dx, y0 + slope * dx]
                    )
                    self.tangent_line.set_visible(True)
                except Exception:
                    self.tangent_line.set_visible(False)
            else:
                self.tangent_line.set_visible(False)

            # Secant
            if self.show_secant:
                try:
                    y1 = float(self.engine.evaluate_numeric(
                        self.func_strs[active], {"x": x0 + h, **self.params}
                    ))
                    self.secant_line.set_data([x0, x0 + h], [y0, y1])
                    self.secant_line.set_visible(True)
                except Exception:
                    self.secant_line.set_visible(False)
            else:
                self.secant_line.set_visible(False)

            self.canvas.draw_idle()
        except Exception:
            self.point_marker.set_visible(False)
            self.tangent_line.set_visible(False)
            self.secant_line.set_visible(False)

    def _update_info_panel(self):
        active = self.active_idx
        if not self.visible[active]:
            self.active_info.config(text="No active function selected for exploration")
            self.deriv_info.config(text="f'(x) = —")
            self.numeric_info.config(text="")
            return

        f_str = self.func_strs[active]
        self.active_info.config(text=f"Active:  {f_str}")

        try:
            deriv = self.engine.symbolic_derivative(f_str)
            pretty = self.engine.pretty(deriv, use_unicode=True)
            if len(pretty) > 78:
                pretty = pretty[:75] + "…"
            self.deriv_info.config(text=f"f'(x) = {pretty}", fg=DARK["warning"])
        except Exception:
            self.deriv_info.config(text="f'(x) = (could not compute symbolic derivative)", fg=DARK["error"])

        try:
            x0 = float(self.x0)
            h = float(self.h)

            f0 = float(self.engine.evaluate_numeric(f_str, {"x": x0, **self.params}))
            deriv0 = float(self.engine.evaluate_numeric(
                self.engine.symbolic_derivative(f_str), {"x": x0, **self.params}
            ))

            y1 = float(self.engine.evaluate_numeric(f_str, {"x": x0 + h, **self.params}))
            sec_slope = (y1 - f0) / h if abs(h) > 1e-9 else deriv0

            self.numeric_info.config(
                text=f"At x₀ = {x0:.4f}   •   f(x₀) = {f0:.5f}   •   f'(x₀) ≈ {deriv0:.5f}   •   secant(h={h:.4f}) ≈ {sec_slope:.5f}",
                fg=DARK["success"]
            )
        except Exception as e:
            self.numeric_info.config(text=f"Numeric evaluation issue: {str(e)[:55]}", fg=DARK["error"])

    # -------------------------------------------------------------------------
    # THE KILLER ANIMATION — makes the limit definition visceral
    # -------------------------------------------------------------------------
    def animate_limit(self):
        """Animate h shrinking toward zero. This is the money shot for students."""
        if not self.visible[self.active_idx]:
            self.status.config(text="Select a visible function first", fg=DARK["warning"])
            return

        self.show_secant = True
        self.sec_var.set(True)

        self.status.config(text="Animating limit h → 0 ... (watch the yellow line converge)", fg=DARK["warning"])

        h_start = max(self.h, 0.9)
        target = 0.0008
        steps = 26
        h_vals = np.linspace(h_start, target, steps)

        def step(idx=0):
            if idx >= len(h_vals):
                self.status.config(text="✓ Limit reached — secant slope now matches the instantaneous rate f'(x)!", fg=DARK["success"])
                self.after(2400, lambda: self.status.config(text=""))
                return

            self.h = float(h_vals[idx])
            self.h_var.set(self.h)
            self._update_derivative_artists()
            self._update_info_panel()
            self.canvas.draw_idle()

            delay = 48 if idx < 8 else 32
            self.after(delay, lambda: step(idx + 1))

        step(0)

    # -------------------------------------------------------------------------
    # PUBLIC API FOR EMBEDDING / EXTENSION
    # -------------------------------------------------------------------------
    def set_function(self, index: int, expr: str, visible: bool = True):
        if 0 <= index < 3:
            self.func_strs[index] = expr
            self.visible[index] = visible
            self.expr_vars[index].set(expr)
            self.vis_vars[index].set(visible)
            self._on_func_change()

    def set_active(self, index: int):
        if 0 <= index < 3:
            self.active_var.set(index)
            self._on_active_change()

    def get_current_derivative(self) -> str:
        """Return pretty-printed symbolic derivative of the active function (for external use)."""
        try:
            return self.engine.pretty(self.engine.symbolic_derivative(self.func_strs[self.active_idx]), use_unicode=False)
        except Exception:
            return "N/A"


# =============================================================================
# CONTAINER FOR EASY DROPPING INTO TABS / EXISTING APPS
# =============================================================================
class Grapher2DFrame(tk.Frame):
    """
    Ready-to-embed titled container. Use this in notebooks/tabs.
    """

    def __init__(self, parent, engine: MathEngine):
        super().__init__(parent, bg=DARK["bg"])
        self.engine = engine

        header = tk.Frame(self, bg=DARK["panel"])
        header.pack(fill="x")
        tk.Label(
            header,
            text="2D Grapher & Calculus Visualizations",
            bg=DARK["panel"], fg=DARK["text"], font=("Segoe UI", 14, "bold")
        ).pack(pady=6, padx=12, anchor="w")

        self.grapher = Grapher2D(self, engine)
        self.grapher.pack(fill="both", expand=True)


# =============================================================================
# BACK-COMPAT ALIASES (so existing imports in main.py and __init__.py keep working)
# =============================================================================
DerivativeExplorer = Grapher2D          # Preferred modern name is Grapher2D
__all__ = ["Grapher2D", "Grapher2DFrame", "DerivativeExplorer"]


# =============================================================================
# STANDALONE RUNNABLE DEMO (run this file directly for instant wow demo)
# =============================================================================
if __name__ == "__main__":
    print("Launching standalone Grapher2D demo...")

    root = tk.Tk()
    root.title("Grapher2D • Derivative Explorer — Standalone Educational Demo")
    root.geometry("1120x780")
    root.minsize(960, 620)
    root.configure(bg=DARK["bg"])

    engine = MathEngine(use_numpy=True)

    # The component itself
    frame = Grapher2DFrame(root, engine)
    frame.pack(fill="both", expand=True, padx=4, pady=4)

    # Extra standalone hint
    hint = tk.Label(
        root,
        text="TIP: Click or drag the white point on the graph • Change expressions (use a,b,c) • Hit Animate h → 0 • This is the limit definition made visual.",
        bg=DARK["panel"], fg=DARK["secondary"], font=("Segoe UI", 9)
    )
    hint.pack(fill="x", pady=(0, 3))

    root.mainloop()
