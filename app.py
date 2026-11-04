"""Smart Traffic Signal Optimisation - dashboard (simulation + ambulance priority)."""

import streamlit as st

from config import settings
from src.dashboard.style import apply_style, banner, hero, intersection_html
from src.signal_control.controller import density_label
from src.signal_control.simulation import IntersectionSimulation, generate_arrivals

st.set_page_config(page_title="Smart Traffic Signal AI", page_icon="🚦", layout="wide")
apply_style()

hero(
    "🚦 Smart Traffic Signal Optimisation",
    "Adaptive signals · live simulation · emergency vehicle priority",
)

# ---------- Sidebar: scenario settings ----------
st.sidebar.header("Scenario")
mode_label = st.sidebar.radio("Signal control", ["Adaptive", "Fixed-time"])
mode = "adaptive" if mode_label == "Adaptive" else "fixed"

st.sidebar.subheader("Vehicles arriving per minute")
arrivals_per_minute = {}
for road in settings.ROADS:
    arrivals_per_minute[road] = st.sidebar.slider(
        f"{road} road",
        0,
        settings.MAX_ARRIVALS_PER_MINUTE,
        settings.DEFAULT_ARRIVALS_PER_MINUTE[road],
    )

speed = st.sidebar.select_slider(
    "Speed (simulated seconds per real second)",
    options=settings.SPEED_OPTIONS,
    value=5,
)

st.sidebar.subheader("🚑 Emergency vehicle")
ambulance_road = st.sidebar.selectbox(
    "Ambulance approaches from", settings.ROADS, key="ambulance_road"
)
scheduled_time = st.sidebar.slider(
    "Scheduled ambulance at (simulated s, 0 = none)",
    0,
    settings.SIMULATION_SECONDS - 60,
    0,
    step=10,
    help="A scheduled ambulance appears at the same moment in both control "
    "modes, so you can compare them fairly.",
)

# ---------- Session state: the simulation survives between refreshes ----------
if "running" not in st.session_state:
    st.session_state.running = False
if "scenario_key" not in st.session_state:
    st.session_state.scenario_key = None


def build_new_simulation(scenario_key) -> None:
    """Create a fresh simulation with the current scenario."""
    rates = {road: arrivals_per_minute[road] / 60 for road in settings.ROADS}
    arrivals = generate_arrivals(
        rates, settings.SIMULATION_SECONDS, settings.RANDOM_SEED
    )
    events = [(ambulance_road, scheduled_time)] if scheduled_time > 0 else []
    st.session_state.sim = IntersectionSimulation(
        mode, arrivals, settings.SIMULATION_SECONDS, emergency_events=events
    )
    st.session_state.scenario_key = scenario_key
    st.session_state.running = False


# Changing the mode or any scenario setting automatically restarts the simulation.
scheduled_key = (ambulance_road, scheduled_time) if scheduled_time > 0 else None
current_key = (
    mode,
    tuple(arrivals_per_minute[road] for road in settings.ROADS),
    scheduled_key,
)
if st.session_state.scenario_key != current_key:
    build_new_simulation(current_key)

sim = st.session_state.sim


def toggle_running() -> None:
    st.session_state.running = not st.session_state.running


def reset_simulation() -> None:
    st.session_state.scenario_key = None  # forces a rebuild on the next run


def send_ambulance() -> None:
    st.session_state.sim.dispatch_ambulance(st.session_state.ambulance_road)


button_left, button_right = st.sidebar.columns(2)
button_left.button(
    "⏸ Pause" if st.session_state.running else "▶ Start",
    on_click=toggle_running,
    disabled=sim.finished,
    use_container_width=True,
    type="primary",
)
button_right.button(
    "↺ Reset", on_click=reset_simulation, use_container_width=True
)
st.sidebar.button(
    "🚑 Send ambulance now",
    on_click=send_ambulance,
    disabled=sim.finished,
    use_container_width=True,
)
st.sidebar.caption(
    "Changing a slider or the control mode restarts the simulation. "
    "The traffic is generated from a fixed random seed, so both modes "
    "see exactly the same vehicles."
)

STATE_ICONS = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}


def render(simulation: IntersectionSimulation) -> None:
    """Draw everything that changes while the simulation runs."""
    minutes, seconds = divmod(simulation.time, 60)
    total_minutes, total_seconds = divmod(simulation.duration, 60)

    # ----- Headline numbers -----
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "⏱ Simulated time",
        f"{minutes:02d}:{seconds:02d}",
        help=f"Total run length: {total_minutes:02d}:{total_seconds:02d}",
    )
    c2.metric(
        "⌛ Total waiting time",
        f"{simulation.total_wait} veh·s",
        help="Every second, each waiting vehicle adds 1 vehicle-second.",
    )
    c3.metric("🚗 Vehicles served", simulation.served)
    c4.metric(
        "📉 Avg wait per served vehicle",
        f"{simulation.average_wait_served:.1f} s",
    )
    st.progress(min(simulation.time / simulation.duration, 1.0))

    # ----- Emergency status -----
    emergency = simulation.emergency_status()
    if emergency:
        reach = emergency["seconds_to_reach"]
        where = (
            "is at the stop line"
            if reach == 0
            else f"reaches the stop line in {reach} s"
        )
        if simulation.mode == "adaptive":
            banner(
                "red",
                f"🚑 EMERGENCY PRIORITY ACTIVE - ambulance on the "
                f"{emergency['road']} road {where}",
            )
        else:
            banner(
                "red",
                f"🚑 Ambulance on the {emergency['road']} road {where}. "
                "Fixed-time control has no priority, so it waits for its normal turn.",
            )
    else:
        banner("blue", "🚑 Emergency priority: standby (no ambulance detected)")

    # ----- Current signal status -----
    if simulation.phase == "GREEN":
        banner(
            "green",
            f"🟢 {simulation.current_road} has GREEN - "
            f"{simulation.seconds_left()} s remaining &nbsp;|&nbsp; Mode: {mode_label}",
        )
    else:
        banner(
            "yellow",
            f"🟡 {simulation.current_road} is YELLOW - {simulation.next_road} "
            f"gets green in {simulation.seconds_left()} s &nbsp;|&nbsp; Mode: {mode_label}",
        )

    # ----- Intersection drawing -----
    st.markdown(intersection_html(simulation), unsafe_allow_html=True)

    # ----- One summary card per road -----
    states = simulation.signal_states()
    for column, road in zip(st.columns(4), settings.ROADS):
        count = simulation.queue_length(road)
        with column:
            st.metric(f"{STATE_ICONS[states[road]]} {road}", count)
            st.progress(min(count / settings.MAX_SLIDER_COUNT, 1.0))
            st.caption(f"Density: {density_label(count)}")

    # ----- Queue chart and per-road table -----
    st.divider()
    chart_col, table_col = st.columns([3, 2])
    with chart_col:
        st.subheader("Queue length over time")
        if simulation.time > 0:
            st.line_chart(
                simulation.history,
                color=["#2563eb", "#f59e0b", "#10b981", "#ef4444"],
            )
        else:
            st.info("Press ▶ Start in the sidebar to begin.")
    with table_col:
        st.subheader("Per-road totals")
        rows = []
        for road in settings.ROADS:
            rows.append(
                {
                    "Road": road,
                    "Arrived": simulation.arrived_by_road[road],
                    "Served": simulation.served_by_road[road],
                    "Waiting now": simulation.queue_length(road),
                }
            )
        st.table(rows)
        st.write(
            f"**Average queue length per road:** "
            f"{simulation.average_queue_per_road:.2f} vehicles"
        )

    # ----- Ambulance log -----
    st.subheader("🚑 Ambulance log")
    if simulation.emergency_log:
        st.table(
            [
                {
                    "Road": entry["road"],
                    "Detected (s)": entry["detected"],
                    "Reached stop line (s)": entry["reach"],
                    "Passed (s)": entry["passed"],
                    "Wait at stop line (s)": entry["wait"],
                }
                for entry in simulation.emergency_log
            ]
        )
        st.write(
            f"**Average ambulance wait:** {simulation.average_emergency_wait:.1f} s"
        )
    else:
        st.caption("No ambulance has passed yet.")

    if simulation.finished:
        banner(
            "green",
            "✅ Simulation finished. Switch the control mode in the sidebar "
            "and run again to see how the same traffic is handled.",
        )


def live_view() -> None:
    """Advance the simulation (if running) and draw it."""
    simulation = st.session_state.sim
    if st.session_state.running and not simulation.finished:
        for _ in range(speed):
            simulation.step()
            if simulation.finished:
                break

    render(simulation)

    if simulation.finished and st.session_state.running:
        st.session_state.running = False
        st.rerun()  # refresh the sidebar buttons


# While running, this part of the page refreshes itself every second.
refresh_seconds = 1 if st.session_state.running else None
st.fragment(run_every=refresh_seconds)(live_view)()

with st.expander("How is this measured?"):
    st.write(
        f"""
**One tick = one simulated second.** On green, one vehicle leaves every
{settings.DEPARTURE_INTERVAL_SECONDS} seconds. No vehicle passes on yellow or red.

**Total waiting time (vehicle-seconds):** each second, every vehicle still
waiting adds 1. Ten vehicles waiting for 30 s = 300 veh·s.

**Average wait per served vehicle:** the seconds each vehicle spent in the
queue before leaving, averaged over vehicles that have left.

**Average queue length per road:** total waiting time divided by
(seconds simulated x 4 roads).

**Fixed-time:** each road gets {settings.FIXED_GREEN_SECONDS} s green in order.
Ambulances get no special treatment.

**Adaptive:** the road with the highest score goes next (queue length plus a
small bonus for time spent waiting). Empty roads are skipped. Green time is
{settings.MIN_GREEN_SECONDS} s + {settings.SECONDS_PER_VEHICLE} s per vehicle,
at most {settings.MAX_GREEN_SECONDS} s. Green ends early if the road empties
after the minimum time.

**Emergency priority (adaptive only):** when an ambulance is detected, the
current green ends, a {settings.YELLOW_SECONDS} s yellow runs, and the
ambulance's road gets green. If its road is already green, the green is held
(up to {settings.MAX_GREEN_SECONDS} s) until the ambulance passes. The
ambulance needs {settings.AMBULANCE_APPROACH_SECONDS} s from detection to reach
the stop line. **Ambulance wait** = seconds between reaching the stop line and
passing it. Ambulances are tracked separately and are not part of the normal
vehicle statistics.

**Safety:** only one road is non-red at any moment, and a yellow always sits
between two different greens, even for an ambulance.

**The drawing** shows up to {5} vehicles per road as coloured cars. Any more are
shown as "+N". The real count is in the pill next to each road.

These are simulated vehicles with simplified rules, not real traffic.
"""
    )