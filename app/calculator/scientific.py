#!/usr/bin/env python3
"""
Scientific Expression Calculator — Full SymPy-powered mode for MathForge.

A self-contained, dark-themed Tkinter Frame implementing professional-grade
expression entry, symbolic operations, numeric approximation with parameters,
history, and beautiful result display.

Usage (embeddable):
    from app.core.math_engine import MathEngine
    from app.calculator.scientific import ScientificCalculator, ScientificCalculatorFrame

    engine = MathEngine()
    calc = ScientificCalculator(parent, engine)
    calc.pack(fill="both", expand=True)

Or use ScientificCalculatorFrame for a ready titled container (perfect for tabs).

Features:
- Large expression entry with full MathEngine / SymPy syntax (^ power, implicit *, all functions)
- Evaluate (Enter key) + instant symbolic pretty + LaTeX + high-precision numeric
- One-click quick actions: Derivative, Indefinite/Definite Integral, Limit, Simplify, Taylor, Expand, Factor
- Live parameter / variable panel with editable values for numeric approximations
- Clickable history (last 20) that reloads expressions instantly
- Example presets for instant exploration
- Smart insert buttons for common math tokens
- Helpful, precise error display powered by MathEngineError
- Chaining-friendly workflow (load result back to input)
- Modern dark theme consistent with the rest of MathForge
- Standalone demo runnable

Integrates directly with production MathEngine — zero duplication of math logic.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any

import sympy as sp

from app.core.math_engine import MathEngine, MathEngineError


# =============================================================================
# DARK MODERN THEME (identical contract with Grapher2D for visual harmony)
# =============================================================================

DARK = {
    "bg": "#202020",
    "panel": "#1A1A1A",
    "display": "#2D2D2D",
    "btn": "#3A3A3A",
    "btn_hover": "#4A4A4A",
    "accent": "#0078D4",
    "accent2": "#00A3E0",
    "text": "#FFFFFF",
    "secondary": "#B0B0B0",
    "success": "#4ADE80",
    "warning": "#FACC15",
    "error": "#F87171",
    "result_bg": "#252525",
    "history_bg": "#181818",
}


# =============================================================================
# THE CORE WIDGET
# =============================================================================

class ScientificCalculator(tk.Frame):
    """
    The primary embeddable Scientific Expression Calculator.

    Drop this Frame anywhere you have a MathEngine instance.
    """

    HISTORY_LIMIT = 20

    def __init__(self, parent, engine: MathEngine | None = None):
        super().__init__(parent, bg=DARK["bg"])
        self.engine = engine or MathEngine(use_numpy=True)

        # --- State ---
        self.current_result_expr: sp.Expr | None = None
        self.param_vars: dict[str, tk.StringVar] = {}
        self.param_entries: dict[str, tk.Entry] = {}
        self.history: list[dict[str, Any]] = []          # newest first
        self.history_display: list[str] = []

        # Operation parameter widgets (populated in UI)
        self.var_var = tk.StringVar(value="x")
        self.limit_point_var = tk.StringVar(value="0")
        self.limit_dir_var = tk.StringVar(value="+-")
        self.taylor_point_var = tk.StringVar(value="0")
        self.taylor_order_var = tk.IntVar(value=6)
        self.int_lower_var = tk.StringVar(value="0")
        self.int_upper_var = tk.StringVar(value="1")

        self._setup_styles()
        self._build_ui()

        # Boot with a nice starter expression
        self._load_example("x^2 * sin(x) + exp(-x/2)")

        # Initial variable discovery
        self.after(120, self._refresh_parameters)

    # -------------------------------------------------------------------------
    # STYLING
    # -------------------------------------------------------------------------
    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Large input
        style.configure(
            "SciInput.TEntry",
            fieldbackground=DARK["display"],
            foreground=DARK["text"],
            font=("Consolas", 16, "bold"),
            borderwidth=1,
            relief="flat",
            padding=10,
        )

        # Result displays
        style.configure(
            "Result.TLabel",
            background=DARK["result_bg"],
            foreground=DARK["text"],
            font=("Consolas", 13),
            padding=8,
            anchor="w",
        )

        # Action buttons (prominent)
        style.configure(
            "SciAction.TButton",
            font=("Segoe UI", 10, "bold"),
            background=DARK["btn"],
            foreground=DARK["text"],
            padding=(10, 8),
            borderwidth=0,
        )
        style.map(
            "SciAction.TButton",
            background=[("active", DARK["accent"]), ("pressed", "#005A9E")],
            foreground=[("active", "#FFFFFF")],
        )

        # Small utility buttons
        style.configure(
            "SciSmall.TButton",
            font=("Segoe UI", 9),
            background=DARK["btn"],
            foreground=DARK["secondary"],
            padding=(6, 4),
        )
        style.map(
            "SciSmall.TButton",
            background=[("active", DARK["btn_hover"])],
        )

        # Success / copy buttons
        style.configure(
            "SciSuccess.TButton",
            font=("Segoe UI", 9, "bold"),
            background="#166534",
            foreground=DARK["success"],
            padding=(6, 4),
        )

    # -------------------------------------------------------------------------
    # UI CONSTRUCTION
    # -------------------------------------------------------------------------
    def _build_ui(self):
        # === HEADER ===
        header = tk.Frame(self, bg=DARK["panel"], height=38)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Scientific Expression Calculator",
            bg=DARK["panel"],
            fg=DARK["text"],
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left", padx=14, pady=6)

        tk.Label(
            header,
            text="Full SymPy syntax  •  Powered by MathEngine",
            bg=DARK["panel"],
            fg=DARK["secondary"],
            font=("Segoe UI", 9),
        ).pack(side="left", padx=8)

        # Quick status
        self.status_label = tk.Label(
            header, text="Ready", bg=DARK["panel"], fg=DARK["success"],
            font=("Segoe UI", 9, "bold")
        )
        self.status_label.pack(side="right", padx=14)

        # === EXPRESSION INPUT ===
        input_outer = tk.Frame(self, bg=DARK["bg"])
        input_outer.pack(fill="x", padx=8, pady=(8, 4))

        tk.Label(
            input_outer,
            text="Expression  (use ^ for powers, implicit multiplication, sin, cos, ln, pi, oo, etc.)",
            bg=DARK["bg"],
            fg=DARK["secondary"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=2)

        # Big input row
        input_row = tk.Frame(input_outer, bg=DARK["bg"])
        input_row.pack(fill="x", pady=3)

        self.expr_var = tk.StringVar()
        self.input_entry = ttk.Entry(
            input_row,
            textvariable=self.expr_var,
            style="SciInput.TEntry",
            width=70,
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.input_entry.bind("<Return>", self._on_evaluate)
        self.input_entry.bind("<FocusOut>", lambda e: self._refresh_parameters())
        self.input_entry.bind("<KeyRelease>", lambda e: self._debounced_param_refresh())

        # Evaluate button (big & prominent)
        self.eval_btn = ttk.Button(
            input_row,
            text="EVALUATE",
            style="SciAction.TButton",
            command=self._on_evaluate,
            width=14,
        )
        self.eval_btn.pack(side="left", padx=2, ipady=4)

        # === SMART INSERT BUTTONS (impressive calculator feel) ===
        insert_bar = tk.Frame(input_outer, bg=DARK["bg"])
        insert_bar.pack(fill="x", pady=(2, 4))

        inserts = [
            ("π", "pi"), ("e", "e"), ("θ", "theta"), ("∞", "oo"),
            ("x", "x"), ("^2", "**2"), ("^", "^"), ("√", "sqrt("),
            ("sin(", "sin("), ("cos(", "cos("), ("tan(", "tan("),
            ("ln(", "ln("), ("exp(", "exp("), ("abs(", "abs("),
            ("(", "("), (")", ")"), ("/", "/"),
        ]

        for label, token in inserts:
            b = ttk.Button(
                insert_bar,
                text=label,
                style="SciSmall.TButton",
                width=4,
                command=lambda t=token: self._insert_token(t),
            )
            b.pack(side="left", padx=1, pady=1)

        ttk.Button(
            insert_bar,
            text="Clear",
            style="SciSmall.TButton",
            command=lambda: (self.expr_var.set(""), self._refresh_parameters()),
        ).pack(side="right", padx=4)

        # === OPERATION PARAMETER CONTROLS ===
        params_bar = tk.Frame(self, bg=DARK["panel"])
        params_bar.pack(fill="x", padx=8, pady=3)

        # Variable selector
        tk.Label(params_bar, text="Main variable:", bg=DARK["panel"], fg=DARK["text"],
                 font=("Segoe UI", 9)).pack(side="left", padx=(8, 3))
        self.var_entry = ttk.Entry(params_bar, textvariable=self.var_var, width=6, font=("Consolas", 10))
        self.var_entry.pack(side="left", padx=2)

        # Limit controls
        tk.Label(params_bar, text="  Limit @", bg=DARK["panel"], fg=DARK["secondary"],
                 font=("Segoe UI", 9)).pack(side="left", padx=4)
        ttk.Entry(params_bar, textvariable=self.limit_point_var, width=6).pack(side="left")
        ttk.Combobox(
            params_bar, textvariable=self.limit_dir_var,
            values=["+-", "+", "-", "real"], width=5, state="readonly"
        ).pack(side="left", padx=2)

        # Taylor controls
        tk.Label(params_bar, text="  Taylor @", bg=DARK["panel"], fg=DARK["secondary"],
                 font=("Segoe UI", 9)).pack(side="left", padx=6)
        ttk.Entry(params_bar, textvariable=self.taylor_point_var, width=5).pack(side="left")
        tk.Label(params_bar, text="order", bg=DARK["panel"], fg=DARK["secondary"],
                 font=("Segoe UI", 8)).pack(side="left", padx=1)
        ttk.Spinbox(
            params_bar, from_=2, to=30, textvariable=self.taylor_order_var,
            width=4, command=self._noop
        ).pack(side="left", padx=1)

        # Definite integral bounds
        tk.Label(params_bar, text="  Def. ∫ from", bg=DARK["panel"], fg=DARK["secondary"],
                 font=("Segoe UI", 9)).pack(side="left", padx=8)
        ttk.Entry(params_bar, textvariable=self.int_lower_var, width=6).pack(side="left")
        tk.Label(params_bar, text="to", bg=DARK["panel"], fg=DARK["secondary"],
                 font=("Segoe UI", 9)).pack(side="left", padx=2)
        ttk.Entry(params_bar, textvariable=self.int_upper_var, width=6).pack(side="left")

        # === QUICK ACTION BUTTONS (the heart of the experience) ===
        actions_outer = tk.Frame(self, bg=DARK["bg"])
        actions_outer.pack(fill="x", padx=8, pady=4)

        tk.Label(
            actions_outer,
            text="Quick Actions — operate on the expression above",
            bg=DARK["bg"], fg=DARK["secondary"], font=("Segoe UI", 9)
        ).pack(anchor="w", padx=2, pady=(0, 2))

        actions_row = tk.Frame(actions_outer, bg=DARK["bg"])
        actions_row.pack(fill="x")

        # Calculus group
        calc_actions = [
            ("Derivative", self._do_derivative, "#1E3A5F"),
            ("∫ Indefinite", self._do_integral_indef, "#1E3A5F"),
            ("∫ Definite", self._do_integral_def, "#1E3A5F"),
            ("Limit", self._do_limit, "#1E3A5F"),
            ("Taylor", self._do_taylor, "#1E3A5F"),
        ]

        # Algebra group
        alg_actions = [
            ("Simplify", self._do_simplify, "#2F2A1F"),
            ("Expand", self._do_expand, "#2F2A1F"),
            ("Factor", self._do_factor, "#2F2A1F"),
        ]

        for text, cmd, _ in calc_actions:
            btn = ttk.Button(
                actions_row, text=text, command=cmd, style="SciAction.TButton", width=13
            )
            btn.pack(side="left", padx=2, pady=1)

        # Separator visual
        sep = tk.Frame(actions_row, bg=DARK["secondary"], width=1)
        sep.pack(side="left", fill="y", padx=6, pady=2)

        for text, cmd, _ in alg_actions:
            btn = ttk.Button(
                actions_row, text=text, command=cmd, style="SciAction.TButton", width=10
            )
            btn.pack(side="left", padx=2, pady=1)

        # === RESULTS DISPLAY (beautiful cards) ===
        results = tk.Frame(self, bg=DARK["bg"])
        results.pack(fill="both", expand=False, padx=8, pady=6)

        # Pretty result
        pretty_frame = tk.LabelFrame(
            results, text="  Pretty Result (Unicode)", bg=DARK["bg"],
            fg=DARK["accent"], font=("Segoe UI", 10, "bold"), bd=1, relief="groove"
        )
        pretty_frame.pack(fill="x", pady=(0, 3))

        self.pretty_var = tk.StringVar(value="—")
        self.pretty_label = tk.Label(
            pretty_frame,
            textvariable=self.pretty_var,
            bg=DARK["result_bg"],
            fg=DARK["text"],
            font=("Consolas", 14),
            anchor="w",
            padx=10, pady=6,
            justify="left",
            wraplength=900,
        )
        self.pretty_label.pack(fill="x")

        # LaTeX + Numeric side by side
        side = tk.Frame(results, bg=DARK["bg"])
        side.pack(fill="x")

        # LaTeX card
        latex_frame = tk.LabelFrame(
            side, text="  LaTeX (copy for docs / Overleaf)", bg=DARK["bg"],
            fg=DARK["accent2"], font=("Segoe UI", 10, "bold"), bd=1, relief="groove"
        )
        latex_frame.pack(side="left", fill="both", expand=True, padx=(0, 4))

        self.latex_var = tk.StringVar(value="—")
        latex_row = tk.Frame(latex_frame, bg=DARK["result_bg"])
        latex_row.pack(fill="x")
        self.latex_label = tk.Label(
            latex_row, textvariable=self.latex_var,
            bg=DARK["result_bg"], fg="#A5D6FF", font=("Consolas", 11),
            anchor="w", padx=8, pady=5, wraplength=420
        )
        self.latex_label.pack(side="left", fill="x", expand=True)

        ttk.Button(
            latex_row, text="Copy LaTeX", style="SciSuccess.TButton",
            command=self._copy_latex
        ).pack(side="right", padx=4, pady=3)

        # Numeric card
        num_frame = tk.LabelFrame(
            side, text="  Numeric Approximation (high precision)", bg=DARK["bg"],
            fg=DARK["success"], font=("Segoe UI", 10, "bold"), bd=1, relief="groove"
        )
        num_frame.pack(side="left", fill="both", expand=True, padx=(4, 0))

        num_row = tk.Frame(num_frame, bg=DARK["result_bg"])
        num_row.pack(fill="x")
        self.numeric_var = tk.StringVar(value="—")
        self.numeric_label = tk.Label(
            num_row, textvariable=self.numeric_var,
            bg=DARK["result_bg"], fg=DARK["success"], font=("Consolas", 13, "bold"),
            anchor="w", padx=10, pady=5
        )
        self.numeric_label.pack(side="left", fill="x", expand=True)

        ttk.Button(
            num_row, text="Copy Value", style="SciSuccess.TButton",
            command=self._copy_numeric
        ).pack(side="right", padx=4, pady=3)

        # Result actions
        result_actions = tk.Frame(results, bg=DARK["bg"])
        result_actions.pack(fill="x", pady=(4, 0))

        ttk.Button(
            result_actions, text="→ Load Result into Input (chain operations)",
            command=self._load_result_to_input, style="SciSmall.TButton"
        ).pack(side="left", padx=2)

        ttk.Button(
            result_actions, text="Re-evaluate Current Result",
            command=self._reevaluate_current, style="SciSmall.TButton"
        ).pack(side="left", padx=4)

        ttk.Button(
            result_actions, text="Clear Results",
            command=self._clear_results, style="SciSmall.TButton"
        ).pack(side="right", padx=2)

        # === PARAMETERS / VARIABLES PANEL (critical for "support for variables") ===
        param_section = tk.LabelFrame(
            self, text="  Parameters & Variables — edit values for numeric approximation",
            bg=DARK["bg"], fg=DARK["warning"], font=("Segoe UI", 10, "bold"),
            bd=1, relief="groove"
        )
        param_section.pack(fill="x", padx=8, pady=4)

        param_header = tk.Frame(param_section, bg=DARK["bg"])
        param_header.pack(fill="x", padx=6, pady=2)

        tk.Label(
            param_header,
            text="Free symbols detected from expression. Change values then Evaluate / actions to see numeric impact.",
            bg=DARK["bg"], fg=DARK["secondary"], font=("Segoe UI", 8)
        ).pack(side="left")

        ttk.Button(
            param_header, text="Refresh Variables", style="SciSmall.TButton",
            command=self._refresh_parameters
        ).pack(side="right", padx=2)
        ttk.Button(
            param_header, text="Reset to 1.0", style="SciSmall.TButton",
            command=self._reset_parameters
        ).pack(side="right", padx=2)

        self.param_container = tk.Frame(param_section, bg=DARK["bg"])
        self.param_container.pack(fill="x", padx=6, pady=4)

        # Placeholder text shown until symbols exist
        self.param_placeholder = tk.Label(
            self.param_container,
            text="No free variables — expression is constant or uses only pi/e/oo.",
            bg=DARK["bg"], fg=DARK["secondary"], font=("Segoe UI", 9, "italic")
        )
        self.param_placeholder.pack(anchor="w")

        # === EXAMPLES + HISTORY (side-by-side for density) ===
        bottom = tk.Frame(self, bg=DARK["bg"])
        bottom.pack(fill="both", expand=True, padx=8, pady=(2, 6))

        # Examples (left)
        ex_frame = tk.LabelFrame(
            bottom, text="  Example Expressions (click to load)",
            bg=DARK["bg"], fg=DARK["accent"], font=("Segoe UI", 10, "bold"),
            bd=1, relief="groove"
        )
        ex_frame.pack(side="left", fill="both", expand=False, padx=(0, 6))

        examples = [
            "x^2 + 3*sin(x) + ln(x+1)",
            "a*x^2 + b*x + c",
            "(1 + x)^(1/x)",
            "sin(x)/x",
            "exp(-x^2)",
            "x^3 - 6*x^2 + 11*x - 6",
            "sqrt(1 - x^2)",
            "sin(x)^2 + cos(x)^2",
            "diff(x^2, x)   # you can even paste raw SymPy if careful",
            "integrate(sin(x), x)",
        ]

        for ex in examples:
            lbl = tk.Label(
                ex_frame, text=ex, bg=DARK["panel"], fg="#A0D2FF",
                font=("Consolas", 9), anchor="w", padx=6, pady=2, cursor="hand2"
            )
            lbl.pack(fill="x")
            lbl.bind("<Button-1>", lambda e, ex=ex: self._load_example(ex))

        # History (right, dominant)
        hist_frame = tk.LabelFrame(
            bottom, text="  History (last 20 — click any entry to reload expression)",
            bg=DARK["bg"], fg=DARK["accent"], font=("Segoe UI", 10, "bold"),
            bd=1, relief="groove"
        )
        hist_frame.pack(side="left", fill="both", expand=True)

        hist_toolbar = tk.Frame(hist_frame, bg=DARK["bg"])
        hist_toolbar.pack(fill="x", padx=4, pady=2)

        ttk.Button(
            hist_toolbar, text="Clear History", style="SciSmall.TButton",
            command=self._clear_history
        ).pack(side="right")

        self.history_lb = tk.Listbox(
            hist_frame,
            bg=DARK["history_bg"],
            fg=DARK["text"],
            font=("Consolas", 9),
            height=7,
            selectbackground=DARK["accent"],
            selectforeground="#FFFFFF",
            activestyle="none",
            relief="flat",
            borderwidth=0,
        )
        self.history_lb.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.history_lb.bind("<<ListboxSelect>>", self._on_history_click)

        # === ERROR / STATUS BAR ===
        self.error_bar = tk.Frame(self, bg=DARK["error"], height=26)
        self.error_bar.pack(fill="x", side="bottom", padx=0, pady=0)
        self.error_bar.pack_propagate(False)

        self.error_label = tk.Label(
            self.error_bar,
            text="",
            bg=DARK["error"],
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            padx=10,
        )
        self.error_label.pack(fill="both", expand=True)

        # Hide error bar initially
        self._hide_error()

    # -------------------------------------------------------------------------
    # HELPER METHODS — INPUT & TOKENS
    # -------------------------------------------------------------------------
    def _insert_token(self, token: str):
        """Insert math token at cursor position intelligently."""
        entry = self.input_entry
        pos = entry.index(tk.INSERT)
        current = self.expr_var.get()
        new_text = current[:pos] + token + current[pos:]
        self.expr_var.set(new_text)
        entry.icursor(pos + len(token))
        entry.focus_set()
        self._debounced_param_refresh()

    def _load_example(self, expr: str):
        self.expr_var.set(expr)
        self.input_entry.icursor(tk.END)
        self.input_entry.focus_set()
        self._refresh_parameters()
        self._on_evaluate()   # immediate gratification

    def _noop(self):
        pass

    def _debounced_param_refresh(self):
        # Simple debounce via after
        if hasattr(self, "_refresh_after_id"):
            self.after_cancel(self._refresh_after_id)
        self._refresh_after_id = self.after(380, self._refresh_parameters)

    # -------------------------------------------------------------------------
    # PARAMETERS / VARIABLES PANEL
    # -------------------------------------------------------------------------
    def _refresh_parameters(self):
        """Parse current expression and build live parameter editors."""
        expr_str = self.expr_var.get().strip()
        if not expr_str:
            self._clear_param_widgets()
            return

        try:
            parsed = self.engine.parse(expr_str)
            symbols = self.engine.get_free_symbols(parsed)
        except Exception:
            self._clear_param_widgets()
            return

        # Preserve previous values where possible
        old_values = {k: v.get() for k, v in self.param_vars.items()}

        self._clear_param_widgets(keep_container=True)

        if not symbols:
            self.param_placeholder.config(
                text="Expression is constant (no free symbols besides built-ins)."
            )
            self.param_placeholder.pack(anchor="w", pady=2)
            return

        self.param_placeholder.pack_forget()

        # Create a nice row of parameter editors
        row = tk.Frame(self.param_container, bg=DARK["bg"])
        row.pack(fill="x")

        for i, sym in enumerate(symbols[:8]):  # cap at 8 for UI sanity
            col = tk.Frame(row, bg=DARK["bg"])
            col.pack(side="left", padx=8, pady=1, fill="x", expand=True)

            tk.Label(
                col, text=f"{sym} =", bg=DARK["bg"], fg=DARK["text"],
                font=("Segoe UI", 9, "bold")
            ).pack(side="left")

            var = tk.StringVar(value=old_values.get(sym, "1.0"))
            self.param_vars[sym] = var

            ent = tk.Entry(
                col,
                textvariable=var,
                bg=DARK["display"],
                fg=DARK["text"],
                font=("Consolas", 10),
                width=8,
                relief="flat",
                insertbackground=DARK["accent"],
            )
            ent.pack(side="left", padx=3)
            self.param_entries[sym] = ent

            # Live update on focus out / return
            ent.bind("<FocusOut>", lambda e, s=sym: self._on_param_changed(s))
            ent.bind("<Return>", lambda e, s=sym: self._on_param_changed(s))

            # Small indicator
            tk.Label(
                col, text="(float or expr)", bg=DARK["bg"], fg="#555555",
                font=("Segoe UI", 7)
            ).pack(side="left")

        # Hint
        hint = tk.Label(
            self.param_container,
            text="Tip: Set values (e.g. 2.5 or pi/4) then hit Evaluate or any action for updated numeric results.",
            bg=DARK["bg"], fg="#555555", font=("Segoe UI", 8, "italic")
        )
        hint.pack(anchor="w", padx=4, pady=(2, 0))

    def _on_param_changed(self, sym: str):
        """Update internal cache and refresh numeric display if we have a result."""
        self._update_param_cache()
        if self.current_result_expr is not None:
            self._update_numeric_only()

    def _update_param_cache(self):
        """Read all param entry values into a usable dict."""
        self.param_values: dict[str, float] = {}
        for sym, var in self.param_vars.items():
            raw = var.get().strip()
            if not raw:
                continue
            try:
                # Try direct float first (fast path)
                self.param_values[sym] = float(raw)
            except ValueError:
                # Allow simple constants via engine for numeric
                try:
                    val = self.engine.evaluate_at(raw)
                    self.param_values[sym] = float(val)
                except Exception:
                    self.param_values[sym] = 1.0  # safe fallback

    def _clear_param_widgets(self, keep_container: bool = False):
        for w in self.param_container.winfo_children():
            w.destroy()
        self.param_vars.clear()
        self.param_entries.clear()
        self.param_values = {}
        if not keep_container:
            self.param_placeholder.pack_forget()

    def _reset_parameters(self):
        for var in self.param_vars.values():
            var.set("1.0")
        self._update_param_cache()
        if self.current_result_expr is not None:
            self._update_numeric_only()

    # -------------------------------------------------------------------------
    # CORE EVALUATION & DISPLAY
    # -------------------------------------------------------------------------
    def _on_evaluate(self, event=None):
        expr_str = self.expr_var.get().strip()
        if not expr_str:
            self._show_error("Expression cannot be empty")
            return

        self._update_param_cache()
        self._hide_error()

        try:
            parsed = self.engine.parse(expr_str)
            pretty = self.engine.pretty(parsed)
            latex = self.engine.to_latex(parsed)
            numeric = self._compute_numeric_str(parsed)

            self.current_result_expr = parsed
            self._display_results(pretty, latex, numeric)
            self._add_to_history(expr_str, "Evaluate", pretty, latex, numeric)

            self.status_label.config(text="Evaluated", fg=DARK["success"])
            self.after(1600, lambda: self.status_label.config(text="Ready", fg=DARK["success"]))

        except MathEngineError as exc:
            self._show_error(str(exc))
        except Exception as exc:
            self._show_error(f"Unexpected error: {exc}")

    def _compute_numeric_str(self, expr: sp.Expr) -> str:
        """High-precision numeric using current parameters."""
        free = self.engine.get_free_symbols(expr)
        if not free:
            try:
                val = float(self.engine.evaluate_at(expr))
                return f"{val:.16g}"
            except Exception as e:
                return f"(constant — {e})"

        values = {}
        for sym in free:
            if sym in self.param_values:
                values[sym] = self.param_values[sym]
            else:
                values[sym] = 1.0

        try:
            result = self.engine.evaluate_numeric(expr, values)
            if isinstance(result, complex):
                return f"{result.real:.12g} + {result.imag:.12g}i"
            if isinstance(result, (list, tuple)) or hasattr(result, "__len__"):
                return "array result (see grapher for visualization)"
            return f"{float(result):.16g}"
        except MathEngineError as e:
            return f"(numeric unavailable: {e})"
        except Exception as e:
            return f"(numeric error: {e})"

    def _update_numeric_only(self):
        """Refresh only the numeric line when parameters change."""
        if self.current_result_expr is None:
            return
        try:
            numeric = self._compute_numeric_str(self.current_result_expr)
            self.numeric_var.set(numeric)
        except Exception:
            pass

    def _display_results(self, pretty: str, latex: str, numeric: str, expr: sp.Expr | None = None):
        self.pretty_var.set(pretty or "—")
        self.latex_var.set(latex or "—")
        self.numeric_var.set(numeric or "—")

        if expr is not None:
            self.current_result_expr = expr

    def _clear_results(self):
        self.pretty_var.set("—")
        self.latex_var.set("—")
        self.numeric_var.set("—")
        self.current_result_expr = None

    def _load_result_to_input(self):
        if self.current_result_expr is None:
            self._show_error("No result to load — evaluate or use an action first")
            return
        # Use the LaTeX-ish or pretty? Best: use sympy's str form that parser likes
        expr_str = str(self.current_result_expr)
        # Make it nicer for user
        self.expr_var.set(expr_str)
        self.input_entry.icursor(tk.END)
        self.input_entry.focus_set()
        self._refresh_parameters()
        self.status_label.config(text="Result loaded for chaining", fg=DARK["accent2"])

    def _reevaluate_current(self):
        if self.current_result_expr is None:
            self._on_evaluate()
            return
        # Recompute displays from the stored SymPy object
        try:
            pretty = self.engine.pretty(self.current_result_expr)
            latex = self.engine.to_latex(self.current_result_expr)
            numeric = self._compute_numeric_str(self.current_result_expr)
            self._display_results(pretty, latex, numeric)
            self.status_label.config(text="Re-evaluated", fg=DARK["success"])
        except Exception as exc:
            self._show_error(str(exc))

    # -------------------------------------------------------------------------
    # QUICK ACTIONS (heavy MathEngine usage)
    # -------------------------------------------------------------------------
    def _get_expr_str(self) -> str:
        return self.expr_var.get().strip()

    def _get_var(self) -> str:
        v = self.var_var.get().strip()
        return v if v else "x"

    def _perform_action(self, op_name: str, result_expr: sp.Expr, input_desc: str):
        """Common path after any symbolic operation."""
        try:
            pretty = self.engine.pretty(result_expr)
            latex = self.engine.to_latex(result_expr)
            numeric = self._compute_numeric_str(result_expr)

            self.current_result_expr = result_expr
            self._display_results(pretty, latex, numeric)
            self._add_to_history(input_desc, op_name, pretty, latex, numeric)

            self.status_label.config(text=f"{op_name} complete", fg=DARK["success"])
            self.after(1400, lambda: self.status_label.config(text="Ready", fg=DARK["success"]))
            self._hide_error()
        except MathEngineError as exc:
            self._show_error(str(exc))
        except Exception as exc:
            self._show_error(f"{op_name} display error: {exc}")

    def _do_derivative(self):
        expr = self._get_expr_str()
        if not expr:
            return self._show_error("Enter an expression first")
        var = self._get_var()
        try:
            res = self.engine.symbolic_derivative(expr, var, order=1)
            self._perform_action("Derivative", res, f"d/d{var} ({expr})")
        except MathEngineError as e:
            self._show_error(str(e))

    def _do_integral_indef(self):
        expr = self._get_expr_str()
        if not expr:
            return self._show_error("Enter an expression first")
        var = self._get_var()
        try:
            res = self.engine.symbolic_integral(expr, var, definite=False)
            self._perform_action("∫ Indefinite", res, f"∫ {expr} d{var}")
        except MathEngineError as e:
            self._show_error(str(e))

    def _do_integral_def(self):
        expr = self._get_expr_str()
        if not expr:
            return self._show_error("Enter an expression first")
        var = self._get_var()
        lo = self.int_lower_var.get().strip()
        up = self.int_upper_var.get().strip()
        try:
            res = self.engine.symbolic_integral(
                expr, var, definite=True, lower=lo, upper=up
            )
            self._perform_action(
                "∫ Definite",
                res,
                f"∫_{lo}^{up} {expr} d{var}"
            )
        except MathEngineError as e:
            self._show_error(str(e))

    def _do_limit(self):
        expr = self._get_expr_str()
        if not expr:
            return self._show_error("Enter an expression first")
        var = self._get_var()
        pt = self.limit_point_var.get().strip()
        direction = self.limit_dir_var.get()
        try:
            res = self.engine.symbolic_limit(expr, var, pt, direction=direction)
            self._perform_action(
                "Limit",
                res,
                f"lim {var}→{pt} ({direction}) {expr}"
            )
        except MathEngineError as e:
            self._show_error(str(e))

    def _do_taylor(self):
        expr = self._get_expr_str()
        if not expr:
            return self._show_error("Enter an expression first")
        var = self._get_var()
        pt = self.taylor_point_var.get().strip()
        n = self.taylor_order_var.get()
        try:
            res = self.engine.symbolic_series(expr, var, pt, n)
            self._perform_action(
                f"Taylor (n={n})",
                res,
                f"Series {expr} @ {pt} (order {n})"
            )
        except MathEngineError as e:
            self._show_error(str(e))

    def _do_simplify(self):
        expr = self._get_expr_str()
        if not expr:
            return self._show_error("Enter an expression first")
        try:
            res = self.engine.simplify(expr)
            self._perform_action("Simplify", res, f"simplify({expr})")
        except MathEngineError as e:
            self._show_error(str(e))

    def _do_expand(self):
        expr = self._get_expr_str()
        if not expr:
            return self._show_error("Enter an expression first")
        try:
            res = self.engine.expand(expr)
            self._perform_action("Expand", res, f"expand({expr})")
        except MathEngineError as e:
            self._show_error(str(e))

    def _do_factor(self):
        expr = self._get_expr_str()
        if not expr:
            return self._show_error("Enter an expression first")
        try:
            res = self.engine.factor(expr)
            self._perform_action("Factor", res, f"factor({expr})")
        except MathEngineError as e:
            self._show_error(str(e))

    # -------------------------------------------------------------------------
    # HISTORY
    # -------------------------------------------------------------------------
    def _add_to_history(self, expr: str, op: str, pretty: str, latex: str, numeric: str):
        entry = {
            "expr": expr,
            "op": op,
            "pretty": pretty,
            "latex": latex,
            "numeric": numeric,
        }
        self.history.insert(0, entry)
        if len(self.history) > self.HISTORY_LIMIT:
            self.history.pop()

        # Update listbox
        display = f"[{op}]  {expr[:42]}{'…' if len(expr) > 42 else ''}   →  {pretty[:48]}{'…' if len(pretty) > 48 else ''}"
        self.history_display.insert(0, display)
        if len(self.history_display) > self.HISTORY_LIMIT:
            self.history_display.pop()

        self.history_lb.delete(0, tk.END)
        for d in self.history_display:
            self.history_lb.insert(tk.END, d)

    def _on_history_click(self, event):
        selection = self.history_lb.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx >= len(self.history):
            return

        entry = self.history[idx]
        self.expr_var.set(entry["expr"])
        self.input_entry.icursor(tk.END)
        self.input_entry.focus_set()

        # Restore the result displays too (great UX)
        self.current_result_expr = None  # will be re-parsed on demand
        try:
            parsed = self.engine.parse(entry["expr"])
            self.current_result_expr = parsed
        except Exception:
            pass

        self.pretty_var.set(entry.get("pretty", "—"))
        self.latex_var.set(entry.get("latex", "—"))
        self.numeric_var.set(entry.get("numeric", "—"))

        self._refresh_parameters()
        self.status_label.config(text="History entry loaded", fg=DARK["accent2"])
        self.after(1200, lambda: self.status_label.config(text="Ready", fg=DARK["success"]))

    def _clear_history(self):
        self.history.clear()
        self.history_display.clear()
        self.history_lb.delete(0, tk.END)

    # -------------------------------------------------------------------------
    # CLIPBOARD & ERROR UX
    # -------------------------------------------------------------------------
    def _copy_latex(self):
        text = self.latex_var.get()
        if text and text != "—":
            self.clipboard_clear()
            self.clipboard_append(text)
            old = self.status_label.cget("text")
            self.status_label.config(text="LaTeX copied!", fg=DARK["success"])
            self.after(1200, lambda: self.status_label.config(text=old, fg=DARK["success"]))
        else:
            self._show_error("No LaTeX to copy")

    def _copy_numeric(self):
        text = self.numeric_var.get()
        if text and text != "—":
            self.clipboard_clear()
            self.clipboard_append(text)
            old = self.status_label.cget("text")
            self.status_label.config(text="Value copied!", fg=DARK["success"])
            self.after(1200, lambda: self.status_label.config(text=old, fg=DARK["success"]))
        else:
            self._show_error("No numeric value to copy")

    def _show_error(self, message: str):
        self.error_label.config(text=f"  ⚠ {message}")
        self.error_bar.pack(fill="x", side="bottom")

    def _hide_error(self):
        self.error_label.config(text="")
        self.error_bar.pack_forget()

    # -------------------------------------------------------------------------
    # PUBLIC API (nice for external control)
    # -------------------------------------------------------------------------
    def set_expression(self, expr: str, evaluate_immediately: bool = True):
        """Programmatic control — useful for notebooks or demos."""
        self.expr_var.set(expr)
        self._refresh_parameters()
        if evaluate_immediately:
            self._on_evaluate()

    def get_current_result(self) -> sp.Expr | None:
        return self.current_result_expr


# =============================================================================
# TITLED WRAPPER FRAME (matches Grapher2DFrame pattern exactly)
# =============================================================================

class ScientificCalculatorFrame(tk.Frame):
    """
    Ready-to-embed titled container for notebook tabs or any parent.

    Usage in main app:
        from app.calculator.scientific import ScientificCalculatorFrame
        sci = ScientificCalculatorFrame(notebook, engine)
        notebook.add(sci, text="  Scientific  ")
    """

    def __init__(self, parent, engine: MathEngine | None = None):
        super().__init__(parent, bg=DARK["bg"])
        self.engine = engine or MathEngine()

        header = tk.Frame(self, bg=DARK["panel"])
        header.pack(fill="x")
        tk.Label(
            header,
            text="Scientific Expression Calculator  •  Symbolic + Numeric + History",
            bg=DARK["panel"], fg=DARK["text"], font=("Segoe UI", 13, "bold")
        ).pack(pady=7, padx=14, anchor="w")

        self.calculator = ScientificCalculator(self, self.engine)
        self.calculator.pack(fill="both", expand=True)


# =============================================================================
# STANDALONE DEMO (run this file directly — impressive out of the box)
# =============================================================================

if __name__ == "__main__":
    print("Launching standalone Scientific Expression Calculator demo...")

    root = tk.Tk()
    root.title("MathForge — Scientific Expression Calculator (Standalone)")
    root.geometry("1180x860")
    root.minsize(1000, 720)
    root.configure(bg=DARK["bg"])

    engine = MathEngine(use_numpy=True)

    frame = ScientificCalculatorFrame(root, engine)
    frame.pack(fill="both", expand=True, padx=4, pady=4)

    footer = tk.Label(
        root,
        text="TIP: Type expressions using ^ for powers and implicit multiplication. Use quick action buttons for calculus & algebra. "
             "Edit parameters on the fly • Click history entries • Load results to chain operations. All powered by the production MathEngine.",
        bg=DARK["panel"], fg=DARK["secondary"], font=("Segoe UI", 9), wraplength=1150, justify="left"
    )
    footer.pack(fill="x", pady=(0, 4), padx=8)

    root.mainloop()
