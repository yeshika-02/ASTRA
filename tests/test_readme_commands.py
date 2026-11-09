"""Every `python <script> --flag ...` command in README.md must match the script's CLI.

The README used to document flags that did not exist (--seed, --model, --split,
--n_passes, --variant on train_cnn/cross_validate), so reproduction commands failed
or were silently ignored. This test keeps the documentation and the code in sync.
"""

from __future__ import annotations

import re
import subprocess
import sys
import unittest
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"


def _bash_blocks(text: str) -> list[str]:
    return re.findall(r"```bash\n(.*?)```", text, flags=re.S)


def _commands() -> list[tuple[str, list[str]]]:
    """(script path, flags) for each `python <file>.py ...` line, joining backslash continuations."""
    commands = []
    for block in _bash_blocks(README.read_text(encoding="utf-8")):
        joined = re.sub(r"\\\n\s*", " ", block)
        for line in joined.splitlines():
            line = line.split(" #", 1)[0].strip()
            match = re.match(r"python\s+(\S+\.py)\b(.*)", line)
            if match:
                flags = re.findall(r"(?<!\S)(--[a-z][a-z0-9-]*)", match.group(2))
                commands.append((match.group(1), flags))
    return commands


@lru_cache(maxsize=None)
def _help(script: str) -> str:
    result = subprocess.run([sys.executable, script, "--help"], cwd=ROOT, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=300)
    return result.stdout + result.stderr


class ReadmeCommandTests(unittest.TestCase):
    def test_readme_documents_runnable_commands(self) -> None:
        self.assertGreater(len(_commands()), 5)

    def test_scripts_exist(self) -> None:
        missing = sorted({script for script, _ in _commands() if not (ROOT / script).is_file()})
        self.assertEqual(missing, [])

    def test_documented_flags_exist(self) -> None:
        try:
            import torch  # noqa: F401  (most scripts import torch at module level)
        except ImportError:
            self.skipTest("PyTorch not installed")
        unknown = []
        for script, flags in _commands():
            if not flags:  # nothing to check, and scripts without argparse would run on --help
                continue
            help_text = _help(script)
            unknown += [f"{script} {flag}" for flag in flags if flag not in help_text and flag != "--help"]
        self.assertEqual(unknown, [])


if __name__ == "__main__":
    unittest.main()
