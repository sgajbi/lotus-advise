"""
FILE: src/core/engine.py
Compatibility shim for stable imports.
"""

from src.core.advisory_engine import run_proposal_simulation
from src.core.dpm_engine import run_simulation

__all__ = ["run_simulation", "run_proposal_simulation"]
