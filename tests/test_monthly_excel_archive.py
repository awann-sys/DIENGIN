import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from src.archive_aws_monthly import clean_excel, month_url, rebuild


class MonthlyArchiveTests(unittest.TestCase):
    def test_url_year_and_leap_month(self):
        now = date(2026, 10, 20)
        self.assertIn('/downloadaccesdata_year/2024/aws/STA2285/2024-02-01/2024-02-29', month_url(2024, 2, now))
        self.assertIn('/downloadaccesdata_currentyear/aws/STA2285/2026-10-01/2026-10-20', month_url(2026, 10, now))

    def test_clean_flags_duplicates_missing_and_wib(self):
        source = pd.DataFrame({'ID Stasiun': ['STA2285'] * 3, 'Tanggal': ['2021-01-01 00:00:00+00', '2021-01-01 00:00:00+00', 'bad'], 'tt_air_avg': [5., 6., 9.], 'tt_air_avg_flag': [0, 1, 0], 'rr': [0., None, 2.]})
        with patch('src.archive_aws_monthly.pd.read_excel', return_value=source):
            result, audit = clean_excel(b'placeholder')
        self.assertEqual(len(result), 1)
        self.assertTrue(pd.isna(result.iloc[0]['tt_air_avg']))
        self.assertTrue(pd.isna(result.iloc[0]['rr']))
        self.assertIn('07:00:00+07:00', result.iloc[0]['datetime_wib'])
        self.assertEqual(audit['duplicate_rows'], 1)
        self.assertEqual(audit['invalid_times'], 1)

    def test_rebuild_csv_and_sqlite(self):
        import sqlite3
        from contextlib import closing
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'observations').mkdir()
            pd.DataFrame({'id_station': ['STA2285'], 'datetime_utc': ['2021-01-01T00:00:00+00:00'], 'rr': [0.]}).to_csv(root / 'observations/2021-01.csv.gz', index=False)
            self.assertEqual(rebuild(root), 1)
            self.assertTrue((root / 'aws_dieng.sqlite.gz').exists())
            with closing(sqlite3.connect(root / 'aws_dieng.sqlite')) as connection:
                self.assertEqual(connection.execute('SELECT rr FROM observations').fetchone()[0], 0.)

