"""
app.core
========

Core mathematical infrastructure for the high-tier symbolic + numeric calculator.

This package provides the single source of truth for expression parsing,
symbolic calculus, and high-performance numeric evaluation used by
the calculator, grapher, and calculus lab modules.
"""

from .math_engine import MathEngine, MathEngineError

__all__ = ["MathEngine", "MathEngineError"]
