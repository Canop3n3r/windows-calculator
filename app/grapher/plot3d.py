#!/usr/bin/env python3
"""
Plot3D — High-quality 3D Surface + Vector Field viewer skeleton
for MathForge (Windows Calculator high-tier scientific tool).

================================================================================
ANALYSIS + RECOMMENDATION (Godot research + PyVista vs alternatives)
================================================================================

1. Godot Research Status (as of this task, May 2026):
   - README and main.py document prior investigation into embedding Godot 4
     via LibGodot for "seamless same-window 3D".
   - Conclusion recorded: "technically possible (experimental in 2026) but high
     complexity and build cost."
   - No active Godot math-viz code, IPC bridge, or LibGodot bindings exist in
     the app/ tree. The GodotProjects/ folder contains unrelated game prototypes
     (Fateforge dungeon crawler using standard Godot 3D nodes). No evidence of
     LibGodot, godot-python, or cross-process viz research beyond the high-level
     note.
   - Godot excels at stunning real-time 3D (PBR materials, shaders, particles,
     camera fly-throughs) but would require:
       * Custom Godot build or prebuilt LibGodot (still niche on Windows/Python)
       * Foreign Function Interface or message passing (shared memory / sockets)
         to push live SymPy lambdified data + parameter changes from the Python
         MathEngine into the Godot scene graph every frame.
       * Separate render context (difficult to achieve true "native Tkinter/Qt
         widget" feel without heavy lifting or multi-window).
   - Verdict: Excellent for Phase 3+ premium standalone math-art experiences or
     exported demos, but NOT the right foundation for an embeddable, maintainable,
     zero-friction 3D component inside the current pure-Python Tkinter app.

2. Final Clear Recommendation for 3D Math Visualization:
   **PRIMARY: PyVista (with optional PyVistaQt / PySide6)**
   **IMMEDIATE / FALLBACK (current stack): matplotlib mplot3d (this file)**

   Why PyVista wins for this Python scientific app:
   - Purpose-built for exactly the use-case: interactive 3D surfaces z=f(x,y),
     gradient/vector field glyphs, streamlines, slicing, scalar bars, etc.
   - Native NumPy arrays, lightning-fast mesh + arrow rendering, excellent
     lighting/shading, picking, and widget support.
   - Mature embedding story:
       - Best: PySide6 + pyvistaqt.QtInteractor (professional, responsive
         interactor + Qt sliders in one widget — recommended upgrade path).
       - Acceptable with current Tk: VTK TkRenderWindowInteractor + PyVista
         plotter (works today, a bit more boilerplate).
       - Easy offscreen rendering + image push to Tk canvas as ultimate fallback.
   - Perfect synergy with existing MathEngine (lambdify + symbolic partials
     for gradients are trivial to feed into PyVista StructuredGrid / PolyData).
   - Active ecosystem, easy theming, export to high-quality images/videos.
   - Keeps the entire application a single-process Python distribution (PyInstaller
     friendly once optional deps are gated).

   Matplotlib mplot3d role:
   - Zero new dependencies (already in requirements.txt).
   - 100% consistent dark theme + embed pattern with the existing Grapher2D.
   - Good enough for education right now (plot_surface + quiver3D is very
     effective for teaching gradients on surfaces).
   - Serves as the "always works" reference implementation.

   Godot: Park it for now. Revisit only after the app has shipped multiple
   successful 2D/3D educational features and the team wants AAA visuals + is
   willing to own a multi-process or embedded-engine architecture.

   Migration plan (documented in code below):
   - This module is deliberately structured so the public API (class taking
     parent + MathEngine, public methods like set_function, update_plot) can
     stay stable.
   - The rendering core (_update_plot / _draw_surface_and_vectors) can be
     swapped for a PyVista backend behind a thin abstraction later with
     minimal changes to the rest of the UI.

3. What this skeleton delivers TODAY (Tkinter):
   - Embeddable Plot3DSurface (tk.Frame) and Plot3DFrame container — drop-in
     identical pattern to Grapher2D / Grapher2DFrame.
   - z = f(x, y, a, b, ...) live surface with dynamic parameter sliders
     (discovered via MathEngine, exactly like 2D).
   - Optional gradient vector field overlay (symbolic ∂f/∂x, ∂f/∂y computed
     with the shared engine → 3D quiver arrows sampled on a coarser grid).
   - x/y range controls + sensible presets.
   - Resolution control (coarse → fine).
   - Dark theme 100% consistent with the rest of MathForge.
   - Mouse-rotate / zoom / pan via matplotlib 3D navigation (toolbar included).
   - Clean status + symbolic gradient display.
   - Fully self-contained runnable demo at the bottom (just like grapher_2d.py).
   - Ready for future extension: multiple surfaces, streamlines, contour
     projections, isosurfaces, etc.

4. How to upgrade to PyVista later (notes for next agent / Phase 2):
   - pip install pyvista pyvistaqt PySide6 (uncomment in requirements).
   - Create a sibling Plot3DPyVista class (or backend) that owns a
     pv.Plotter or QtInteractor.
   - Reuse the exact same parameter discovery + MathEngine evaluation logic.
   - For gradient vectors: pv arrows / glyphs are dramatically nicer and faster.
   - For pure-Tk stay: use vtk.tk.vtkTkRenderWindowInteractor (advanced).
   - Recommended: replace the 3D tab content in main.py with a PySide6 QWidget
     hosted via a Tk frame (or migrate the advanced tabs to a hybrid/ Qt
     application shell while keeping the classic calculator Tk window).
   - PyVista gives you free:
       * Camera paths / animation export
       * Beautiful colormaps + scalar bars
       * Point picking + live value readout on surface
       * Much higher visual quality with almost no extra code

Usage (identical to 2D grapher):
    from app.core.math_engine import MathEngine
    from app.grapher.plot3d import Plot3DFrame, Plot3DSurface

    engine = MathEngine()
    viewer = Plot3DFrame(parent, engine)
    viewer.pack(fill="both", expand=True)

Integration point:
    In app/main.py the existing "3D" tab placeholder can be replaced by:
        self.three_d_frame = Plot3DFrame(self.notebook, self.engine)
        ...
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers 3d projection)

# Reuse the powerful shared engine
from app.core.math_engine import MathEngine, MathEngineError


# =============================================================================
# DARK THEME (exact match to Grapher2D + Windows Calculator)
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

SURFACE_COLOR = "#00D4FF"       # cyan-ish base (colormap will dominate)
GRADIENT_COLOR = "#FF79C6"      # pink arrows for strong visual pop
AXIS_COLOR = "#AAAAAA"


class Plot3DSurface(tk.Frame):
    """
    Embeddable 3D Surface + Gradient Vector Field viewer.

    Primary use: z = f(x, y; parameters) with live sliders + gradient overlay.

    This is the matplotlib mplot3d implementation intended as the immediate,
    zero-dependency starting point. See module docstring for PyVista upgrade path.
    """

    def __init__(self, parent, engine: MathEngine):
        super().__init__(parent, bg=DARK["bg"])
        self.engine = engine

        # --- Core state (surface z = f(x,y,params)) ---
        self.func_str = "sin(a*x) * cos(b*y) + 0.2*(x**2 - y**2)"
        self.visible_surface = True
        self.show_gradient = True

        self.params: dict[str, float] = {}
        self.param_vars: dict[str, tk.DoubleVar] = {}
        self.param_scales: dict[str, tk.Scale] = {}

        # Domain
        self.xmin, self.xmax = -3.0, 3.0
        self.ymin, self.ymax = -3.0, 3.0
        self.resolution = 48          # surface grid (NxN)
        self.vector_stride = 4        # coarser sampling for arrows (educational clarity)

        # Matplotlib artists
        self.surface = None
        self.quiver = None
        self.colorbar = None

        self.current_param_list: list[str] = []

        # UI vars
        self.func_var = tk.StringVar(value=self.func_str)
        self.show_surf_var = tk.BooleanVar(value=self.visible_surface)
        self.show_grad_var = tk.BooleanVar(value=self.show_gradient)
        self.res_var = tk.IntVar(value=self.resolution)

        self._build_ui()
        self._setup_plot()
        self._connect_events()

        # Boot
        self._on_func_change()

    # -------------------------------------------------------------------------
    # UI CONSTRUCTION (mirrors Grapher2D style exactly)
    # -------------------------------------------------------------------------
    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=DARK["panel"], height=32)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="3D Surface + Gradient Vector Field",
            bg=DARK["panel"],
            fg=DARK["text"],
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left", padx=12, pady=4)

        tk.Label(
            header,
            text="Educational 3D calculus • Rotate with mouse • Live parameters",
            bg=DARK["panel"],
            fg=DARK["secondary"],
            font=("Segoe UI", 9),
        ).pack(side="left", padx=10)

        # Function row
        func_row = tk.Frame(self, bg=DARK["bg"])
        func_row.pack(fill="x", padx=8, pady=(6, 2))

        tk.Label(
            func_row, text="z = f(x, y; params)",
            bg=DARK["bg"], fg=DARK["secondary"], font=("Segoe UI", 9)
        ).pack(side="left")

        entry = ttk.Entry(func_row, textvariable=self.func_var, width=52, font=("Consolas", 10))
        entry.pack(side="left", fill="x", expand=True, padx=6)
        entry.bind("<Return>", lambda e: self._on_func_change())
        entry.bind("<FocusOut>", lambda e: self._on_func_change())

        # Visibility + options
        opt_row = tk.Frame(self, bg=DARK["bg"])
        opt_row.pack(fill="x", padx=8, pady=2)

        tk.Checkbutton(
            opt_row, text="Show Surface", variable=self.show_surf_var,
            bg=DARK["bg"], fg=DARK["text"], selectcolor=DARK["display"],
            command=self._on_visibility_change
        ).pack(side="left", padx=4)

        tk.Checkbutton(
            opt_row, text="Show Gradient Vectors (symbolic ∂f/∂x, ∂f/∂y)", variable=self.show_grad_var,
            bg=DARK["bg"], fg=DARK["text"], selectcolor=DARK["display"],
            command=self._on_visibility_change
        ).pack(side="left", padx=12)

        # Resolution
        res_frame = tk.Frame(opt_row, bg=DARK["bg"])
        res_frame.pack(side="right")
        tk.Label(res_frame, text="Resolution", bg=DARK["bg"], fg=DARK["secondary"], font=("Segoe UI", 8)).pack(side="left")
        res_scale = tk.Scale(
            res_frame, from_=20, to=90, resolution=2, orient="horizontal",
            length=160, variable=self.res_var,
            command=self._on_resolution_change,
            bg=DARK["bg"], fg=DARK["text"], troughcolor=DARK["btn"],
            highlightthickness=0, activebackground=DARK["accent"]
        )
        res_scale.pack(side="left", padx=4)

        # === PARAMETER SLIDERS (dynamic, same engine-powered logic as 2D) ===
        self.param_section = tk.Frame(self, bg=DARK["bg"])
        self.param_section.pack(fill="x", padx=8, pady=(4, 2))

        param_header = tk.Frame(self.param_section, bg=DARK["bg"])
        param_header.pack(fill="x")
        tk.Label(param_header, text="Live Parameters", bg=DARK["bg"], fg=DARK["secondary"], font=("Segoe UI", 9)).pack(side="left")
        ttk.Button(param_header, text="Reset to 1.0", command=self._reset_params, width=12).pack(side="right")

        self.param_container = tk.Frame(self.param_section, bg=DARK["bg"])
        self.param_container.pack(fill="x", pady=2)

        # === DOMAIN CONTROLS ===
        domain = tk.Frame(self, bg=DARK["bg"])
        domain.pack(fill="x", padx=8, pady=3)

        tk.Label(domain, text="x-range:", bg=DARK["bg"], fg=DARK["text"], font=("Segoe UI", 9)).pack(side="left")
        self.xmin_var = tk.StringVar(value=str(self.xmin))
        self.xmax_var = tk.StringVar(value=str(self.xmax))
        ttk.Entry(domain, textvariable=self.xmin_var, width=6).pack(side="left", padx=2)
        tk.Label(domain, text="to", bg=DARK["bg"], fg=DARK["secondary"], font=("Segoe UI", 9)).pack(side="left")
        ttk.Entry(domain, textvariable=self.xmax_var, width=6).pack(side="left", padx=2)

        tk.Label(domain, text="   y-range:", bg=DARK["bg"], fg=DARK["text"], font=("Segoe UI", 9)).pack(side="left", padx=(8, 0))
        self.ymin_var = tk.StringVar(value=str(self.ymin))
        self.ymax_var = tk.StringVar(value=str(self.ymax))
        ttk.Entry(domain, textvariable=self.ymin_var, width=6).pack(side="left", padx=2)
        tk.Label(domain, text="to", bg=DARK["bg"], fg=DARK["secondary"], font=("Segoe UI", 9)).pack(side="left")
        ttk.Entry(domain, textvariable=self.ymax_var, width=6).pack(side="left", padx=2)

        ttk.Button(domain, text="Apply", command=self._apply_domain, width=7).pack(side="left", padx=6)

        # Presets
        presets = [
            ("[-π,π]²", -np.pi, np.pi, -np.pi, np.pi),
            ("[-2,2]²", -2.0, 2.0, -2.0, 2.0),
            ("[-5,5]×[-3,3]", -5.0, 5.0, -3.0, 3.0),
            ("[0,4]²", 0.0, 4.0, 0.0, 4.0),
        ]
        for label, x0, x1, y0, y1 in presets:
            b = ttk.Button(domain, text=label, width=9,
                           command=lambda xlo=x0, xhi=x1, ylo=y0, yhi=y1: self._set_domain(xlo, xhi, ylo, yhi))
            b.pack(side="left", padx=1)

        # === MATPLOTLIB 3D CANVAS ===
        plot_frame = tk.Frame(self, bg=DARK["bg"])
        plot_frame.pack(fill="both", expand=True, padx=6, pady=4)

        # Important: constrained_layout=False for 3D stability with colorbar
        self.fig = Figure(figsize=(9.2, 6.6), dpi=100, facecolor=DARK["bg"])
        self.ax: Axes3D = self.fig.add_subplot(111, projection="3d")
        self.ax.set_facecolor(DARK["display"])

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas, plot_frame, pack_toolbar=False)
        self.toolbar.pack(fill="x")

        # === INFO + STATUS ===
        info = tk.Frame(self, bg=DARK["panel"])
        info.pack(fill="x", padx=8, pady=(0, 6))

        self.grad_info = tk.Label(
            info, text="∇f = (∂f/∂x, ∂f/∂y) = —",
            bg=DARK["panel"], fg=DARK["warning"], font=("Consolas", 10), anchor="w"
        )
        self.grad_info.pack(fill="x", padx=6, pady=(4, 0))

        self.status = tk.Label(
            info, text="Drag to rotate • Scroll to zoom • Right-drag to pan  •  Educational gradient overlay uses symbolic derivatives",
            bg=DARK["panel"], fg=DARK["secondary"], font=("Segoe UI", 8), anchor="w"
        )
        self.status.pack(fill="x", padx=6, pady=(2, 4))

    def _setup_plot(self):
        self.ax.tick_params(colors=DARK["secondary"])
        for spine in self.ax.spines.values():
            spine.set_color(DARK["spine"])
        self.ax.set_xlabel("x", color=DARK["secondary"])
        self.ax.set_ylabel("y", color=DARK["secondary"])
        self.ax.set_zlabel("z = f(x,y)", color=DARK["secondary"])
        # Initial camera
        self.ax.view_init(elev=28, azim=-65)

    # -------------------------------------------------------------------------
    # EVENT HANDLING
    # -------------------------------------------------------------------------
    def _connect_events(self):
        # Resolution change already wired via command
        pass

    def _on_func_change(self, *args):
        new_str = self.func_var.get().strip()
        if new_str:
            self.func_str = new_str

        self._prepare_parameters()
        self._rebuild_param_sliders()
        self._update_plot(full=True)

    def _on_visibility_change(self):
        self.visible_surface = self.show_surf_var.get()
        self.show_gradient = self.show_grad_var.get()
        self._update_plot(full=False)

    def _on_resolution_change(self, val):
        self.resolution = int(val)
        self._update_plot(full=True)

    # -------------------------------------------------------------------------
    # PARAMETER SYSTEM (identical philosophy to Grapher2D)
    # -------------------------------------------------------------------------
    def _prepare_parameters(self):
        all_params: set[str] = set()
        try:
            expr = self.engine.parse(self.func_str)
            free = self.engine.get_free_symbols(expr)
            for p in free:
                if p not in ("x", "y"):
                    all_params.add(p)
        except Exception:
            pass

        new_list = sorted(all_params)[:5]  # sensible cap

        for p in new_list:
            if p not in self.params:
                self.params[p] = 1.0

        self.current_param_list = new_list

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
                text="No parameters detected (pure function of x and y)",
                bg=DARK["bg"], fg=DARK["secondary"], font=("Segoe UI", 9, "italic")
            ).pack(anchor="w", pady=2)
            return

        row = tk.Frame(self.param_container, bg=DARK["bg"])
        row.pack(fill="x")

        for p in self.current_param_list:
            col = tk.Frame(row, bg=DARK["bg"])
            col.pack(side="left", padx=8, fill="x", expand=True)

            val = self.params.get(p, 1.0)
            var = tk.DoubleVar(value=val)
            self.param_vars[p] = var

            label = tk.Label(col, text=f"{p} =", bg=DARK["bg"], fg=DARK["text"], font=("Segoe UI", 9))
            label.pack(side="left")

            value_lbl = tk.Label(col, text=f"{val:.3f}", bg=DARK["bg"], fg=DARK["accent"],
                                 font=("Consolas", 9, "bold"), width=7)
            value_lbl.pack(side="left", padx=(2, 6))

            lo, hi, res = (-5.0, 5.0, 0.02) if p in ("a", "b", "c", "k", "m") else (-4.0, 4.0, 0.05)

            scale = tk.Scale(
                col, from_=lo, to=hi, resolution=res, orient="horizontal",
                length=120, variable=var,
                command=lambda v, pp=p, lbl=value_lbl: self._on_param_change(pp, v, lbl),
                bg=DARK["bg"], fg=DARK["text"], troughcolor=DARK["btn"],
                highlightthickness=0, activebackground=DARK["accent"]
            )
            scale.pack(side="left", fill="x", expand=True)
            self.param_scales[p] = scale

            var.trace_add("write", lambda *_, pp=p, lbl=value_lbl, vv=var: lbl.config(text=f"{vv.get():.3f}"))

    def _on_param_change(self, p: str, val, value_label=None):
        try:
            self.params[p] = float(val)
        except Exception:
            self.params[p] = 1.0
        if value_label:
            value_label.config(text=f"{self.params[p]:.3f}")
        self._update_plot(full=False)

    def _reset_params(self):
        for p in self.current_param_list:
            self.params[p] = 1.0
            if p in self.param_vars:
                self.param_vars[p].set(1.0)
        self._update_plot(full=True)

    # -------------------------------------------------------------------------
    # DOMAIN
    # -------------------------------------------------------------------------
    def _apply_domain(self):
        try:
            xlo = float(self.xmin_var.get())
            xhi = float(self.xmax_var.get())
            ylo = float(self.ymin_var.get())
            yhi = float(self.ymax_var.get())
            if xlo >= xhi or ylo >= yhi:
                raise ValueError
            self._set_domain(xlo, xhi, ylo, yhi)
        except Exception:
            self.status.config(text="Invalid domain — using previous values", fg=DARK["error"])
            self.after(1600, lambda: self.status.config(text="Drag to rotate • Scroll to zoom • Right-drag to pan"))

    def _set_domain(self, xlo: float, xhi: float, ylo: float, yhi: float):
        self.xmin, self.xmax = float(xlo), float(xhi)
        self.ymin, self.ymax = float(ylo), float(yhi)
        self.xmin_var.set(f"{self.xmin:.3g}")
        self.xmax_var.set(f"{self.xmax:.3g}")
        self.ymin_var.set(f"{self.ymin:.3g}")
        self.ymax_var.set(f"{self.ymax:.3g}")
        self._update_plot(full=True)

    # -------------------------------------------------------------------------
    # CORE 3D RENDERING (the heart of the skeleton)
    # -------------------------------------------------------------------------
    def _update_plot(self, full: bool = True):
        """Recompute surface + optional gradient quiver. full=True clears artists."""
        try:
            self.ax.cla()
            self.ax.set_facecolor(DARK["display"])
            self.ax.tick_params(colors=DARK["secondary"])
            for spine in self.ax.spines.values():
                spine.set_color(DARK["spine"])
            self.ax.set_xlabel("x", color=DARK["secondary"])
            self.ax.set_ylabel("y", color=DARK["secondary"])
            self.ax.set_zlabel("z", color=DARK["secondary"])

            # Build grids
            nx = max(20, min(int(self.resolution), 120))
            ny = nx
            x = np.linspace(self.xmin, self.xmax, nx)
            y = np.linspace(self.ymin, self.ymax, ny)
            X, Y = np.meshgrid(x, y)

            # Evaluate surface via the shared high-performance engine
            try:
                Z = self.engine.evaluate_numeric(
                    self.func_str, {"x": X.ravel(), "y": Y.ravel(), **self.params}
                )
                Z = np.asarray(Z, dtype=float).reshape(X.shape)
            except MathEngineError as me:
                self.status.config(text=f"Eval error: {me}", fg=DARK["error"])
                self.canvas.draw_idle()
                return
            except Exception as e:
                self.status.config(text=f"Plot error: {str(e)[:80]}", fg=DARK["error"])
                self.canvas.draw_idle()
                return

            # Surface
            if self.visible_surface:
                try:
                    self.surface = self.ax.plot_surface(
                        X, Y, Z,
                        cmap="viridis",          # excellent perceptual colormap
                        alpha=0.82,
                        linewidth=0,
                        antialiased=True,
                        rstride=1, cstride=1,
                        edgecolor="none"
                    )
                except Exception:
                    # Extremely rare fallback
                    self.surface = self.ax.plot_wireframe(X, Y, Z, color=SURFACE_COLOR, linewidth=0.6, alpha=0.7)

            # Gradient vector field (symbolic via MathEngine — the educational gold)
            if self.show_gradient:
                self._draw_gradient_quiver(X, Y, Z)

            # Auto-scale + nice limits
            if np.all(np.isfinite(Z)):
                zmin, zmax = float(np.nanmin(Z)), float(np.nanmax(Z))
                if zmax - zmin < 1e-6:
                    zmin -= 0.5
                    zmax += 0.5
                pad = (zmax - zmin) * 0.12
                self.ax.set_zlim(zmin - pad, zmax + pad)

            self.ax.set_xlim(self.xmin, self.xmax)
            self.ax.set_ylim(self.ymin, self.ymax)

            # Restore a pleasant default view on major changes
            if full:
                self.ax.view_init(elev=26, azim=-62)

            self.canvas.draw_idle()
            self._update_info_panel()

            if "error" in self.status.cget("text").lower():
                self.status.config(text="Drag to rotate • Scroll to zoom • Right-drag to pan  •  Symbolic gradient overlay active")

        except Exception as e:
            self.status.config(text=f"Unexpected plot error: {str(e)[:70]}", fg=DARK["error"])

    def _draw_gradient_quiver(self, X: np.ndarray, Y: np.ndarray, Z: np.ndarray):
        """Compute symbolic gradient and draw 3D arrows on a coarser grid."""
        try:
            # Symbolic partial derivatives (reuses the engine's SymPy diff)
            fx_expr = self.engine.symbolic_derivative(self.func_str, var="x")
            fy_expr = self.engine.symbolic_derivative(self.func_str, var="y")

            # Coarser sampling grid for arrows (prevents visual clutter)
            step = max(1, self.vector_stride)
            xs = X[::step, ::step].ravel()
            ys = Y[::step, ::step].ravel()

            # Evaluate partials + height at those points
            vals = {"x": xs, "y": ys, **self.params}
            fx = np.asarray(self.engine.evaluate_numeric(fx_expr, vals), dtype=float)
            fy = np.asarray(self.engine.evaluate_numeric(fy_expr, vals), dtype=float)

            # Heights at arrow bases
            zs = np.asarray(self.engine.evaluate_numeric(self.func_str, vals), dtype=float)

            # Scale arrows for visibility (magnitude-aware but capped)
            mag = np.sqrt(fx**2 + fy**2 + 1e-12)
            scale = 0.35 / (np.median(mag) + 0.15)   # heuristic good for most surfaces
            dx = fx * scale
            dy = fy * scale
            dz = np.zeros_like(dx)                   # arrows are "flat" in z for clarity; easy to change

            # Draw
            self.quiver = self.ax.quiver(
                xs, ys, zs,
                dx, dy, dz,
                color=GRADIENT_COLOR,
                length=1.0,          # we already scaled
                normalize=False,
                arrow_length_ratio=0.35,
                linewidths=1.1,
                alpha=0.92
            )

            # Store for potential future manipulation
            self._last_gradient = (fx_expr, fy_expr)

        except Exception as e:
            # Gradient computation failed for this expression (e.g. not differentiable or bad params)
            # Just skip arrows silently — surface still renders
            self.quiver = None
            # Optional: could show a tiny warning in status on first failure only
            pass

    def _update_info_panel(self):
        try:
            fx = self.engine.symbolic_derivative(self.func_str, "x")
            fy = self.engine.symbolic_derivative(self.func_str, "y")
            pretty_x = self.engine.pretty(fx, use_unicode=True)
            pretty_y = self.engine.pretty(fy, use_unicode=True)
            if len(pretty_x) + len(pretty_y) > 92:
                pretty_x = pretty_x[:42] + "…"
                pretty_y = pretty_y[:42] + "…"
            self.grad_info.config(
                text=f"∇f = (∂f/∂x, ∂f/∂y)  =  ({pretty_x},  {pretty_y})",
                fg=DARK["warning"]
            )
        except Exception:
            self.grad_info.config(text="∇f = (symbolic gradient unavailable for this expression)", fg=DARK["error"])

    # -------------------------------------------------------------------------
    # PUBLIC API (stable for future PyVista swap-in)
    # -------------------------------------------------------------------------
    def set_function(self, expr: str):
        """Programmatic control (useful for demos / notebooks)."""
        self.func_var.set(expr)
        self.func_str = expr
        self._on_func_change()

    def set_domain(self, xmin: float, xmax: float, ymin: float, ymax: float):
        self._set_domain(xmin, xmax, ymin, ymax)

    def set_params(self, **kwargs):
        for k, v in kwargs.items():
            if k in self.params:
                self.params[k] = float(v)
                if k in self.param_vars:
                    self.param_vars[k].set(float(v))
        self._update_plot(full=True)

    def toggle_gradient(self, show: bool):
        self.show_gradient = bool(show)
        self.show_grad_var.set(self.show_gradient)
        self._update_plot(full=False)


# =============================================================================
# READY-TO-USE CONTAINER (exact parallel to Grapher2DFrame)
# =============================================================================
class Plot3DFrame(tk.Frame):
    """
    Titled container for easy embedding into tabs/notebooks.
    Drop-in replacement pattern for the existing 3D placeholder in main.py.
    """

    def __init__(self, parent, engine: MathEngine):
        super().__init__(parent, bg=DARK["bg"])
        self.engine = engine

        header = tk.Frame(self, bg=DARK["panel"])
        header.pack(fill="x")
        tk.Label(
            header,
            text="3D Surfaces & Vector Fields  •  matplotlib mplot3d (PyVista upgrade path ready)",
            bg=DARK["panel"], fg=DARK["text"], font=("Segoe UI", 14, "bold")
        ).pack(pady=6, padx=12, anchor="w")

        self.viewer = Plot3DSurface(self, engine)
        self.viewer.pack(fill="both", expand=True)


# =============================================================================
# STANDALONE DEMO (run this file directly — instant 3D gratification)
# =============================================================================
if __name__ == "__main__":
    print("Launching standalone Plot3DSurface demo (matplotlib 3D + MathEngine)...")

    root = tk.Tk()
    root.title("MathForge • 3D Surface + Gradient Vector Field (matplotlib skeleton)")
    root.geometry("1180x820")
    root.minsize(980, 680)
    root.configure(bg=DARK["bg"])

    engine = MathEngine(use_numpy=True)

    frame = Plot3DFrame(root, engine)
    frame.pack(fill="both", expand=True, padx=4, pady=4)

    # Helpful footer
    footer = tk.Label(
        root,
        text="TIP: Try editing the expression (use a,b,c) → hit Enter.  Toggle gradient arrows.  Change resolution.  "
             "Classic surfaces: 'a*x**2 + b*y**2', 'sin(a*x)*cos(b*y)', 'exp(-0.1*(x**2+y**2))*cos(3*x)*sin(2*y)'",
        bg=DARK["panel"], fg=DARK["secondary"], font=("Segoe UI", 9)
    )
    footer.pack(fill="x", pady=(0, 3))

    root.mainloop()
