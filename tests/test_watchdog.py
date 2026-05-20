import time, threading
from unittest.mock import MagicMock, patch


def test_watchdog_removes_dead_client():
    import server as s
    # Injecter un faux client avec last_seen trop ancien
    fake_sock = MagicMock()
    s.clients = {
        "dead-1": {"socket": fake_sock, "address": ("1.2.3.4", 9999),
                   "last_seen": time.time() - 40}
    }
    stop = threading.Event()
    t = threading.Thread(target=s._watchdog, args=(stop, 0.05, 35), daemon=True)
    t.start()
    time.sleep(0.2)
    stop.set()
    t.join(timeout=1)
    assert "dead-1" not in s.clients
    fake_sock.close.assert_called()
