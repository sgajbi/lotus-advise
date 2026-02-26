"""
FILE: src/core/engine.py
Compatibility shim for stable advisory imports.
"""

import warnings

from src.core.advisory_engine import run_proposal_simulation

warnings.warn(
    "src.core.engine is deprecated; import from src.core.advisory_engine.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["run_proposal_simulation"]
