import threading, time
from unittest.mock import patch, MagicMock
from spool import Spool

def test_screenshot_auto_pushes_to_spool(tmp_path):
    sp = Spool(tmp_path)
    stop = threading.Event()
    fake_img = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

    class FakeScreenshot:
        def save(self, buf, format, **kw):
            buf.write(fake_img)

    with patch("client.SCREENSHOT_AVAILABLE", True), \
         patch("client.pyautogui") as mock_pg:
        mock_pg.screenshot.return_value = FakeScreenshot()
        import client as c
        t = threading.Thread(
            target=c._screenshot_auto_thread,
            args=(sp, stop, 0.05),
            daemon=True
        )
        t.start()
        time.sleep(0.2)
        stop.set()
        t.join(timeout=1)

    items = sp.pending()
    assert len(items) >= 1
    assert items[0]["kind"] == "screenshot"
