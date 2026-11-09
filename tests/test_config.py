"""astra.config: path resolution and environment overrides."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from astra.config import PROJECT_ROOT, get_paths


class ConfigDefaultsTests(unittest.TestCase):
    def test_defaults_are_inside_the_repository(self) -> None:
        paths = get_paths(env={})
        root = PROJECT_ROOT.resolve()
        self.assertEqual(paths.project_root, root)
        self.assertEqual(paths.phase6_root, root / "data" / "phase6")
        self.assertEqual(paths.processed_dir, root / "data" / "phase6" / "processed")
        self.assertEqual(paths.splits_dir, root / "data" / "phase6" / "splits")
        self.assertEqual(paths.models_dir, root / "models" / "saved")
        self.assertEqual(paths.output_dir, root / "outputs")
        self.assertEqual(paths.lightkurve_cache, Path.home() / ".lightkurve" / "cache")

    def test_no_default_points_at_a_developer_machine(self) -> None:
        for value in vars(get_paths(env={})).values():
            self.assertNotIn("soumyadebtripathy", str(value))


class ConfigOverrideTests(unittest.TestCase):
    def test_phase6_root_override_moves_processed_and_splits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = get_paths(env={"ASTRA_PHASE6_ROOT": tmp})
            self.assertEqual(paths.processed_dir, Path(tmp) / "processed")
            self.assertEqual(paths.splits_dir, Path(tmp) / "splits")

    def test_relative_overrides_resolve_against_the_repository_root(self) -> None:
        paths = get_paths(env={"ASTRA_PROCESSED_DIR": "astra-platform/data/processed"})
        self.assertEqual(paths.processed_dir, PROJECT_ROOT.resolve() / "astra-platform" / "data" / "processed")

    def test_specific_overrides_win_over_phase6_root(self) -> None:
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            paths = get_paths(env={"ASTRA_PHASE6_ROOT": a, "ASTRA_SPLITS_DIR": b})
            self.assertEqual(paths.splits_dir, Path(b))
            self.assertEqual(paths.processed_dir, Path(a) / "processed")

    def test_empty_override_falls_back_to_default(self) -> None:
        self.assertEqual(get_paths(env={"ASTRA_OUTPUT_DIR": ""}).output_dir, PROJECT_ROOT.resolve() / "outputs")

    def test_output_helper_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = get_paths(env={"ASTRA_OUTPUT_DIR": tmp})
            target = paths.output("reports", "calibration.md")
            self.assertEqual(target, Path(tmp) / "reports" / "calibration.md")
            self.assertTrue(target.parent.is_dir())

    def test_model_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = get_paths(env={"ASTRA_MODELS_DIR": tmp})
            self.assertEqual(paths.model("best.pt"), Path(tmp) / "best.pt")


if __name__ == "__main__":
    unittest.main()
