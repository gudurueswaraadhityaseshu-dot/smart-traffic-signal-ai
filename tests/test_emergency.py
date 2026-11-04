"""Automatic checks for emergency vehicle priority."""

import unittest

from config import settings
from src.signal_control.simulation import IntersectionSimulation, generate_arrivals

RATES = {"North": 0.15, "East": 0.08, "South": 0.03, "West": 0.0}
DURATION = 600
SEED = 42


def make_sim(mode, events=None):
    arrivals = generate_arrivals(RATES, DURATION, SEED)
    return IntersectionSimulation(mode, arrivals, DURATION, emergency_events=events)


def run_to_end(sim):
    while not sim.finished:
        sim.step()


class TestEmergency(unittest.TestCase):
    def test_adaptive_ambulance_never_waits_at_stop_line(self):
        for road in settings.ROADS:
            for second in (15, 20, 33, 47):
                sim = make_sim("adaptive", [(road, second)])
                run_to_end(sim)
                self.assertEqual(len(sim.emergency_log), 1)
                self.assertEqual(sim.emergency_pending, [])
                self.assertEqual(sim.emergency_log[0]["wait"], 0)

    def test_adaptive_ambulance_wait_not_worse_than_fixed(self):
        for road in settings.ROADS:
            for second in (15, 20, 33, 47):
                adaptive = make_sim("adaptive", [(road, second)])
                fixed = make_sim("fixed", [(road, second)])
                run_to_end(adaptive)
                run_to_end(fixed)
                self.assertEqual(len(fixed.emergency_log), 1)
                self.assertLessEqual(
                    adaptive.emergency_log[0]["wait"], fixed.emergency_log[0]["wait"]
                )

    def test_safety_holds_with_several_ambulances(self):
        events = [("West", 20), ("East", 25), ("South", 60), ("North", 61)]
        sim = make_sim("adaptive", events)
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
        self.assertEqual(len(sim.emergency_log), 4)
        self.assertEqual(sim.emergency_pending, [])

    def test_normal_vehicle_bookkeeping_still_balances(self):
        sim = make_sim("adaptive", [("West", 20), ("East", 90)])
        run_to_end(sim)
        still_waiting = sum(len(q) for q in sim.queues.values())
        self.assertEqual(sim.arrived, sim.served + still_waiting)
        waiting_so_far = sum(
            sim.time - arrival_time
            for queue in sim.queues.values()
            for arrival_time in queue
        )
        self.assertEqual(sim.total_wait, sim.served_wait_sum + waiting_so_far)

    def test_scheduled_event_matches_manual_dispatch(self):
        scheduled = make_sim("adaptive", [("East", 30)])
        manual = make_sim("adaptive")
        for _ in range(30):
            manual.step()
        manual.dispatch_ambulance("East")
        run_to_end(scheduled)
        run_to_end(manual)
        self.assertEqual(scheduled.emergency_log, manual.emergency_log)
        self.assertEqual(scheduled.served, manual.served)
        self.assertEqual(scheduled.total_wait, manual.total_wait)

    def test_only_adaptive_preempts(self):
        fixed = make_sim("fixed", [("West", 5)])
        run_to_end(fixed)
        self.assertFalse(any(entry["preempted"] for entry in fixed.green_log))

        adaptive = make_sim("adaptive", [("West", 5)])
        run_to_end(adaptive)
        preempted = [e for e in adaptive.green_log if e["preempted"]]
        self.assertGreaterEqual(len(preempted), 1)
        self.assertEqual(preempted[0]["road"], "North")  # North was green at second 5


if __name__ == "__main__":
    unittest.main()