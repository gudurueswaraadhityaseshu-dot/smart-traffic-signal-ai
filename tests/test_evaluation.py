"""Automatic checks for the evaluation code (no YOLO model needed)."""

import unittest

from config import settings
from src.evaluation.detection_eval import (
    average_precision,
    box_iou,
    evaluate_dataset,
    match_image,
    yolo_label_to_boxes,
)
from src.evaluation.traffic_eval import (
    METRICS,
    change_percent,
    compare_scenario,
    run_once,
    summarise,
)

A = (0, 0, 10, 10)
B = (20, 20, 30, 30)
C = (50, 50, 60, 60)
FAR = (100, 100, 110, 110)


def image(preds, gt, elapsed=0.02):
    return {"name": "x", "preds": preds, "gt": gt, "elapsed": elapsed}


class TestDetectionMetrics(unittest.TestCase):
    def test_box_iou(self):
        self.assertAlmostEqual(box_iou(A, A), 1.0)
        self.assertEqual(box_iou(A, FAR), 0.0)
        self.assertAlmostEqual(box_iou((0, 0, 10, 10), (5, 0, 15, 10)), 1 / 3)

    def test_yolo_label_parsing(self):
        text = "2 0.5 0.5 0.2 0.4\nnot a label\n0 0.1 0.1\n\n"
        boxes, ignored = yolo_label_to_boxes(text, 100, 50)
        self.assertEqual(len(boxes), 1)
        self.assertEqual(ignored, 2)
        for got, want in zip(boxes[0], (40, 15, 60, 35)):
            self.assertAlmostEqual(got, want)

    def test_duplicate_detection_is_false_positive(self):
        flags = match_image([(0.9, A), (0.8, FAR), (0.7, A)], [A, B])
        self.assertEqual(flags, [(0.9, True), (0.8, False), (0.7, False)])

    def test_average_precision(self):
        self.assertAlmostEqual(average_precision([(0.9, True), (0.8, True)], 2), 1.0)
        self.assertAlmostEqual(average_precision([(0.9, True), (0.8, False)], 2), 0.5)
        self.assertIsNone(average_precision([(0.9, False)], 0))
        self.assertEqual(average_precision([], 3), 0.0)

    def test_evaluate_dataset_at_two_thresholds(self):
        items = [
            image([(0.9, A), (0.8, B), (0.2, FAR)], [A, B], 0.02),
            image([(0.6, C)], [C], 0.04),
        ]
        strict = evaluate_dataset(items, 0.5)
        self.assertEqual((strict["tp"], strict["fp"], strict["fn"]), (3, 0, 0))
        self.assertAlmostEqual(strict["precision"], 1.0)
        self.assertAlmostEqual(strict["f1"], 1.0)
        self.assertAlmostEqual(strict["count_mae"], 0.0)
        self.assertAlmostEqual(strict["avg_inference_ms"], 30.0)
        self.assertAlmostEqual(strict["fps"], 1000 / 30)

        loose = evaluate_dataset(items, 0.1)
        self.assertEqual((loose["tp"], loose["fp"], loose["fn"]), (3, 1, 0))
        self.assertAlmostEqual(loose["precision"], 0.75)
        self.assertAlmostEqual(loose["f1"], 2 * 0.75 / 1.75)
        self.assertAlmostEqual(loose["accuracy"], 0.75)
        self.assertAlmostEqual(loose["count_mae"], 0.5)
        self.assertAlmostEqual(loose["exact_count_rate"], 0.5)
        self.assertAlmostEqual(loose["ap50"], 1.0)

    def test_dataset_without_real_vehicles(self):
        result = evaluate_dataset([image([(0.9, A)], [])], 0.5)
        self.assertEqual(result["precision"], 0.0)
        self.assertIsNone(result["recall"])
        self.assertIsNone(result["f1"])
        self.assertIsNone(result["ap50"])


class TestTrafficEvaluation(unittest.TestCase):
    def test_change_percent(self):
        self.assertAlmostEqual(change_percent(100, 80, True), 20)
        self.assertAlmostEqual(change_percent(100, 120, True), -20)
        self.assertAlmostEqual(change_percent(10, 12, False), 20)
        self.assertIsNone(change_percent(0, 5, True))

    def test_runs_are_repeatable_and_both_modes_see_same_traffic(self):
        rates = {"North": 9, "East": 5, "South": 2, "West": 0}
        first = run_once("fixed", rates, 7, 600, [])
        again = run_once("fixed", rates, 7, 600, [])
        adaptive = run_once("adaptive", rates, 7, 600, [])
        self.assertEqual(first, again)
        self.assertEqual(first["arrived"], adaptive["arrived"])

    def test_summary_without_ambulances_has_no_emergency_data(self):
        scenario = {"rates": {"North": 4, "East": 4, "South": 4, "West": 4}, "ambulances": []}
        summary = summarise(compare_scenario(scenario, [1, 2], 600))
        self.assertIsNone(summary["emergency_wait"]["fixed"])
        self.assertIsNone(summary["emergency_wait"]["change"])
        self.assertEqual(summary["total_wait"]["compared"], 2)

    def test_every_default_scenario_runs_and_is_consistent(self):
        for name, scenario in settings.SCENARIOS.items():
            runs = compare_scenario(scenario, [1], 600)
            for mode in ("fixed", "adaptive"):
                run = runs[mode][0]
                self.assertLessEqual(run["served"], run["arrived"], name)
                self.assertEqual(run["unserved"], run["arrived"] - run["served"], name)
                self.assertEqual(run["ambulances_passed"], run["ambulances_expected"], name)
                for key, _label, _lower, _fmt in METRICS:
                    self.assertIn(key, run)
            self.assertEqual(runs["fixed"][0]["arrived"], runs["adaptive"][0]["arrived"], name)


if __name__ == "__main__":
    unittest.main()