import os, json, tempfile, pytest
from spool import Spool

def test_push_creates_file(tmp_path):
    s = Spool(tmp_path)
    s.push("keylog", {"data": "hello"})
    files = list(tmp_path.glob("keylog_*.json"))
    assert len(files) == 1

def test_pending_returns_pushed_items(tmp_path):
    s = Spool(tmp_path)
    s.push("keylog", {"data": "abc"})
    s.push("clipboard", {"data": "xyz"})
    items = s.pending()
    assert len(items) == 2

def test_ack_removes_file(tmp_path):
    s = Spool(tmp_path)
    s.push("keylog", {"data": "test"})
    items = s.pending()
    s.ack(items[0]["id"])
    assert s.pending() == []

def test_survives_empty_dir(tmp_path):
    s = Spool(tmp_path)
    assert s.pending() == []

def test_ack_ignores_missing_file(tmp_path):
    s = Spool(tmp_path)
    # Should not raise even if file doesn't exist
    s.ack("nonexistent_12345.json")
