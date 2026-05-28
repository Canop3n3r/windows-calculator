"""
app.core
========
Core mathematical infrastructure for MathForge.
The MathEngine is the single source of truth for all symbolic and numeric math.
"""
from .math_engine import MathEngine, MathEngineError

__all__ = ["MathEngine", "MathEngineError"]

