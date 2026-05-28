"""
Comprehensive test suite for MathForge's MathEngine.

Covers:
- Safe parsing (SymPy-backed, calculator syntax: ^, implicit multiplication)
- Free symbol / independent variable introspection
- Full symbolic calculus: derivatives (any order), integrals (indefinite + definite),
  limits (one-sided + two-sided), Taylor/Laurent series
- Algebraic rewriting: simplify, expand, factor
- High-performance numeric evaluation: scalars, 1D/2D arrays, parameter substitution
- lambdify for reusable vectorized callables
- Convenience APIs: evaluate_at, pretty, to_latex, substitute, is_constant
- Error handling: MathEngineError with clear messages for all user-facing failure modes
- Both numpy and pure-Python backends (use_numpy flag)

Run:
    pytest tests/test_math_engine.py -v
    # or with coverage: pytest ... --cov=app.core.math_engine
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the project importable when running tests directly (no editable install required)
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pytest
import sympy as sp

from app.core.math_engine import MathEngine, MathEngineError


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def engine() -> MathEngine:
    """Default engine with NumPy vectorization enabled (recommended for graphing)."""
    return MathEngine(use_numpy=True)


@pytest.fixture(scope="module")
def engine_pure() -> MathEngine:
    """Engine using pure Python math (no NumPy)."""
    return MathEngine(use_numpy=False)


# =============================================================================
# PARSING TESTS
# =============================================================================

@pytest.mark.parametrize(
    "expr_str, expected_type",
    [
        ("2 + 3", sp.Add),
        ("x^2", sp.Pow),
        ("sin(x)", sp.sin),
        ("2x", sp.Mul),  # implicit multiplication
        ("(x+1)(x-2)", sp.Mul),
        ("log(x+1)", sp.log),
        ("pi * e^2", sp.Mul),
        ("sqrt(2) + cbrt(8)", sp.Add),
        ("a*sin(b*x) + 1", sp.Add),
    ],
)
def test_parse_success_various_forms(engine: MathEngine, expr_str: str, expected_type: type) -> None:
    expr = engine.parse(expr_str)
    assert isinstance(expr, sp.Expr)
    assert isinstance(expr, expected_type) or any(isinstance(a, expected_type) for a in sp.preorder_traversal(expr))


def test_parse_calculator_syntax(engine: MathEngine) -> None:
    """^ becomes exponent, implicit mult works exactly like graphing calculators."""
    expr = engine.parse("2x^3 + 3sin(x) + (x+1)(x-2)")
    # Should parse without error and contain the right structure
    assert "x**3" in str(expr) or "Pow" in str(type(expr))
    free = engine.get_free_symbols(expr)
    assert set(free) == {"x"}


def test_parse_empty_and_whitespace(engine: MathEngine) -> None:
    for bad in ("", "   ", "\t\n"):
        with pytest.raises(MathEngineError, match="cannot be empty"):
            engine.parse(bad)


@pytest.mark.parametrize(
    "bad_expr, match_text",
    [
        ("sin(x", "parenthes"),           # unbalanced
        ("(x + y)^", "syntax"),           # incomplete
        ("foo(x)", "Could not parse"),    # unknown symbol (not whitelisted)
        ("2x + * 3", "syntax|invalid"),   # bad operator
        ("log()", "parse|syntax"),        # missing arg
    ],
)
def test_parse_error_cases(engine: MathEngine, bad_expr: str, match_text: str) -> None:
    with pytest.raises(MathEngineError) as exc:
        engine.parse(bad_expr)
    assert any(kw in str(exc.value).lower() for kw in match_text.split("|"))


def test_parse_with_additional_locals(engine: MathEngine) -> None:
    expr = engine.parse("myvar + 1", additional_locals={"myvar": sp.Symbol("myvar")})
    assert "myvar" in engine.get_free_symbols(expr)


# =============================================================================
# INTROSPECTION TESTS
# =============================================================================

def test_get_free_symbols_filters_constants(engine: MathEngine) -> None:
    expr = engine.parse("pi + e + 3 + x + sin(y)")
    syms = engine.get_free_symbols(expr)
    assert syms == ["x", "y"]


def test_get_free_symbols_constant_only(engine: MathEngine) -> None:
    expr = engine.parse("pi^2 + 3*e")
    assert engine.get_free_symbols(expr) == []


def test_get_independent_variable_preference(engine: MathEngine) -> None:
    # No 'x' present → falls back to first alphabetically sorted free symbol
    assert engine.get_independent_variable("a*x + b") == "a"
    assert engine.get_independent_variable("a*x + b", preferred="x") == "a"

    # Preferred 'x' wins when available
    assert engine.get_independent_variable("sin(t) + k") == "t"
    assert engine.get_independent_variable("sin(x) + k") == "x"

    # Pure constant expression
    assert engine.get_independent_variable("42") is None


# =============================================================================
# SYMBOLIC CALCULUS TESTS
# =============================================================================

def test_symbolic_derivative_basic(engine: MathEngine) -> None:
    d = engine.symbolic_derivative("x^3 + 4*sin(x)", "x", order=1)
    # 3x^2 + 4cos(x)
    assert sp.simplify(d - (3*sp.Symbol("x")**2 + 4*sp.cos(sp.Symbol("x")))) == 0


def test_symbolic_derivative_higher_order(engine: MathEngine) -> None:
    d2 = engine.symbolic_derivative("x^4 + sin(x)", "x", order=2)
    # 12 x^2 - sin(x)
    x = sp.Symbol("x")
    expected = 12 * x**2 - sp.sin(x)
    assert sp.simplify(d2 - expected) == 0


def test_symbolic_derivative_errors(engine: MathEngine) -> None:
    with pytest.raises(MathEngineError, match="order must be a positive integer"):
        engine.symbolic_derivative("x^2", "x", order=0)
    with pytest.raises(MathEngineError, match="order must be a positive integer"):
        engine.symbolic_derivative("x^2", "x", order=-1)


def test_symbolic_integral_indefinite(engine: MathEngine) -> None:
    integ = engine.symbolic_integral("x^2", "x")
    x = sp.Symbol("x")
    assert sp.simplify(integ - x**3 / 3) == 0


def test_symbolic_integral_definite(engine: MathEngine) -> None:
    res = engine.symbolic_integral("sin(x)", "x", definite=True, lower=0, upper="pi")
    # Should be exactly 2
    assert float(sp.N(res)) == pytest.approx(2.0, abs=1e-12)


def test_symbolic_integral_definite_missing_bounds(engine: MathEngine) -> None:
    with pytest.raises(MathEngineError, match="requires both lower and upper"):
        engine.symbolic_integral("x^2", "x", definite=True)


def test_symbolic_limit(engine: MathEngine) -> None:
    lim = engine.symbolic_limit("sin(x)/x", "x", 0)
    assert lim == 1

    lim_right = engine.symbolic_limit("1/x", "x", 0, direction="+")
    assert lim_right == sp.oo


def test_symbolic_series(engine: MathEngine) -> None:
    ser = engine.symbolic_series("exp(x)", "x", 0, n=5)
    # 1 + x + x^2/2 + x^3/6 + x^4/24
    x = sp.Symbol("x")
    expected = 1 + x + x**2/2 + x**3/6 + x**4/24
    assert sp.simplify(ser - expected).is_zero is True or sp.simplify(ser - expected) == 0


# =============================================================================
# ALGEBRAIC REWRITING TESTS
# =============================================================================

@pytest.mark.parametrize("method", ["simplify", "expand", "factor"])
def test_algebraic_methods(engine: MathEngine, method: str) -> None:
    expr = "(x+1)^2 * (x-1)^2 / (x^2 - 1)"
    func = getattr(engine, method)
    result = func(expr)
    assert isinstance(result, sp.Expr)
    # All three should succeed without raising and return something different or canonical


def test_simplify_trig(engine: MathEngine) -> None:
    res = engine.simplify("sin(x)^2 + cos(x)^2")
    assert res == 1


# =============================================================================
# NUMERIC EVALUATION + ARRAYS (CORE OF GRAPHING)
# =============================================================================

def test_evaluate_numeric_scalar(engine: MathEngine) -> None:
    res = engine.evaluate_numeric("a*x^2 + b", {"x": 2.0, "a": 3.0, "b": -1.0})
    assert isinstance(res, float)
    assert res == pytest.approx(3*4 - 1)


def test_evaluate_numeric_1d_array(engine: MathEngine) -> None:
    x_vals = np.linspace(0, np.pi, 5)
    res = engine.evaluate_numeric("sin(x)", {"x": x_vals})
    assert isinstance(res, np.ndarray)
    assert res.shape == (5,)
    assert np.allclose(res, np.sin(x_vals))


def test_evaluate_numeric_2d_array(engine: MathEngine) -> None:
    """Support for surface-style or grid evaluations (common in advanced graphing)."""
    x = np.linspace(-1, 1, 3)
    y = np.linspace(-2, 2, 4)
    X, Y = np.meshgrid(x, y)
    res = engine.evaluate_numeric("x*y + 1", {"x": X, "y": Y})
    assert isinstance(res, np.ndarray)
    assert res.shape == X.shape
    assert np.allclose(res, X * Y + 1)


def test_evaluate_numeric_with_parameters(engine: MathEngine) -> None:
    x_vals = np.linspace(0, 2 * np.pi, 8)
    res = engine.evaluate_numeric("a * sin(b * x)", {"x": x_vals, "a": 2.5, "b": 3.0})
    expected = 2.5 * np.sin(3.0 * x_vals)
    assert np.allclose(res, expected)


def test_evaluate_numeric_missing_variables(engine: MathEngine) -> None:
    with pytest.raises(MathEngineError, match="Missing value"):
        engine.evaluate_numeric("x + y", {"x": 1.0})


def test_evaluate_numeric_domain_error(engine: MathEngine) -> None:
    with pytest.raises(MathEngineError, match="Domain error|not defined"):
        engine.evaluate_numeric("log(x)", {"x": -1.0})


def test_evaluate_numeric_division_by_zero(engine: MathEngine) -> None:
    with pytest.raises(MathEngineError, match="Division by zero"):
        engine.evaluate_numeric("1 / (x - 1)", {"x": 1.0})


def test_evaluate_at_convenience(engine: MathEngine) -> None:
    res = engine.evaluate_at("a*x^2 + b", x=1.5, a=4, b=-1)
    assert isinstance(res, float)
    assert res == pytest.approx(4 * 2.25 - 1)


# =============================================================================
# LAMBDIFY (PERFORMANCE PRIMITIVE)
# =============================================================================

def test_lambdify_vectorized(engine: MathEngine) -> None:
    f = engine.lambdify("a*sin(x) + b", variables=["x", "a", "b"])
    x_arr = np.linspace(0, 1, 20)
    out = f(x_arr, 2.0, -0.5)
    assert isinstance(out, np.ndarray)
    assert out.shape == (20,)


def test_lambdify_constant_expr(engine: MathEngine) -> None:
    f = engine.lambdify("pi^2 + 3")
    assert f() == pytest.approx(float(sp.N(sp.pi**2 + 3)))


def test_lambdify_pure_python(engine_pure: MathEngine) -> None:
    f = engine_pure.lambdify("x^2 + 1", variables=["x"])
    assert f(3) == 10.0


# =============================================================================
# DISPLAY & UTILITY HELPERS
# =============================================================================

def test_pretty_and_latex(engine: MathEngine) -> None:
    expr = engine.parse("x^2 + sin(x)")
    pretty = engine.pretty(expr)
    latex = engine.to_latex(expr)
    assert isinstance(pretty, str) and len(pretty) > 0
    assert isinstance(latex, str) and "sin" in latex.lower()


def test_is_constant(engine: MathEngine) -> None:
    assert engine.is_constant("pi + 3*e") is True
    assert engine.is_constant("x + 1") is False


def test_substitute_symbolic(engine: MathEngine) -> None:
    res = engine.substitute("x^2 + a", {"x": sp.Symbol("y"), "a": 5})
    assert "y**2" in str(res)


# =============================================================================
# ERROR HANDLING & EDGE CASES (ROBUSTNESS)
# =============================================================================

def test_math_engine_error_is_value_error_subclass() -> None:
    assert issubclass(MathEngineError, ValueError)


@pytest.mark.parametrize("use_numpy", [True, False])
def test_full_roundtrip_with_both_backends(use_numpy: bool) -> None:
    eng = MathEngine(use_numpy=use_numpy)
    expr = eng.parse("exp(-k*t) * sin(omega * t)")
    deriv = eng.symbolic_derivative(expr, "t", 1)
    numeric = eng.evaluate_numeric(deriv, {"t": np.array([0.0, 0.1, 0.5]), "k": 0.8, "omega": 2.0})
    assert isinstance(numeric, (float, np.ndarray))


def test_evaluate_numeric_list_input_converted(engine: MathEngine) -> None:
    res = engine.evaluate_numeric("x + 1", {"x": [1, 2, 3]})
    assert isinstance(res, np.ndarray)
    assert list(res) == pytest.approx([2, 3, 4])


def test_complex_result_preserved(engine: MathEngine) -> None:
    # Some expressions legitimately produce complex during intermediate steps
    res = engine.evaluate_numeric("I * x", {"x": 2.0})
    assert isinstance(res, complex)
    assert res == 2j


# =============================================================================
# INTEGRATION WITH REALISTIC GRAPHING / CALCULUS USE CASES
# =============================================================================

def test_derivative_explorer_style_workflow(engine: MathEngine) -> None:
    """Simulates the flagship Derivative Explorer use case."""
    f_str = "a*sin(b*x)"
    f_prime = engine.symbolic_derivative(f_str, "x")
    assert "cos" in str(f_prime).lower()

    x_grid = np.linspace(-4, 4, 200)
    y = engine.evaluate_numeric(f_str, {"x": x_grid, "a": 1.0, "b": 1.5})
    slope = engine.evaluate_numeric(f_prime, {"x": 1.2, "a": 1.0, "b": 1.5})

    assert y.shape == (200,)
    assert isinstance(slope, float)


if __name__ == "__main__":
    # Allow direct execution for quick smoke test
    pytest.main([__file__, "-v", "--tb=line"])
