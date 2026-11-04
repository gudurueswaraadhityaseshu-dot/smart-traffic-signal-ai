# Architecture

```
Traffic video / photo ──► YOLO detector ──► vehicle counts per road ──┐
        (src/detection)                                              ▼
                                                     Signal planner (src/signal_control)
                                                                      │
Random traffic generator (fixed seed) ──► Simulation engine ◄─────────┘
                                              │  fixed-time or adaptive
                                              ▼
                              Metrics (src/evaluation) ──► Streamlit dashboard
                                                            (app.py, pages/)
```

- **Detection** finds vehicles in frames and reports a count per road.
- **Signal control** decides which road is green and for how long.
- **Simulation** advances the junction one second at a time. Both control modes
  receive identical arrivals and ambulance events.
- **Evaluation** turns a finished simulation into comparable metrics.
- **Dashboard** only displays results. The logic has no Streamlit code in it, so it
  can be tested separately.

Safety rule: only one road is non-red at any moment, and a yellow phase always sits
between two different greens, including for ambulances.

Why a custom simulation instead of SUMO: it is simpler to install, runs on a
Windows laptop and the free cloud, and gives both systems identical traffic.
SUMO would be a natural next step.