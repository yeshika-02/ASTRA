"""
ASTRA — verify model artifacts against the published hashes.

Checks every file listed in models/published_weights.json: files shipped in the
repository at their shipped path, and recovered or retrained weights in the models
directory (models/saved, or ASTRA_MODELS_DIR / --models-dir). A file is only trusted
as a published artifact when its SHA256 matches the manifest.

Exit code: 0 when nothing mismatches (missing files are reported, not failures),
1 when a file mismatches or a --require'd file is missing or unverified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from astra.config import get_paths, resolve_cli_path

MANIFEST_PATH = PROJECT_ROOT / "models" / "published_weights.json"

MATCH = "match"
MISMATCH = "MISMATCH"
MISSING = "missing"
NO_HASH = "present (no published hash)"


@dataclass(frozen=True)
class Check:
    filename: str
    kind: str
    status: str
    path: Path | None
    expected_sha256: str | None
    actual_sha256: str | None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path = MANIFEST_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["files"]


def find_published(filename: str, manifest: list[dict] | None = None) -> dict | None:
    """Manifest entry for a file name, or None when the file is not a published artifact."""
    for entry in manifest if manifest is not None else load_manifest():
        if entry["filename"] == filename:
            return entry
    return None


def check_file(path: Path, entry: dict) -> Check:
    expected = entry.get("sha256")
    if not path.is_file():
        return Check(entry["filename"], entry["kind"], MISSING, None, expected, None)
    actual = sha256_file(path)
    if expected is None:
        status = NO_HASH
    else:
        status = MATCH if actual == expected else MISMATCH
    return Check(entry["filename"], entry["kind"], status, path, expected, actual)


def verify(models_dir: Path, manifest: list[dict] | None = None, project_root: Path = PROJECT_ROOT) -> list[Check]:
    """Check each manifest entry: the copy in models_dir wins, else the shipped copy."""
    checks = []
    for entry in manifest if manifest is not None else load_manifest():
        candidate = models_dir / entry["filename"]
        if not candidate.is_file() and entry.get("shipped_path"):
            candidate = project_root / entry["shipped_path"]
        checks.append(check_file(candidate, entry))
    return checks


def _display(path: Path) -> Path:
    return path.relative_to(PROJECT_ROOT) if path.is_relative_to(PROJECT_ROOT) else path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify model artifacts against models/published_weights.json.")
    parser.add_argument("--models-dir", default=None,
                        help="Directory with recovered weights (default: configured models dir, models/saved)")
    parser.add_argument("--require", action="append", default=[], metavar="FILENAME",
                        help="Fail unless this file is present and matches (repeatable)")
    parser.add_argument("--json", action="store_true", help="Print the results as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    from astra.console import ensure_utf8_stdio
    ensure_utf8_stdio()
    args = build_arg_parser().parse_args(argv)
    models_dir = resolve_cli_path(args.models_dir, get_paths().models_dir)
    checks = verify(models_dir)

    known = {check.filename for check in checks}
    unknown = [name for name in args.require if name not in known]
    if unknown:
        print(f"Not in the manifest: {', '.join(unknown)}")
        return 1

    if args.json:
        print(json.dumps([{**check.__dict__, "path": str(check.path) if check.path else None} for check in checks],
                         indent=2))
    else:
        print(f"Models dir: {models_dir}")
        for check in checks:
            where = f"  ({_display(check.path)})" if check.path else ""
            print(f"  {check.status:<28} {check.filename}{where}")

    failed = [check for check in checks if check.status == MISMATCH]
    failed += [check for check in checks if check.filename in args.require and check.status != MATCH]
    if failed:
        print(f"\nFAILED: {', '.join(sorted({check.filename for check in failed}))}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
