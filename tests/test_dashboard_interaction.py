"""Exercise navigation, insight callbacks, missing data and night isolation."""
import unittest

from streamlit.testing.v1 import AppTest


FIXTURE = '''
import pandas as pd
import streamlit as st
import app
import nav_dashboard as nav

now = pd.Timestamp.now(tz="Asia/Jakarta").floor("h")
monitor = {"status":"success", "latest_observation":{"time_wib":now.isoformat(),
    "parameters":{"tt_air_avg":4,"rh_avg":90,"ws_avg":1,"dew_point_c":2}}}
pred = {"target_night_date":"2026-10-16", "threshold_stacked":0.5,
    "latest_release":{"stacked_probability":0.8,"hour_wib":1}}
mh = pd.DataFrame({"_time":[now-pd.Timedelta(hours=1), now], "tt_air_avg":[5,4]})
rh = pd.DataFrame({"_time":[now-pd.Timedelta(hours=1), now],
    "tanggal_target":["2026-10-15","2026-10-16"], "stack_prob":[0.2,0.8]})
app.get_bmkg_forecast = lambda: ({}, "unavailable")
app.render_bmkg_forecast = lambda now: st.info("Prakiraan belum tersedia")
nav._load_data = lambda: (monitor, pred, {}, mh, rh, pd.DataFrame(), {"monitoring":"ok"})
if st.session_state.get("empty_fixture"):
    nav._load_data = lambda: ({}, {}, {}, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {"monitoring":"missing"})
st.markdown(nav.base.CSS, unsafe_allow_html=True)
nav.dashboard()
'''


class DashboardInteractionTests(unittest.TestCase):
    def test_insight_callback_navigation_and_missing_data(self):
        app = AppTest.from_string(FIXTURE).run(timeout=20)
        self.assertFalse(app.exception)
        markup = " ".join(item.value for item in app.markdown)
        self.assertIn("Ilustrasi potensi frost model", markup)
        self.assertIn("80.0", markup)
        self.assertNotIn(">20.0</text>", markup)  # Previous target night excluded.
        app.button(key="dg_insight_button_1").click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="dg_journey_parameter").value, "Suhu udara")
        app.session_state["dg_primary_nav"] = "Monitoring"
        app.run(timeout=20)
        self.assertFalse(app.exception)
        self.assertNotIn("Probabilitas ANN", app.selectbox(key="dg_monitor_parameter").options)
        app.session_state["dg_primary_nav"] = "Prospek BMKG"
        app.run(timeout=20)
        self.assertFalse(app.exception)
        app.session_state["dg_primary_nav"] = "Prediksi"
        app.session_state["empty_fixture"] = True
        app.run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(app.info)


if __name__ == "__main__":
    unittest.main()
