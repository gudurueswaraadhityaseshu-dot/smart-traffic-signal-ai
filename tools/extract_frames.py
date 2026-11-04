"""Save evenly spaced frames from a video as JPG files, ready for labelling.

Usage (from the project root, with the venv active):
    python -m tools.extract_frames videos/north.mp4 eval_images 20
"""

import os
import sys

import cv2

from src.detection.video_utils import read_frames


def main(argv: list) -> int:
    if len(argv) != 4:
        print("Usage: python -m tools.extract_frames <video> <output_folder> <number_of_frames>")
        return 1

    video, folder, count_text = argv[1], argv[2], argv[3]
    try:
        count = int(count_text)
    except ValueError:
        print("The number of frames must be a whole number, for example 20.")
        return 1

    frames = read_frames(video, count)
    if not frames:
        print(f"Could not read any frames from {video}.")
        return 1

    os.makedirs(folder, exist_ok=True)
    base = os.path.splitext(os.path.basename(video))[0]
    for index, frame in enumerate(frames):
        cv2.imwrite(os.path.join(folder, f"{base}_{index:03d}.jpg"), frame)
    print(f"Saved {len(frames)} frames to {folder}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))