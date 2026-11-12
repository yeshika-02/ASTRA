"""The cross-validation protocol cannot leak (SP-21, ADR-0062).

Synthetic stars only, no training: an injected fake trainer stands in for the network.
- No frozen test star enters any fold.
- No duplicate group (same TIC id or within 2 arcsec) is split across train / selection / test.
- The reported score is the outer fold's, never the selection set's.
"""

from __future__ import annotations

import unittest

import numpy as np

from training import cross_validate as cv


def synthetic_samples(n_per_class: int = 12, duplicates: int = 6) -> list[dict]:
    """Stars on a coarse sky grid; the last `duplicates` stars sit 1 arcsec from an earlier star of the same class."""
    samples = []
    for i in range(5 * n_per_class):
        samples.append({"tic_id": f"TIC_{1000 + i}", "label": i % 5, "ra": 10.0 + i, "dec": -5.0,
                        "period_source": "catalog" if i % 2 else "BLS"})
    for k in range(duplicates):
        twin = samples[k]
        samples.append({"tic_id": f"TIC_{9000 + k}", "label": twin["label"], "ra": twin["ra"] + 1 / 3600,
                        "dec": twin["dec"], "period_source": twin["period_source"]})
    return samples


class PoolAndGroupTests(unittest.TestCase):
    def test_test_stars_are_removed_from_the_pool(self) -> None:
        samples = synthetic_samples()
        test_ids = {"TIC_1000", "TIC_1001", "TIC_1002"}
        pool = cv.cv_pool(samples, test_ids)
        self.assertEqual(len(pool), len(samples) - 3)
        self.assertFalse({s["tic_id"] for s in pool} & test_ids)

    def test_missing_test_id_file_is_refused(self) -> None:
        with self.assertRaisesRegex(FileNotFoundError, "must exclude the test stars"):
            cv.read_test_ids("definitely/not/here/test_ids.json")

    def test_duplicates_share_a_group(self) -> None:
        samples = synthetic_samples(duplicates=6)
        groups = cv.duplicate_groups(samples)
        self.assertEqual(len(set(groups)), len(samples) - 6)
        for k in range(6):
            self.assertEqual(groups[k], groups[-6 + k], f"TIC_{9000 + k} not grouped with its twin")


class PlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.samples = synthetic_samples()
        self.labels = np.array([s["label"] for s in self.samples])
        self.groups = cv.duplicate_groups(self.samples)
        self.plans = cv.plan_folds(self.labels, self.groups, seeds=[1, 2, 3], n_folds=3, inner_folds=3)

    def test_no_group_straddles_and_folds_cover_the_pool(self) -> None:
        cv.check_plans(self.plans, self.groups, len(self.samples))  # raises on any leak
        for plan in self.plans:
            parts = [set(self.groups[idx]) for idx in (plan.train_idx, plan.select_idx, plan.test_idx)]
            self.assertFalse(parts[0] & parts[1] or parts[0] & parts[2] or parts[1] & parts[2])
            self.assertGreater(len(plan.select_idx), 0)

    def test_check_plans_catches_leaks(self) -> None:
        plan = self.plans[0]
        straddle = cv.FoldPlan(plan.seed, plan.fold, np.append(plan.train_idx, plan.test_idx[0]),
                               plan.select_idx, plan.test_idx)
        with self.assertRaisesRegex(AssertionError, "share stars"):
            cv.check_plans([straddle], self.groups, len(self.samples))
        twin, original = len(self.samples) - 6, 0  # same duplicate group
        split_group = cv.FoldPlan(1, 0, np.array([original]), np.array([5]), np.array([twin]))
        with self.assertRaisesRegex(AssertionError, "straddles"):
            cv.check_plans([split_group], self.groups, len(self.samples))
        with self.assertRaisesRegex(AssertionError, "cover every pool star"):
            cv.check_plans([plan], self.groups, len(self.samples))  # one fold of a seed is not a full cover


class ReportedScoreTests(unittest.TestCase):
    def test_score_is_the_outer_folds_and_the_trainer_never_sees_it(self) -> None:
        samples = synthetic_samples()
        labels = np.array([s["label"] for s in samples])
        groups = cv.duplicate_groups(samples)
        plans = cv.plan_folds(labels, groups, seeds=[7], n_folds=3, inner_folds=3)
        seen: list[set[str]] = []

        def memorising_trainer(train_samples, select_samples):
            # Perfect on everything it was shown (it memorises), predicts class 0 for anything new.
            known = {s["tic_id"]: s["label"] for s in train_samples + select_samples}
            seen.append(set(known))
            predict = lambda batch: [known.get(s["tic_id"], 0) for s in batch]  # noqa: E731
            return predict, {"selection_accuracy": 1.0, "best_epoch": 3}

        results = cv.run_plans(samples, plans, memorising_trainer)
        for plan, result, shown in zip(plans, results, seen):
            test_ids = {samples[i]["tic_id"] for i in plan.test_idx}
            self.assertFalse(shown & test_ids, "the trainer saw outer-test stars")
            expected = float(np.mean(labels[plan.test_idx] == 0))  # only class-0 stars are right
            self.assertAlmostEqual(result["accuracy"], expected)
            self.assertLess(result["accuracy"], 0.5)
            self.assertEqual(result["selection_accuracy"], 1.0)  # recorded, but not the score
            self.assertEqual(set(result["test_tic_ids"]), test_ids)

    def test_summary_uses_out_of_fold_predictions(self) -> None:
        samples = synthetic_samples()
        labels = np.array([s["label"] for s in samples])
        groups = cv.duplicate_groups(samples)
        plans = cv.plan_folds(labels, groups, seeds=[1, 2], n_folds=3, inner_folds=3)

        def perfect(train_samples, select_samples):
            return (lambda batch: [s["label"] for s in batch]), {"selection_accuracy": 0.9, "best_epoch": 1}

        summary = cv.summarise(cv.run_plans(samples, plans, perfect), n_resamples=50)
        self.assertEqual(summary["mean_fold_accuracy"], 1.0)
        self.assertEqual(set(summary["per_seed"]), {"1", "2"})
        self.assertEqual(summary["per_seed"]["1"]["accuracy_ci95"], [1.0, 1.0])
        self.assertAlmostEqual(summary["mean_selection_accuracy"], 0.9)


if __name__ == "__main__":
    unittest.main()
