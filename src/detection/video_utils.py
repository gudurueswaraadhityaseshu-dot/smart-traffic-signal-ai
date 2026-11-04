"""Reading frames from videos and photos, and turning detections into a count."""

import os
import statistics
import tempfile

import cv2
import numpy as np

from config import settings
from src.detection.detector import count_by_type, draw_detections


def shrink(frame, max_width: int = settings.MAX_FRAME_WIDTH):
    """Make very large frames smaller (keeping the shape) to save memory."""
    height, width = frame.shape[:2]
    if width <= max_width:
        return frame
    scale = max_width / width
    return cv2.resize(frame, (max_width, int(height * scale)))


def find_local_file(road: str):
    """Look for videos/<road>.<ext> (e.g. videos/north.mp4). None if missing."""
    for extension in settings.VIDEO_EXTENSIONS + settings.IMAGE_EXTENSIONS:
        path = os.path.join(settings.VIDEO_FOLDER, road.lower() + extension)
        if os.path.isfile(path):
            return path
    return None


def decode_image(data: bytes):
    """Turn the bytes of a JPG/PNG into a frame. Returns None if unreadable."""
    array = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
    return shrink(frame) if frame is not None else None


def read_frames(path: str, max_frames: int) -> list:
    """Read up to max_frames evenly spaced frames from a video file.

    Returns an empty list if the video cannot be opened.
    """
    capture = cv2.VideoCapture(path)
    frames = []
    try:
        if not capture.isOpened():
            return []

        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if total > 0:
            wanted = min(max_frames, total)
            for i in range(wanted):
                capture.set(cv2.CAP_PROP_POS_FRAMES, int(i * total / wanted))
                ok, frame = capture.read()
                if ok:
                    frames.append(shrink(frame))
        else:
            # Frame count unknown: read the start of the video and sample it.
            everything = []
            while len(everything) < 300:
                ok, frame = capture.read()
                if not ok:
                    break
                everything.append(frame)
            wanted = min(max_frames, len(everything))
            for i in range(wanted):
                frames.append(shrink(everything[int(i * len(everything) / wanted)]))
    finally:
        capture.release()
    return frames


def read_frames_from_bytes(data: bytes, suffix: str, max_frames: int) -> list:
    """Same as read_frames, but for a video uploaded through the browser."""
    handle, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(handle, "wb") as file:
            file.write(data)
        return read_frames(path, max_frames)
    finally:
        if os.path.exists(path):
            os.remove(path)


def analyse_frames(detector, frames: list, confidence: float, progress_callback=None):
    """Run the detector on every frame and summarise the road.

    Returns None if there are no frames. Otherwise a dict with:
      count            - median number of vehicles per frame (rounded)
      per_frame_counts - the count in every analysed frame
      type_counts      - cars/buses/... in the representative frame
      annotated        - the representative frame with boxes drawn (BGR)
      avg_inference_ms - average model time per frame
      fps              - 1 / average model time (model only)
    """
    if not frames:
        return None

    per_frame_counts = []
    all_detections = []
    times = []
    for index, frame in enumerate(frames):
        detections, elapsed = detector.detect(frame, confidence)
        all_detections.append(detections)
        per_frame_counts.append(len(detections))
        times.append(elapsed)
        if progress_callback:
            progress_callback(index + 1, len(frames))

    count = int(round(statistics.median(per_frame_counts)))
    best = min(range(len(frames)), key=lambda i: abs(per_frame_counts[i] - count))
    average_time = sum(times) / len(times)

    return {
        "count": count,
        "per_frame_counts": per_frame_counts,
        "type_counts": count_by_type(all_detections[best]),
        "annotated": draw_detections(frames[best], all_detections[best]),
        "frames_analysed": len(frames),
        "avg_inference_ms": average_time * 1000,
        "fps": (1 / average_time) if average_time > 0 else 0.0,
    }