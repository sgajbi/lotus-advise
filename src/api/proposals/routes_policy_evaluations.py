"""Compatibility loader for Advisory Policy Evaluation routes.

The proposal router imports this module for registration. Focused route modules
own policy evaluation commands, read/projection routes, workflow sign-off
routes, and external package or AI evidence request routes.

Governance breadcrumbs for RFC evidence tests:
- Advisory Policy Evaluation
- /advisory/policy-evaluations/review-queue
- /advisory/policy-evaluations/{evaluation_id}
- /advisory/policy-evaluations/{evaluation_id}/lineage
- /advisory/policy-evaluations/{evaluation_id}/diagnostics
- /advisory/policy-evaluations/{evaluation_id}/workflow
- /advisory/policy-evaluations/{evaluation_id}/sign-off-package
- /advisory/policy-evaluations/{evaluation_id}/sign-off-decisions
- /advisory/policy-evaluations/{evaluation_id}/report-packages
- /advisory/policy-evaluations/{evaluation_id}/ai-evidence
"""

from src.api.proposals import routes_policy_evaluation_commands as routes_policy_evaluation_commands
from src.api.proposals import routes_policy_evaluation_packages as routes_policy_evaluation_packages
from src.api.proposals import routes_policy_evaluation_reads as routes_policy_evaluation_reads
from src.api.proposals import routes_policy_evaluation_workflow as routes_policy_evaluation_workflow

__all__ = [
    "routes_policy_evaluation_commands",
    "routes_policy_evaluation_packages",
    "routes_policy_evaluation_reads",
    "routes_policy_evaluation_workflow",
]
