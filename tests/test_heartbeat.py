import threading, time
from unittest.mock import MagicMock, patch


def test_heartbeat_sends_ping_every_30s():
    sent = []
    mock_sock = MagicMock()
    stop = threading.Event()
    send_lock = threading.Lock()

    def fake_send(sock, msg, key=None):
        sent.append(msg)

    with patch("client.send_msg", fake_send):
        import client as c
        t = threading.Thread(
            target=c._heartbeat_thread,
            args=(mock_sock, None, stop, send_lock, 0.05),  # interval=0.05s pour le test
            daemon=True
        )
        t.start()
        time.sleep(0.35)
        stop.set()
        t.join(timeout=1)
        assert not t.is_alive(), "Heartbeat thread should stop after stop event"

    assert any(m == "PING" for m in sent), f"PING not sent, got: {sent}"
    assert len(sent) >= 3  # au moins 3 PING en 0.35s avec interval=0.05s
