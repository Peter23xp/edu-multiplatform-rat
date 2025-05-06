#!/usr/bin/env python3
# ⚠️ Ce projet est à but pédagogique uniquement. Toute utilisation non autorisée est strictement interdite.
# Connection test utility for Educational RAT

import socket
import sys
import platform
import subprocess
import ipaddress
import time
import os

HEADER = '\033[95m'
BLUE = '\033[94m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
END = '\033[0m'
BOLD = '\033[1m'

def clear_screen():
    os.system('cls' if platform.system() == 'Windows' else 'clear')

def print_banner():
    print(f"{BOLD}Educational RAT Connection Tester{END}")
    print(f"{YELLOW}⚠️ For educational purposes only{END}")
    print("-" * 50)

def ping_host(host):
    """Ping the host to check if it's reachable"""
    print(f"{BLUE}[*] Pinging {host}...{END}")
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', host]
    try:
        result = subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result == 0:
            print(f"{GREEN}[+] Host is pingable{END}")
            return True
        else:
            print(f"{RED}[!] Host is not responding to ping{END}")
            print(f"{YELLOW}    Note: Some servers block ICMP packets{END}")
            return False
    except:
        print(f"{RED}[!] Ping failed{END}")
        return False

def check_localhost(host):
    """Check if using localhost inappropriately"""
    is_local_ip = False
    try:
        ip_obj = ipaddress.ip_address(host)
        is_local_ip = ip_obj.is_loopback
    except:
        if host in ["localhost", "127.0.0.1"]:
            is_local_ip = True
    
    if is_local_ip:
        print(f"{YELLOW}[!] Using localhost/127.0.0.1 - this only works if client and server are on the same machine{END}")
        print(f"{YELLOW}[!] For different machines, the server needs to use its LAN IP address{END}")
        return True
    return False

def get_ip_info():
    """Get all IP addresses for this machine"""
    print(f"{BLUE}[*] Getting local IP information...{END}")
    hostname = socket.gethostname()
    print(f"{BLUE}[*] Hostname: {hostname}{END}")
    
    try:
        # Get IP by hostname
        ip = socket.gethostbyname(hostname)
        print(f"{GREEN}[+] IP by hostname: {ip}{END}")
    except:
        print(f"{RED}[!] Could not get IP by hostname{END}")
    
    try:
        # Try socket method
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        print(f"{GREEN}[+] External IP: {ip} (recommended for LAN connections){END}")
    except:
        print(f"{RED}[!] Could not determine external IP{END}")
    
    print(f"{BLUE}[*] Available IP addresses:{END}")
    try:
        # Try to get all IPs
        for interface in socket.getaddrinfo(socket.gethostname(), None):
            ip = interface[4][0]
            if "." in ip:  # Only show IPv4
                print(f"{GREEN}    • {ip}{END}")
    except:
        print(f"{RED}    Could not enumerate IP addresses{END}")

def test_port(host, port):
    """Test if port is open on the host"""
    print(f"{BLUE}[*] Testing port {port} on {host}...{END}")
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    
    try:
        s.connect((host, port))
        s.close()
        print(f"{GREEN}[+] Port {port} is open!{END}")
        return True
    except ConnectionRefusedError:
        print(f"{RED}[!] Connection refused. The server is not running or is blocking connections.{END}")
        print(f"{YELLOW}    Troubleshooting steps:{END}")
        print(f"{YELLOW}    1. Make sure the server is running{END}")
        print(f"{YELLOW}    2. Check that you're using the correct port{END}")
        print(f"{YELLOW}    3. Check firewall settings{END}")
        return False
    except socket.timeout:
        print(f"{RED}[!] Connection timed out.{END}")
        print(f"{YELLOW}    The host may be behind a firewall that blocks this port{END}")
        return False
    except Exception as e:
        print(f"{RED}[!] Error: {str(e)}{END}")
        return False

def check_firewall():
    """Provide firewall checking guidance"""
    system = platform.system()
    
    print(f"{BLUE}[*] Firewall checking guidance for {system}:{END}")
    
    if system == "Windows":
        print(f"{YELLOW}    • Open Windows Defender Firewall: Control Panel > System and Security > Windows Defender Firewall{END}")
        print(f"{YELLOW}    • Click 'Allow an app or feature through Windows Defender Firewall'{END}")
        print(f"{YELLOW}    • Check if Python is allowed for both private and public networks{END}")
        print(f"{YELLOW}    • If not, click 'Change settings' > 'Allow another app' > browse to your Python executable{END}")
    
    elif system == "Linux":
        print(f"{YELLOW}    • Check iptables rules: sudo iptables -L{END}")
        print(f"{YELLOW}    • Allow incoming connections: sudo iptables -A INPUT -p tcp --dport PORT -j ACCEPT{END}")
        print(f"{YELLOW}    • Check if ufw is active: sudo ufw status{END}")
        print(f"{YELLOW}    • Allow port with ufw: sudo ufw allow PORT/tcp{END}")
    
    elif system == "Darwin":  # macOS
        print(f"{YELLOW}    • Check System Preferences > Security & Privacy > Firewall{END}")
        print(f"{YELLOW}    • Click 'Firewall Options' and allow Python if it's in the list{END}")
        print(f"{YELLOW}    • If not, click '+' and add Python application{END}")

def main():
    clear_screen()
    print_banner()
    
    print(f"{BOLD}This utility will help troubleshoot connection issues with the RAT server.{END}")
    print()
    
    # Get system information
    print(f"{BLUE}[*] System: {platform.system()} {platform.version()}{END}")
    print(f"{BLUE}[*] Python: {platform.python_version()}{END}")
    print()
    
    # Get server information
    server_host = input("Enter server IP address [127.0.0.1]: ") or "127.0.0.1"
    try:
        server_port = int(input("Enter server port [4444]: ") or "4444")
    except ValueError:
        server_port = 4444
    
    print()
    # Check if using localhost
    check_localhost(server_host)
    print()
    
    # Show local IP information
    get_ip_info()
    print()
    
    # Ping the server
    ping_host(server_host)
    print()
    
    # Test port
    test_port(server_host, server_port)
    print()
    
    # Firewall guidance
    check_firewall()
    print()
    
    print(f"{BOLD}Connection testing completed.{END}")
    print(f"{YELLOW}If you're still having issues, please check the logs for both server and client.{END}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    input("\nPress Enter to exit...") 