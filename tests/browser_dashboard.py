"""Capture desktop/mobile views and verify basic browser behavior."""
import base64
import io
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright
from test_dashboard import write_fixture

ROOT = Path(__file__).resolve().parents[1]
artifacts = ROOT / "ui-review"
artifacts.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp)
    shutil.copyfile(ROOT / "app.py", work / "app.py")
    write_fixture(work)
    for theme, port in [("dark", 8501), ("light", 8502)]:
        proc = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", str(work / "app.py"),
             "--server.headless=true", f"--server.port={port}", f"--theme.base={theme}",
             "--browser.gatherUsageStats=false"],
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
        )
        try:
            for _ in range(150):
                try:
                    urllib.request.urlopen(f"http://localhost:{port}/_stcore/health", timeout=1)
                    break
                except OSError:
                    time.sleep(.2)
            with sync_playwright() as p:
                browser = p.chromium.launch()
                for device, viewport in [("desktop", {"width": 1440, "height": 960}),
                                          ("mobile", {"width": 390, "height": 844})]:
                    context = browser.new_context(viewport=viewport, device_scale_factor=1,
                                                   timezone_id="America/New_York")
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("console", lambda message: print("BROWSER_CONSOLE:", message.type, message.text, flush=True) if message.type == "error" else None)
                    page.goto(f"http://localhost:{port}", wait_until="networkidle")
                    page.get_by_text("Terindikasi embun beku", exact=True).wait_for(timeout=60000)
                    try:
                        page.locator('[data-testid="stVegaLiteChart"]').first.wait_for(timeout=10000)
                    except Exception:
                        print("CHART_ERRORS:", errors, flush=True)
                    page.screenshot(path=str(artifacts / f"{theme}-{device}.png"), full_page=True)
                    if theme == "dark":
                        preview = Image.open(artifacts / f"{theme}-{device}.png").convert("RGB")
                        preview.thumbnail((1280, 1500))
                        buffer = io.BytesIO()
                        preview.save(buffer, format="JPEG", quality=70)
                        print(f"UI_PREVIEW:{device}:" + base64.b64encode(buffer.getvalue()).decode(), flush=True)
                    assert page.locator('[data-testid="stVegaLiteChart"]').first.is_visible(), "Chart did not render"
                    assert page.locator('[data-testid="stException"]').count() == 0
                    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2"), "Horizontal page overflow"
                    # Primary weather values must be visible near the top on desktop.
                    if device == "desktop":
                        bounds = page.get_by_text("Suhu udara", exact=True).first.bounding_box()
                        assert bounds and bounds["y"] < 500, bounds
                    page.get_by_role("tab", name="Eksplorasi data").click()
                    page.get_by_text("Eksplorasi observasi", exact=True).wait_for()
                    page.get_by_role("tab", name="Panduan & status").click()
                    page.get_by_text("Kenali angkanya", exact=True).wait_for()
                    assert not errors, errors
                    context.close()
                browser.close()
        finally:
            proc.terminate()
            proc.wait(timeout=15)
