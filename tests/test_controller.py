"""Automatic checks for the signal controller. Run with unittest."""

import unittest

from config import settings
from src.signal_control.controller import (
    build_adaptive_plan,
    build_fixed_plan,
    density_label,
    green_duration,
)


class TestController(unittest.TestCase):
    def test_density_labels(self):
        self.assertEqual(density_label(0), "None")
        self.assertEqual(density_label(3), "Low")
        self.assertEqual(density_label(10), "Moderate")
        self.assertEqual(density_label(20), "Heavy")

    def test_green_duration_respects_limits(self):
        self.assertGreaterEqual(green_duration(0), settings.MIN_GREEN_SECONDS)
        self.assertEqual(green_duration(1000), settings.MAX_GREEN_SECONDS)

    def test_fixed_plan_serves_all_roads_equally(self):
        plan = build_fixed_plan()
        self.assertEqual(len(plan), 4)
        self.assertEqual({p["green"] for p in plan}, {settings.FIXED_GREEN_SECONDS})

    def test_adaptive_plan_busiest_first_and_skips_empty(self):
        counts = {"North": 20, "East": 10, "South": 4, "West": 0}
        plan = build_adaptive_plan(counts)
        self.assertEqual([p["road"] for p in plan], ["North", "East", "South"])
        self.assertGreaterEqual(plan[0]["green"], plan[1]["green"])

    def test_adaptive_plan_empty_when_no_traffic(self):
        counts = {road: 0 for road in settings.ROADS}
        self.assertEqual(build_adaptive_plan(counts), [])


if __name__ == "__main__":
    unittest.main()