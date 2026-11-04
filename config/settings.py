"""Central settings for the Smart Traffic Signal project.

Change numbers here instead of searching through the code.
"""

# The four roads of the intersection, in a fixed order.
ROADS = ["North", "East", "South", "West"]

# ---------- Signal timing rules (all values in seconds) ----------
MIN_GREEN_SECONDS = 10      # A green light never lasts shorter than this.
MAX_GREEN_SECONDS = 40      # A green light never lasts longer than this.
YELLOW_SECONDS = 3          # Warning time between green and red.
FIXED_GREEN_SECONDS = 25    # Green time for every road in the fixed-time system.

# Adaptive rule: each waiting vehicle adds this many seconds of green.
SECONDS_PER_VEHICLE = 2

# Adaptive fairness: every second a road waits adds this to its priority
# score, so a quiet road is not ignored forever.
STARVATION_BONUS_PER_SECOND = 0.1

# ---------- Density labels (based on number of vehicles on a road) ----------
MODERATE_THRESHOLD = 6      # 1-5 vehicles   -> "Low"
HEAVY_THRESHOLD = 15        # 6-14 vehicles  -> "Moderate", 15+ -> "Heavy"

# Used to scale the progress bars.
MAX_SLIDER_COUNT = 30

# ---------- Simulation settings (Stage 2) ----------
SIMULATION_SECONDS = 600            # Length of one simulation run (10 minutes).
DEPARTURE_INTERVAL_SECONDS = 2      # On green, one vehicle leaves every 2 seconds.
RANDOM_SEED = 42                    # Same seed = same traffic every run.

# Default traffic: vehicles arriving per minute on each road.
DEFAULT_ARRIVALS_PER_MINUTE = {"North": 9, "East": 5, "South": 2, "West": 0}
MAX_ARRIVALS_PER_MINUTE = 20

# Dashboard speed choices (simulated seconds per real second).
SPEED_OPTIONS = [1, 2, 5, 10]


# ---------- Detection settings (Stage 3) ----------
MODEL_NAME = "yolov8n.pt"            # Downloaded automatically on first use (~6 MB).
VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}  # COCO class ids
DEFAULT_CONFIDENCE = 0.35            # Ignore detections the model is less sure about.
DETECTION_IMAGE_SIZE = 640           # Size the model resizes frames to.
FRAMES_TO_ANALYSE = 10               # Default number of frames sampled per video.
MAX_FRAME_WIDTH = 1280               # Larger frames are shrunk to save memory.

VIDEO_FOLDER = "videos"              # Folder checked for north.mp4, east.mp4, ...
VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")


# ---------- Emergency vehicle settings (Stage 4) ----------
AMBULANCE_APPROACH_SECONDS = 12   # Time from detection to reaching the stop line.


# ---------- Evaluation settings (Stage 5) ----------
EVAL_SEEDS = 5                       # Random traffic samples per scenario.
EVAL_DURATION_SECONDS = 600          # Length of each evaluation run.
CROSSING_SECONDS = 5                 # Assumed time to cross the junction once served.

# Traffic scenarios: arrivals per minute on each road, plus scheduled
# ambulances as (road, simulated second). These are assumptions, not real data.
SCENARIOS = {
    "Demo: heavy / moderate / low / none": {
        "rates": {"North": 9, "East": 5, "South": 2, "West": 0},
        "ambulances": [],
    },
    "Demo + ambulances (West at 120 s, East at 300 s)": {
        "rates": {"North": 9, "East": 5, "South": 2, "West": 0},
        "ambulances": [("West", 120), ("East", 300)],
    },
    "Balanced moderate (4 per minute each)": {
        "rates": {"North": 4, "East": 4, "South": 4, "West": 4},
        "ambulances": [],
    },
    "Balanced heavy (8 per minute each)": {
        "rates": {"North": 8, "East": 8, "South": 8, "West": 8},
        "ambulances": [],
    },
    "One very busy road (North 12, others 1)": {
        "rates": {"North": 12, "East": 1, "South": 1, "West": 1},
        "ambulances": [],
    },
    "Light traffic (2 per minute each)": {
        "rates": {"North": 2, "East": 2, "South": 2, "West": 2},
        "ambulances": [],
    },
}

# Detection evaluation
EVAL_MIN_CONFIDENCE = 0.01           # Model runs this low so AP can use the full ranking.
IOU_THRESHOLD = 0.5                  # A detection is correct if it overlaps a real box this much.
EVAL_THRESHOLDS = [0.15, 0.25, 0.35, 0.50, 0.65]   # Shown in the threshold table.