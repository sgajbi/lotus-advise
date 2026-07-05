from pathlib import Path

REPORTING_SOURCE_PATH = Path("src/core/policy_packs/reporting.py")
AI_SOURCE_PATH = Path("src/core/policy_packs/ai.py")
PORTS_SOURCE_PATH = Path("src/core/policy_packs/ports.py")
RUNTIME_CLIENTS_SOURCE_PATH = Path("src/runtime/policy_evaluation_clients.py")
ROUTE_SOURCE_PATH = Path("src/api/proposals/routes_policy_evaluation_packages.py")


def test_policy_report_and_ai_workflows_use_application_ports() -> None:
    reporting_source = REPORTING_SOURCE_PATH.read_text(encoding="utf-8")
    ai_source = AI_SOURCE_PATH.read_text(encoding="utf-8")
    ports_source = PORTS_SOURCE_PATH.read_text(encoding="utf-8")
    runtime_source = RUNTIME_CLIENTS_SOURCE_PATH.read_text(encoding="utf-8")
    route_source = ROUTE_SOURCE_PATH.read_text(encoding="utf-8")

    assert "from src.integrations" not in reporting_source
    assert "from src.integrations" not in ai_source
    assert "PolicyReportPackageClient" in ports_source
    assert "PolicyAiEvidenceClient" in ports_source
    assert "request_policy_sign_off_report_package_with_lotus_report" in runtime_source
    assert "generate_policy_evidence_summary_with_lotus_ai" in runtime_source
    assert "get_policy_report_package_client()" in route_source
    assert "get_policy_ai_evidence_client()" in route_source
