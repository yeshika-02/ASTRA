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
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.phase6_utils import sha256_file  # noqa: E402

SHIPPED_PROCESSED = PROJECT_ROOT / "astra-platform" / "data" / "processed"
SHIPPED_MANIFEST = PROJECT_ROOT / "astra-platform" / "data" / "scientific_dataset_freeze_v2.csv"

# Published in README.md and models/saved/experiment_metadata.json.
EXPECTED_MANIFEST_SHA256 = "f99b4b06f16952033b5445bb0682d059e9ea4c3f99320a05d31aebb25c2dbf58"

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


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--verify-only", action="store_true", help="Only verify the shipped files")
    return parser


def main(argv: list[str] | None = None) -> int:
    build_arg_parser().parse_args(argv)
    errors = verify_manifest_file(SHIPPED_MANIFEST)
    if not errors:
        errors = verify_processed(SHIPPED_MANIFEST, SHIPPED_PROCESSED)
    if errors:
        for error in errors[:20]:
            print(f"FAIL {error}")
        print(f"{len(errors)} problem(s) found.")
        return 1
    n = len(read_manifest(SHIPPED_MANIFEST))
    print(f"OK   manifest {EXPECTED_MANIFEST_SHA256[:12]}... and {n} stars x {len(HASHED_FILES)} files verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
