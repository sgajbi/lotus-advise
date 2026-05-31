from pathlib import Path

WIKI_HOME = Path("wiki/Home.md")
WIKI_SIDEBAR = Path("wiki/_Sidebar.md")
WIKI_SUPPORTED_FEATURES = Path("wiki/Supported-Features.md")
WIKI_DEMO_PROOF = Path("wiki/Demo-and-Commercial-Proof.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_demo_commercial_proof_wiki_page_is_navigable():
    page_link = "[Demo and Commercial Proof](Demo-and-Commercial-Proof)"

    assert WIKI_DEMO_PROOF.exists()
    assert page_link in _read(WIKI_HOME)
    assert page_link in _read(WIKI_SIDEBAR)
    assert page_link in _read(WIKI_SUPPORTED_FEATURES)


def test_demo_commercial_proof_wiki_page_is_implementation_backed():
    text = _read(WIKI_DEMO_PROOF)

    required_terms = [
        "RFC28_BANK_DEMO_CLIENT_READY_PROOF_CANONICAL",
        "PB_SG_GLOBAL_BAL_001",
        "BANK_DEMO_PROOF_PACK_CREATED",
        "GET /advisory/bank-demo-proof/scenario-contract",
        "GET /advisory/bank-demo-proof/supported-claim-register",
        "POST /advisory/bank-demo-proof/proof-packs",
        "scripts/capture_rfc0028_backend_proof.py",
        "docs/commercial/RFC-0028-bank-demo-client-proof-materials.md",
        "material-field-review.json",
        "commercial-material-pack.json",
    ]

    for term in required_terms:
        assert term in text


def test_demo_commercial_proof_wiki_page_preserves_blocked_claims():
    text = _read(WIKI_DEMO_PROOF)

    blocked_terms = [
        "client-ready publication",
        "external client communication",
        "legal or regulatory advice",
        "completed policy approval",
        "AI approval",
        "OMS order, fill, settlement",
        "bank-specific security",
    ]

    for term in blocked_terms:
        assert term in text


def test_demo_commercial_proof_wiki_page_contains_business_and_runtime_diagrams():
    text = _read(WIKI_DEMO_PROOF)

    assert "```mermaid" in text
    assert "flowchart LR" in text
    assert "Audience Guide" in text
    assert "Operator Checklist" in text
