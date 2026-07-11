from __future__ import annotations

from scripts import no_alias_contract_guard


def test_no_alias_contract_guard_rejects_legacy_dpm_owner_role(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    src_root = tmp_path / "src"
    src_root.mkdir()
    (src_root / "public_contract.py").write_text('role = "DPM_OWNER"\n', encoding="utf-8")

    monkeypatch.setattr(no_alias_contract_guard, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(no_alias_contract_guard, "SRC_ROOT", src_root)

    assert no_alias_contract_guard.main() == 1
    output = capsys.readouterr().out
    assert "legacy_dpm_owner_role" in output
    assert "public_contract.py" in output


def test_no_alias_contract_guard_allows_canonical_portfolio_manager_role(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    src_root = tmp_path / "src"
    src_root.mkdir()
    (src_root / "public_contract.py").write_text(
        'role = "PORTFOLIO_MANAGER"\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(no_alias_contract_guard, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(no_alias_contract_guard, "SRC_ROOT", src_root)

    assert no_alias_contract_guard.main() == 0
    assert "No-alias contract guard passed." in capsys.readouterr().out
