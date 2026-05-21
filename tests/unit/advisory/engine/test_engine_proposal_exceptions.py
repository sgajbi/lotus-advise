from src.core.proposals import ProposalValidationError as PublicProposalValidationError
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalLifecycleError,
    ProposalNotFoundError,
    ProposalStateConflictError,
    ProposalTransitionError,
    ProposalValidationError,
)
from src.core.proposals.service import ProposalValidationError as ServiceProposalValidationError


def test_proposal_exception_taxonomy_uses_lifecycle_base():
    for exception_type in [
        ProposalNotFoundError,
        ProposalValidationError,
        ProposalIdempotencyConflictError,
        ProposalStateConflictError,
        ProposalTransitionError,
    ]:
        assert issubclass(exception_type, ProposalLifecycleError)


def test_proposal_exception_import_compatibility_is_preserved():
    assert ServiceProposalValidationError is ProposalValidationError
    assert PublicProposalValidationError is ProposalValidationError
