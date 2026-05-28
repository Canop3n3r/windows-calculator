"""
Calculus Lab - High-impact educational visualizations for derivatives, integrals, series, and limits.

Currently available:
- RiemannStudio: complete interactive Riemann sums + trapezoidal rule visualizer
  with live partitions, animation, symbolic exact integrals via MathEngine, and parameter support.

TaylorPlayground planned for a future iteration (series convergence playground).
"""
from .riemann_studio import RiemannStudio

# TaylorPlayground will be added when implemented. Import is guarded so the package
# remains importable today.
try:
    from .taylor_playground import TaylorPlayground  # type: ignore
except ImportError:
    TaylorPlayground = None  # type: ignore

__all__ = ["RiemannStudio", "TaylorPlayground"]
