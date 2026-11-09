"""models/published_weights.json and training/verify_weights.py (SP-14).

The manifest is the single list of published artifact hashes. It must agree with every
other place the repository records them, and the shipped artifacts must match it.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from training.verify_weights import (
    MATCH,
    MISMATCH,
    MISSING,
    NO_HASH,
    find_published,
    load_manifest,
    main,
    verify,
)

ROOT = Path(__file__).resolve().parent.parent


def _by_name() -> dict[str, dict]:
    return {entry["filename"]: entry for entry in load_manifest()}


class ManifestConsistencyTests(unittest.TestCase):
    def test_checkpoint_hashes_match_the_platform_registry(self) -> None:
        ts = (ROOT / "astra-platform/src/lib/data/constants.ts").read_text(encoding="utf-8")
        registry = dict(re.findall(r"filename: '([^']+\.pt)'.*?sha256: '([0-9a-f]{64})'", ts))
        manifest = {name: e["sha256"] for name, e in _by_name().items() if e["kind"] == "pytorch_checkpoint"}
        self.assertEqual(manifest, registry)

    def test_production_checkpoint_matches_the_inference_contract(self) -> None:
        ts = (ROOT / "astra-platform/src/lib/server/inference.ts").read_text(encoding="utf-8")
        expected = re.search(r"EXPECTED_CHECKPOINT_SHA256 =\s*'([0-9a-f]{64})'", ts).group(1)
        self.assertEqual(_by_name()["best_star_transformer_shared.pt"]["sha256"], expected)

    def test_hashes_match_model_registry_json(self) -> None:
        registry = json.loads((ROOT / "astra-platform/data/artifacts/model_registry.json").read_text(encoding="utf-8"))
        manifest = _by_name()
        # The registry also lists 4 pilot *_smoke.pt checkpoints; they back no reported result.
        published = [c for c in registry["checkpoints"] if not c["filename"].endswith("_smoke.pt")]
        self.assertEqual(len(published), 9)
        for checkpoint in published:
            self.assertEqual(manifest[checkpoint["filename"]]["sha256"], checkpoint["sha256"], checkpoint["filename"])
        active = registry["active_model"]
        self.assertEqual(manifest["best_star_transformer_shared.onnx"]["sha256"], active["onnx_hash"])
        self.assertEqual(manifest["best_star_transformer_shared.onnx.data"]["sha256"], active["onnx_data_hash"])
        self.assertEqual(manifest["optimal_temperature_transformer_shared.txt"]["sha256"], active["temperature_hash"])

    def test_experiment_metadata_records_the_same_checkpoints(self) -> None:
        hashes = {e["sha256"] for e in load_manifest() if e["kind"] == "pytorch_checkpoint"}
        for path in sorted((ROOT / "models/saved").glob("experiment_metadata_*.json")):
            recorded = json.loads(path.read_text(encoding="utf-8")).get("checkpoint_sha256")
            if recorded:
                self.assertIn(recorded, hashes, path.name)

    def test_shipped_artifacts_match_the_manifest(self) -> None:
        for entry in load_manifest():
            if entry.get("shipped_path") and entry.get("sha256"):
                data = (ROOT / entry["shipped_path"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"], entry["filename"])

    def test_weights_are_not_in_the_repository(self) -> None:
        # Recorded as a fact (SP-14); update this test when weights are published.
        for entry in load_manifest():
            if entry["kind"] in ("pytorch_checkpoint", "onnx_external_data"):
                self.assertIsNone(entry["shipped_path"], entry["filename"])


class VerifyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        good = b"published bytes"
        self.manifest = [
            {"filename": "good.pt", "kind": "pytorch_checkpoint", "sha256": hashlib.sha256(good).hexdigest()},
            {"filename": "bad.pt", "kind": "pytorch_checkpoint", "sha256": "0" * 64},
            {"filename": "absent.pt", "kind": "pytorch_checkpoint", "sha256": "1" * 64},
            {"filename": "nohash.onnx.data", "kind": "onnx_external_data", "sha256": None},
        ]
        (self.dir / "good.pt").write_bytes(good)
        (self.dir / "bad.pt").write_bytes(b"retrained, different bytes")
        (self.dir / "nohash.onnx.data").write_bytes(b"x")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_statuses(self) -> None:
        statuses = {c.filename: c.status for c in verify(self.dir, self.manifest, project_root=self.dir)}
        self.assertEqual(statuses, {"good.pt": MATCH, "bad.pt": MISMATCH, "absent.pt": MISSING,
                                    "nohash.onnx.data": NO_HASH})

    def test_shipped_copy_is_used_when_models_dir_lacks_the_file(self) -> None:
        shipped = self.dir / "shipped"
        shipped.mkdir()
        (shipped / "graph.onnx").write_bytes(b"graph")
        manifest = [{"filename": "graph.onnx", "kind": "onnx_graph", "sha256": hashlib.sha256(b"graph").hexdigest(),
                     "shipped_path": "shipped/graph.onnx"}]
        (check,) = verify(self.dir / "empty", manifest, project_root=self.dir)
        self.assertEqual((check.status, check.path), (MATCH, shipped / "graph.onnx"))

    def test_find_published(self) -> None:
        self.assertEqual(find_published("best_star_transformer_shared.pt")["parameters"], 1373701)
        self.assertIsNone(find_published("my_retrained_model.pt"))


class VerifyCliTests(unittest.TestCase):
    def test_this_checkout_has_no_mismatches(self) -> None:
        with redirect_stdout(io.StringIO()) as out:
            code = main([])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("match", out.getvalue())

    def test_requiring_a_missing_checkpoint_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--models-dir", tmp, "--require", "best_star_transformer_shared.pt"]), 1)

    def test_unknown_required_name_fails(self) -> None:
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--require", "not_a_published_file.pt"]), 1)


if __name__ == "__main__":
    unittest.main()
