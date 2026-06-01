from pathlib import Path

from scripts.engineering_health_report import build_report, render_markdown


def test_engineering_health_report_captures_structural_metrics(tmp_path: Path) -> None:
    src = tmp_path / "src" / "api"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("", encoding="utf-8")
    (src / "routes_demo.py").write_text(
        "\n".join(
            [
                "from fastapi import APIRouter",
                "router = APIRouter()",
                "@router.get('/demo')",
                "def demo_route():",
                "    value = 1",
                "    return {'value': value}",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "Makefile").write_text(
        "lint:\n\tpython -m ruff check .\ntypecheck:\n\tpython -m mypy --config-file mypy.ini\n",
        encoding="utf-8",
    )

    report = build_report(tmp_path, source_roots=("src",), limit=5)
    markdown = render_markdown(report)

    assert report.python_file_count == 2
    assert report.package_count == 1
    assert report.module_count == 1
    assert report.router_hotspots[0].path == "src/api/routes_demo.py"
    assert report.router_hotspots[0].route_decorator_count == 1
    assert any(gate.make_target == "lint" for gate in report.gate_inventory)
    assert "Largest Functions" in markdown
    assert "`demo_route`" in markdown
