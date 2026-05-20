#!/usr/bin/env python3
# Connection test utility for Educational RAT

import socket
import sys
import platform
import subprocess
import ipaddress
import os
import base64

HEADER_SIZE = 10

BLUE = '\033[94m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
END = '\033[0m'
BOLD = '\033[1m'

if platform.system() == "Windows":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except:
        BLUE = GREEN = YELLOW = RED = END = BOLD = ''


def print_banner():
    print(f"\n{BOLD}Educational RAT - Connection Tester{END}")
    print(f"{YELLOW}For educational purposes only{END}")
    print("-" * 50)


def get_local_ips():
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ips.append(s.getsockname()[0])
        s.close()
    except:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ip = info[4][0]
            if "." in ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except:
        pass
    return ips


def test_ping(host):
    print(f"\n{BLUE}[1] Ping test to {host}...{END}")
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    try:
        result = subprocess.call(['ping', param, '1', host],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result == 0:
            print(f"    {GREEN}Host is reachable via ICMP{END}")
            return True
        else:
            print(f"    {YELLOW}Host did not respond to ping (may still be reachable){END}")
            return False
    except:
        print(f"    {RED}Ping failed{END}")
        return False


def test_tcp(host, port):
    print(f"\n{BLUE}[2] TCP connection test to {host}:{port}...{END}")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        s.close()
        print(f"    {GREEN}TCP connection successful! Server is accepting connections.{END}")
        return True
    except ConnectionRefusedError:
        print(f"    {RED}Connection refused - server not running on this port{END}")
        return False
    except socket.timeout:
        print(f"    {RED}Connection timed out - firewall blocking or wrong address{END}")
        return False
    except Exception as e:
        print(f"    {RED}Error: {e}{END}")
        return False


def test_protocol(host, port):
    print(f"\n{BLUE}[3] Protocol handshake test...{END}")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))

        raw_len = b""
        while len(raw_len) < HEADER_SIZE:
            chunk = s.recv(HEADER_SIZE - len(raw_len))
            if not chunk:
                print(f"    {RED}Server closed connection immediately{END}")
                s.close()
                return False
            raw_len += chunk

        msg_len = int(raw_len.decode())
        data = b""
        while len(data) < msg_len:
            chunk = s.recv(min(65536, msg_len - len(data)))
            if not chunk:
                break
            data += chunk

        decoded = base64.b64decode(data).decode()
        if decoded == "AUTH":
            print(f"    {GREEN}Server sent AUTH challenge - protocol is working!{END}")
            s.close()
            return True
        else:
            print(f"    {YELLOW}Unexpected response: {decoded[:50]}{END}")
            s.close()
            return False
    except Exception as e:
        print(f"    {RED}Protocol test failed: {e}{END}")
        return False


def show_network_info():
    print(f"\n{BLUE}[4] Local network information:{END}")
    print(f"    Hostname: {socket.gethostname()}")
    ips = get_local_ips()
    for ip in ips:
        print(f"    {GREEN}LAN IP: {ip}{END}")
    if not ips:
        print(f"    {YELLOW}Could not detect LAN IP{END}")
    print(f"    Loopback: 127.0.0.1")


def show_firewall_help():
    print(f"\n{BLUE}[5] Firewall troubleshooting:{END}")
    system = platform.system()
    if system == "Windows":
        print(f"    {YELLOW}Windows Firewall:{END}")
        print(f"    - Control Panel > Windows Defender Firewall > Allow an app")
        print(f"    - Ensure Python is allowed for Private and Public networks")
        print(f"    - Or add inbound rule for your port in Advanced Settings")
    elif system == "Linux":
        print(f"    {YELLOW}Linux:{END}")
        print(f"    - Check: sudo iptables -L / sudo ufw status")
        print(f"    - Allow: sudo ufw allow <port>/tcp")
    elif system == "Darwin":
        print(f"    {YELLOW}macOS:{END}")
        print(f"    - System Preferences > Security > Firewall > Allow Python")


def main():
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')

    print_banner()

    print(f"\n{BOLD}System: {platform.system()} {platform.release()}{END}")
    print(f"{BOLD}Python: {platform.python_version()}{END}")

    host = input(f"\nServer IP [{GREEN}127.0.0.1{END}]: ").strip() or "127.0.0.1"
    try:
        port = int(input(f"Server Port [{GREEN}4444{END}]: ").strip() or "4444")
    except ValueError:
        port = 4444

    try:
        ip_obj = ipaddress.ip_address(host)
        if ip_obj.is_loopback:
            print(f"\n    {YELLOW}Note: Using loopback - only works on same machine{END}")
    except ValueError:
        pass

    test_ping(host)
    tcp_ok = test_tcp(host, port)

    if tcp_ok:
        test_protocol(host, port)

    show_network_info()
    show_firewall_help()

    print(f"\n{BOLD}{'=' * 50}{END}")
    if tcp_ok:
        print(f"{GREEN}Server appears to be running and reachable!{END}")
    else:
        print(f"{RED}Could not connect to server. Check the issues above.{END}")
    print()

    input("Press Enter to exit...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")
