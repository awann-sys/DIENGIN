"""Regression checks for the Web 2.0 frost dashboard presentation."""
import unittest
import ast
from pathlib import Path

import pandas as pd

import web2_visuals as ui


class TestWeb2Presentation(unittest.TestCase):
    def setUp(self):
        self.pred = {
            "target_night_date": "2026-10-19",
            "threshold_stacked": 0.2969953,
            "data_status": "stale",
            "latest_release": {"hour_wib": 7, "stacked_probability": 0.0902578},
        }
        self.monitor = {"latest_observation": {
            "time_wib": "2026-10-19T08:40:00+07:00",
            "parameters": {"tt_air_avg": 19.74},
        }}
        self.now = pd.Timestamp("2026-10-19T12:10:00+07:00")

    def test_hero_renders_real_probability_and_threshold(self):
        markup = ui.hero_markup(self.pred, self.monitor, {"probability_now": 0.0902578}, "", self.now)
        self.assertIn("9.03", markup)
        self.assertIn("29.70%", markup)
        self.assertIn("07.00 WIB", markup)
        self.assertIn("19.7 °C", markup)
        self.assertIn("Suasana Siang", markup)
        self.assertIn("Data prediksi perlu diperiksa", markup)

    def test_missing_values_remain_missing(self):
        markup = ui.hero_markup({}, {}, {}, "", self.now)
        self.assertIn("Probabilitas belum tersedia", markup)
        self.assertNotIn("nan", markup.lower())
        self.assertNotIn("100.00%", markup)

    def test_scene_tracks_wib(self):
        morning = ui.scene_markup(pd.Timestamp("2026-10-19T06:30:00+07:00"))
        night = ui.scene_markup(pd.Timestamp("2026-10-19T22:30:00+07:00"))
        self.assertIn("suasana pagi", morning)
        self.assertIn("suasana malam", night)
        self.assertIn("dg-scene", morning)

    def test_untrusted_text_escaped(self):
        markup = ui.hero_markup({"target_night_date": "<script>alert(1)</script>"}, {}, {}, "", self.now)
        self.assertNotIn("<script>", markup)
        self.assertIn("&lt;script&gt;", markup)

    def test_navigation_default_is_a_valid_option(self):
        source = Path("nav_dashboard.py").read_text(encoding="utf-8")
        module = ast.parse(source)
        nav = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "_top_nav")
        options = None
        default = None
        for node in ast.walk(nav):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "options" for t in node.targets):
                options = ast.literal_eval(node.value)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "segmented_control":
                default = next((ast.literal_eval(kw.value) for kw in node.keywords if kw.arg == "default"), None)
        self.assertIsNotNone(options)
        self.assertIn(default, options)

    def test_sticky_header_and_grid_present(self):
        self.assertIn("position:sticky", ui.CSS)
        self.assertIn("grid-template-columns:minmax(0,1.7fr)", ui.CSS)
        self.assertIn(".dg-prediction-instruments", ui.CSS)


if __name__ == "__main__":
    unittest.main()
