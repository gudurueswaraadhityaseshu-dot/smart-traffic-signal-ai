"""The Performance Evaluation page: fixed-time vs adaptive (Stage 5)."""

import pandas as pd
import streamlit as st

from config import settings
from src.evaluation.traffic_eval import METRICS, compare_scenario, seeds_for, summarise

FORMATS = {key: fmt for key, _label, _lower, fmt in METRICS}


def fmt_value(agg, fmt: str) -> str:
    """'123 ± 4' style text, or n/a when there is no data."""
    if agg is None:
        return "n/a"
    text = fmt.format(agg["mean"])
    if agg["n"] > 1:
        text += f" ± {fmt.format(agg['sd'])}"
    return text


def fmt_change(change) -> str:
    if change is None:
        return "n/a"
    if abs(change) < 0.05:
        return "no change"
    return f"{abs(change):.1f}% better" if change > 0 else f"{abs(change):.1f}% worse"


def render_evaluation_page() -> None:
    st.title("📊 Traffic Signal Performance Evaluation")
    st.caption("Stage 5: fixed-time vs adaptive control on identical simulated traffic")

    st.sidebar.header("Evaluation settings")
    names = list(settings.SCENARIOS.keys())
    chosen = st.sidebar.multiselect("Scenarios", names, default=names)
    seed_count = st.sidebar.slider(
        "Random traffic samples per scenario", 1, 20, settings.EVAL_SEEDS,
        help="More samples = more reliable averages, but a longer run.",
    )
    duration = st.sidebar.select_slider(
        "Length of each run (simulated seconds)",
        options=[600, 900, 1800],
        value=settings.EVAL_DURATION_SECONDS,
    )

    if st.button("▶ Run evaluation", type="primary"):
        if not chosen:
            st.warning("Choose at least one scenario in the sidebar.")
        else:
            seeds = seeds_for(seed_count)
            all_runs = {}
            summaries = {}
            progress = st.progress(0.0, text="Starting...")
            for index, name in enumerate(chosen):
                progress.progress(index / len(chosen), text=f"Running: {name}")
                runs = compare_scenario(settings.SCENARIOS[name], seeds, duration)
                all_runs[name] = runs
                summaries[name] = summarise(runs)
            progress.progress(1.0, text="Done")
            st.session_state.traffic_eval = {
                "runs": all_runs,
                "summaries": summaries,
                "seeds": seeds,
                "duration": duration,
            }

    results = st.session_state.get("traffic_eval")
    if not results:
        st.info("Choose scenarios in the sidebar, then press **Run evaluation**.")
        _render_explanation()
        return

    summaries = results["summaries"]
    st.caption(
        f"{len(results['seeds'])} random traffic samples per scenario, "
        f"{results['duration']} simulated seconds each. Values are mean ± standard "
        "deviation across samples. Both systems see identical traffic in every sample."
    )

    # ---------- Headline table ----------
    st.subheader("1. Summary by scenario")
    rows = []
    for name, summary in summaries.items():
        rows.append(
            {
                "Scenario": name,
                "Total waiting time": fmt_change(summary["total_wait"]["change"]),
                "Avg wait per vehicle": fmt_change(summary["avg_wait_arrived"]["change"]),
                "Vehicles served": fmt_change(summary["served"]["change"]),
                "Ambulance wait, fixed (s)": fmt_value(summary["emergency_wait"]["fixed"], "{:.1f}"),
                "Ambulance wait, adaptive (s)": fmt_value(summary["emergency_wait"]["adaptive"], "{:.1f}"),
            }
        )
    st.table(rows)
    st.caption(
        "'Better' / 'worse' describes the adaptive system relative to fixed-time, "
        "using the mean over all samples. Worse results are real results and are kept."
    )

    # ---------- Chart ----------
    st.subheader("2. Chart")
    labels = {label: key for key, label, _lower, _fmt in METRICS}
    choice = st.selectbox("Metric to chart", list(labels))
    key = labels[choice]
    chart_rows = {}
    for name, summary in summaries.items():
        fixed_agg = summary[key]["fixed"]
        adaptive_agg = summary[key]["adaptive"]
        if fixed_agg is None or adaptive_agg is None:
            continue
        chart_rows[name] = {"Fixed-time": fixed_agg["mean"], "Adaptive": adaptive_agg["mean"]}
    if chart_rows:
        st.bar_chart(pd.DataFrame(chart_rows).T)
    else:
        st.info("No data for this metric in the chosen scenarios (for example, no ambulances).")

    # ---------- Detail tables ----------
    st.subheader("3. All metrics, per scenario")
    for name, summary in summaries.items():
        with st.expander(name):
            detail = []
            for metric_key, label, _lower, fmt in METRICS:
                entry = summary[metric_key]
                if entry["compared"] > 0:
                    better_in = f"{entry['adaptive_wins']} of {entry['compared']} samples"
                else:
                    better_in = "n/a"
                detail.append(
                    {
                        "Metric": label,
                        "Fixed-time": fmt_value(entry["fixed"], fmt),
                        "Adaptive": fmt_value(entry["adaptive"], fmt),
                        "Change": fmt_change(entry["change"]),
                        "Adaptive better in": better_in,
                    }
                )
            st.table(detail)

            runs = results["runs"][name]
            expected = sum(r["ambulances_expected"] for r in runs["fixed"])
            if expected:
                st.caption(
                    f"Ambulances that passed: fixed {sum(r['ambulances_passed'] for r in runs['fixed'])} "
                    f"of {expected}, adaptive {sum(r['ambulances_passed'] for r in runs['adaptive'])} of {expected}."
                )

    # ---------- Download ----------
    csv_rows = []
    for name, runs in results["runs"].items():
        for mode, mode_runs in runs.items():
            for seed, run in zip(results["seeds"], mode_runs):
                csv_rows.append({"scenario": name, "mode": mode, "seed": seed, **run})
    st.download_button(
        "⬇ Download every run as CSV",
        pd.DataFrame(csv_rows).to_csv(index=False),
        file_name="traffic_evaluation_runs.csv",
        mime="text/csv",
    )

    _render_explanation()


def _render_explanation() -> None:
    with st.expander("How are these metrics calculated? What are the limits?"):
        st.write(
            f"""
**Same traffic for both systems.** For each random sample (seed), the arrivals
and ambulance times are generated once and given to both systems.

**Total waiting time (vehicle-seconds):** every second, each vehicle still
waiting adds 1.

**Avg wait per arrived vehicle:** total waiting time / vehicles that arrived.
It includes vehicles still queued at the end, so it cannot be improved by
ignoring a long queue.

**Avg wait per served vehicle:** waiting time of vehicles that already left,
averaged. It ignores vehicles still queued, so read it together with the
'still waiting' row.

**Avg travel time:** average wait of served vehicles plus an assumed
{settings.CROSSING_SECONDS} s to cross the junction (same for both systems).

**Avg queue length per road:** total waiting time / (seconds x 4 roads).

**Vehicles served:** vehicles that passed the stop line.

**Ambulance wait:** seconds between reaching the stop line and passing it.
Ambulances are tracked separately from normal vehicles.

**Improvement:** (fixed - adaptive) / fixed x 100 when lower is better, and
(adaptive - fixed) / fixed x 100 for vehicles served.

**Limits:** this is a simplified simulation of one isolated junction. Vehicles
leave at a constant rate, there are no turns, pedestrians or start-up delays,
and the scenarios are assumptions, not measured city traffic. The results show
how the two control rules compare under these assumptions. They do not
predict real-world savings.
"""
        )