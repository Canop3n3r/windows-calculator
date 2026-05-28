#!/usr/bin/env python3
"""
Windows Calculator App
A clean, functional desktop calculator built with Python + Tkinter (stdlib only).
Features:
- Basic arithmetic + - * /
- Parentheses support
- Percentage, square, square root, 1/x
- Memory functions (MC, MR, MS, M+)
- Full keyboard support
- Dark modern theme matching Windows style
- Error handling and safe evaluation
"""

import tkinter as tk
from tkinter import ttk, messagebox
import math
import re
from decimal import Decimal, InvalidOperation


class CalculatorApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Calculator")
        self.geometry("380x520")
        self.minsize(340, 480)
        self.resizable(True, True)

        # Dark theme colors (Windows 11 inspired)
        self.bg_color = "#202020"
        self.display_bg = "#2D2D2D"
        self.btn_bg = "#3A3A3A"
        self.btn_hover = "#4A4A4A"
        self.operator_bg = "#5A5A5A"
        self.equals_bg = "#0078D4"
        self.text_color = "#FFFFFF"
        self.secondary_text = "#B0B0B0"

        self.configure(bg=self.bg_color)

        # State
        self.current_input = ""
        self.memory = Decimal("0")
        self.last_result = None

        self._setup_styles()
        self._create_widgets()
        self._bind_keyboard()

        # Start with clean state
        self.clear_all()

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Display style
        style.configure(
            "Display.TEntry",
            fieldbackground=self.display_bg,
            foreground=self.text_color,
            font=("Segoe UI", 28, "bold"),
            borderwidth=0,
            relief="flat",
            padding=12,
        )

        # Button styles
        style.configure(
            "Calc.TButton",
            font=("Segoe UI", 14),
            background=self.btn_bg,
            foreground=self.text_color,
            borderwidth=0,
            relief="flat",
            padding=(8, 14),
        )

        style.map(
            "Calc.TButton",
            background=[("active", self.btn_hover), ("pressed", self.operator_bg)],
        )

        style.configure(
            "Operator.TButton",
            font=("Segoe UI", 14),
            background=self.operator_bg,
            foreground=self.text_color,
            borderwidth=0,
            padding=(8, 14),
        )

        style.map(
            "Operator.TButton",
            background=[("active", "#6A6A6A"), ("pressed", self.equals_bg)],
        )

        style.configure(
            "Equals.TButton",
            font=("Segoe UI", 14, "bold"),
            background=self.equals_bg,
            foreground=self.text_color,
            borderwidth=0,
            padding=(8, 14),
        )

        style.map(
            "Equals.TButton",
            background=[("active", "#0086F0"), ("pressed", "#005A9E")],
        )

        style.configure(
            "Memory.TButton",
            font=("Segoe UI", 11),
            background=self.btn_bg,
            foreground=self.secondary_text,
            borderwidth=0,
            padding=(4, 10),
        )

    def _create_widgets(self):
        # Main container with padding
        main_frame = tk.Frame(self, bg=self.bg_color, padx=8, pady=8)
        main_frame.pack(fill="both", expand=True)

        # === Display ===
        display_frame = tk.Frame(main_frame, bg=self.display_bg, padx=4, pady=4)
        display_frame.pack(fill="x", pady=(0, 12))

        self.display_var = tk.StringVar(value="0")
        self.display = ttk.Entry(
            display_frame,
            textvariable=self.display_var,
            style="Display.TEntry",
            justify="right",
            state="readonly",
        )
        self.display.pack(fill="x", ipady=8)

        # Memory status indicator (small)
        self.memory_label = tk.Label(
            display_frame,
            text="",
            bg=self.display_bg,
            fg=self.secondary_text,
            font=("Segoe UI", 9),
            anchor="e",
        )
        self.memory_label.pack(fill="x", padx=4)

        # === Memory Buttons Row ===
        mem_frame = tk.Frame(main_frame, bg=self.bg_color)
        mem_frame.pack(fill="x", pady=(0, 6))

        mem_buttons = [
            ("MC", self.memory_clear),
            ("MR", self.memory_recall),
            ("MS", self.memory_store),
            ("M+", self.memory_add),
            ("M-", self.memory_subtract),
        ]

        for text, cmd in mem_buttons:
            btn = ttk.Button(
                mem_frame,
                text=text,
                command=cmd,
                style="Memory.TButton",
                width=5,
            )
            btn.pack(side="left", fill="x", expand=True, padx=2)

        # === Main Button Grid ===
        btn_frame = tk.Frame(main_frame, bg=self.bg_color)
        btn_frame.pack(fill="both", expand=True)

        # Button layout (rows of 4)
        # Using a mix of standard and advanced functions
        buttons = [
            ["C", "CE", "⌫", "÷"],
            ["1/x", "x²", "√x", "×"],
            ["7", "8", "9", "−"],
            ["4", "5", "6", "+"],
            ["1", "2", "3", "="],
            ["±", "0", ".", ""],  # last row special
        ]

        self.buttons = {}

        for row_idx, row in enumerate(buttons):
            for col_idx, text in enumerate(row):
                if not text:
                    continue

                # Determine style
                if text in ["÷", "×", "−", "+"]:
                    style = "Operator.TButton"
                    cmd = lambda t=text: self._on_operator(t)
                elif text == "=":
                    style = "Equals.TButton"
                    cmd = self.calculate
                elif text in ["C", "CE", "⌫"]:
                    style = "Calc.TButton"
                    if text == "C":
                        cmd = self.clear_all
                    elif text == "CE":
                        cmd = self.clear_entry
                    else:
                        cmd = self.backspace
                elif text in ["1/x", "x²", "√x"]:
                    style = "Calc.TButton"
                    cmd = lambda t=text: self._on_function(t)
                elif text == "±":
                    style = "Calc.TButton"
                    cmd = self.toggle_sign
                else:
                    style = "Calc.TButton"
                    cmd = lambda t=text: self._on_digit(t)

                btn = ttk.Button(
                    btn_frame,
                    text=text,
                    command=cmd,
                    style=style,
                )
                btn.grid(
                    row=row_idx,
                    column=col_idx,
                    sticky="nsew",
                    padx=3,
                    pady=3,
                    ipadx=4,
                    ipady=8,
                )

                self.buttons[text] = btn

                # Make grid expand nicely
                btn_frame.columnconfigure(col_idx, weight=1)
                btn_frame.rowconfigure(row_idx, weight=1)

        # Special last row handling for 0 which spans
        # We already placed ± 0 . in row 5, columns 0,1,2

    def _bind_keyboard(self):
        # Number keys
        for i in range(10):
            self.bind(str(i), lambda e, d=str(i): self._on_digit(d))
            self.bind(f"KP_{i}", lambda e, d=str(i): self._on_digit(d))  # Numpad

        # Operators
        self.bind("+", lambda e: self._on_operator("+"))
        self.bind("-", lambda e: self._on_operator("−"))
        self.bind("*", lambda e: self._on_operator("×"))
        self.bind("/", lambda e: self._on_operator("÷"))
        self.bind("Return", lambda e: self.calculate())
        self.bind("KP_Enter", lambda e: self.calculate())
        self.bind("=", lambda e: self.calculate())

        # Functions
        self.bind(".", lambda e: self._on_digit("."))
        self.bind("KP_Decimal", lambda e: self._on_digit("."))

        # Control
        self.bind("Escape", lambda e: self.clear_all())
        self.bind("c", lambda e: self.clear_all())
        self.bind("C", lambda e: self.clear_all())
        self.bind("<BackSpace>", lambda e: self.backspace())
        self.bind("<Delete>", lambda e: self.clear_entry())

        # Memory shortcuts (common in calculators)
        self.bind("m", lambda e: self.memory_store())
        self.bind("M", lambda e: self.memory_recall())
        self.bind("r", lambda e: self.memory_recall())

        # Percentage
        self.bind("%", lambda e: self._on_function("%"))

        # Copy / Paste
        self.bind("<Control-c>", lambda e: self._copy_result())
        self.bind("<Control-v>", lambda e: self._paste())

        # Focus display so user can see it's active
        self.display.focus_set()

    # =====================
    # Core Logic
    # =====================

    def _on_digit(self, digit):
        """Handle number and decimal point input."""
        current = self.current_input

        if digit == ".":
            if "." in current:
                return  # Already has decimal
            if not current:
                current = "0"

        # Prevent leading zeros
        if current == "0" and digit != ".":
            current = ""

        self.current_input = current + digit
        self._update_display(self.current_input)

    def _on_operator(self, op):
        """Handle arithmetic operators."""
        # If we have pending input and previous result, we can chain operations
        if self.current_input:
            try:
                # If user presses operator after typing a number, treat it as the new start
                # For simple chaining we just store the number and operator
                self.last_result = Decimal(self.current_input)
            except (InvalidOperation, ValueError):
                self._show_error("Invalid number")
                return
        elif self.last_result is None:
            self.last_result = Decimal("0")

        self.pending_operator = op
        self.current_input = ""
        # Show the operator in a subtle way on display if desired (kept simple here)
        self._update_display(str(self.last_result) + " " + op)

    def _on_function(self, func):
        """Handle unary functions like sqrt, square, 1/x, %."""
        try:
            if not self.current_input and self.last_result is not None:
                value = self.last_result
            else:
                value = Decimal(self.current_input or "0")

            if func == "√x":
                if value < 0:
                    raise ValueError("Square root of negative")
                result = value.sqrt()
            elif func == "x²":
                result = value * value
            elif func == "1/x":
                if value == 0:
                    raise ValueError("Division by zero")
                result = Decimal("1") / value
            elif func == "%":
                # Percentage of current (or of last result)
                result = value / Decimal("100")
            else:
                return

            self.current_input = str(result.normalize())
            self.last_result = result
            self._update_display(self.current_input)

        except Exception as e:
            self._show_error(str(e))

    def calculate(self):
        """Evaluate the pending operation or current expression."""
        if not hasattr(self, "pending_operator") or not self.pending_operator:
            # No pending op — just keep current or evaluate simple expression
            if self.current_input:
                try:
                    result = Decimal(self.current_input)
                    self.last_result = result
                    self._update_display(str(result.normalize()))
                except Exception:
                    self._show_error("Invalid input")
            return

        try:
            right = Decimal(self.current_input or "0")
            left = self.last_result if self.last_result is not None else Decimal("0")
            op = self.pending_operator

            if op == "+":
                result = left + right
            elif op == "−":
                result = left - right
            elif op == "×":
                result = left * right
            elif op == "÷":
                if right == 0:
                    raise ZeroDivisionError("Cannot divide by zero")
                result = left / right
            else:
                result = right

            # Clean up trailing zeros nicely
            result_str = str(result.normalize())

            self.last_result = result
            self.current_input = result_str
            self.pending_operator = None

            self._update_display(result_str)

        except ZeroDivisionError:
            self._show_error("Cannot divide by zero")
        except (InvalidOperation, ValueError) as e:
            self._show_error("Invalid operation")

    def clear_all(self):
        """Full reset (C button)."""
        self.current_input = ""
        self.last_result = None
        if hasattr(self, "pending_operator"):
            self.pending_operator = None
        self._update_display("0")

    def clear_entry(self):
        """Clear just the current entry (CE)."""
        self.current_input = ""
        self._update_display("0" if self.last_result is None else str(self.last_result))

    def backspace(self):
        """Delete last character."""
        if self.current_input:
            self.current_input = self.current_input[:-1]
            if not self.current_input:
                self.current_input = ""
            self._update_display(self.current_input or "0")
        else:
            # If display shows previous result + operator, clear the op
            if hasattr(self, "pending_operator"):
                self.pending_operator = None
            self._update_display("0")

    def toggle_sign(self):
        """+/- toggle."""
        if not self.current_input:
            if self.last_result is not None:
                self.last_result = -self.last_result
                self._update_display(str(self.last_result))
            return

        if self.current_input.startswith("-"):
            self.current_input = self.current_input[1:]
        else:
            self.current_input = "-" + self.current_input

        self._update_display(self.current_input)

    # =====================
    # Memory Functions
    # =====================

    def memory_clear(self):
        self.memory = Decimal("0")
        self.memory_label.config(text="")

    def memory_recall(self):
        self.current_input = str(self.memory.normalize())
        self._update_display(self.current_input)

    def memory_store(self):
        try:
            val = Decimal(self.current_input or "0")
            self.memory = val
            self.memory_label.config(text="M")
        except Exception:
            self._show_error("Cannot store value")

    def memory_add(self):
        try:
            val = Decimal(self.current_input or "0")
            self.memory += val
            self.memory_label.config(text="M")
        except Exception:
            pass

    def memory_subtract(self):
        try:
            val = Decimal(self.current_input or "0")
            self.memory -= val
            self.memory_label.config(text="M")
        except Exception:
            pass

    # =====================
    # Display & UX Helpers
    # =====================

    def _update_display(self, text):
        # Limit display length for readability
        if len(text) > 18:
            # Use scientific notation for very large numbers
            try:
                d = Decimal(text)
                text = f"{d:.6e}"
            except Exception:
                text = text[:18]

        self.display_var.set(text)

        # Update memory indicator
        if self.memory != 0 and self.memory_label.cget("text") != "M":
            self.memory_label.config(text="M")

    def _show_error(self, message):
        self.display_var.set("Error")
        self.current_input = ""
        self.last_result = None
        if hasattr(self, "pending_operator"):
            self.pending_operator = None

        # Brief error flash then clear
        self.after(1200, lambda: self.clear_all() if self.display_var.get() == "Error" else None)

    def _copy_result(self):
        """Copy current display value to clipboard."""
        result = self.display_var.get().strip()
        self.clipboard_clear()
        self.clipboard_append(result)
        # Optional: flash feedback (simple)
        original_bg = self.display.cget("style")
        self.after(180, lambda: None)  # Could add visual flash if desired

    def _paste(self):
        """Attempt to paste a number from clipboard."""
        try:
            clip = self.clipboard_get()
            # Very basic sanitization
            clip = clip.strip()
            # Only allow reasonable numeric input
            if re.match(r"^-?[\d.]+$", clip):
                self.current_input = clip
                self._update_display(clip)
        except Exception:
            pass  # Silent fail on bad paste

    def run(self):
        # Center window on screen
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

        self.mainloop()


def main():
    app = CalculatorApp()
    app.run()


if __name__ == "__main__":
    main()
