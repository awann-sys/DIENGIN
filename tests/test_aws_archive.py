import tempfile
import unittest
from pathlib import Path
import pandas as pd
from src.archive_aws import store_months

class ArchiveTests(unittest.TestCase):
    def test_month_partition_and_upsert(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            frame = pd.DataFrame({'id_station': ['STA2285', 'STA2285'], 'datetime_utc': ['2020-01-31T16:50:00Z', '2020-01-31T17:00:00Z'], 'tt_air_avg': [2., 3.]})
            store_months(frame, root)
            frame.loc[0, 'tt_air_avg'] = 4.
            store_months(frame, root)
            jan = pd.read_csv(root / 'observations/2020-01.csv.gz')
            feb = pd.read_csv(root / 'observations/2020-02.csv.gz')
            self.assertEqual(len(jan), 1)
            self.assertEqual(len(feb), 1)
            self.assertEqual(jan.iloc[0]['tt_air_avg'], 4.)

