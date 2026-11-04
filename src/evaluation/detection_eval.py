"""Object-detection metrics: IoU matching, precision, recall, F1, accuracy, AP@0.5.

Pure Python. No YOLO and no Streamlit here, so it is tested with made-up boxes.

All vehicle types (car, motorcycle, bus, truck) are merged into ONE class
called "vehicle". That keeps labelling simple and matches what the signal
controller needs: how many vehicles are there.

A box is (x1, y1, x2, y2) in pixels. A prediction is (confidence, box).
"""

from config import settings


def box_iou(a: tuple, b: tuple) -> float:
    """Intersection over Union: 1.0 = identical boxes, 0.0 = no overlap."""
    inter_w = min(a[2], b[2]) - max(a[0], b[0])
    inter_h = min(a[3], b[3]) - max(a[1], b[1])
    if inter_w <= 0 or inter_h <= 0:
        return 0.0
    inter = inter_w * inter_h
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def yolo_label_to_boxes(text: str, width: int, height: int):
    """Read a YOLO-format label file: 'class x_center y_center w h' (0-1 values).

    Returns (boxes_in_pixels, number_of_ignored_lines). Lines that do not have
    exactly 5 numbers (for example polygons) are ignored and counted.
    """
    boxes = []
    ignored = 0
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if len(parts) != 5:
            ignored += 1
            continue
        try:
            _, x_centre, y_centre, box_w, box_h = [float(p) for p in parts]
        except ValueError:
            ignored += 1
            continue
        boxes.append(
            (
                (x_centre - box_w / 2) * width,
                (y_centre - box_h / 2) * height,
                (x_centre + box_w / 2) * width,
                (y_centre + box_h / 2) * height,
            )
        )
    return boxes, ignored


def match_image(preds: list, gt: list, iou_threshold: float = settings.IOU_THRESHOLD) -> list:
    """Match predictions to real boxes, most confident first.

    Each real box can be matched only once, so a duplicate detection of the
    same vehicle counts as a false positive.
    Returns [(confidence, is_true_positive), ...] in order of confidence.
    """
    ordered = sorted(preds, key=lambda item: item[0], reverse=True)
    used = set()
    flags = []
    for confidence, box in ordered:
        best_index = None
        best_iou = 0.0
        for index, truth in enumerate(gt):
            if index in used:
                continue
            iou = box_iou(box, truth)
            if iou > best_iou:
                best_iou = iou
                best_index = index
        if best_index is not None and best_iou >= iou_threshold:
            used.add(best_index)
            flags.append((confidence, True))
        else:
            flags.append((confidence, False))
    return flags


def average_precision(flags: list, total_gt: int):
    """Area under the precision-recall curve (all-point interpolation).

    flags: (confidence, is_true_positive) for every prediction in the dataset.
    Returns None when there are no real vehicles at all.
    """
    if total_gt == 0:
        return None
    if not flags:
        return 0.0

    ordered = sorted(flags, key=lambda item: item[0], reverse=True)
    recalls = []
    precisions = []
    tp = 0
    fp = 0
    for _confidence, is_tp in ordered:
        if is_tp:
            tp += 1
        else:
            fp += 1
        recalls.append(tp / total_gt)
        precisions.append(tp / (tp + fp))

    mrec = [0.0] + recalls + [1.0]
    mpre = [0.0] + precisions + [0.0]
    for i in range(len(mpre) - 2, -1, -1):   # make precision never increase
        mpre[i] = max(mpre[i], mpre[i + 1])

    ap = 0.0
    for i in range(1, len(mrec)):
        ap += (mrec[i] - mrec[i - 1]) * mpre[i]
    return ap


def evaluate_dataset(images: list, threshold: float, iou_threshold: float = settings.IOU_THRESHOLD) -> dict:
    """Compute all detection metrics for a labelled dataset.

    images: list of dicts with
        "name"    - image name
        "preds"   - [(confidence, box), ...] from the model at a LOW confidence
        "gt"      - [box, ...] the hand-labelled vehicles
        "elapsed" - model time for this image, in seconds
    threshold: the confidence cut-off used for precision/recall/F1/counts.
    AP@0.5 uses all predictions (no cut-off), as is standard.
    """
    if not images:
        raise ValueError("No images to evaluate")

    tp = fp = fn = 0
    total_gt = 0
    all_flags = []
    count_errors = []
    exact_matches = 0
    per_image = []

    for item in images:
        flags = match_image(item["preds"], item["gt"], iou_threshold)
        all_flags.extend(flags)
        kept = [flag for flag in flags if flag[0] >= threshold]

        image_tp = sum(1 for _, is_tp in kept if is_tp)
        image_fp = len(kept) - image_tp
        image_fn = len(item["gt"]) - image_tp

        tp += image_tp
        fp += image_fp
        fn += image_fn
        total_gt += len(item["gt"])
        error = abs(len(kept) - len(item["gt"]))
        count_errors.append(error)
        if error == 0:
            exact_matches += 1
        per_image.append(
            {
                "name": item.get("name", ""),
                "actual": len(item["gt"]),
                "predicted": len(kept),
                "tp": image_tp,
                "fp": image_fp,
                "fn": image_fn,
            }
        )

    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None
    if precision is None or recall is None:
        f1 = None
    elif precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    accuracy = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else None

    times = [item["elapsed"] for item in images]
    average_time = sum(times) / len(times)

    return {
        "images": len(images),
        "total_gt": total_gt,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "ap50": average_precision(all_flags, total_gt),
        "count_mae": sum(count_errors) / len(count_errors),
        "exact_count_rate": exact_matches / len(images),
        "avg_inference_ms": average_time * 1000,
        "fps": (1 / average_time) if average_time > 0 else 0.0,
        "per_image": per_image,
    }