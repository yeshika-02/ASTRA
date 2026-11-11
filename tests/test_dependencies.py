"""Every third-party package imported by the research code must be declared.

seaborn, onnxruntime and pandas were imported but missing from requirements.txt, so
cross-validation crashed at its first confusion-matrix plot in any environment built
from the requirements (CI included).
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE_DIRS = ["astra", "pipeline", "training", "data"]
LOCAL_PACKAGES = {"astra", "pipeline", "training", "data", "tests"}
IMPORT_TO_DISTRIBUTION = {"sklearn": "scikit-learn", "PIL": "pillow", "yaml": "pyyaml"}


def _third_party_imports() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for directory in CODE_DIRS:
        for path in (ROOT / directory).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    names = [node.module.split(".")[0]]
                else:
                    continue
                for name in names:
                    if name not in sys.stdlib_module_names and name not in LOCAL_PACKAGES:
                        found.setdefault(name, set()).add(str(path.relative_to(ROOT)))
    return found


def _names(requirements: list[str]) -> set[str]:
    return {re.split(r"[<>=!~\[; ]", r.strip(), maxsplit=1)[0].lower() for r in requirements if r.strip()}


def _requirements_txt() -> set[str]:
    lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    return _names([line.split("#", 1)[0] for line in lines if not line.lstrip().startswith("#")])


def _pyproject() -> set[str]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return _names(data["project"]["dependencies"])


class DependencyDeclarationTests(unittest.TestCase):
    def test_imports_are_declared_in_requirements_txt(self) -> None:
        declared = _requirements_txt()
        missing = {
            module: sorted(files)[:3]
            for module, files in _third_party_imports().items()
            if IMPORT_TO_DISTRIBUTION.get(module, module).lower() not in declared
        }
        self.assertEqual(missing, {}, "imported but not in requirements.txt")

    def test_pyproject_and_requirements_list_the_same_packages(self) -> None:
        self.assertEqual(_pyproject(), _requirements_txt())


if __name__ == "__main__":
    unittest.main()
