#!/usr/bin/env python3
"""Rebuild the Phase 6 working layout from the files shipped in this repository.

A fresh clone contains the frozen dataset, but not in the layout the training and
evaluation scripts expect (data/phase6/{processed,splits}):

- processed arrays and metadata:  astra-platform/data/processed/TIC_*/
- dataset manifest (hash-locked): astra-platform/data/scientific_dataset_freeze_v2.csv
- frozen split ids:               docs/engineering-log/phase6_{train,val,test}_ids.json
- split metadata:                 astra-platform/data/artifacts/dataset_audit.json

Every step is verified against the published SHA256 values before anything is used.

Usage:
    python pipeline/prepare_from_repo.py --verify-only   # check the shipped files
    python pipeline/prepare_from_repo.py                 # build data/phase6 (verified)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from astra.config import get_paths, resolve_cli_path  # noqa: E402
from pipeline.dataset_audit import run_audit  # noqa: E402
from pipeline.phase6_utils import sha256_file  # noqa: E402

SHIPPED_PROCESSED = PROJECT_ROOT / "astra-platform" / "data" / "processed"
SHIPPED_MANIFEST = PROJECT_ROOT / "astra-platform" / "data" / "scientific_dataset_freeze_v2.csv"
SHIPPED_SPLIT_IDS = PROJECT_ROOT / "docs" / "engineering-log"
SHIPPED_AUDIT = PROJECT_ROOT / "astra-platform" / "data" / "artifacts" / "dataset_audit.json"

# Published in README.md and models/saved/experiment_metadata.json.
EXPECTED_MANIFEST_SHA256 = "f99b4b06f16952033b5445bb0682d059e9ea4c3f99320a05d31aebb25c2dbf58"

EXPECTED_SPLIT_FILE_SHA256 = {
    "train": "5a9bf6c6ad40757a52d0f4a044626e82a4876839b175f5070fb28834c815eed0",
    "val": "c733ab95c4a22ebc29ca123b2e923c8b8069933ccdff2e9f03a3fdc882f761b3",
    "test": "2b62970d610f66f12711b6d9594305b33961a04d17c48807bd6123562350f4c0",
}
EXPECTED_SPLIT_HASH = "ebcdc44c3dba849579675369b1559c77e50b6fead06abd40d3fc187425a7d4e4"
SPLITS = ("train", "val", "test")

# Manifest column -> file name inside each TIC_* directory.
HASHED_FILES = {
    "flux_1000_hash": "flux_1000.npy",
    "flux_200_hash": "flux_200.npy",
    "folded_flux_1000_hash": "folded_flux_1000.npy",
    "folded_flux_200_hash": "folded_flux_200.npy",
    "metadata_hash": "metadata.json",
}


def read_manifest(manifest: Path) -> list[dict[str, str]]:
    with manifest.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify_manifest_file(manifest: Path, expected_sha256: str = EXPECTED_MANIFEST_SHA256) -> list[str]:
    """The manifest itself must match its published hash."""
    if not manifest.is_file():
        return [f"manifest missing: {manifest}"]
    actual = sha256_file(manifest)
    return [] if actual == expected_sha256 else [f"manifest hash mismatch: {actual}"]


def verify_processed(manifest: Path, processed_dir: Path) -> list[str]:
    """Every star in the manifest must exist with byte-identical arrays and metadata."""
    errors: list[str] = []
    rows = read_manifest(manifest)
    for row in rows:
        star = processed_dir / f"TIC_{row['tic_id']}"
        if not star.is_dir():
            errors.append(f"{star.name}: missing directory")
            continue
        for column, filename in HASHED_FILES.items():
            path = star / filename
            if not path.is_file():
                errors.append(f"{star.name}/{filename}: missing")
            elif sha256_file(path) != row[column]:
                errors.append(f"{star.name}/{filename}: hash mismatch")
    return errors


def compute_split_hash(split_ids: dict[str, list[str]]) -> str:
    """Same algorithm as pipeline/freeze_phase6_splits.py (train, val, calibration, test)."""
    hasher = hashlib.sha256()
    for split in ("train", "val", "calibration", "test"):
        hasher.update(json.dumps(split_ids.get(split, [])).encode("utf-8"))
    return hasher.hexdigest()


def build_splits(
    target: Path,
    ids_dir: Path = SHIPPED_SPLIT_IDS,
    audit_json: Path = SHIPPED_AUDIT,
    expected_file_sha256: dict[str, str] | None = None,
    expected_split_hash: str = EXPECTED_SPLIT_HASH,
) -> list[str]:
    """Write <target>/{train,val,test,calibration}_ids.json and split_metadata.json.

    The id files are byte-for-byte copies of the shipped phase6_*_ids.json files, so their
    published hashes still hold. Nothing is written unless every check passes.
    """
    expected_file_sha256 = expected_file_sha256 or EXPECTED_SPLIT_FILE_SHA256
    errors: list[str] = []
    sources = {split: ids_dir / f"phase6_{split}_ids.json" for split in SPLITS}
    for split, path in sources.items():
        if not path.is_file():
            errors.append(f"{path.name}: missing")
        elif sha256_file(path) != expected_file_sha256[split]:
            errors.append(f"{path.name}: hash mismatch")
    if errors:
        return errors

    split_ids = {split: json.loads(path.read_text(encoding="utf-8")) for split, path in sources.items()}
    split_ids["calibration"] = []  # the frozen split has no calibration set (calibration_size 0)
    metadata = json.loads(audit_json.read_text(encoding="utf-8"))["split_metadata"]
    recomputed = compute_split_hash(split_ids)
    if recomputed != metadata.get("split_hash") or recomputed != expected_split_hash:
        return [f"split hash mismatch: recomputed {recomputed}, metadata {metadata.get('split_hash')}"]
    for split in SPLITS:
        if metadata.get(f"{split}_size") != len(split_ids[split]):
            errors.append(f"{split}: size {len(split_ids[split])} != metadata {metadata.get(f'{split}_size')}")
    if errors:
        return errors

    target.mkdir(parents=True, exist_ok=True)
    for split, path in sources.items():
        (target / f"{split}_ids.json").write_bytes(path.read_bytes())
    (target / "calibration_ids.json").write_bytes(b"[]")
    (target / "split_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return []


@dataclass
class Sources:
    """Where the shipped dataset lives and the hashes it must match."""

    processed: Path = SHIPPED_PROCESSED
    manifest: Path = SHIPPED_MANIFEST
    split_ids: Path = SHIPPED_SPLIT_IDS
    audit: Path = SHIPPED_AUDIT
    manifest_sha256: str = EXPECTED_MANIFEST_SHA256
    split_file_sha256: dict[str, str] = field(default_factory=lambda: dict(EXPECTED_SPLIT_FILE_SHA256))
    split_hash: str = EXPECTED_SPLIT_HASH


def verify_sources(sources: Sources) -> list[str]:
    errors = verify_manifest_file(sources.manifest, sources.manifest_sha256)
    return errors or verify_processed(sources.manifest, sources.processed)


def prepare(target: Path, sources: Sources | None = None, force: bool = False) -> list[str]:
    """Build <target>/{processed, splits, audits} and the manifest copy. Returns errors."""
    sources = sources or Sources()
    errors = verify_sources(sources)
    if errors:
        return errors
    processed = target / "processed"
    if processed.exists() and any(processed.iterdir()):
        if not force:
            return [f"{processed} already exists (use --force to replace it)"]
        shutil.rmtree(processed)
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(sources.processed, processed)
    shutil.copy2(sources.manifest, target / sources.manifest.name)

    errors = verify_processed(target / sources.manifest.name, processed)
    errors += build_splits(target / "splits", sources.split_ids, sources.audit,
                           sources.split_file_sha256, sources.split_hash)
    if errors:
        return errors

    # Raw light curves are not shipped; the processed files were verified against the manifest.
    status = run_audit(target, stage=0, require_raw=False)
    if status["overall_status"] != "PASS":
        return [f"dataset audit failed with {status['error_count']} error(s); see {target / 'audits'}"]
    return []


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--verify-only", action="store_true", help="Only verify the shipped files")
    parser.add_argument("--target", type=str, default=None,
                        help="Phase 6 root to build (default: configured phase6 root, data/phase6)")
    parser.add_argument("--force", action="store_true", help="Replace an existing processed/ directory")
    return parser


def _report(errors: list[str]) -> int:
    for error in errors[:20]:
        print(f"FAIL {error}")
    print(f"{len(errors)} problem(s) found.")
    return 1


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    sources = Sources()
    n = len(read_manifest(sources.manifest)) if sources.manifest.is_file() else 0
    if args.verify_only:
        errors = verify_sources(sources)
        if errors:
            return _report(errors)
        print(f"OK   manifest {EXPECTED_MANIFEST_SHA256[:12]}... and {n} stars x {len(HASHED_FILES)} files verified")
        return 0

    target = resolve_cli_path(args.target, get_paths().phase6_root)
    errors = prepare(target, sources, force=args.force)
    if errors:
        return _report(errors)
    print(f"OK   {n} verified stars in {target / 'processed'}")
    print(f"OK   frozen splits rebuilt in {target / 'splits'} (split hash {EXPECTED_SPLIT_HASH[:12]}...)")
    print(f"OK   dataset audit PASS (raw light curves not shipped) in {target / 'audits'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
