"""Automatic checks for the simulation engine."""

import unittest

from config import settings
from src.signal_control.simulation import IntersectionSimulation, generate_arrivals

RATES = {"North": 0.15, "East": 0.08, "South": 0.03, "West": 0.0}
DURATION = 600
SEED = 42


def make_sim(mode, rates=RATES):
    arrivals = generate_arrivals(rates, DURATION, SEED)
    return IntersectionSimulation(mode, arrivals, DURATION)


def run_to_end(sim):
    while not sim.finished:
        sim.step()


class TestSimulation(unittest.TestCase):
    def test_arrivals_same_seed_identical_and_different_seed_differs(self):
        first = generate_arrivals(RATES, DURATION, 1)
        second = generate_arrivals(RATES, DURATION, 1)
        other = generate_arrivals(RATES, DURATION, 2)
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)

    def test_never_two_roads_active_and_no_direct_green_to_green_switch(self):
        for mode in ("fixed", "adaptive"):
            sim = make_sim(mode)
            previous_green = None
            for _ in range(DURATION):
                sim.step()
                states = sim.signal_states()
                active = [r for r, s in states.items() if s != "RED"]
                self.assertEqual(len(active), 1)
                greens = [r for r, s in states.items() if s == "GREEN"]
                green = greens[0] if greens else None
                if previous_green and green:
                    self.assertEqual(previous_green, green)
                previous_green = green

    def test_green_durations_within_limits(self):
        for mode in ("fixed", "adaptive"):
            sim = make_sim(mode)
            run_to_end(sim)
            self.assertGreater(len(sim.green_log), 0)
            for entry in sim.green_log:
                self.assertGreaterEqual(entry["seconds"], settings.MIN_GREEN_SECONDS)
                self.assertLessEqual(entry["seconds"], settings.MAX_GREEN_SECONDS)

    def test_vehicle_and_waiting_time_bookkeeping(self):
        for mode in ("fixed", "adaptive"):
            sim = make_sim(mode)
            run_to_end(sim)
            still_waiting = sum(len(q) for q in sim.queues.values())
            self.assertEqual(sim.arrived, sim.served + still_waiting)

            waiting_so_far = sum(
                sim.time - arrival_time
                for queue in sim.queues.values()
                for arrival_time in queue
            )
            self.assertEqual(sim.total_wait, sim.served_wait_sum + waiting_so_far)

    def test_adaptive_never_serves_empty_road(self):
        sim = make_sim("adaptive")
        run_to_end(sim)
        self.assertEqual(sim.arrived_by_road["West"], 0)
        self.assertEqual(sim.served_by_road["West"], 0)
        self.assertNotIn("West", [entry["road"] for entry in sim.green_log])

    def test_fixed_cycles_in_order(self):
        sim = make_sim("fixed")
        run_to_end(sim)
        roads = [entry["road"] for entry in sim.green_log]
        for index, road in enumerate(roads):
            self.assertEqual(road, settings.ROADS[index % len(settings.ROADS)])

    def test_no_traffic_runs_cleanly(self):
        zero = {road: 0.0 for road in settings.ROADS}
        for mode in ("fixed", "adaptive"):
            sim = make_sim(mode, zero)
            run_to_end(sim)
            self.assertTrue(sim.finished)
            self.assertEqual(sim.served, 0)
            self.assertEqual(sim.total_wait, 0)


if __name__ == "__main__":
    unittest.main()