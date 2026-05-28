"""
History / Notebook — Cross-tool persistent scratchpad for MathForge.

Lightweight module providing:
- Save interesting expressions + results from Scientific, Grapher, Riemann, Taylor, etc.
- Simple list + detail view with timestamp, source, expression, result/pretty
- "Load in Scientific" (switches tab + loads + evaluates)
- "Plot this" (sends to 2D Grapher first slot)
- Manual quick-add
- Copy, delete, clear
- Persists to JSON in standard user data dir (APPDATA/MathForge on Windows)

Usage from any tool (no direct reference required):
    from app.ui.history_notebook import HistoryNotebook
    HistoryNotebook.add_entry(
        expression="x^2 * sin(x)",
        result="x²·sin(x)",
        source="Scientific",
        pretty="x² sin(x)"
    )

Integrate as tab (see main.py). Fully dark-themed and consistent with MathForge.
"""

from __future__ import annotations

import json
import datetime
import os
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import ttk, messagebox


# =============================================================================
# DARK THEME (kept in sync with Scientific + Grapher)
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


def _get_history_file() -> Path:
    """Return cross-platform writable location for notebook JSON."""
    if os.name == "nt":
        base = Path(os.getenv("APPDATA") or Path.home())
    else:
        base = Path.home() / ".local" / "share"
    data_dir = base / "MathForge"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "notebook_history.json"


class HistoryNotebook(tk.Frame):
    """
    Embeddable History/Notebook panel. Add as a tab or sidebar.

    Exposes classmethod `add_entry(...)` so any calculator or studio
    can save results with a single import — no wiring required.
    """

    MAX_ENTRIES = 80

    _instance: "HistoryNotebook | None" = None

    def __init__(
        self,
        parent,
        engine: Any = None,
        callbacks: dict[str, Any] | None = None,
    ):
        super().__init__(parent, bg=DARK["bg"])
        self.engine = engine
        self.callbacks: dict[str, Any] = callbacks or {}

        # Singleton for tool-agnostic saves
        HistoryNotebook._instance = self

        self.entries: list[dict[str, Any]] = []
        self.selected_idx: int | None = None
        self._history_file = _get_history_file()

        self._load_entries()
        self._setup_styles()
        self._build_ui()

    # -------------------------------------------------------------------------
    # PUBLIC / CROSS-TOOL API
    # -------------------------------------------------------------------------
    @classmethod
    def add_entry(
        cls,
        expression: str,
        result: str = "",
        source: str = "User",
        pretty: str | None = None,
    ) -> None:
        """
        Save an expression/result from anywhere (Scientific, Grapher, Riemann, Taylor...).
        Completely safe to call even if the notebook tab has not been created yet.
        """
        if cls._instance is not None:
            cls._instance._do_add_entry(expression, result, source, pretty)
        # If no instance yet, the entry is simply lost (acceptable for lightweight design)

    # -------------------------------------------------------------------------
    # INTERNAL ADD + PERSISTENCE
    # -------------------------------------------------------------------------
    def _do_add_entry(
        self,
        expression: str,
        result: str = "",
        source: str = "User",
        pretty: str | None = None,
    ) -> None:
        expr = (expression or "").strip()
        if not expr:
            return

        entry = {
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "source": source,
            "expression": expr,
            "result": (pretty or result or "").strip(),
        }

        self.entries.insert(0, entry)
        if len(self.entries) > self.MAX_ENTRIES:
            self.entries = self.entries[: self.MAX_ENTRIES]

        self._save_entries()
        self._refresh_list()

        # Gentle UI feedback
        if hasattr(self, "status_label"):
            self.status_label.config(text=f"Saved from {source}", fg=DARK["success"])
            self.after(
                1600,
                lambda: (
                    self.status_label.config(text="Ready", fg=DARK["secondary"])
                    if hasattr(self, "status_label")
                    else None
                ),
            )

    def _load_entries(self) -> None:
        try:
            if self._history_file.exists():
                raw = json.loads(self._history_file.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    self.entries = raw[: self.MAX_ENTRIES]
                else:
                    self.entries = []
            else:
                self.entries = []
        except Exception:
            self.entries = []  # corrupt or permission issue → start fresh

    def _save_entries(self) -> None:
        try:
            self._history_file.write_text(
                json.dumps(self.entries, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass  # never crash the UI over persistence

    # -------------------------------------------------------------------------
    # STYLING (self-contained, matches rest of app)
    # -------------------------------------------------------------------------
    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "NoteSmall.TButton",
            font=("Segoe UI", 9),
            background=DARK["btn"],
            foreground=DARK["text"],
            padding=(8, 4),
            borderwidth=0,
        )
        style.map(
            "NoteSmall.TButton",
            background=[("active", DARK["btn_hover"]), ("pressed", DARK["accent"])],
            foreground=[("active", "#FFFFFF")],
        )

        style.configure(
            "NoteAccent.TButton",
            font=("Segoe UI", 9, "bold"),
            background="#1E3A5F",
            foreground=DARK["text"],
            padding=(8, 5),
        )
        style.map(
            "NoteAccent.TButton",
            background=[("active", DARK["accent"]), ("pressed", "#005A9E")],
        )

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
            text="📓  History / Notebook",
            bg=DARK["panel"],
            fg=DARK["text"],
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left", padx=14, pady=6)

        tk.Label(
            header,
            text="Cross-tool saved expressions & results — persists across sessions",
            bg=DARK["panel"],
            fg=DARK["secondary"],
            font=("Segoe UI", 9),
        ).pack(side="left", padx=6)

        self.status_label = tk.Label(
            header, text="Ready", bg=DARK["panel"], fg=DARK["secondary"], font=("Segoe UI", 9, "bold")
        )
        self.status_label.pack(side="right", padx=14)

        # Quick manual add bar
        manual_bar = tk.Frame(self, bg=DARK["bg"])
        manual_bar.pack(fill="x", padx=8, pady=(6, 2))

        tk.Label(
            manual_bar,
            text="Quick add expression:",
            bg=DARK["bg"],
            fg=DARK["secondary"],
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(2, 6))

        self.manual_var = tk.StringVar()
        manual_entry = ttk.Entry(
            manual_bar,
            textvariable=self.manual_var,
            font=("Consolas", 11),
            width=48,
        )
        manual_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        manual_entry.bind("<Return>", lambda e: self._save_manual())

        ttk.Button(
            manual_bar,
            text="Save to Notebook",
            style="NoteAccent.TButton",
            command=self._save_manual,
        ).pack(side="left", padx=2)

        # Main split area
        body = tk.Frame(self, bg=DARK["bg"])
        body.pack(fill="both", expand=True, padx=8, pady=4)

        # === LEFT: list of entries ===
        list_container = tk.LabelFrame(
            body,
            text="  Saved Entries (newest first — click to select)  ",
            bg=DARK["bg"],
            fg=DARK["accent"],
            font=("Segoe UI", 10, "bold"),
            bd=1,
            relief="groove",
        )
        list_container.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.listbox = tk.Listbox(
            list_container,
            bg=DARK["history_bg"],
            fg=DARK["text"],
            font=("Consolas", 9),
            height=14,
            selectbackground=DARK["accent"],
            selectforeground="#FFFFFF",
            activestyle="none",
            relief="flat",
            borderwidth=0,
        )
        self.listbox.pack(fill="both", expand=True, padx=4, pady=(4, 2))
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        self.listbox.bind("<Double-1>", lambda e: self._load_in_scientific())

        list_toolbar = tk.Frame(list_container, bg=DARK["bg"])
        list_toolbar.pack(fill="x", padx=4, pady=(0, 4))

        ttk.Button(
            list_toolbar, text="Delete", style="NoteSmall.TButton", command=self._delete_selected
        ).pack(side="left", padx=2)
        ttk.Button(
            list_toolbar, text="Clear All", style="NoteSmall.TButton", command=self._clear_all
        ).pack(side="left", padx=2)
        ttk.Button(
            list_toolbar, text="Refresh", style="NoteSmall.TButton", command=self._refresh_list
        ).pack(side="right", padx=2)

        # === RIGHT: detail + actions ===
        detail_container = tk.LabelFrame(
            body,
            text="  Selection Details & Actions  ",
            bg=DARK["bg"],
            fg=DARK["accent"],
            font=("Segoe UI", 10, "bold"),
            bd=1,
            relief="groove",
        )
        detail_container.pack(side="left", fill="both", expand=False)

        self.detail_text = tk.Text(
            detail_container,
            bg=DARK["result_bg"],
            fg=DARK["text"],
            font=("Consolas", 10),
            height=9,
            width=40,
            wrap="word",
            relief="flat",
            borderwidth=0,
            padx=8,
            pady=6,
            state="disabled",
        )
        self.detail_text.pack(fill="both", expand=True, padx=6, pady=(6, 4))

        action_bar = tk.Frame(detail_container, bg=DARK["bg"])
        action_bar.pack(fill="x", padx=6, pady=(0, 8))

        self.btn_load_sci = ttk.Button(
            action_bar,
            text="Load in Scientific",
            style="NoteAccent.TButton",
            command=self._load_in_scientific,
            state="disabled",
        )
        self.btn_load_sci.pack(fill="x", pady=2)

        self.btn_plot = ttk.Button(
            action_bar,
            text="Plot this in Grapher",
            style="NoteAccent.TButton",
            command=self._plot_in_grapher,
            state="disabled",
        )
        self.btn_plot.pack(fill="x", pady=2)

        ttk.Button(
            action_bar, text="Copy Expression", style="NoteSmall.TButton", command=self._copy_expression
        ).pack(fill="x", pady=2)
        ttk.Button(
            action_bar, text="Copy Result", style="NoteSmall.TButton", command=self._copy_result
        ).pack(fill="x", pady=2)

        # Footer tip
        tip = tk.Label(
            self,
            text="Tip: Tools have 💾 Save to Notebook buttons. Double-click an entry or use the actions above. Everything is saved automatically.",
            bg=DARK["bg"],
            fg="#555555",
            font=("Segoe UI", 8),
            anchor="w",
        )
        tip.pack(fill="x", padx=8, pady=(0, 4))

        # Initial population
        self._refresh_list()

    # -------------------------------------------------------------------------
    # LIST & DETAIL MANAGEMENT
    # -------------------------------------------------------------------------
    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for entry in self.entries:
            ts = entry.get("timestamp", "")
            # Show date + time compactly
            if "T" in ts:
                date_part, time_part = ts.split("T", 1)
                time_str = time_part[:5]
            else:
                time_str = ts[-8:-3] if len(ts) > 8 else ts

            src = entry.get("source", "User")[:12].ljust(12)
            expr = entry.get("expression", "")[:40]
            res = (entry.get("result") or "")[:28]

            line = f"[{time_str}] {src}  {expr}"
            if res:
                line += f"   →  {res}"
            self.listbox.insert(tk.END, line)

        if not self.entries:
            self.listbox.insert(tk.END, "(Notebook is empty — save expressions from any tool)")
            self._update_detail("No entries yet.\n\nUse 'Save to Notebook' inside Scientific, Grapher, or the quick-add bar above.")
            self._set_buttons_enabled(False)

    def _on_select(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            self.selected_idx = None
            self._update_detail("")
            self._set_buttons_enabled(False)
            return

        idx = sel[0]
        if idx >= len(self.entries):
            return

        self.selected_idx = idx
        entry = self.entries[idx]

        detail = (
            f"Source: {entry.get('source', 'Unknown')}\n"
            f"Saved:  {entry.get('timestamp', '')}\n\n"
            f"Expression:\n{entry.get('expression', '')}\n\n"
            f"Result / Pretty:\n{entry.get('result') or '(no result stored)'}"
        )
        self._update_detail(detail)
        self._set_buttons_enabled(True)

    def _update_detail(self, text: str):
        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert("1.0", text)
        self.detail_text.config(state="disabled")

    def _set_buttons_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        for btn in (self.btn_load_sci, self.btn_plot):
            btn.config(state=state)

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------
    def _save_manual(self):
        expr = self.manual_var.get().strip()
        if not expr:
            return
        self._do_add_entry(expr, "", source="Manual")
        self.manual_var.set("")

    def _delete_selected(self):
        if self.selected_idx is None:
            return
        if messagebox.askyesno("Delete Entry", "Remove the selected notebook entry?"):
            del self.entries[self.selected_idx]
            self._save_entries()
            self.selected_idx = None
            self._refresh_list()
            self._update_detail("")
            self._set_buttons_enabled(False)

    def _clear_all(self):
        if not self.entries:
            return
        if messagebox.askyesno("Clear Notebook", "Delete ALL saved notebook entries? This cannot be undone."):
            self.entries.clear()
            self._save_entries()
            self.selected_idx = None
            self._refresh_list()
            self._update_detail("Notebook cleared.")
            self._set_buttons_enabled(False)

    def _load_in_scientific(self):
        if self.selected_idx is None:
            return
        expr = self.entries[self.selected_idx]["expression"]
        if "load_scientific" in self.callbacks:
            try:
                self.callbacks["load_scientific"](expr)
            except Exception as exc:
                messagebox.showerror("Notebook", f"Failed to load in Scientific:\n{exc}")
        else:
            # Fallback: at least copy to clipboard so user can paste
            self.clipboard_clear()
            self.clipboard_append(expr)
            messagebox.showinfo(
                "Notebook",
                "Loaded expression copied to clipboard (Scientific tab callback not connected)."
            )

    def _plot_in_grapher(self):
        if self.selected_idx is None:
            return
        expr = self.entries[self.selected_idx]["expression"]
        if "plot_grapher" in self.callbacks:
            try:
                self.callbacks["plot_grapher"](expr)
            except Exception as exc:
                messagebox.showerror("Notebook", f"Failed to plot in Grapher:\n{exc}")
        else:
            self.clipboard_clear()
            self.clipboard_append(expr)
            messagebox.showinfo(
                "Notebook",
                "Expression copied to clipboard (Grapher callback not connected)."
            )

    def _copy_expression(self):
        if self.selected_idx is None:
            return
        expr = self.entries[self.selected_idx]["expression"]
        self.clipboard_clear()
        self.clipboard_append(expr)
        old = self.status_label.cget("text") if hasattr(self, "status_label") else ""
        if hasattr(self, "status_label"):
            self.status_label.config(text="Expression copied!", fg=DARK["success"])
            self.after(1200, lambda: self.status_label.config(text=old or "Ready", fg=DARK["secondary"]))

    def _copy_result(self):
        if self.selected_idx is None:
            return
        res = self.entries[self.selected_idx].get("result", "")
        if not res:
            return
        self.clipboard_clear()
        self.clipboard_append(res)
        old = self.status_label.cget("text") if hasattr(self, "status_label") else ""
        if hasattr(self, "status_label"):
            self.status_label.config(text="Result copied!", fg=DARK["success"])
            self.after(1200, lambda: self.status_label.config(text=old or "Ready", fg=DARK["secondary"]))

    # -------------------------------------------------------------------------
    # PUBLIC HELPERS (for advanced use)
    # -------------------------------------------------------------------------
    def get_entries(self) -> list[dict[str, Any]]:
        """Return a copy of current notebook entries (newest first)."""
        return [e.copy() for e in self.entries]

    def clear(self):
        """Programmatic clear (used by tests / reset)."""
        self.entries.clear()
        self._save_entries()
        self._refresh_list()
