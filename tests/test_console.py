"""astra.console.ensure_utf8_stdio: scripts must not crash when their output is redirected."""

from __future__ import annotations

import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra.console import ensure_utf8_stdio

ROOT = Path(__file__).resolve().parent.parent


class EnsureUtf8StdioTests(unittest.TestCase):
    def test_cp1252_stream_is_switched_to_utf8(self) -> None:
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252")
        with patch.object(sys, "stdout", stream), patch.object(sys, "stderr", stream):
            ensure_utf8_stdio()
            print("│ ✓ ─", file=sys.stdout)
            sys.stdout.flush()
        self.assertEqual(raw.getvalue().decode("utf-8").strip(), "│ ✓ ─")

    def test_streams_without_reconfigure_are_left_alone(self) -> None:
        buffer = io.StringIO()
        with patch.object(sys, "stdout", buffer):
            ensure_utf8_stdio()
            print("✓")
        self.assertEqual(buffer.getvalue(), "✓\n")

    def test_redirected_script_output_survives_a_legacy_code_page(self) -> None:
        # A child process whose stdout is a file in cp1252 (the Windows default when redirected).
        code = "import sys; sys.path.insert(0, r'%s'); " % ROOT
        code += "from astra.console import ensure_utf8_stdio; ensure_utf8_stdio(); print('Epoch │ ✓')"
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "out.log"
            with log.open("wb") as out:
                result = subprocess.run([sys.executable, "-c", code], stdout=out, stderr=subprocess.PIPE,
                                        env={"PYTHONIOENCODING": "cp1252", "SYSTEMROOT": _systemroot()})
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
            self.assertEqual(log.read_bytes().decode("utf-8").strip(), "Epoch │ ✓")


def _systemroot() -> str:
    import os

    return os.environ.get("SYSTEMROOT", "")


if __name__ == "__main__":
    unittest.main()
