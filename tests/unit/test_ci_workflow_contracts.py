from pathlib import Path


def test_nightly_postgres_demo_pack_declares_controlled_ci_fallback() -> None:
    workflow = Path(".github/workflows/nightly-postgres-full.yml").read_text(encoding="utf-8")

    assert "ENVIRONMENT: ci" in workflow
    assert 'LOTUS_ADVISE_ALLOW_LOCAL_SIMULATION_FALLBACK: "true"' in workflow
    assert "python scripts/run_demo_pack_live.py --base-url http://127.0.0.1:8010" in workflow
