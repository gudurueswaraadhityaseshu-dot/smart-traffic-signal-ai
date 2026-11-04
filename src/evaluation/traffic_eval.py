"""Fixed-time vs adaptive evaluation over several scenarios and random seeds.

No Streamlit in this file. Both modes always receive the same arrivals and
the same ambulance events for a given seed, so the comparison is paired.
"""

import statistics

from config import settings
from src.signal_control.simulation import IntersectionSimulation, generate_arrivals

# (key, label, lower_is_better, number format)
METRICS = [
    ("total_wait", "Total waiting time (veh·s)", True, "{:.0f}"),
    ("avg_wait_arrived", "Avg wait per arrived vehicle (s)", True, "{:.1f}"),
    ("avg_wait_served", "Avg wait per served vehicle (s)", True, "{:.1f}"),
    ("avg_travel", "Avg travel time through junction (s)", True, "{:.1f}"),
    ("avg_queue", "Avg queue length per road (vehicles)", True, "{:.2f}"),
    ("served", "Vehicles served", False, "{:.0f}"),
    ("unserved", "Vehicles still waiting at the end", True, "{:.0f}"),
    ("emergency_wait", "Avg ambulance wait at stop line (s)", True, "{:.1f}"),
]


def seeds_for(count: int) -> list:
    """The random seeds used for `count` traffic samples."""
    return [settings.RANDOM_SEED + i for i in range(count)]


def collect_metrics(sim: IntersectionSimulation, expected_ambulances: int) -> dict:
    """Read the final numbers out of a finished simulation."""
    arrived = sim.arrived
    served = sim.served
    return {
        "arrived": arrived,
        "total_wait": sim.total_wait,
        "avg_wait_arrived": (sim.total_wait / arrived) if arrived else 0.0,
        "avg_wait_served": sim.average_wait_served if served else None,
        "avg_travel": (sim.average_wait_served + settings.CROSSING_SECONDS) if served else None,
        "avg_queue": sim.average_queue_per_road,
        "served": served,
        "unserved": arrived - served,
        "emergency_wait": sim.average_emergency_wait if sim.emergency_log else None,
        "ambulances_expected": expected_ambulances,
        "ambulances_passed": sim.emergency_served,
    }


def run_once(mode: str, rates_per_minute: dict, seed: int, duration: int, ambulances: list) -> dict:
    """Run one full simulation and return its metrics."""
    rates = {road: rates_per_minute.get(road, 0) / 60 for road in settings.ROADS}
    arrivals = generate_arrivals(rates, duration, seed)
    events = [(road, second) for road, second in ambulances if second < duration]
    sim = IntersectionSimulation(mode, arrivals, duration, emergency_events=events)
    while not sim.finished:
        sim.step()
    return collect_metrics(sim, len(events))


def compare_scenario(scenario: dict, seeds: list, duration: int) -> dict:
    """Run both modes on the same seeds. Returns {"fixed": [...], "adaptive": [...]}."""
    runs = {"fixed": [], "adaptive": []}
    for seed in seeds:
        for mode in runs:
            runs[mode].append(
                run_once(mode, scenario["rates"], seed, duration, scenario["ambulances"])
            )
    return runs


def aggregate(values: list):
    """Mean and standard deviation, ignoring missing (None) values."""
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return {
        "mean": statistics.mean(clean),
        "sd": statistics.stdev(clean) if len(clean) > 1 else 0.0,
        "n": len(clean),
    }


def change_percent(fixed_mean: float, adaptive_mean: float, lower_is_better: bool):
    """Positive = adaptive is better, negative = adaptive is worse. None if undefined."""
    if fixed_mean == 0:
        return None
    if lower_is_better:
        return (fixed_mean - adaptive_mean) / fixed_mean * 100
    return (adaptive_mean - fixed_mean) / fixed_mean * 100


def summarise(runs: dict) -> dict:
    """Turn the per-seed runs of one scenario into a per-metric summary."""
    summary = {}
    for key, _label, lower_is_better, _fmt in METRICS:
        fixed_values = [run[key] for run in runs["fixed"]]
        adaptive_values = [run[key] for run in runs["adaptive"]]
        fixed_agg = aggregate(fixed_values)
        adaptive_agg = aggregate(adaptive_values)

        change = None
        if fixed_agg is not None and adaptive_agg is not None:
            change = change_percent(fixed_agg["mean"], adaptive_agg["mean"], lower_is_better)

        compared = 0
        adaptive_wins = 0
        for fixed_value, adaptive_value in zip(fixed_values, adaptive_values):
            if fixed_value is None or adaptive_value is None:
                continue
            compared += 1
            better = adaptive_value < fixed_value if lower_is_better else adaptive_value > fixed_value
            if better:
                adaptive_wins += 1

        summary[key] = {
            "fixed": fixed_agg,
            "adaptive": adaptive_agg,
            "change": change,
            "adaptive_wins": adaptive_wins,
            "compared": compared,
        }
    return summary