import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest
from src import history


class InteractiveHistoryTests(unittest.TestCase):
    def test_chart_handles_gaps_and_wib_dates(self):
        import dashboard_features as features
        data = pd.DataFrame({'temperature': [4., float('nan'), 6., 7.]}, index=pd.date_range('2026-10-19 21:00', periods=4, freq='h', tz='Asia/Jakarta'))
        with patch.object(features.st, 'altair_chart') as output, patch.object(features.st, 'caption'):
            features.render_interactive_chart(data, 'temperature', '°C', 'Suhu')
        chart = output.call_args.args[0].to_dict()
        rows = next(iter(chart['datasets'].values()))
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]['Waktu WIB'], '19/10/2026 21:00')
        self.assertNotEqual(rows[0]['segment'], rows[1]['segment'])
        self.assertEqual(rows[1]['segment'], rows[2]['segment'])

    def test_archive_keeps_all_observations_and_deduplicates_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            processed = root / 'data' / 'processed'
            processed.mkdir(parents=True)
            pd.DataFrame({'datetime_wib': ['2026-10-19 21:00:00+07:00', '2026-10-19 21:10:00+07:00'], 'tt_air_avg': [4., 3.]}).to_csv(processed / 'aws_dieng_latest.csv', index=False)
            latest = root / 'latest.json'
            latest.write_text(json.dumps({'status': 'success', 'latest_observation': {'time_wib': '2026-10-19T21:10:00+07:00', 'parameters': {'tt_air_avg': 3.}}}))
            target = root / 'history.csv'
            with patch.object(history, 'PROJECT_ROOT', root), patch.object(history, 'MONITORING_LATEST', latest), patch.object(history, 'MONITORING_HISTORY', target):
                history.archive_monitoring()
                history.archive_monitoring()
            stored = pd.read_csv(target)
            self.assertEqual(len(stored), 2)
            self.assertEqual(stored['tt_air_avg'].tolist(), [4., 3.])

