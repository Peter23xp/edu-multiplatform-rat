# spool.py
import os
import json
import time
import glob
import secrets

class Spool:
    def __init__(self, directory=None):
        if directory is None:
            directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spool")
        self.dir = str(directory)
        os.makedirs(self.dir, exist_ok=True)

    def push(self, kind, payload):
        """Writes an entry to disk. Returns the filename (item id)."""
        ts = int(time.time() * 1000)
        uid = secrets.token_hex(4)
        filename = f"{kind}_{ts}_{uid}.json"
        path = os.path.join(self.dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"kind": kind, "ts": ts, "payload": payload}, f)
        return filename

    def pending(self):
        """Returns pending entries sorted by timestamp."""
        items = []
        for path in sorted(glob.glob(os.path.join(self.dir, "*.json"))):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["id"] = os.path.basename(path)
                data["path"] = path
                items.append(data)
            except Exception:
                pass
        return items

    def ack(self, item_id):
        """Deletes entry after successful send."""
        path = os.path.join(self.dir, item_id)
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
