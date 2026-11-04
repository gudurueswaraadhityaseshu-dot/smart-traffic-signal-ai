"""Automatic checks for the detection helpers (no YOLO model needed)."""

import os
import tempfile
import unittest

import cv2
import numpy as np

from src.detection.detector import count_by_type, draw_detections
from src.detection.video_utils import (
    analyse_frames,
    decode_image,
    find_local_file,
    read_frames,
)


def make_detection(label="car", box=(5, 5, 30, 30)):
    return {"class_id": 2, "label": label, "confidence": 0.9, "box": box}


class FakeDetector:
    """Returns a different number of cars for each frame it is given."""

    def __init__(self, counts):
        self.counts = counts
        self.calls = 0

    def detect(self, frame, confidence):
        n = self.counts[self.calls]
        self.calls += 1
        return [make_detection() for _ in range(n)], 0.01


class TestDetectionUtils(unittest.TestCase):
    def test_count_by_type(self):
        detections = [make_detection("car"), make_detection("car"), make_detection("bus")]
        self.assertEqual(count_by_type(detections), {"car": 2, "bus": 1})
        self.assertEqual(count_by_type([]), {})

    def test_draw_detections_keeps_shape_and_original(self):
        frame = np.zeros((100, 120, 3), dtype=np.uint8)
        annotated = draw_detections(frame, [make_detection()])
        self.assertEqual(annotated.shape, frame.shape)
        self.assertEqual(int(frame.sum()), 0)       # original untouched
        self.assertGreater(int(annotated.sum()), 0)  # copy has boxes drawn

    def test_analyse_frames_uses_median_count(self):
        frames = [np.zeros((50, 50, 3), dtype=np.uint8) for _ in range(3)]
        result = analyse_frames(FakeDetector([2, 4, 3]), frames, 0.35)
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["per_frame_counts"], [2, 4, 3])
        self.assertEqual(result["type_counts"], {"car": 3})
        self.assertAlmostEqual(result["avg_inference_ms"], 10.0, places=3)
        self.assertAlmostEqual(result["fps"], 100.0, places=3)

    def test_analyse_frames_with_no_frames(self):
        self.assertIsNone(analyse_frames(FakeDetector([]), [], 0.35))

    def test_decode_image(self):
        frame = np.full((40, 60, 3), 128, dtype=np.uint8)
        ok, encoded = cv2.imencode(".png", frame)
        self.assertTrue(ok)
        decoded = decode_image(encoded.tobytes())
        self.assertEqual(decoded.shape, (40, 60, 3))
        self.assertIsNone(decode_image(b"this is not an image"))

    def test_read_frames_samples_evenly(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "test.avi")
            writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
            for i in range(30):
                writer.write(np.full((48, 64, 3), i * 8, dtype=np.uint8))
            writer.release()

            self.assertEqual(len(read_frames(path, 5)), 5)
            self.assertEqual(read_frames(os.path.join(folder, "missing.avi"), 5), [])

    def test_find_local_file_returns_none_when_missing(self):
        self.assertIsNone(find_local_file("NoSuchRoadName"))


if __name__ == "__main__":
    unittest.main()