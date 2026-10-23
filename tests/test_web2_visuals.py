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
        self.assertIn('Skor peringatan', markup)
        self.assertIn('/100', markup)
        self.assertIn('Probabilitas asli: 9.03%', markup)

    def test_score_endpoints_threshold_and_monotonicity(self):
        threshold = 0.2969953759055436
        self.assertEqual(ui.warning_score(0, threshold), 0)
        self.assertEqual(ui.warning_score(threshold, threshold), 80)
        self.assertEqual(ui.warning_score(1, threshold), 100)
        self.assertAlmostEqual(ui.warning_score(threshold / 2, threshold), 40)
        scores = [ui.warning_score(p / 100, threshold) for p in range(101)]
        self.assertEqual(scores, sorted(scores))
        for p, t in [(None, threshold), (.2, None), (.2, 0), (.2, 1), (float('nan'), threshold), (1.1, threshold)]:
            self.assertIsNone(ui.warning_score(p, t))

    def test_threshold_score_and_badge_use_original_decision(self):
        import copy
        pred = copy.deepcopy(self.pred)
        threshold = pred['threshold_stacked']
        markup = ui.hero_markup(pred, self.monitor, {'probability_now': threshold}, '', self.now)
        self.assertIn('80.0<span>/100</span>', markup)
        self.assertIn('width:80.00%', markup)
        self.assertIn('● Siaga', markup)
        self.assertIn('dg2-level-siaga', markup)
        self.assertIn('dg2-warning', markup)
        self.assertEqual(pred, self.pred)
        below = ui.hero_markup(pred, self.monitor, {'probability_now': threshold - .01}, '', self.now)
        self.assertIn('● Waspada', below)
        self.assertNotIn('dg2-warning', below)

    def test_missing_values_remain_missing(self):
        markup = ui.hero_markup({}, {}, {}, "", self.now)
        self.assertIn("Belum tersedia", markup)
        self.assertIn('dg2-level-unavailable', markup)
        self.assertNotIn('● Aman', markup)
        self.assertNotIn("nan", markup.lower())
        self.assertNotIn("100.00%", markup)

    def test_three_level_boundaries_and_preventive_advice(self):
        threshold = self.pred['threshold_stacked']
        cases = [(0, 'aman'), (threshold / 2 - 1e-8, 'aman'),
                 (threshold / 2, 'waspada'), (threshold - 1e-8, 'waspada'),
                 (threshold, 'siaga'), (1, 'siaga')]
        for probability, expected in cases:
            level, name, advice = ui.warning_level(probability, threshold)
            self.assertEqual(level, expected)
            markup = ui.hero_markup(self.pred, self.monitor, {'probability_now': probability}, '', self.now)
            self.assertIn('dg2-level-' + expected, markup)
            self.assertIn('● ' + name, markup)
            self.assertIn(advice, markup)
            self.assertIn('Periksa waktu rilis', markup)
        self.assertIn('background:#166534', ui.CSS)
        self.assertIn('background:#fde047', ui.CSS)
        self.assertIn('background:#b91c1c', ui.CSS)

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
