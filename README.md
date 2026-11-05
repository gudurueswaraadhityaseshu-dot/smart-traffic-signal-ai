# Smart Traffic Signal Optimisation using AI/ML

An adaptive traffic-signal prototype for a four-road intersection. It compares
adaptive control with traditional fixed-time control on identical simulated
traffic, gives emergency vehicles priority, and uses a pretrained YOLO model to
count vehicles from video.

**Live demo:** https://gudurueswaraadhityaseshu-dot-smart-traffic-signal-ai-app-9fdagk.streamlit.app/

## Features

- Live simulation with countdown timers, yellow phases and waiting-time metrics
- Adaptive control: busiest road first, green time scales with queue length,
  minimum and maximum green limits, and no two roads ever active together
- Emergency priority (simulated ambulance) with a safe yellow transition
- Fixed-time vs adaptive comparison over several scenarios and random samples
- YOLO vehicle detection (cars, motorcycles, buses, trucks) with bounding boxes
- Detection evaluation (precision, recall, F1, mAP@0.5) from labelled images

## Run locally (Windows)

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements-local.txt
python -m streamlit run app.py
```

Run the automatic tests:

```
python -m unittest discover -s tests -t .
```

## Folder structure

| Folder | Purpose |
|---|---|
| `app.py`, `pages/` | The Streamlit dashboard pages |
| `config/` | All adjustable settings |
| `src/signal_control/` | Fixed and adaptive controllers and the simulation engine |
| `src/detection/` | YOLO detector and video helpers |
| `src/evaluation/` | Traffic and detection metrics |
| `src/dashboard/` | Page layouts and styling |
| `videos/` | Optional local traffic videos (not uploaded to GitHub) |
| `tests/` | Automatic tests |
| `docs/` | Documentation and saved example detections |
| `tools/` | Helper scripts, for example frame extraction for labelling |

## Honest limitations

- The signal comparison uses a simplified simulation of one isolated junction with
  assumed traffic scenarios. It is not measured city traffic, and results do not
  predict real-world savings.
- The simulated traffic is generated randomly. It is not driven by the YOLO counts.
- The ambulance is a simulated trigger. The COCO-trained model has no ambulance class.
- Detection accuracy is only reported from labelled images you supply.
- The public cloud version runs without live YOLO because of server resource limits.