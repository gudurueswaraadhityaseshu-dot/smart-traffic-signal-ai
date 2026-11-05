"""YOLO vehicle detector, plus helpers to draw boxes and count vehicles.

The ultralytics library is imported inside VehicleDetector.__init__, so the
rest of the project (and the tests) work even if it is not installed.
"""

import time

import numpy as np

try:
    import cv2
except ImportError:  # OpenCV missing: detection is simply unavailable
    cv2 = None

from config import settings

# Box colours in BGR order (OpenCV uses BGR, not RGB).
CLASS_COLOURS = {
    "car": (0, 200, 0),
    "motorcycle": (0, 165, 255),
    "bus": (255, 100, 0),
    "truck": (0, 0, 220),
}


class VehicleDetector:
    """Wraps a pretrained YOLO model and finds vehicles in one frame."""

    def __init__(self, model_name: str = settings.MODEL_NAME):
        from ultralytics import YOLO  # imported here on purpose

        self.model = YOLO(model_name)
        # The first prediction is slower (the model "warms up"), so we do
        # one throwaway prediction now to keep later timings honest.
        blank = np.zeros((settings.DETECTION_IMAGE_SIZE, settings.DETECTION_IMAGE_SIZE, 3), dtype=np.uint8)
        self.model.predict(blank, verbose=False)

    def detect(self, frame, confidence: float):
        """Return (detections, seconds_taken) for one BGR frame.

        Each detection is a dict with: class_id, label, confidence, box.
        """
        start = time.perf_counter()
        results = self.model.predict(
            frame,
            classes=list(settings.VEHICLE_CLASSES.keys()),
            conf=confidence,
            imgsz=settings.DETECTION_IMAGE_SIZE,
            verbose=False,
        )
        elapsed = time.perf_counter() - start

        detections = []
        for box in results[0].boxes:
            class_id = int(box.cls[0])
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            detections.append(
                {
                    "class_id": class_id,
                    "label": settings.VEHICLE_CLASSES.get(class_id, "vehicle"),
                    "confidence": float(box.conf[0]),
                    "box": (x1, y1, x2, y2),
                }
            )
        return detections, elapsed


def count_by_type(detections: list) -> dict:
    """Count detections per vehicle type, e.g. {"car": 5, "bus": 1}."""
    counts = {}
    for detection in detections:
        label = detection["label"]
        counts[label] = counts.get(label, 0) + 1
    return counts


def draw_detections(frame, detections: list):
    """Return a COPY of the frame with a labelled box around every vehicle."""
    annotated = frame.copy()
    width = annotated.shape[1]
    thickness = max(2, width // 400)
    font_scale = max(0.5, width / 1400)

    for detection in detections:
        x1, y1, x2, y2 = detection["box"]
        colour = CLASS_COLOURS.get(detection["label"], (255, 255, 255))
        cv2.rectangle(annotated, (x1, y1), (x2, y2), colour, thickness)

        text = f"{detection['label']} {detection['confidence']:.2f}"
        (text_w, text_h), baseline = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1
        )
        top = max(y1 - text_h - baseline, 0)
        cv2.rectangle(annotated, (x1, top), (x1 + text_w, top + text_h + baseline), colour, -1)
        cv2.putText(
            annotated,
            text,
            (x1, top + text_h),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
    return annotated