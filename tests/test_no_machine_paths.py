"""No research code may depend on a specific developer machine.

Twenty-seven absolute paths into the original author's home directory used to decide
where scripts read data and wrote reports (audit finding R3). Paths now come from
astra.config.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE_DIRS = ["astra", "pipeline", "training", "data", "tests"]
# Absolute home-directory paths on macOS/Linux/Windows, and file:// URLs.
MACHINE_PATH = re.compile(r"(/Users/[A-Za-z0-9_.-]+/|/home/[A-Za-z0-9_.-]+/|[A-Za-z]:\\\\Users\\\\|file:///)")


class NoMachinePathTests(unittest.TestCase):
    def test_no_absolute_home_paths_or_file_urls_in_code(self) -> None:
        offenders = []
        for directory in CODE_DIRS:
            for path in (ROOT / directory).rglob("*.py"):
                if path.name == Path(__file__).name:
                    continue
                for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if MACHINE_PATH.search(line):
                        offenders.append(f"{path.relative_to(ROOT)}:{number}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
