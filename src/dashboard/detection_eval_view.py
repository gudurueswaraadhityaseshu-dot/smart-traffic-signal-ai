"""The Detection Evaluation page: precision, recall, F1, mAP (Stage 5)."""

import os

import pandas as pd
import streamlit as st

from config import settings
from src.dashboard.detection_view import load_detector, yolo_available
from src.detection.video_utils import decode_image
from src.evaluation.detection_eval import evaluate_dataset, yolo_label_to_boxes


def show(value, percent: bool = False, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%" if percent else f"{value:.{digits}f}"


def pair_files(files: list):
    """Match image files with label files that share the same name."""
    images = {}
    labels = {}
    for file in files:
        stem, extension = os.path.splitext(file.name)
        extension = extension.lower()
        if extension in settings.IMAGE_EXTENSIONS:
            images[stem] = file
        elif extension == ".txt":
            labels[stem] = file
    paired = [stem for stem in sorted(images) if stem in labels]
    missing_label = [stem for stem in sorted(images) if stem not in labels]
    return images, labels, paired, missing_label


def render_detection_evaluation_page() -> None:
    st.title("🎯 Vehicle Detection Evaluation")
    st.caption("Measure the YOLO model against images you labelled by hand")

    if not yolo_available():
        st.warning(
            "This page needs the YOLO library, which is not installed on this server. "
            "Run the project on a laptop to evaluate detection (see the README). "
            "Precision, recall, F1 and mAP are only reported when labelled test images "
            "are supplied. Nothing is estimated or invented."
        )
        st.stop()
        
    with st.expander("Read first: what this page can and cannot tell you", expanded=True):
        st.write(
            """
Precision, recall, F1 and mAP can only be calculated by comparing the model
with **real, hand-labelled vehicles**. If you have no labelled images, this page
shows no accuracy numbers, because any number would be invented.

**What you need:** a set of images plus one label file per image, in YOLO format
(a `.txt` file with the same name as the image, one line per vehicle:
`class x_center y_center width height`, all between 0 and 1).

**How to label:** use a free labelling tool such as Roboflow or CVAT, draw a box
around **every** visible vehicle (cars, motorcycles, buses, trucks, including
small, distant and parked ones), then export in **YOLO** format. All vehicle
types are merged into one class called "vehicle". Interfaces change, so follow
the tool's own export instructions.

**How many:** aim for at least 30 images and a few hundred labelled vehicles,
from several different videos or scenes. Frames from one short video are very
similar, so they count for less than they seem.

**An image without a label file is skipped.** A missing file means "unknown",
not "no vehicles". For an image with truly no vehicles, upload an empty `.txt`.
"""
        )

    files = st.file_uploader(
        "Upload images and their label files together",
        type=[e.lstrip(".") for e in settings.IMAGE_EXTENSIONS] + ["txt"],
        accept_multiple_files=True,
    )
    threshold = st.slider(
        "Confidence threshold for precision / recall / F1 / counts",
        0.05, 0.90, settings.DEFAULT_CONFIDENCE, 0.05,
        help="mAP does not depend on this. It uses every detection.",
    )

    if st.button("🔍 Run detection evaluation", type="primary"):
        images, labels, paired, missing_label = pair_files(files or [])
        if not paired:
            st.error(
                "No image/label pairs found. Each image (for example `road1.jpg`) needs a "
                "label file with the same name (`road1.txt`). Without labelled data, "
                "precision, recall and F1 cannot be calculated."
            )
            st.stop()
        try:
            detector = load_detector()
        except Exception as error:
            st.error("The YOLO model could not be loaded.")
            st.code(str(error))
            st.stop()

        items = []
        ignored_lines = 0
        unreadable = []
        progress = st.progress(0.0, text="Starting...")
        for index, stem in enumerate(paired):
            progress.progress(index / len(paired), text=f"Analysing {stem}")
            frame = decode_image(images[stem].getvalue())
            if frame is None:
                unreadable.append(stem)
                continue
            height, width = frame.shape[:2]
            text = labels[stem].getvalue().decode("utf-8", errors="ignore")
            truth, ignored = yolo_label_to_boxes(text, width, height)
            ignored_lines += ignored
            detections, elapsed = detector.detect(frame, settings.EVAL_MIN_CONFIDENCE)
            items.append(
                {
                    "name": stem,
                    "preds": [(d["confidence"], d["box"]) for d in detections],
                    "gt": truth,
                    "elapsed": elapsed,
                }
            )
        progress.progress(1.0, text="Done")
        st.session_state.detection_eval = {
            "items": items,
            "ignored_lines": ignored_lines,
            "unreadable": unreadable,
            "missing_label": missing_label,
        }

    stored = st.session_state.get("detection_eval")
    if not stored or not stored["items"]:
        st.info("Upload images with label files, then press **Run detection evaluation**.")
        _render_explanation()
        return

    items = stored["items"]
    result = evaluate_dataset(items, threshold)

    if stored["missing_label"]:
        st.warning(f"Skipped {len(stored['missing_label'])} image(s) with no label file.")
    if stored["unreadable"]:
        st.warning(f"Could not read {len(stored['unreadable'])} image(s): {', '.join(stored['unreadable'])}")
    if stored["ignored_lines"]:
        st.warning(
            f"Ignored {stored['ignored_lines']} label line(s) that did not have exactly 5 numbers "
            "(for example polygons)."
        )
    if result["images"] < 30 or result["total_gt"] < 100:
        st.warning(
            f"Small test set ({result['images']} images, {result['total_gt']} labelled vehicles). "
            "Treat these numbers as rough. They can change a lot with a different set of images."
        )

    # ---------- Main metrics ----------
    st.subheader(f"1. Results at confidence threshold {threshold:.2f}")
    st.caption(
        f"{result['images']} images, {result['total_gt']} labelled vehicles. "
        f"A detection is correct if it overlaps a real vehicle with IoU ≥ {settings.IOU_THRESHOLD}."
    )
    a, b, c, d = st.columns(4)
    a.metric("Precision", show(result["precision"], percent=True),
             help="Of the vehicles the model reported, how many were real.")
    b.metric("Recall", show(result["recall"], percent=True),
             help="Of the real vehicles, how many the model found.")
    c.metric("F1-score", show(result["f1"], percent=True),
             help="Harmonic mean of precision and recall.")
    d.metric("Detection accuracy", show(result["accuracy"], percent=True),
             help="TP / (TP + FP + FN). Plain accuracy needs 'true negatives', which "
                  "do not exist in object detection, so this is the usual substitute.")

    e, f, g, h = st.columns(4)
    e.metric("mAP@0.5", show(result["ap50"], percent=True),
             help="Average precision at IoU 0.5 for the merged 'vehicle' class. "
                  "With one class, mAP equals AP.")
    f.metric("Count error (MAE)", show(result["count_mae"], digits=2),
             help="Average difference between predicted and real vehicles per image.")
    g.metric("Exact count rate", show(result["exact_count_rate"], percent=True),
             help="Share of images where the predicted count equals the real count.")
    h.metric("Inference time", f"{result['avg_inference_ms']:.1f} ms")
    st.caption(
        f"Model speed on this computer: {result['fps']:.1f} FPS (model only). "
        f"TP = {result['tp']}, FP = {result['fp']}, FN = {result['fn']}."
    )

    # ---------- Threshold table ----------
    st.subheader("2. Effect of the confidence threshold")
    sweep = []
    for value in settings.EVAL_THRESHOLDS:
        row = evaluate_dataset(items, value)
        sweep.append(
            {
                "Threshold": value,
                "Precision": show(row["precision"], percent=True),
                "Recall": show(row["recall"], percent=True),
                "F1": show(row["f1"], percent=True),
                "TP": row["tp"],
                "FP": row["fp"],
                "FN": row["fn"],
                "Count MAE": show(row["count_mae"], digits=2),
            }
        )
    st.table(sweep)
    st.caption("A higher threshold raises precision and usually lowers recall. Pick the one that suits the use case.")

    # ---------- Per image ----------
    st.subheader("3. Real vs predicted vehicle count per image")
    table = pd.DataFrame(result["per_image"])
    st.bar_chart(table.set_index("name")[["actual", "predicted"]])
    st.dataframe(table, use_container_width=True)

    _render_explanation()


def _render_explanation() -> None:
    with st.expander("How are these metrics calculated? What are the limits?"):
        st.write(
            f"""
**Matching:** detections are sorted by confidence. Each one is matched to the
unmatched real box it overlaps most. If IoU ≥ {settings.IOU_THRESHOLD}, it is a
true positive (TP). Otherwise it is a false positive (FP). Real boxes left
unmatched are false negatives (FN). A second detection of an already-matched
vehicle is an FP.

**Precision** = TP / (TP + FP). **Recall** = TP / (TP + FN).
**F1** = 2 x precision x recall / (precision + recall).

**mAP@0.5:** the model is run with a very low threshold
({settings.EVAL_MIN_CONFIDENCE}) so every detection is ranked by confidence.
AP is the area under the resulting precision-recall curve. Because all vehicle
types are merged into one class, mAP here equals the AP of that single class.
It is **not comparable** to published COCO benchmark numbers.

**Inference time and FPS:** the average time of the model call per image on
this computer. FPS = 1 / average time. It excludes reading and drawing, and it
changes between computers.

**Limits:** results describe only the images you labelled. Different cameras,
lighting, weather or traffic can give different numbers. Labelling mistakes
(missed vehicles) make precision look worse than it is. A small test set gives
unstable numbers. These results do not mean the system is 100% accurate.
"""
        )