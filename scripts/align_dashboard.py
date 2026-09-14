from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

old_css = '''.dg-panel-title {
    display: flex;
    align-items: center;
    gap: .5rem;
    font-size: 1.22rem;
    font-weight: 650;
    margin: .2rem 0 .35rem;
}
.dg-panel-title .dg-panel-emoji { font-size: 1.05rem; }
'''
new_css = '''.dg-panel-title {
    display: flex;
    align-items: center;
    font-size: 1.22rem;
    font-weight: 650;
    line-height: 1.3;
    margin: .15rem 0 .1rem;
}
.dg-field-note {
    font-size: .78rem;
    opacity: .68;
    margin: .1rem 0 .2rem;
}
'''

old_trend = '''def render_trend(mh):
    title, control = st.columns([1.8, 1])
    with title:
        st.markdown(
            '<div class="dg-panel-title"><span class="dg-panel-emoji">📈</span><span>Jejak cuaca</span></div>',
            unsafe_allow_html=True,
        )
    with control:
        hours = st.selectbox(
            "Rentang waktu",
            [6, 12, 24, 48],
            index=2,
            format_func=lambda x: f"{x} jam terakhir",
            key="trend_hours",
            label_visibility="collapsed",
        )
    if mh.empty:
'''
new_trend = '''def render_trend(mh):
    st.markdown('<div class="dg-panel-title">Jejak cuaca</div>', unsafe_allow_html=True)
    st.markdown('<div class="dg-field-note">Rentang waktu</div>', unsafe_allow_html=True)
    hours = st.selectbox(
        "Rentang waktu",
        [6, 12, 24, 48],
        index=2,
        format_func=lambda x: f"{x} jam terakhir",
        key="trend_hours",
        label_visibility="collapsed",
    )
    if mh.empty:
'''

old_prediction_title = '''def render_prediction_history(rh, nights, pred, now):
    st.markdown(
        '<div class="dg-panel-title"><span class="dg-panel-emoji">❄️</span><span>Perjalanan prediksi</span></div>',
        unsafe_allow_html=True,
    )
'''
new_prediction_title = '''def render_prediction_history(rh, nights, pred, now):
    st.markdown('<div class="dg-panel-title">Perjalanan prediksi</div>', unsafe_allow_html=True)
'''

old_select = '''    target = st.selectbox("Tanggal target prediksi", dates, format_func=date_label, key="prediction_date")
'''
new_select = '''    st.markdown('<div class="dg-field-note">Tanggal target prediksi</div>', unsafe_allow_html=True)
    target = st.selectbox(
        "Tanggal target prediksi",
        dates,
        format_func=date_label,
        key="prediction_date",
        label_visibility="collapsed",
    )
'''

replacements = [
    (old_css, new_css, "panel CSS"),
    (old_trend, new_trend, "weather panel header"),
    (old_prediction_title, new_prediction_title, "prediction panel title"),
    (old_select, new_select, "prediction selector"),
]

for old, new, label in replacements:
    if old not in text:
        raise SystemExit(f"Expected block not found: {label}")
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("Dashboard lower panels aligned.")
