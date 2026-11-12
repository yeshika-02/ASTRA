"""Provenance for experiment records: code version, environment, seed and data hashes.

Every training or evaluation record should say exactly which code, which software and
which data produced it. ``collect()`` gathers that in one dictionary; missing tools
(no git, a package not installed) give ``None`` rather than an error.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRACKED_PACKAGES = ("torch", "numpy", "scipy", "scikit-learn", "pandas", "onnxruntime", "onnx", "lightkurve", "astropy")
SPLITS = ("train", "val", "test")


def _git(args: list[str], project_root: Path) -> str | None:
    try:
        result = subprocess.run(["git", *args], cwd=project_root, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def git_info(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Commit SHA, branch and whether tracked files differ from that commit."""
    commit = _git(["rev-parse", "HEAD"], project_root)
    if commit is None:
        return {"commit": None, "branch": None, "dirty": None}
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], project_root)
    status = _git(["status", "--porcelain", "--untracked-files=no"], project_root)
    return {
        "commit": commit,
        "branch": None if branch in (None, "HEAD") else branch,
        "dirty": None if status is None else bool(status),
    }


def package_versions(packages: tuple[str, ...] = TRACKED_PACKAGES) -> dict[str, str | None]:
    versions = {}
    for name in packages:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def environment() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "executable": Path(sys.executable).name,
        "packages": package_versions(),
    }


def file_sha256(path: Path) -> str | None:
    path = Path(path)
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def data_fingerprint(manifest: Path, splits_dir: Path | None) -> dict[str, Any]:
    """Hashes of the dataset manifest, the frozen split files and the recorded split hash.

    Pass ``splits_dir=None`` when no frozen split files were used (a random split): the
    split fields are then ``None`` rather than describing files the run never read.
    """
    if splits_dir is None:
        return {"manifest_sha256": file_sha256(manifest), "split_hash": None, "split_file_sha256": None}
    split_hash = None
    meta_path = Path(splits_dir) / "split_metadata.json"
    if meta_path.is_file():
        try:
            split_hash = json.loads(meta_path.read_text(encoding="utf-8")).get("split_hash")
        except (OSError, json.JSONDecodeError):
            split_hash = None
    return {
        "manifest_sha256": file_sha256(manifest),
        "split_hash": split_hash,
        "split_file_sha256": {split: file_sha256(Path(splits_dir) / f"{split}_ids.json") for split in SPLITS},
    }


def collect(
    seed: int | None = None,
    data: dict[str, Any] | None = None,
    device: str | None = None,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Everything needed to say which code, software, settings and data produced a result."""
    return {
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "git": git_info(project_root),
        "environment": environment(),
        "device": device,
        "seed": seed,
        "data": data,
    }
