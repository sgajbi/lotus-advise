from pathlib import Path


def test_local_docker_compose_uses_canonical_upstream_urls() -> None:
    compose_text = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert (
        "LOTUS_CORE_BASE_URL=${LOTUS_CORE_BASE_URL:-http://core-control.dev.lotus}"
        in compose_text
    )
    assert (
        "LOTUS_CORE_QUERY_BASE_URL=${LOTUS_CORE_QUERY_BASE_URL:-http://core-query.dev.lotus}"
        in compose_text
    )
    assert "LOTUS_RISK_BASE_URL=${LOTUS_RISK_BASE_URL:-http://risk.dev.lotus}" in compose_text
    assert '"core-control.dev.lotus:host-gateway"' in compose_text
    assert '"core-query.dev.lotus:host-gateway"' in compose_text
    assert '"risk.dev.lotus:host-gateway"' in compose_text


def test_local_docker_compose_does_not_publish_internal_postgres_port() -> None:
    compose_text = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert 'postgres:\n' in compose_text
    assert '"5432:5432"' not in compose_text


def test_readme_documents_canonical_local_docker_urls() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "http://core-control.dev.lotus" in readme
    assert "http://core-query.dev.lotus" in readme
    assert "http://risk.dev.lotus" in readme
