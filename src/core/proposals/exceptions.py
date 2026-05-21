class ProposalLifecycleError(Exception):
    """Base error for advisory proposal lifecycle commands."""


class ProposalNotFoundError(ProposalLifecycleError):
    """Raised when a proposal, version, or async operation referent cannot be found."""


class ProposalValidationError(ProposalLifecycleError):
    """Raised when a proposal command fails domain validation."""


class ProposalIdempotencyConflictError(ProposalLifecycleError):
    """Raised when an idempotent replay key maps to a different request."""


class ProposalStateConflictError(ProposalLifecycleError):
    """Raised when a command targets an unexpected proposal state."""


class ProposalTransitionError(ProposalLifecycleError):
    """Raised when a requested lifecycle transition is not allowed."""
