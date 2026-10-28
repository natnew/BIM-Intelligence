"""Import boundaries from AGENTS.md §3, checked statically so a violation fails CI.

* ``llm/`` is the only package that may import the ``openai`` SDK.
* ``bim/`` and ``validation/`` are the only packages that may import ``ifcopenshell`` or
  ``ifctester``.
* ``api/`` may import only the entry-point packages listed in AGENTS.md.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "backend" / "bim_intelligence"

OPENBIM_MODULES = {"ifcopenshell", "ifctester"}
OPENBIM_ALLOWED_PACKAGES = {"bim", "validation"}
LLM_MODULES = {"openai"}
LLM_ALLOWED_PACKAGES = {"llm"}
API_ALLOWED_IMPORTS = {
    "api",
    "config",
    "schemas",
    "store",
    "orchestration",
    "bim",
    "requirements",
    "reporting",
    "__init__",
}


def _modules() -> list[Path]:
    return sorted(p for p in PACKAGE_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def _package_of(path: Path) -> str:
    relative = path.relative_to(PACKAGE_ROOT)
    return relative.parts[0] if len(relative.parts) > 1 else relative.stem


def _first_party_targets(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            parts = node.module.split(".")
            if parts[0] == "bim_intelligence":
                targets.add(parts[1] if len(parts) > 1 else "__init__")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == "bim_intelligence":
                    targets.add(parts[1] if len(parts) > 1 else "__init__")
    return targets


@pytest.mark.parametrize("path", _modules(), ids=lambda p: p.relative_to(PACKAGE_ROOT).as_posix())
def test_third_party_boundaries(path: Path) -> None:
    package = _package_of(path)
    imports = _top_level_imports(path)
    if imports & OPENBIM_MODULES:
        assert package in OPENBIM_ALLOWED_PACKAGES, f"{path.name} imports an openBIM library"
    if imports & LLM_MODULES:
        assert package in LLM_ALLOWED_PACKAGES, f"{path.name} imports the openai SDK"


@pytest.mark.parametrize(
    "path",
    [p for p in _modules() if _package_of(p) == "api"],
    ids=lambda p: p.relative_to(PACKAGE_ROOT).as_posix(),
)
def test_api_imports_only_entry_points(path: Path) -> None:
    targets = _first_party_targets(path)
    assert targets <= API_ALLOWED_IMPORTS, (
        f"{path.name} imports {sorted(targets - API_ALLOWED_IMPORTS)}"
    )
