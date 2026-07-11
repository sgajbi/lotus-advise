from src.core.advisory.policy_context import (
    CLIENT_CONTEXT_STATUS,
    JURISDICTION_CONTEXT_STATUS,
    MANDATE_CONTEXT_STATUS,
    POLICY_CONTEXT_AVAILABLE,
    POLICY_CONTEXT_MISSING,
    ProposalPolicySelectors,
    build_advisory_policy_context,
    client_context_available,
    jurisdiction_context_available,
    mandate_context_available,
)


def test_policy_context_projects_available_and_missing_source_status() -> None:
    context = build_advisory_policy_context(
        input_mode="stateful",
        resolution_source="LOTUS_CORE",
        selectors=ProposalPolicySelectors(
            household_id="hh_1",
            mandate_id=None,
            jurisdiction="SG",
            legal_entity_code="REFERENCE",
            benchmark_id="GLOBAL_BALANCED",
        ),
    )

    assert context[CLIENT_CONTEXT_STATUS] == POLICY_CONTEXT_AVAILABLE
    assert context[MANDATE_CONTEXT_STATUS] == POLICY_CONTEXT_MISSING
    assert context[JURISDICTION_CONTEXT_STATUS] == POLICY_CONTEXT_AVAILABLE
    assert context["legal_entity_code"] == "REFERENCE"
    assert context["missing_context"] == ["MANDATE_CONTEXT"]
    assert client_context_available(context) is True
    assert mandate_context_available(context) is False
    assert jurisdiction_context_available(context) is True


def test_policy_context_accessors_do_not_default_missing_or_unknown_to_available() -> None:
    assert client_context_available(None) is False
    assert mandate_context_available({}) is False
    assert jurisdiction_context_available({JURISDICTION_CONTEXT_STATUS: "UNKNOWN"}) is False


def test_policy_context_marks_all_source_context_missing_without_selectors() -> None:
    context = build_advisory_policy_context(
        input_mode="stateless",
        resolution_source="DIRECT_REQUEST",
        selectors=ProposalPolicySelectors(),
    )

    assert context[CLIENT_CONTEXT_STATUS] == POLICY_CONTEXT_MISSING
    assert context[MANDATE_CONTEXT_STATUS] == POLICY_CONTEXT_MISSING
    assert context[JURISDICTION_CONTEXT_STATUS] == POLICY_CONTEXT_MISSING
    assert context["missing_context"] == [
        "CLIENT_CONTEXT",
        "MANDATE_CONTEXT",
        "JURISDICTION",
    ]
