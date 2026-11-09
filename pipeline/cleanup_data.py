#!/usr/bin/env python3
"""One-off Phase 5 cleanup of a processed-data folder after a batch re-run.

Keeps star folders listed as successful in a batch log (lines such as
"[57/254] TIC 445190111 (rr_lyrae) ✓"), keeps solar_like folders whose metadata
matches the catalog, and removes the rest (missing/corrupt metadata, class
mismatches, obsolete folders).

Safety: the batch log is required (--log), and nothing is deleted unless --apply is
given. Previously the log path was hard-coded to the original author's machine; when
it was missing the script carried on with an empty list of successful stars and
deleted almost every processed folder.

Usage:
    python pipeline/cleanup_data.py --log path/to/task-912.log            # dry run
    python pipeline/cleanup_data.py --log path/to/task-912.log --apply    # delete
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CATALOG_PATH = DATA_DIR / "catalog_full.json"


def parse_successful_tics(log_text: str) -> set[int]:
    """TIC ids marked successful (✓) in a batch log."""
    return {int(m) for m in re.findall(r"TIC (\S+) \(\S+\) ✓", log_text) if m.isdigit()}


def plan_cleanup(
    processed_dir: pathlib.Path,
    successful_tics: set[int],
    solar_like_tics: set[int],
) -> tuple[list[tuple[pathlib.Path, str]], list[pathlib.Path]]:
    """Return (folders to delete with a reason, folders to keep). Deletes nothing."""
    delete: list[tuple[pathlib.Path, str]] = []
    keep: list[pathlib.Path] = []
    for path in sorted(processed_dir.glob("TIC_*")):
        if not path.is_dir():
            continue
        meta_path = path / "metadata.json"
        if not meta_path.exists():
            delete.append((path, "missing metadata.json"))
            continue
        try:
            meta = json.loads(meta_path.read_text())
            tic = int(meta["tic_id"])
            meta_class = meta["astra_class"]
        except Exception as e:  # any unreadable metadata is treated as corrupt
            delete.append((path, f"corrupt metadata ({e})"))
            continue
        if tic in successful_tics:
            keep.append(path)
        elif tic in solar_like_tics:
            if meta_class == "solar_like":
                keep.append(path)
            else:
                delete.append((path, f"mismatched solar_like (metadata class: {meta_class})"))
        else:
            delete.append((path, f"obsolete directory (class: {meta_class})"))
    return delete, keep


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--log", type=pathlib.Path, required=True, help="Batch log listing successful TICs")
    parser.add_argument("--processed-dir", type=pathlib.Path, default=PROCESSED_DIR)
    parser.add_argument("--catalog", type=pathlib.Path, default=CATALOG_PATH)
    parser.add_argument("--apply", action="store_true", help="Delete folders (default: dry run)")
    args = parser.parse_args(argv)

    if not args.log.is_file():
        parser.error(f"batch log not found: {args.log}")
    if not args.catalog.is_file():
        parser.error(f"catalog not found: {args.catalog}")

    catalog = json.loads(args.catalog.read_text())
    solar_like_tics = {
        e["tic_id"] for e in catalog if e["astra_class"] == "solar_like" and e.get("tic_id") is not None
    }
    successful_tics = parse_successful_tics(args.log.read_text(encoding="utf-8"))
    print(f"{len(solar_like_tics)} solar_like TICs in catalog; {len(successful_tics)} successful TICs in log.")

    delete, keep = plan_cleanup(args.processed_dir, successful_tics, solar_like_tics)
    for path, reason in delete:
        print(f"{'Deleting' if args.apply else 'Would delete'} {path.name}: {reason}")
        if args.apply:
            shutil.rmtree(path)
    mode = "Deleted" if args.apply else "Would delete (dry run, pass --apply)"
    print(f"\nKept: {len(keep)}, {mode}: {len(delete)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
