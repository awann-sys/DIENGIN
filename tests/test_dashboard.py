"""Regression tests for data interpretation and the Streamlit UI."""
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app.py"
BASE = ROOT / "app_base.py"


def write_fixture(root):
    """Synthetic test data only, written outside the application repository."""
    (root / "output").mkdir(parents=True, exist_ok=True)
    (root / "data/history").mkdir(parents=True, exist_ok=True)
    now = pd.Timestamp.now(tz="Asia/Jakarta").floor("min")
    target = now.normalize() + (pd.Timedelta(days=1) if now.hour >= 19 else pd.Timedelta(0))
    monitor = {
        "status": "success", "monitoring_status": "partial", "generated_at_wib": now.isoformat(),
        "station": {"station_name": "AWS TEST · Data simulasi", "elevation_m": 2078},
        "latest_observation": {"time_wib": (now - pd.Timedelta(minutes=10)).isoformat(),
            "parameters": {"tt_air_avg": 7.4, "tt_air_min": 6.8, "rh_avg": None,
                           "ws_avg": 0, "dew_point_c": None, "rr": 0, "pp_air": 798.4, "wd_avg": 45}},
        "trend_1h": {"tt_air_avg_change": -2.3, "ws_avg_change": 0},
    }
    pred = {
        "status": "success", "target_night_date": target.date().isoformat(),
        "generated_at_wib": now.isoformat(), "latest_observation_wib": monitor["latest_observation"]["time_wib"],
        "probability_max_so_far": .42, "threshold_stacked": .297, "prediction_so_far": 1,
        "releases_available": 4, "releases_expected": 11, "night_complete": False,
        "latest_release": {"release_time_wib": now.floor("h").isoformat(), "stacked_probability": .31},
    }
    for filename, data in [("monitoring_latest.json", monitor), ("prediction_latest.json", pred),
                           ("pipeline_status.json", {"status": "success"})]:
        (root / "output" / filename).write_text(json.dumps(data), encoding="utf-8")
    times = pd.date_range(end=now - pd.Timedelta(minutes=10), periods=20, freq="20min")
    frame = pd.DataFrame({
        "observation_time_wib": [t.isoformat() for t in times],
        "tt_air_avg": [10 - i / 8 for i in range(20)], "tt_air_min": [9 - i / 8 for i in range(20)],
        "rh_avg": [94.0] * 16 + [None] * 4, "ws_avg": [0.0] * 20, "rr": [0.0] * 20,
    })
    frame.to_csv(root / "data/history/monitoring_history.csv", index=False)
    release = pd.DataFrame({
        "tanggal_target": [target.date().isoformat()] * 4,
        "jam_rilis_wib": [21, 22, 23, 0],
        "waktu_rilis_wib": [(target - pd.Timedelta(hours=3) + pd.Timedelta(hours=i)).isoformat() for i in range(4)],
        "stack_prob": [.10, .20, .42, .31], "ann_prob": [.3, .4, .5, .6],
        "svm_prob": [.01, .02, .03, .04], "rf_prob": [.1, .2, .3, .2], "status_data_rilis": ["tepat_waktu"] * 4,
    })
    release.to_csv(root / "data/history/prediction_release_history.csv", index=False)
    pd.DataFrame([{"tanggal_target": target.date().isoformat(), "jumlah_rilis_tersedia": 4,
                   "ambang_final": .297, "probabilitas_maksimum": .42, "prediksi_malam": 1}]
    ).to_csv(root / "data/history/prediction_night_history.csv", index=False)
    return monitor, pred


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copyfile(SOURCE, self.root / "app.py")
        shutil.copyfile(BASE, self.root / "app_base.py")
        self.monitor, self.pred = write_fixture(self.root)
        spec = importlib.util.spec_from_file_location("dashboard_under_test", self.root / "app.py")
        self.app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.app)

    def tearDown(self):
        self.temp.cleanup()

    def run_app(self):
        app = AppTest.from_file(str(self.root / "app.py"), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0, [str(e.value) for e in app.exception])
        return app

    def test_weather_and_prediction_render_without_sidebar(self):
        app = self.run_app()
        self.assertEqual([t.label for t in app.tabs], ["Ringkasan", "Eksplorasi data", "Panduan & status"])
        self.assertEqual(len(app.sidebar), 0)
        text = "\n".join(m.value for m in app.markdown)
        self.assertIn("Terindikasi embun beku", text)
        self.assertIn("42,0", text)
        self.assertIn("Belum tersedia / tidak lolos QC", text)

    def test_period_and_parameter_controls(self):
        app = self.run_app()
        app.selectbox(key="trend_hours").set_value(6).run()
        self.assertEqual(len(app.exception), 0)
        for value in ["Kelembapan", "Angin", "Hujan AWS", "Suhu"]:
            app.radio(key="weather_parameter").set_value(value).run()
            self.assertEqual(len(app.exception), 0, value)
        app.multiselect(key="explore_columns").set_value(["tt_air_avg"]).run()
        self.assertEqual(len(app.exception), 0)

    def test_missing_monitoring_does_not_hide_prediction(self):
        (self.root / "output/monitoring_latest.json").unlink()
        app = self.run_app()
        text = "\n".join(m.value for m in app.markdown)
        self.assertIn("Terindikasi embun beku", text)
        self.assertIn("Monitoring belum tersedia", text)

    def test_empty_and_malformed_files(self):
        for file in (self.root / "output").glob("*.json"):
            file.write_text("{broken", encoding="utf-8")
        for file in (self.root / "data/history").glob("*.csv"):
            file.write_text("", encoding="utf-8")
        app = self.run_app()
        self.assertIn("Prediksi belum tersedia", "\n".join(m.value for m in app.markdown))

    def test_missing_timestamp_columns_and_all_invalid_values(self):
        pd.DataFrame({"other": [1]}).to_csv(self.root / "data/history/prediction_release_history.csv", index=False)
        pd.DataFrame({"observation_time_wib": ["broken"], "tt_air_avg": ["oops"]}).to_csv(
            self.root / "data/history/monitoring_history.csv", index=False)
        self.run_app()

    def test_clock_age_boundaries_and_timezone(self):
        now = pd.Timestamp("2026-09-15 00:00", tz="Asia/Jakarta")
        for minutes, expected in [(10, "current"), (30, "current"), (31, "delayed"),
                                  (60, "delayed"), (61, "stale"), (-6, "future")]:
            self.assertEqual(self.app.freshness(now - pd.Timedelta(minutes=minutes), now)[0], expected)
        self.assertEqual(self.app.time_label("2026-09-14T17:00:00Z"), "15 Sep 2026, 00:00 WIB")
        self.assertEqual(self.app.time_label("2026-09-15 00:00"), "15 Sep 2026, 00:00 WIB")

    def test_stale_forecast_is_labeled_as_archive(self):
        now = pd.Timestamp("2026-09-16T01:00:00+07:00")
        pred = {**self.pred, "target_night_date": "2026-09-15"}
        self.assertEqual(self.app.prediction_state(pred, now)["status"], "Arsip prediksi")
        pred["probability_max_so_far"] = "NaN"
        self.assertFalse(self.app.prediction_state(pred, now)["valid"])

    def test_missing_values_and_time_gaps_split_lines(self):
        frame = pd.DataFrame({
            "observation_time_wib": ["2026-09-15T00:00+07:00", "2026-09-15T00:10+07:00",
                                     "2026-09-15T00:20+07:00", "2026-09-15T01:30+07:00"],
            "tt_air_avg": [7, None, 6, 5],
        })
        timed = self.app.timed_frame(frame, "observation_time_wib")
        rows = self.app.chart_rows(timed, {"tt_air_avg": "Suhu"})
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows["Segmen"].nunique(), 3)

    def test_zero_is_valid_and_untrusted_html_is_escaped(self):
        self.assertEqual(self.app.fmt(0), "0,0")
        self.assertEqual(self.app.fmt("bad"), "—")
        self.assertIn("&lt;script&gt;", self.app.weather_card("<script>", 0))
        self.assertIsNone(self.app.probability(1.1))


if __name__ == "__main__":
    unittest.main()
