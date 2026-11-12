"""Console output helpers for ASTRA command-line scripts."""

from __future__ import annotations

import sys
from typing import TextIO


def _is_utf8(stream: TextIO) -> bool:
    return (getattr(stream, "encoding", "") or "").lower().replace("-", "").replace("_", "") == "utf8"


def ensure_utf8_stdio() -> None:
    """Make print() safe for the scripts' non-ASCII output (✓, ─, │, ×, ±).

    On Windows, redirected stdout/stderr use the ANSI code page (cp1252), which cannot
    encode these characters, so a script run as ``python train.py > train.log`` crashed
    with UnicodeEncodeError before training started. Streams are switched to UTF-8 and
    unencodable characters are replaced. Streams that cannot be reconfigured (e.g.
    io.StringIO in tests) are left alone.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None or _is_utf8(stream):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass
