"""A second-by-second simulation of one four-road intersection.

Two control modes are supported:
  "fixed"    - every road gets the same green time, in order.
  "adaptive" - busiest road first, green time depends on queue length,
               and ambulances get priority.

This file does NOT use Streamlit, so it can be tested on its own and
reused later for the fair fixed-vs-adaptive comparison.
"""

from collections import deque

import numpy as np

from config import settings
from src.signal_control.controller import green_duration


def generate_arrivals(rates_per_second: dict, duration: int, seed: int) -> dict:
    """Create the full list of vehicle arrivals for every road in advance.

    Returns {road: [vehicles arriving in second 0, second 1, ...]}.
    The same seed and rates always give exactly the same traffic.
    """
    arrivals = {}
    for index, road in enumerate(settings.ROADS):
        # Each road has its own random generator, so changing one road's
        # rate does not change the random traffic on the other roads.
        rng = np.random.default_rng([seed, index])
        counts = rng.poisson(rates_per_second.get(road, 0.0), size=duration)
        arrivals[road] = [int(c) for c in counts]
    return arrivals


class IntersectionSimulation:
    """One intersection, advanced one second at a time with step().

    emergency_events is an optional list of (road, second) pairs. At that
    simulated second an ambulance is detected approaching on that road.
    """

    def __init__(self, mode: str, arrivals: dict, duration: int, emergency_events=None):
        if mode not in ("fixed", "adaptive"):
            raise ValueError("mode must be 'fixed' or 'adaptive'")

        self.mode = mode
        self.arrivals = arrivals
        self.duration = duration
        self.time = 0  # seconds simulated so far

        # Each queue stores the arrival time of every waiting vehicle.
        self.queues = {road: deque() for road in settings.ROADS}
        self.last_green_end = {road: 0 for road in settings.ROADS}

        # ----- Metrics (normal vehicles) -----
        self.arrived = 0
        self.served = 0
        self.total_wait = 0          # vehicle-seconds spent waiting (everyone)
        self.served_wait_sum = 0     # waiting seconds of vehicles that left
        self.arrived_by_road = {road: 0 for road in settings.ROADS}
        self.served_by_road = {road: 0 for road in settings.ROADS}
        self.green_log = []          # one entry per finished green phase
        self.history = {road: [] for road in settings.ROADS}

        # ----- Emergency vehicles (kept separate from normal vehicles) -----
        self.scheduled_emergencies = list(emergency_events or [])
        self.emergency_pending = []  # ambulances not yet through
        self.emergency_log = []      # ambulances that have passed

        # ----- Signal state -----
        self.current_road = settings.ROADS[0]
        self.next_road = None
        self.phase = "GREEN"         # "GREEN" or "YELLOW"
        self.phase_elapsed = 0
        self.phase_length = 0
        self._start_green()

    # ------------------------------------------------------------------
    # Things the dashboard can read
    # ------------------------------------------------------------------
    @property
    def finished(self) -> bool:
        return self.time >= self.duration

    def queue_length(self, road: str) -> int:
        return len(self.queues[road])

    def signal_states(self) -> dict:
        """Colour of every road. Only the current road is ever not RED."""
        states = {road: "RED" for road in settings.ROADS}
        states[self.current_road] = self.phase
        return states

    def seconds_left(self) -> int:
        """Countdown for the current green or yellow phase."""
        return max(self.phase_length - self.phase_elapsed, 0)

    @property
    def average_wait_served(self) -> float:
        """Average seconds a vehicle waited before it was served."""
        if self.served == 0:
            return 0.0
        return self.served_wait_sum / self.served

    @property
    def average_queue_per_road(self) -> float:
        """Average number of waiting vehicles per road, over time."""
        if self.time == 0:
            return 0.0
        return self.total_wait / (self.time * len(settings.ROADS))

    @property
    def emergency_served(self) -> int:
        return len(self.emergency_log)

    @property
    def average_emergency_wait(self) -> float:
        """Average seconds ambulances waited at the stop line."""
        if not self.emergency_log:
            return 0.0
        return sum(entry["wait"] for entry in self.emergency_log) / len(self.emergency_log)

    def ambulance_on_road(self, road: str) -> bool:
        return any(a["road"] == road for a in self.emergency_pending)

    def emergency_status(self):
        """Info about the earliest waiting ambulance, or None if there is none."""
        if not self.emergency_pending:
            return None
        first = min(self.emergency_pending, key=lambda a: a["detected"])
        return {
            "road": first["road"],
            "seconds_to_reach": max(first["reach"] - self.time, 0),
        }

    # ------------------------------------------------------------------
    # Emergency vehicles
    # ------------------------------------------------------------------
    def dispatch_ambulance(self, road: str) -> None:
        """An ambulance is detected approaching on `road` right now."""
        if road not in settings.ROADS:
            raise ValueError(f"Unknown road: {road}")
        self.emergency_pending.append(
            {
                "road": road,
                "detected": self.time,
                "reach": self.time + settings.AMBULANCE_APPROACH_SECONDS,
            }
        )
        # Adaptive control reacts straight away instead of waiting a second.
        self._emergency_priority_step()

    def _emergency_road(self):
        """Road of the earliest detected ambulance (adaptive mode only)."""
        if self.mode != "adaptive" or not self.emergency_pending:
            return None
        first = min(self.emergency_pending, key=lambda a: a["detected"])
        return first["road"]

    def _pass_ambulances(self, t: int) -> None:
        """Ambulances at the stop line of the green road drive through."""
        for ambulance in list(self.emergency_pending):
            if ambulance["road"] == self.current_road and ambulance["reach"] <= t:
                self.emergency_pending.remove(ambulance)
                self.emergency_log.append(
                    {
                        "road": ambulance["road"],
                        "detected": ambulance["detected"],
                        "reach": ambulance["reach"],
                        "passed": t,
                        "wait": t - ambulance["reach"],
                    }
                )

    def _emergency_priority_step(self) -> bool:
        """Adaptive priority rule. Returns True if normal green logic must be skipped.

        - Ambulance on another road: end this green now. A yellow follows,
          so the change is still safe.
        - Ambulance on the current road: hold the green (never beyond the
          maximum green time) until it has passed.
        """
        if self.mode != "adaptive" or self.phase != "GREEN":
            return False
        road = self._emergency_road()
        if road is None:
            return False
        if road != self.current_road:
            self._end_green(preempted=True)
            return True
        return self.phase_elapsed < settings.MAX_GREEN_SECONDS

    # ------------------------------------------------------------------
    # Moving the simulation forward
    # ------------------------------------------------------------------
    def step(self) -> None:
        """Advance the simulation by exactly one second."""
        if self.finished:
            return

        t = self.time

        # 0. Scheduled ambulances are detected.
        for road, second in self.scheduled_emergencies:
            if second == t:
                self.dispatch_ambulance(road)

        # 1. New vehicles arrive.
        for road in settings.ROADS:
            for _ in range(self.arrivals[road][t]):
                self.queues[road].append(t)
                self.arrived += 1
                self.arrived_by_road[road] += 1

        # 2. On green, ambulances pass and one vehicle leaves every few seconds.
        if self.phase == "GREEN":
            self._pass_ambulances(t)
            if (self.phase_elapsed + 1) % settings.DEPARTURE_INTERVAL_SECONDS == 0:
                queue = self.queues[self.current_road]
                if queue:
                    arrival_time = queue.popleft()
                    self.served += 1
                    self.served_by_road[self.current_road] += 1
                    self.served_wait_sum += t - arrival_time

        # 3. Every vehicle still waiting adds one second of waiting time.
        self.total_wait += sum(len(q) for q in self.queues.values())
        for road in settings.ROADS:
            self.history[road].append(len(self.queues[road]))

        # 4. Move the clock and the signal timer forward.
        self.time += 1
        self.phase_elapsed += 1
        self._advance_signal()

    # ------------------------------------------------------------------
    # Signal logic (private helpers)
    # ------------------------------------------------------------------
    def _start_green(self) -> None:
        self.phase = "GREEN"
        self.phase_elapsed = 0
        if self.mode == "fixed":
            self.phase_length = settings.FIXED_GREEN_SECONDS
        else:
            self.phase_length = green_duration(len(self.queues[self.current_road]))

    def _advance_signal(self) -> None:
        if self.phase == "GREEN":
            if self._emergency_priority_step():
                return
            green_over = self.phase_elapsed >= self.phase_length
            if not green_over and self.mode == "adaptive" and self._can_end_early():
                green_over = True
            if green_over:
                self._end_green()
        else:  # YELLOW
            if self.phase_elapsed >= self.phase_length:
                target = self.next_road
                emergency_road = self._emergency_road()
                if emergency_road is not None:
                    target = emergency_road  # ambulance gets the next green
                self.current_road = target
                self.next_road = None
                self._start_green()

    def _can_end_early(self) -> bool:
        """Adaptive only: end green early if the road emptied and others wait.

        The minimum green time is always respected.
        """
        if self.phase_elapsed < settings.MIN_GREEN_SECONDS:
            return False
        if self.queues[self.current_road]:
            return False
        return any(len(q) > 0 for q in self.queues.values())

    def _end_green(self, preempted: bool = False) -> None:
        self.green_log.append(
            {
                "road": self.current_road,
                "seconds": self.phase_elapsed,
                "preempted": preempted,
            }
        )
        self.last_green_end[self.current_road] = self.time

        chosen = self._choose_next_road()
        if chosen == self.current_road:
            # Same road keeps going: no yellow needed, start a new green.
            self._start_green()
        else:
            self.next_road = chosen
            self.phase = "YELLOW"
            self.phase_elapsed = 0
            self.phase_length = settings.YELLOW_SECONDS

    def _choose_next_road(self) -> str:
        roads = settings.ROADS

        if self.mode == "fixed":
            index = roads.index(self.current_road)
            return roads[(index + 1) % len(roads)]

        # Adaptive: an ambulance always wins.
        emergency_road = self._emergency_road()
        if emergency_road is not None:
            return emergency_road

        # Otherwise highest score wins. Roads with no vehicles are skipped.
        best_road = None
        best_score = 0.0
        for road in roads:
            waiting = len(self.queues[road])
            if waiting == 0:
                continue
            waited = self.time - self.last_green_end[road]
            score = waiting + settings.STARVATION_BONUS_PER_SECOND * waited
            if best_road is None or score > best_score:
                best_road = road
                best_score = score

        # Nobody is waiting anywhere: stay on the current road.
        return best_road if best_road is not None else self.current_road