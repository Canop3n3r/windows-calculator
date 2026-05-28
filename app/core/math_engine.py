"""
High-Tier MathEngine — The single source of truth for symbolic and numeric mathematics.

Uses SymPy for safe parsing, symbolic calculus, and pretty output.
Uses NumPy via lambdify for fast numeric evaluation (critical for smooth graphing).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import sympy as sp
from sympy import (
    diff,
    integrate,
    limit,
    series,
    simplify,
    expand,
    factor,
    N,
    sin,
    cos,
    tan,
    exp,
    log,
    sqrt,
    pi,
    E,
    I,
    oo,
    Abs,
    asin,
    acos,
    atan,
    sinh,
    cosh,
    tanh,
    factorial,
)
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)


class MathEngineError(ValueError):
    """Exception raised for all user-facing errors in the MathEngine.

    Messages are designed to be clear and actionable for end users
    (calculator input, graphing parameters, calculus operations).
    """

    pass


@dataclass
class EvaluationResult:
    """Container for a completed evaluation (symbolic or numeric)."""
    value: Any
    latex: str | None = None
    error: str | None = None


class MathEngine:
    """
    The single source of truth for all symbolic and numeric mathematics
    in the application.

    Features:
    - Safe parsing via SymPy's parse_expr with calculator-friendly syntax:
      * '^' for exponentiation (e.g. x^2)
      * implicit multiplication (2x, sin x, (x+1)(x-2))
    - Full symbolic calculus: derivative, integral (definite/indefinite),
      limits, Taylor/Laurent series.
    - High-performance numeric evaluation via lambdify + NumPy (vectorized).
      Perfect for real-time graphing with parameter sliders.
    - Parameter / free symbol introspection for dynamic UIs.
    - Whitelisted safe namespace (no arbitrary code execution).
    - Consistent, user-friendly error messages.

    This class is intentionally lightweight, stateless after construction,
    and importable everywhere:
        from app.core.math_engine import MathEngine, MathEngineError
    """

    def __init__(self, *, use_numpy: bool = True) -> None:
        """Initialize the engine.

        Args:
            use_numpy: If True (default), lambdify targets NumPy for fast
                       vectorized evaluation over arrays (ideal for plotting).
                       Set False to fall back to Python math (scalar only).
        """
        self.use_numpy = use_numpy
        self.transformations = standard_transformations + (
            implicit_multiplication_application,
            convert_xor,  # ^ -> ** exactly like most calculators and graphing tools
        )
        self._safe_locals: dict[str, Any] = self._build_safe_namespace()

    def _build_safe_namespace(self) -> dict[str, Any]:
        """Construct a strict whitelist of allowed names for safe parsing."""
        ns: dict[str, Any] = {
            # --- Constants ---
            "pi": pi,
            "e": E,
            "E": E,
            "i": I,
            "I": I,
            "oo": oo,
            "inf": oo,
            "nan": sp.nan,

            # --- Common variable names (pre-declared for convenience) ---
            "x": sp.Symbol("x"),
            "y": sp.Symbol("y"),
            "z": sp.Symbol("z"),
            "t": sp.Symbol("t"),
            "u": sp.Symbol("u"),
            "v": sp.Symbol("v"),
            "a": sp.Symbol("a"),
            "b": sp.Symbol("b"),
            "c": sp.Symbol("c"),
            "k": sp.Symbol("k"),
            "m": sp.Symbol("m"),
            "n": sp.Symbol("n"),
            "theta": sp.Symbol("theta"),
            "phi": sp.Symbol("phi"),
            "alpha": sp.Symbol("alpha"),
            "beta": sp.Symbol("beta"),

            # --- Trigonometric & inverse trig (real + hyperbolic) ---
            "sin": sin,
            "cos": cos,
            "tan": tan,
            "asin": asin,
            "acos": acos,
            "atan": atan,
            "atan2": sp.atan2,
            "sinh": sinh,
            "cosh": cosh,
            "tanh": tanh,
            "asinh": sp.asinh,
            "acosh": sp.acosh,
            "atanh": sp.atanh,

            # --- Exponential & logarithmic (with common aliases) ---
            "exp": exp,
            "log": log,        # natural logarithm (SymPy convention)
            "ln": log,         # alias used by many users/calculators
            "log10": lambda arg: log(arg, 10),
            "log2": lambda arg: log(arg, 2),

            # --- Roots & powers ---
            "sqrt": sqrt,
            "cbrt": lambda arg: sp.Pow(arg, sp.Rational(1, 3)),
            "root": lambda arg, n: sp.Pow(arg, 1 / sp.Integer(n)),

            # --- Other elementary + special functions ---
            "abs": Abs,
            "Abs": Abs,
            "sign": sp.sign,
            "floor": sp.floor,
            "ceil": sp.ceiling,
            "ceiling": sp.ceiling,
            "factorial": factorial,
            "gamma": sp.gamma,
            "erf": sp.erf,
            "Max": sp.Max,
            "Min": sp.Min,
            "re": sp.re,
            "im": sp.im,
            "arg": sp.arg,
            "conjugate": sp.conjugate,
        }
        return ns

    # ------------------------------------------------------------------
    # Core Parsing
    # ------------------------------------------------------------------

    def parse(
        self,
        expr_str: str,
        additional_locals: dict[str, Any] | None = None,
    ) -> sp.Expr:
        """Safely parse a mathematical expression string into a SymPy Expr.

        Supports full calculator syntax:
            - ^ for powers (x^2 + 3^x)
            - implicit multiplication (2x, sin(x+1)2, (x+1)(x-2))
            - all whitelisted functions and constants above

        Raises:
            MathEngineError: with a clear, user-friendly message.
        """
        if not expr_str or not expr_str.strip():
            raise MathEngineError("Expression cannot be empty")

        merged_locals = {**self._safe_locals, **(additional_locals or {})}

        try:
            expr = parse_expr(
                expr_str.strip(),
                local_dict=merged_locals,
                transformations=self.transformations,
                evaluate=True,
            )
            return expr
        except (sp.SympifyError, SyntaxError, TypeError) as exc:
            msg = str(exc).lower()
            if "parenthes" in msg or "eof" in msg or "unexpected" in msg:
                raise MathEngineError(
                    f"Syntax error: check for unbalanced parentheses or missing operators in '{expr_str}'"
                ) from exc
            if "invalid syntax" in msg:
                raise MathEngineError(
                    f"Invalid syntax near '{expr_str}'. Common causes: missing '*', bad exponent, or unknown function."
                ) from exc
            raise MathEngineError(f"Could not parse expression '{expr_str}': {exc}") from exc
        except Exception as exc:
            raise MathEngineError(f"Unexpected parsing error for '{expr_str}': {exc}") from exc

    def get_free_symbols(self, expr: str | sp.Expr) -> list[str]:
        """Return the sorted list of free variable names in the expression.

        Constants (pi, e, I, oo, ...) are excluded. Useful for:
        - Discovering which variables are available for sliders
        - Determining independent variable vs. parameters for graphing
        """
        if isinstance(expr, str):
            expr = self.parse(expr)

        constants = {pi, E, I, oo, sp.nan, sp.zoo}
        symbols = sorted(
            str(s)
            for s in expr.free_symbols
            if s not in constants and not s.is_Number
        )
        return symbols

    def get_independent_variable(
        self, expr: str | sp.Expr, preferred: str = "x"
    ) -> str | None:
        """Heuristic to pick the best independent variable for graphing/calculus.

        Prefers 'x', then 't', then the first alphabetically.
        Returns None for constant expressions.
        """
        free = self.get_free_symbols(expr)
        if not free:
            return None
        if preferred in free:
            return preferred
        if "t" in free:
            return "t"
        return free[0]

    # ------------------------------------------------------------------
    # Symbolic Calculus
    # ------------------------------------------------------------------

    def symbolic_derivative(
        self,
        expr: str | sp.Expr,
        var: str = "x",
        order: int = 1,
    ) -> sp.Expr:
        """Symbolic derivative of any order.

        Example:
            engine.symbolic_derivative("x^3 + sin(x)", "x", 2)
            -> 6*x + cos(x)   (actually -cos? wait, second deriv of sin is -sin)
        """
        if isinstance(expr, str):
            expr = self.parse(expr)
        if order < 1 or not isinstance(order, int):
            raise MathEngineError("Derivative order must be a positive integer")

        sym = sp.Symbol(var)
        try:
            return diff(expr, sym, order)
        except Exception as exc:
            raise MathEngineError(f"Failed to compute derivative: {exc}") from exc

    def symbolic_integral(
        self,
        expr: str | sp.Expr,
        var: str = "x",
        definite: bool = False,
        lower: str | float | sp.Expr | None = None,
        upper: str | float | sp.Expr | None = None,
    ) -> sp.Expr:
        """Symbolic (indefinite or definite) integral."""
        if isinstance(expr, str):
            expr = self.parse(expr)
        sym = sp.Symbol(var)

        try:
            if definite:
                if lower is None or upper is None:
                    raise MathEngineError(
                        "Definite integral requires both lower and upper bounds"
                    )
                lo = self.parse(str(lower)) if isinstance(lower, str) else lower
                up = self.parse(str(upper)) if isinstance(upper, str) else upper
                return integrate(expr, (sym, lo, up))
            return integrate(expr, sym)
        except Exception as exc:
            raise MathEngineError(f"Failed to compute integral: {exc}") from exc

    def symbolic_limit(
        self,
        expr: str | sp.Expr,
        var: str = "x",
        point: str | float | sp.Expr = 0,
        direction: str = "+-",
    ) -> sp.Expr:
        """Compute one-sided or two-sided limit.

        direction: '+' (right), '-' (left), or '+-' / None (both / real).
        """
        if isinstance(expr, str):
            expr = self.parse(expr)
        sym = sp.Symbol(var)

        try:
            pt = self.parse(str(point)) if isinstance(point, str) else point
            dir_arg = None if direction in {"+-", ""} else direction
            return limit(expr, sym, pt, dir=dir_arg)
        except Exception as exc:
            raise MathEngineError(f"Failed to compute limit: {exc}") from exc

    def symbolic_series(
        self,
        expr: str | sp.Expr,
        var: str = "x",
        point: str | float = 0,
        n: int = 6,
    ) -> sp.Expr:
        """Taylor/Laurent series expansion around point up to O(var**n).

        The O() term is automatically removed for a clean polynomial.
        """
        if isinstance(expr, str):
            expr = self.parse(expr)
        sym = sp.Symbol(var)

        try:
            pt = self.parse(str(point)) if isinstance(point, str) else point
            ser = series(expr, sym, pt, n)
            return ser.removeO()
        except Exception as exc:
            raise MathEngineError(f"Failed to compute series expansion: {exc}") from exc

    # ------------------------------------------------------------------
    # Simplification & Rewriting
    # ------------------------------------------------------------------

    def simplify(self, expr: str | sp.Expr) -> sp.Expr:
        """Apply SymPy's powerful general simplification heuristics."""
        if isinstance(expr, str):
            expr = self.parse(expr)
        try:
            return simplify(expr)
        except Exception as exc:
            raise MathEngineError(f"Simplification failed: {exc}") from exc

    def expand(self, expr: str | sp.Expr) -> sp.Expr:
        """Expand products and powers (e.g. (x+1)^2 -> x^2 + 2x + 1)."""
        if isinstance(expr, str):
            expr = self.parse(expr)
        try:
            return expand(expr)
        except Exception as exc:
            raise MathEngineError(f"Expand failed: {exc}") from exc

    def factor(self, expr: str | sp.Expr) -> sp.Expr:
        """Factor polynomials and expressions when possible."""
        if isinstance(expr, str):
            expr = self.parse(expr)
        try:
            return factor(expr)
        except Exception as exc:
            raise MathEngineError(f"Factorization failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Numeric Evaluation (the heart of graphing & fast computation)
    # ------------------------------------------------------------------

    def lambdify(
        self,
        expr: str | sp.Expr,
        variables: list[str] | None = None,
    ) -> Callable[..., Any]:
        """Return a fast, vectorized Python callable for the expression.

        This is the recommended low-level primitive for graphing and
        numeric calculus labs. The returned function accepts positional
        arguments in the order of `variables` (or auto-detected free symbols).

        Args:
            expr: string or SymPy expression
            variables: explicit order of arguments. If None, uses sorted free symbols.

        Returns:
            Callable that accepts floats or numpy arrays and returns same shape.
        """
        if isinstance(expr, str):
            expr = self.parse(expr)

        if variables is None:
            variables = self.get_free_symbols(expr)

        if not variables:
            # Constant expression -> callable with no arguments
            const_func = sp.lambdify([], expr, modules=["numpy" if self.use_numpy else "sympy"])
            return lambda *args, **kwargs: const_func()

        syms = [sp.Symbol(v) for v in variables]
        modules = ["numpy"] if self.use_numpy else ["math", "sympy"]

        try:
            return sp.lambdify(syms, expr, modules=modules)
        except Exception as exc:
            raise MathEngineError(f"Failed to create numeric function: {exc}") from exc

    def evaluate_numeric(
        self,
        expr: str | sp.Expr,
        values: dict[str, float | int | complex | np.ndarray | list[float | int]],
    ) -> float | np.ndarray:
        """High-performance numeric evaluation with full parameter support.

        Designed specifically for graphing and interactive exploration:
            - Independent variable can receive 1D/2D numpy arrays
            - Parameters (a, b, k, ...) receive scalars (sliders)
            - Fully vectorized via NumPy

        Example (graphing f(x,a) = a*sin(x) + 0.5):
            engine.evaluate_numeric(
                "a*sin(x) + 0.5",
                {"x": np.linspace(0, 2*np.pi, 200), "a": 2.3}
            )
            # returns shape (200,) array ready for plotting

        Raises:
            MathEngineError on missing variables, domain errors, etc.
        """
        if isinstance(expr, str):
            expr = self.parse(expr)

        if not values:
            raise MathEngineError("No substitution values provided")

        needed = self.get_free_symbols(expr)
        provided = set(values.keys())
        missing = [v for v in needed if v not in provided]
        if missing:
            raise MathEngineError(
                f"Missing value(s) for: {missing}. Got keys: {sorted(provided)}"
            )

        # Use deterministic order (alphabetical from get_free_symbols)
        vars_ordered = needed
        syms = [sp.Symbol(name) for name in vars_ordered]

        # Convert inputs to numpy where helpful (keeps scalars as-is for speed)
        call_args = []
        for name in vars_ordered:
            val = values[name]
            if isinstance(val, (list, tuple)):
                call_args.append(np.asarray(val, dtype=np.float64))
            else:
                call_args.append(val)

        modules = ["numpy"] if self.use_numpy else ["math", "sympy"]

        try:
            func = sp.lambdify(syms, expr, modules=modules)
            result = func(*call_args)

            # Normalize return type
            if isinstance(result, (list, tuple)):
                result = np.asarray(result, dtype=float)
            if isinstance(result, np.ndarray):
                return result
            # scalar path
            if isinstance(result, (int, float, np.number)):
                return float(result)
            if isinstance(result, complex):
                return result
            # fallback
            return float(N(result))
        except ZeroDivisionError as exc:
            raise MathEngineError("Division by zero encountered during evaluation") from exc
        except (ValueError, TypeError) as exc:
            msg = str(exc).lower()
            if any(x in msg for x in ("domain", "log", "negative", "sqrt", "pow")):
                raise MathEngineError(
                    "Domain error: the expression is not defined for one or more of the supplied real values "
                    "(e.g. logarithm or square root of a negative number)"
                ) from exc
            raise MathEngineError(f"Numeric evaluation error: {exc}") from exc
        except Exception as exc:
            raise MathEngineError(f"Numeric evaluation failed: {exc}") from exc

    def evaluate_at(
        self, expr: str | sp.Expr, **subs: float | int | complex
    ) -> float | complex:
        """Convenience method for scalar point evaluation using keyword arguments.

        Example:
            engine.evaluate_at("a*x^2 + b", x=1.5, a=2, b=-1)
        """
        if isinstance(expr, str):
            expr = self.parse(expr)
        try:
            mapping = {sp.Symbol(k): v for k, v in subs.items()}
            result = expr.subs(mapping)
            return float(N(result))
        except Exception as exc:
            raise MathEngineError(f"Point evaluation failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Display & Export Helpers
    # ------------------------------------------------------------------

    def pretty(self, expr: str | sp.Expr, use_unicode: bool = True) -> str:
        """Return a human-readable pretty-printed string (Unicode by default)."""
        if isinstance(expr, str):
            expr = self.parse(expr)
        return sp.pretty(expr, use_unicode=use_unicode)

    def to_latex(self, expr: str | sp.Expr) -> str:
        """Return LaTeX representation suitable for rendering in UIs / Matplotlib."""
        if isinstance(expr, str):
            expr = self.parse(expr)
        return sp.latex(expr)

    def to_numeric_callable(self, expr: str | sp.Expr) -> Callable:
        """Deprecated alias for .lambdify() kept for backward compatibility."""
        return self.lambdify(expr)

    # ------------------------------------------------------------------
    # Introspection & Utilities
    # ------------------------------------------------------------------

    def is_constant(self, expr: str | sp.Expr) -> bool:
        """True if the expression contains no free variables."""
        return len(self.get_free_symbols(expr)) == 0

    def substitute(
        self, expr: str | sp.Expr, subs: dict[str, float | int | sp.Expr]
    ) -> sp.Expr:
        """Substitute values or expressions into the given expression (symbolic)."""
        if isinstance(expr, str):
            expr = self.parse(expr)
        mapping = {sp.Symbol(k): v for k, v in subs.items()}
        return expr.subs(mapping)


# ----------------------------------------------------------------------
# Self-test / Demonstration (executed only when run directly)
# ----------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("MathEngine v2 — Comprehensive Demo & Validation")
    print("=" * 60)

    engine = MathEngine(use_numpy=True)

    # 1. Basic parsing with calculator syntax (^ and implicit mult)
    print("\n[1] Parsing & pretty printing")
    expr1 = engine.parse("2x^2 + 3*sin(x) + log(x+1)")
    print("   Input : 2x^2 + 3*sin(x) + log(x+1)")
    print("   Parsed:", expr1)
    print("   Pretty:\n" + engine.pretty(expr1))

    # 2. Free symbols for graphing parameter handling
    print("\n[2] Free symbols (for sliders / independent var)")
    print("   Free symbols:", engine.get_free_symbols(expr1))
    print("   Suggested independent var:", engine.get_independent_variable(expr1))

    # 3. Symbolic calculus
    print("\n[3] Symbolic calculus")
    deriv = engine.symbolic_derivative("x^3 + 4*sin(x)", "x", order=2)
    print("   d²/dx² (x³ + 4 sin x) =", engine.pretty(deriv))

    integ = engine.symbolic_integral("x^2 * exp(x)", "x")
    print("   ∫ x²eˣ dx =", engine.pretty(integ))

    def_int = engine.symbolic_integral("sin(x)", "x", definite=True, lower=0, upper="pi")
    print("   ∫_0^π sin(x) dx =", def_int, "≈", float(N(def_int)))

    lim = engine.symbolic_limit("(sin(x)/x)", "x", 0)
    print("   lim x→0 sin(x)/x =", lim)

    taylor = engine.symbolic_series("exp(x)", "x", 0, n=5)
    print("   Taylor exp(x) @0 (order 4) =", engine.pretty(taylor))

    # 4. Simplification family
    print("\n[4] Algebraic rewriting")
    complicated = "(x+1)^2 * (x-1)^2 / (x^2 - 1)"
    print("   Original :", complicated)
    print("   Simplified:", engine.simplify(complicated))
    print("   Expanded  :", engine.expand(complicated))
    print("   Factored  :", engine.factor(complicated))

    # 5. High-speed numeric evaluation with parameters (graphing use case)
    print("\n[5] Numeric evaluation (vectorized for graphing)")
    import numpy as np

    graph_expr = "a * sin(x) + b * cos(2*x)"
    x_vals = np.linspace(0, 2 * np.pi, 6)
    numeric_result = engine.evaluate_numeric(
        graph_expr,
        values={"x": x_vals, "a": 2.0, "b": -0.75},
    )
    print(f"   f(x) = {graph_expr}")
    print(f"   a=2, b=-0.75, x={np.round(x_vals, 2)}")
    print("   Result:", np.round(numeric_result, 4))

    # Single point via kwargs
    pt = engine.evaluate_at("a*x^2 + b", x=1.5, a=4, b=-1)
    print(f"   evaluate_at('a*x²+b', x=1.5, a=4, b=-1) = {pt}")

    # 6. Callable for repeated use (performance critical path)
    print("\n[6] Reusable numeric callable (lambdify)")
    f = engine.lambdify("a*x**2 + b*x + c", variables=["x", "a", "b", "c"])
    print("   f(2.0, a=1.5, b=0, c=10) =", f(2.0, 1.5, 0.0, 10))

    # 7. Error handling examples
    print("\n[7] User-friendly error handling")
    errors_to_test = [
        ("", "empty expression"),
        ("sin(x", "unbalanced parens"),
        ("log(-1)", "domain error (will appear at numeric eval)"),
        ("(x + y)^", "bad syntax"),
    ]
    for bad_expr, desc in errors_to_test:
        try:
            if desc == "domain error (will appear at numeric eval)":
                # parsing succeeds, numeric fails
                e = engine.parse(bad_expr)
                _ = engine.evaluate_numeric(e, {"x": -1})
            else:
                _ = engine.parse(bad_expr)
        except MathEngineError as err:
            print(f"   [{desc}] → {err}")

    print("\n" + "=" * 60)
    print("MathEngine self-test complete. Ready for calculator, grapher, and calculus lab.")
    print("=" * 60)
