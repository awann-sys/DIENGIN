import unittest

import dashboard_features as d


class TestWeatherInstruments(unittest.TestCase):
    def test_all_twelve_instrument_styles(self):
        self.assertEqual(len(d.INSTRUMENT_STYLES), 12)

    def test_unit_next_to_number(self):
        card = d._instrument_card("Suhu udara", 19.74, "°C", "Naik", "tt_air_avg")
        self.assertIn('dg-instrument-reading', card)
        self.assertIn('19,74', card)
        self.assertIn('°C', card)

    def test_missing_value_never_fake(self):
        card = d._instrument_card("Radiasi", None, "unit AWS", "Belum tersedia", "sr_avg")
        self.assertIn('>—</span>', card)
        self.assertNotIn('>unit AWS</span>', card)

    def test_escapes_untrusted_label(self):
        card = d._instrument_card("<script>", 2.0, "%", "ok", "rh_avg")
        self.assertNotIn("<script>", card)
        self.assertIn("&lt;script&gt;", card)


if __name__ == "__main__":
    unittest.main()
