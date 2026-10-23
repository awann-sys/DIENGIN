"""All active chart families receive the same QC-cleaned AWS archive."""
import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import dashboard_features as features


class ArchiveChartTests(unittest.TestCase):
    def test_overlap_preserves_archive_missing_and_zero_and_extends_latest(self):
        recent = pd.DataFrame({
            '_time': pd.to_datetime(['2026-01-01T00:00:00+07:00', '2026-01-01T00:10:00+07:00', '2026-10-23T00:00:00+07:00']),
            'tt_air_avg': [99., 99., 8.], 'rr': [5., 5., 0.],
        })
        archive = pd.DataFrame({
            '_time': pd.to_datetime(['2025-12-31T17:00:00Z', '2025-12-31T17:10:00Z']),
            'tt_air_avg': [float('nan'), 0.], 'rr': [0., 0.],
        })
        result = features.merge_chart_weather_history(recent, archive)
        self.assertEqual(len(result), 3)
        self.assertEqual(str(result['_time'].dt.tz), 'Asia/Jakarta')
        self.assertTrue(pd.isna(result.iloc[0]['tt_air_avg']))
        self.assertEqual(result.iloc[1]['tt_air_avg'], 0.)
        self.assertEqual(result.iloc[0]['rr'], 0.)
        self.assertEqual(result.iloc[-1]['tt_air_avg'], 8.)

    def test_archive_available_without_runtime_and_failure_is_distinct(self):
        archive = pd.DataFrame({'_time': pd.to_datetime(['2021-01-01T00:00:00Z']), 'tt_air_avg': [5.]})
        with patch.object(features, '_chart_archive', return_value=archive):
            frame, status = features.load_chart_weather_history(pd.DataFrame())
        self.assertEqual(status, 'ok')
        self.assertEqual(len(frame), 1)
        with patch.object(features, '_chart_archive', side_effect=OSError('offline')):
            frame, status = features.load_chart_weather_history(archive)
        self.assertEqual(status, 'unavailable')
        pd.testing.assert_frame_equal(frame, archive)

    def test_selected_wib_range_loads_previous_utc_month(self):
        data = pd.DataFrame({
            '_time': pd.to_datetime(['2025-12-31T16:50:00Z', '2025-12-31T17:00:00Z', '2026-01-01T17:00:00Z']).tz_convert(features.WIB),
            'tt_air_avg': [9., 4., 8.],
        })
        features.fetch_stored_aws_archive.clear()
        with patch.object(features, '_read_aws_archive_file', return_value=data) as reader:
            result = features.fetch_stored_aws_archive('2026-01-01T00:00:00+07:00', '2026-01-01T23:59:59+07:00')
        self.assertEqual([call.args[0] for call in reader.call_args_list], ['observations/2025-12.csv.gz', 'observations/2026-01.csv.gz'])
        self.assertEqual(result['tt_air_avg'].tolist(), [4.])

    def test_long_range_uses_full_database_export(self):
        data = pd.DataFrame({'_time': pd.to_datetime(['2021-01-01T00:00:00Z', '2026-03-04T00:00:00Z']).tz_convert(features.WIB), 'tt_air_avg': [4., 5.]})
        features.fetch_stored_aws_archive.clear()
        with patch.object(features, '_read_aws_archive_file', return_value=data) as reader:
            result = features.fetch_stored_aws_archive('2021-01-01', '2026-03-05')
        reader.assert_called_once_with('aws_dieng_merged.csv.gz')
        self.assertEqual(len(result), 2)

    def test_journey_and_multivariable_explorer_accept_historical_range(self):
        fixture = '''
import pandas as pd
import streamlit as st
import dashboard_features as features
import expressive_dashboard as design
import nav_dashboard as nav
from unittest.mock import patch
archive = pd.DataFrame({'_time': pd.to_datetime(['2021-01-01T00:00:00Z', '2026-01-01T00:00:00Z', '2026-03-04T00:00:00Z', '2026-10-23T00:00:00Z']), 'tt_air_avg': [3., 4., 5., 6.]})
with patch.object(features, '_chart_archive', return_value=archive), patch.object(nav.base, 'read_file', side_effect=lambda relative, kind='json': ((pd.DataFrame() if kind == 'csv' else {}), 'ok')):
    _, _, _, mh, rh, _, _ = nav._load_data()
with patch.object(features, 'render_interactive_chart', side_effect=lambda series, key, unit, label: st.text('SERIES=' + ','.join(series[key].dropna().astype(str)))), patch.object(st, 'dataframe'):
    design.render_journey(mh, rh, {}, include_models=False)
    features.render_custom_explorer(mh, rh, key_prefix='archive_test', include_models=False, default_labels=['Suhu udara'], allow_download=True)
'''
        app = AppTest.from_string(fixture).run(timeout=30)
        self.assertFalse(app.exception)
        app.date_input(key='monitoring_chart_start').set_value(date(2026, 1, 1))
        app.date_input(key='monitoring_chart_end').set_value(date(2026, 3, 4))
        app.date_input(key='archive_test_from_0').set_value(date(2026, 1, 1))
        app.date_input(key='archive_test_to_0').set_value(date(2026, 3, 4))
        app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertIn('SERIES=4.0,5.0', [item.value for item in app.text])
        markup = ' '.join(item.value for item in app.markdown)
        self.assertIn('4.00', markup)
        self.assertIn('5.00', markup)
        self.assertNotIn('6.00 °C', markup)
        app.date_input(key='monitoring_chart_start').set_value(date(2021, 1, 1))
        app.date_input(key='monitoring_chart_end').set_value(date(2021, 1, 1))
        app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertIn('SERIES=3.0', [item.value for item in app.text])


if __name__ == '__main__':
    unittest.main()
