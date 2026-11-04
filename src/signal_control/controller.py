"""Traffic signal logic: fixed-time and adaptive (rule-based).

Safety rule: only ONE road is green at a time. Because every road
is its own phase, conflicting directions can never be green together.
"""

from config import settings


def density_label(count: int) -> str:
    """Turn a vehicle count into a human-readable density level."""
    if count <= 0:
        return "None"
    if count < settings.MODERATE_THRESHOLD:
        return "Low"
    if count < settings.HEAVY_THRESHOLD:
        return "Moderate"
    return "Heavy"


def green_duration(vehicle_count: int) -> int:
    """Green time = minimum + extra seconds per vehicle, capped at the maximum."""
    seconds = settings.MIN_GREEN_SECONDS + vehicle_count * settings.SECONDS_PER_VEHICLE
    return min(seconds, settings.MAX_GREEN_SECONDS)


def build_fixed_plan() -> list:
    """Traditional signal: every road gets the same green time, in order."""
    plan = []
    for road in settings.ROADS:
        plan.append(
            {
                "road": road,
                "green": settings.FIXED_GREEN_SECONDS,
                "yellow": settings.YELLOW_SECONDS,
            }
        )
    return plan


def build_adaptive_plan(counts: dict) -> list:
    """Adaptive signal: busiest road goes first and gets more green time.

    Roads with zero vehicles are skipped for this cycle. They are served
    in the next cycle as soon as vehicles appear.
    """
    # Keep only roads that have vehicles.
    busy_roads = [road for road in settings.ROADS if counts.get(road, 0) > 0]

    # Sort busiest first. Python's sort is stable, so ties keep the
    # normal road order (North, East, South, West).
    busy_roads.sort(key=lambda road: counts[road], reverse=True)

    plan = []
    for road in busy_roads:
        plan.append(
            {
                "road": road,
                "green": green_duration(counts[road]),
                "yellow": settings.YELLOW_SECONDS,
            }
        )
    return plan


def total_cycle_seconds(plan: list) -> int:
    """Total time for one full pass through the plan (green + yellow)."""
    return sum(phase["green"] + phase["yellow"] for phase in plan)