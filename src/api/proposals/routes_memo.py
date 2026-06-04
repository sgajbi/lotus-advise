"""Compatibility loader for proposal memo routes.

The router imports this module for registration. Focused route modules below own
memo commands, external package requests, and read/projection surfaces.
"""

from src.api.proposals import routes_memo_commands as routes_memo_commands
from src.api.proposals import routes_memo_packages as routes_memo_packages
from src.api.proposals import routes_memo_reads as routes_memo_reads

__all__ = [
    "routes_memo_commands",
    "routes_memo_packages",
    "routes_memo_reads",
]
