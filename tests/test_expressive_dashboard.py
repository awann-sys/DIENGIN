"""Hourly display must preserve WIB, gaps, and actual operational values."""
import unittest

import pandas as pd

from expressive_dashboard import hourly_chart, hourly_series, phase_at
from src.history import flatten_monitoring


class HourlyDisplayTests(unittest.TestCase):
    def test_completed_hours_do_not_backdate_or_fill_gaps(self):
        frame = pd.DataFrame({
            "time": ["2026-10-15 21:00", "2026-10-15 21:50", "2026-10-16 00:00", "2026-10-16 00:20"],
            "tt_air_avg": [8, 7, 4, 3],
        })
        result = hourly_series(frame, "tt_air_avg")
        self.assertEqual(str(result.index.tz), "Asia/Jakarta")
        self.assertEqual(result.index[-1].hour, 0)
        self.assertEqual(result.iloc[1, 0], 7)
        self.assertTrue(pd.isna(result.iloc[2, 0]))
        self.assertEqual(result.iloc[-1, 0], 4)
        svg = hourly_chart(result, "tt_air_avg", "°C", "Suhu udara")
        self.assertEqual(svg.count("<circle"), 3)
        self.assertEqual(svg.count("<path"), 1)  # No line over the missing hour.

    def test_utc_converts_to_wib_and_infinity_is_missing(self):
        result = hourly_series(pd.DataFrame({
            "time": ["2026-10-15T17:00:00Z", "2026-10-15T18:00:00Z"],
            "p": [10, float("inf")],
        }), "p")
        self.assertEqual(result.index[0].hour, 0)
        self.assertTrue(pd.isna(result.iloc[-1, 0]))

    def test_empty_data_and_distinct_day_palettes(self):
        self.assertTrue(hourly_series(pd.DataFrame(), "p").empty)
        self.assertIn("Belum ada data", hourly_chart(pd.DataFrame(), "p", "%", "Probabilitas"))
        self.assertEqual(len({phase_at(h)[1] for h in [6, 12, 16, 18, 22]}), 5)

    def test_additional_aws_parameters_reach_history(self):
        result = flatten_monitoring({"status": "success", "latest_observation": {
            "time_wib": "2026-10-16T07:00:00+07:00",
            "parameters": {"tt_air_max": 13, "ws_max": 2, "sr_avg": 300, "sr_max": 400},
        }})
        self.assertEqual(result.iloc[0]["sr_max"], 400)
        self.assertEqual(result.iloc[0]["tt_air_max"], 13)


if __name__ == "__main__":
    unittest.main()
