import ast
from pathlib import Path

API_EXCEPTION_IMPORT_FILES = [
    Path("src/api/proposals/errors.py"),
    Path("src/api/proposals/routes_async.py"),
    Path("src/api/proposals/routes_lifecycle.py"),
    Path("src/api/proposals/routes_delivery.py"),
    Path("src/api/proposals/routes_support.py"),
    Path("src/api/services/proposal_reporting_service.py"),
    Path("src/api/workspaces/router.py"),
]

PROPOSAL_EXCEPTION_NAMES = {
    "ProposalIdempotencyConflictError",
    "ProposalNotFoundError",
    "ProposalStateConflictError",
    "ProposalTransitionError",
    "ProposalValidationError",
}


def test_api_modules_import_proposal_exceptions_from_exception_taxonomy():
    for path in API_EXCEPTION_IMPORT_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            imported_names = {alias.name for alias in node.names}
            if not imported_names.intersection(PROPOSAL_EXCEPTION_NAMES):
                continue
            assert node.module == "src.core.proposals.exceptions", (
                f"{path} should import proposal exception vocabulary from "
                "src.core.proposals.exceptions"
            )
