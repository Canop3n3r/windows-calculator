"""
Calculus Lab - High-impact educational visualizations for derivatives, integrals, series, and limits.

Currently available:
- RiemannStudio: complete interactive Riemann sums + trapezoidal rule visualizer
  with live partitions, animation, symbolic exact integrals via MathEngine, and parameter support.

TaylorPlayground: fully implemented interactive Taylor series explorer with live order slider, symbolic display, animation, and remainder/error visualization (powered by MathEngine).
"""
from .riemann_studio import RiemannStudio

# TaylorPlayground will be added when implemented. Import is guarded so the package
# remains importable today.
try:
    from .taylor_playground import TaylorPlayground, TaylorPlaygroundFrame  # type: ignore
except ImportError:
    TaylorPlayground = None  # type: ignore
    TaylorPlaygroundFrame = None  # type: ignore

__all__ = ["RiemannStudio", "TaylorPlayground", "TaylorPlaygroundFrame"]
