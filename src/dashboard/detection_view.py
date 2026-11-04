"""The Vehicle Detection page.

If the YOLO library (ultralytics) is not installed, for example on the free
cloud server, the page shows saved example results and lets the visitor type
vehicle counts by hand, so the demonstration still works.
"""

import importlib.util
import os

import cv2
import streamlit as st

from config import settings
from src.detection.video_utils import (
    analyse_frames,
    decode_image,
    find_local_file,
    read_frames,
    read_frames_from_bytes,
)
from src.signal_control.controller import (
    build_adaptive_plan,
    build_fixed_plan,
    density_label,
    total_cycle_seconds,
)

SAMPLE_FOLDER = os.path.join("docs", "sample_detections")


def yolo_available() -> bool:
    """True if the ultralytics package is installed in this environment."""
    return importlib.util.find_spec("ultralytics") is not None


@st.cache_resource(show_spinner="Loading the YOLO model (first run downloads about 6 MB)...")
def load_detector():
    from src.detection.detector import VehicleDetector

    return VehicleDetector()


def get_frames(road: str, uploaded, frames_wanted: int):
    """Return (frames, source_label). source_label is None when no input exists."""
    if uploaded is not None:
        suffix = os.path.splitext(uploaded.name)[1].lower()
        data = uploaded.getvalue()
        if suffix in settings.IMAGE_EXTENSIONS:
            frame = decode_image(data)
            return ([frame] if frame is not None else []), f"upload: {uploaded.name}"
        return read_frames_from_bytes(data, suffix, frames_wanted), f"upload: {uploaded.name}"

    local = find_local_file(road)
    if local is None:
        return [], None
    if local.lower().endswith(settings.IMAGE_EXTENSIONS):
        with open(local, "rb") as file:
            frame = decode_image(file.read())
        return ([frame] if frame is not None else []), local
    return read_frames(local, frames_wanted), local


def plan_rows(plan: list) -> list:
    return [
        {
            "Order": number,
            "Road": phase["road"],
            "Green (s)": phase["green"],
            "Yellow (s)": phase["yellow"],
        }
        for number, phase in enumerate(plan, start=1)
    ]


def render_signal_plan(counts: dict) -> None:
    """Show the density table and the adaptive and fixed-time plans."""
    st.table(
        [
            {"Road": road, "Vehicles": counts[road], "Density": density_label(counts[road])}
            for road in settings.ROADS
        ]
    )
    left, right = st.columns(2)
    adaptive_plan = build_adaptive_plan(counts)
    with left:
        st.markdown("**Adaptive plan**")
        if adaptive_plan:
            st.table(plan_rows(adaptive_plan))
            st.write(f"Cycle length: {total_cycle_seconds(adaptive_plan)} s")
        else:
            st.info("No vehicles on any road.")
    with right:
        st.markdown("**Fixed-time plan**")
        fixed_plan = build_fixed_plan()
        st.table(plan_rows(fixed_plan))
        st.write(f"Cycle length: {total_cycle_seconds(fixed_plan)} s")


def render_without_yolo() -> None:
    """Fallback page used when ultralytics is not installed."""
    st.warning(
        "Live YOLO detection is not installed on this server, because it needs a very "
        "large library. Below are saved example results from a local run, and you can "
        "type vehicle counts by hand to see the signal plan the controller produces. "
        "To run live detection, use the project on a laptop (see the README)."
    )

    st.subheader("1. Example detection results (saved from a local run)")
    samples = []
    if os.path.isdir(SAMPLE_FOLDER):
        samples = sorted(
            name
            for name in os.listdir(SAMPLE_FOLDER)
            if name.lower().endswith(settings.IMAGE_EXTENSIONS)
        )
    if samples:
        for start in range(0, len(samples), 2):
            for column, name in zip(st.columns(2), samples[start:start + 2]):
                with column:
                    st.image(
                        os.path.join(SAMPLE_FOLDER, name),
                        caption=name,
                        use_container_width=True,
                    )
    else:
        st.info("No saved examples yet. Add screenshots to docs/sample_detections.")

    st.subheader("2. Signal plan from vehicle counts you enter")
    defaults = {"North": 12, "East": 6, "South": 2, "West": 0}
    counts = {}
    for column, road in zip(st.columns(4), settings.ROADS):
        with column:
            counts[road] = st.number_input(
                f"{road} vehicles",
                min_value=0,
                max_value=100,
                value=defaults[road],
                step=1,
                key=f"manual_{road}",
            )
    render_signal_plan(counts)


def render_detection_page() -> None:
    st.title("🚗 Vehicle Detection (YOLO)")
    st.caption("Count vehicles from video, then plan the signals from those counts")

    if not yolo_available():
        render_without_yolo()
        return

    st.sidebar.header("Detection settings")
    confidence = st.sidebar.slider(
        "Confidence threshold",
        0.10,
        0.90,
        settings.DEFAULT_CONFIDENCE,
        0.05,
        help="Higher = fewer but surer detections. Lower = more detections, more mistakes.",
    )
    frames_wanted = st.sidebar.slider(
        "Frames to analyse per video", 1, 30, settings.FRAMES_TO_ANALYSE
    )

    # ---------- 1. Inputs ----------
    st.subheader("1. Choose a video or photo for each road")
    st.caption(
        f"Upload a file below, or save files in the '{settings.VIDEO_FOLDER}' folder "
        "named north.mp4, east.mp4, south.mp4, west.mp4."
    )
    upload_types = [e.lstrip(".") for e in settings.VIDEO_EXTENSIONS + settings.IMAGE_EXTENSIONS]
    uploads = {}
    for column, road in zip(st.columns(4), settings.ROADS):
        with column:
            st.markdown(f"**{road}**")
            uploads[road] = st.file_uploader(
                f"{road} video or photo",
                type=upload_types,
                key=f"upload_{road}",
                label_visibility="collapsed",
            )
            if uploads[road] is None:
                local = find_local_file(road)
                if local:
                    st.caption(f"Using {local}")
                else:
                    st.caption("No file yet (counted as 0)")

    # ---------- 2. Run detection ----------
    if st.button("🔍 Detect vehicles", type="primary"):
        try:
            detector = load_detector()
        except Exception as error:  # show a friendly message instead of a crash
            st.error(
                "The YOLO model could not be loaded. Check that `ultralytics` is "
                "installed and that you are online for the first run."
            )
            st.code(str(error))
            st.stop()

        results = {}
        progress = st.progress(0.0, text="Starting...")
        for index, road in enumerate(settings.ROADS):
            progress.progress(index / 4, text=f"Analysing {road} road...")
            frames, source = get_frames(road, uploads[road], frames_wanted)
            if source is None:
                results[road] = {"status": "no_input"}
            elif not frames:
                results[road] = {"status": "unreadable", "source": source}
            else:
                result = analyse_frames(detector, frames, confidence)
                result["status"] = "ok"
                result["source"] = source
                results[road] = result
        progress.progress(1.0, text="Done")
        st.session_state.detection_results = results
        st.session_state.detection_confidence = confidence

    results = st.session_state.get("detection_results")
    if not results:
        st.info("Add a file for at least one road, then press **Detect vehicles**.")
        return

    # ---------- Results ----------
    st.subheader("2. Detection results")
    st.caption(
        f"Confidence threshold used: {st.session_state.detection_confidence:.2f}. "
        "Press the button again after changing settings."
    )
    for pair in (settings.ROADS[:2], settings.ROADS[2:]):
        for column, road in zip(st.columns(2), pair):
            with column:
                result = results[road]
                st.markdown(f"### {road}")
                if result["status"] == "no_input":
                    st.info("No video or photo provided. Counted as 0 vehicles.")
                elif result["status"] == "unreadable":
                    st.error(
                        f"Could not read {result['source']}. Try converting it to "
                        "H.264 .mp4 or use a different file."
                    )
                else:
                    st.image(
                        cv2.cvtColor(result["annotated"], cv2.COLOR_BGR2RGB),
                        caption=f"{result['source']} (representative frame)",
                        use_container_width=True,
                    )
                    st.metric("Vehicles (median per frame)", result["count"])
                    types = ", ".join(f"{n} {t}" for t, n in result["type_counts"].items())
                    st.caption(f"In the shown frame: {types or 'none'}")
                    st.caption(f"Counts per analysed frame: {result['per_frame_counts']}")

    counts = {
        road: results[road]["count"] if results[road]["status"] == "ok" else 0
        for road in settings.ROADS
    }

    # ---------- Speed ----------
    st.subheader("3. Detection speed")
    speed_rows = [
        {
            "Road": road,
            "Frames analysed": results[road]["frames_analysed"],
            "Avg inference (ms/frame)": round(results[road]["avg_inference_ms"], 1),
            "Model FPS": round(results[road]["fps"], 1),
        }
        for road in settings.ROADS
        if results[road]["status"] == "ok"
    ]
    if speed_rows:
        st.table(speed_rows)
        st.caption("Measured on this computer. FPS = 1 / average model time; it excludes video reading and drawing.")

    # ---------- Signal plan ----------
    st.subheader("4. Signal plan from the detected counts")
    render_signal_plan(counts)

    with st.expander("How is the count measured? What are the limits?"):
        st.write(
            f"""
**Model:** `{settings.MODEL_NAME}`, a small YOLO model pretrained on the COCO
dataset. We keep only cars, motorcycles, buses and trucks.

**Count:** the median number of vehicles visible per analysed frame. It is a
snapshot of the queue, not a count of vehicles passing a line.

**Limits:** small or distant vehicles can be missed, partly hidden vehicles may
be missed or counted twice, night video and heavy rain are harder, and the
count depends on what the camera can see. This page does **not** measure
detection accuracy. That needs hand-labelled test images (see the Detection
Evaluation page).
"""
        )