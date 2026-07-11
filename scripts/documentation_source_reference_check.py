"""Validate live documentation references to repository source paths."""

from __future__ import annotations

import argparse
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

LIVE_DOCUMENTATION_ROOTS = (
    Path("README.md"),
    Path("REPOSITORY-ENGINEERING-CONTEXT.md"),
    Path("docs/documentation"),
    Path("wiki"),
)

DOCUMENTED_PATH_PREFIXES = (
    "src/",
    "tests/",
    "docs/",
    "wiki/",
    "scripts/",
    "contracts/",
    ".github/",
)

DOCUMENTED_ROOT_FILES = {
    ".dockerignore",
    ".importlinter",
    "Dockerfile",
    "Makefile",
    "docker-compose.ci-local.yml",
    "docker-compose.yml",
    "mypy.ini",
    "pyproject.toml",
    "requirements-dev.txt",
    "requirements.txt",
}

BACKTICK_REFERENCE = re.compile(r"`([^`\n]+)`")


@dataclass(frozen=True)
class DocumentationReferenceFailure:
    document_path: Path
    line_number: int
    referenced_path: str

    def message(self) -> str:
        return (
            f"{self.document_path.as_posix()}:{self.line_number} references missing "
            f"repository path `{self.referenced_path}`"
        )


def validate_documentation_source_references(
    repo_root: Path = REPO_ROOT,
) -> list[DocumentationReferenceFailure]:
    failures: list[DocumentationReferenceFailure] = []
    for document_path in _iter_live_markdown_documents(repo_root):
        relative_document_path = document_path.relative_to(repo_root)
        for line_number, line in enumerate(
            document_path.read_text(encoding="utf-8").splitlines(), 1
        ):
            for referenced_path in _extract_documented_paths(line):
                resolved_path = repo_root / referenced_path
                if not resolved_path.exists():
                    failures.append(
                        DocumentationReferenceFailure(
                            document_path=relative_document_path,
                            line_number=line_number,
                            referenced_path=referenced_path,
                        )
                    )
    return failures


def _iter_live_markdown_documents(repo_root: Path) -> Iterable[Path]:
    for root in LIVE_DOCUMENTATION_ROOTS:
        resolved = repo_root / root
        if resolved.is_file() and resolved.suffix.lower() == ".md":
            yield resolved
        elif resolved.is_dir():
            yield from sorted(resolved.rglob("*.md"))


def _extract_documented_paths(line: str) -> list[str]:
    documented_paths: list[str] = []
    for match in BACKTICK_REFERENCE.finditer(line):
        candidate = _normalize_reference(match.group(1))
        if _is_documented_repository_path(candidate):
            documented_paths.append(candidate)
    return documented_paths


def _normalize_reference(raw_reference: str) -> str:
    reference = raw_reference.strip().replace("\\", "/")
    reference = reference.split("#", maxsplit=1)[0]
    reference = reference.rstrip(".,:;)")
    return reference.rstrip("/")


def _is_documented_repository_path(reference: str) -> bool:
    if not reference or " " in reference:
        return False
    if reference in DOCUMENTED_ROOT_FILES:
        return True
    return reference.startswith(DOCUMENTED_PATH_PREFIXES)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()

    failures = validate_documentation_source_references(args.repo_root.resolve())
    for failure in failures:
        print(failure.message())
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
