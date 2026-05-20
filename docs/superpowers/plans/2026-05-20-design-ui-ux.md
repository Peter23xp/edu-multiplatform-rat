# Design UI/UX — EduRAT Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refondre `server_gui.py` pour remplacer les 14 onglets par une sidebar groupée, ajouter des messages d'erreur contextuels (client + opération + cause + suggestion), et moderniser le dark theme avec 3 niveaux de profondeur.

**Architecture:** L'interface reste en Tkinter mono-fichier (`server_gui.py`). La sidebar gauche est un `tk.Frame` scrollable avec des groupes cliquables. Le contenu principal est un `tk.Frame` à droite avec une zone de notifications en haut. Tous les `_setup_*` existants sont migrés dans ce nouveau squelette sans toucher à la logique réseau.

**Tech Stack:** Python 3, Tkinter (tk + ttk), threading, PIL/ImageTk (déjà présents)

---

## Structure des fichiers

| Fichier | Action | Responsabilité |
|---|---|---|
| `server_gui.py` | Modifier | Toute la refonte UI — squelette, sidebar, thème, erreurs |

Aucun nouveau fichier — tout reste dans `server_gui.py` pour suivre la structure existante.

---

## Task 1 : Nouvelle palette de couleurs et styles ttk

**Files:**
- Modify: `server_gui.py:81-98` (bloc couleurs + styles)

- [ ] **Step 1 : Remplacer le bloc de couleurs et styles dans `__init__`**

Remplacer les lignes 81–98 par :

```python
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
self.style.configure("TEntry",       fieldbackground=self.bg_input, foreground=self.text_color, insertcolor=self.text_color, borderwidth=1, relief="flat")
self.style.configure("TNotebook",    background=self.bg_main)
self.style.configure("TScrollbar",   background=self.bg_sidebar, troughcolor=self.bg_main, arrowcolor=self.text_muted)
```

- [ ] **Step 2 : Vérifier que l'app démarre sans erreur**

```bash
cd "D:/PETER/edu-multiplatform-rat"
python server_gui.py
```

Attendu : fenêtre s'ouvre, aucune exception dans le terminal.

- [ ] **Step 3 : Commit**

```bash
git add server_gui.py
git commit -m "refactor(ui): nouvelle palette dark theme 3 niveaux de profondeur"
```

---

## Task 2 : Nouveau squelette de layout (sidebar + zone contenu)

**Files:**
- Modify: `server_gui.py:135-167` (méthode `_build_ui`)

- [ ] **Step 1 : Ajouter les attributs de navigation dans `__init__` après la ligne `self.streaming = False` (ligne 105)**

```python
self.streaming = False
self._sidebar_buttons = {}      # slug -> bouton sidebar
self._content_frames = {}       # slug -> frame contenu
self._active_section = None     # slug actif
self._notif_widgets = []        # widgets notification actifs
```

- [ ] **Step 2 : Remplacer `_build_ui` (lignes 135–167) par le nouveau squelette**

```python
def _build_ui(self):
    # Barre de titre
    self._build_titlebar()
    # Corps principal : sidebar gauche + contenu droit
    body = tk.Frame(self.root, bg=self.bg_main)
    body.pack(fill="both", expand=True)
    self._build_sidebar(body)
    self._build_content_area(body)
    # Remplir chaque section
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
    # Afficher la section par défaut
    self._show_section("dashboard")
```

- [ ] **Step 3 : Ajouter `_build_titlebar` après `_build_ui`**

```python
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
                                   bg="#bf616a18", font=("Segoe UI", 8),
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
                                  bg="#ebcb8b18", font=("Segoe UI", 8),
                                  padx=7, pady=1)
    self._alert_badge.pack(side="right", padx=4)
    self._alert_count = 0
```

- [ ] **Step 4 : Ajouter `_build_sidebar` après `_build_titlebar`**

```python
def _build_sidebar(self, parent):
    sidebar = tk.Frame(parent, bg=self.bg_sidebar, width=165)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    # Séparateur droit
    sep = tk.Frame(parent, bg=self.border_color, width=1)
    sep.pack(side="left", fill="y")

    groups = [
        ("CONTRÔLE", [
            ("dashboard",   "⚡", "Dashboard"),
            ("terminal",    "🖥", "Terminal"),
            ("clients",     "👥", "Clients"),
        ]),
        ("SURVEILLANCE", [
            ("stream",      "📺", "Écran / Stream"),
            ("screenshots", "📸", "Screenshots"),
            ("webcam",      "📷", "Webcam"),
            ("keylogger",   "⌨", "Keylogger"),
            ("clipboard",   "📋", "Presse-papier"),
        ]),
        ("FICHIERS", [
            ("files",       "📂", "Transfert"),
        ]),
        ("RÉSEAU & SYSTÈME", [
            ("scanner",     "🌐", "Scanner réseau"),
            ("persistence", "🔒", "Persistance"),
            ("sysinfo",     "💻", "Info système"),
        ]),
    ]
    bottom_items = [
        ("settings",  "⚙", "Paramètres"),
        ("defense",   "🛡", "Défense"),
        ("report",    "📄", "Rapports"),
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

    # Bas de sidebar
    tk.Frame(sidebar, bg=self.border_color, height=1).pack(fill="x", pady=4)
    bottom_frame = tk.Frame(sidebar, bg=self.bg_sidebar)
    bottom_frame.pack(fill="x", pady=2)
    for slug, icon, label in bottom_items:
        self._make_sidebar_item(bottom_frame, slug, icon, label)
```

- [ ] **Step 5 : Ajouter `_make_sidebar_item` et `_build_content_area`**

```python
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

    # Zone de notifications (initialement cachée)
    self._notif_zone = tk.Frame(content_outer, bg=self.bg_main)
    self._notif_zone.pack(fill="x", padx=10, pady=(6, 0))

    # Stack de frames contenu
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
```

- [ ] **Step 6 : Ajouter `_show_section`**

```python
def _show_section(self, slug):
    # Désactiver l'ancien item actif
    if self._active_section and self._active_section in self._sidebar_buttons:
        frame, icon_lbl, text_lbl = self._sidebar_buttons[self._active_section]
        frame.config(bg=self.bg_sidebar)
        icon_lbl.config(bg=self.bg_sidebar, fg=self.text_muted)
        text_lbl.config(bg=self.bg_sidebar, fg=self.text_muted)

    # Activer le nouvel item
    self._active_section = slug
    if slug in self._sidebar_buttons:
        frame, icon_lbl, text_lbl = self._sidebar_buttons[slug]
        frame.config(bg=self.bg_input)
        icon_lbl.config(bg=self.bg_input, fg=self.accent_color)
        text_lbl.config(bg=self.bg_input, fg=self.text_color)

    # Afficher la frame correspondante
    if slug in self._content_frames:
        self._content_frames[slug].lift()
```

- [ ] **Step 7 : Supprimer le bloc `_setup_control` complet (lignes 173–223) — sera remplacé par `_setup_dashboard`, `_setup_terminal`, `_setup_clients` dans les tâches suivantes**

Supprimer la méthode `_setup_control` (lignes 173–223).

- [ ] **Step 8 : Lancer l'app et vérifier le layout**

```bash
python server_gui.py
```

Attendu : sidebar visible à gauche avec tous les groupes, clic sur un item change la sélection (fond `#1e2433`), zone contenu à droite vide pour l'instant.

- [ ] **Step 9 : Commit**

```bash
git add server_gui.py
git commit -m "refactor(ui): sidebar groupée remplace les 14 onglets ttk.Notebook"
```

---

## Task 3 : Section Dashboard

**Files:**
- Modify: `server_gui.py` — ajouter `_setup_dashboard`

- [ ] **Step 1 : Ajouter `_setup_dashboard` après `_build_content_area`**

```python
def _setup_dashboard(self, parent):
    parent.configure(bg=self.bg_main)

    # Rangée de stats
    stats_row = tk.Frame(parent, bg=self.bg_main)
    stats_row.pack(fill="x", pady=(0, 8))
    self._stat_clients = self._make_stat_card(stats_row, "0", "CLIENTS",    self.success_color)
    self._stat_server  = self._make_stat_card(stats_row, "OFF", "SERVEUR",  self.error_color)
    self._stat_alerts  = self._make_stat_card(stats_row, "0", "ALERTES",    self.warning_color)
    self._stat_port    = self._make_stat_card(stats_row, "4444", "PORT",     self.accent_color)

    # Liste des clients connectés
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

    # Console
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
```

- [ ] **Step 2 : Mettre à jour `_update_indicator` (lignes 1193–1199) pour mettre à jour les stat cards et badges**

Remplacer la méthode `_update_indicator` par :

```python
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
```

- [ ] **Step 3 : Lancer et vérifier le Dashboard**

```bash
python server_gui.py
```

Attendu : section Dashboard visible avec 4 stat cards, liste clients, console, boutons Démarrer/Arrêter.

- [ ] **Step 4 : Commit**

```bash
git add server_gui.py
git commit -m "feat(ui): section Dashboard avec stat cards et liste clients"
```

---

## Task 4 : Sections Terminal et Clients

**Files:**
- Modify: `server_gui.py` — ajouter `_setup_terminal` et `_setup_clients`

- [ ] **Step 1 : Ajouter `_setup_terminal`**

```python
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
```

- [ ] **Step 2 : Ajouter `_setup_clients`**

```python
def _setup_clients(self, parent):
    parent.configure(bg=self.bg_main)
    tk.Label(parent, text="Clients connectés", fg=self.accent_color, bg=self.bg_main,
             font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 8))

    frame = tk.Frame(parent, bg=self.bg_card,
                      highlightbackground=self.border_color, highlightthickness=1)
    frame.pack(fill="both", expand=True)
    tk.Label(frame, text="Sélectionne un client pour l'activer, puis utilise les autres sections.",
             fg=self.text_muted, bg=self.bg_card, font=("Segoe UI", 9),
             anchor="w", padx=10).pack(fill="x", pady=(8, 4))
    self._clients_detail_text = tk.Text(frame, bg=self.bg_console, fg=self.text_color,
                                         font=("Consolas", 9), borderwidth=0,
                                         highlightthickness=0, state="disabled")
    self._clients_detail_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
```

- [ ] **Step 3 : Adapter `send_command` pour aussi écrire dans `terminal_out`**

Remplacer le corps de `_handle_generic` (lignes 778–788) :

```python
def _handle_generic(self, cmd):
    if cmd.startswith("download "):
        self._do_download(cmd)
    elif cmd.startswith("upload "):
        self._do_upload(cmd)
    else:
        resp = self._send_recv(cmd)
        if resp:
            self.root.after(0, lambda: self._write_terminal(f"$ {cmd}\n{resp}\n"))
            self.root.after(0, lambda: self.log_message(resp, "info"))
            if self.report and cmd not in ("sysinfo", "capabilities", "persist_check", "persist_methods"):
                self.report.add_command_result(cmd, resp)

def _write_terminal(self, text):
    if not hasattr(self, "terminal_out"):
        return
    self.terminal_out.config(state="normal")
    self.terminal_out.insert("end", text + "\n")
    self.terminal_out.see("end")
    self.terminal_out.config(state="disabled")
```

- [ ] **Step 4 : Vérifier**

```bash
python server_gui.py
```

Attendu : onglets "Terminal" et "Clients" dans la sidebar fonctionnels, champ commande dans Terminal.

- [ ] **Step 5 : Commit**

```bash
git add server_gui.py
git commit -m "feat(ui): sections Terminal et Clients"
```

---

## Task 5 : Système de notifications contextuelles

**Files:**
- Modify: `server_gui.py` — ajouter `show_notification`, `_dismiss_notification`, et remplacer les appels d'erreur

- [ ] **Step 1 : Ajouter `show_notification` et `_dismiss_notification`**

Insérer après `_update_indicator` :

```python
def show_notification(self, level, title, client_ip=None, operation=None,
                       cause=None, suggestion=None):
    """
    level : "error" | "warning" | "timeout" | "success" | "info"
    """
    import time as _time
    colors = {
        "error":   (self.error_color,   "#bf616a18"),
        "warning": (self.warning_color, "#ebcb8b0d"),
        "timeout": (self.orange_color,  "#d087700d"),
        "success": (self.success_color, "#a3be8c0d"),
        "info":    (self.info_color,    "#5e81ac0d"),
    }
    icons = {"error": "✕", "warning": "⚠", "timeout": "⏱", "success": "✓", "info": "ℹ"}
    border_clr, bg_clr = colors.get(level, colors["info"])
    icon = icons.get(level, "ℹ")
    ts = _time.strftime("%H:%M:%S")

    notif = tk.Frame(self._notif_zone, bg=bg_clr,
                     highlightbackground=border_clr, highlightthickness=1)
    # Bordure gauche colorée (simulée avec un Frame fin)
    accent_bar = tk.Frame(notif, bg=border_clr, width=4)
    accent_bar.pack(side="left", fill="y")

    inner = tk.Frame(notif, bg=bg_clr)
    inner.pack(side="left", fill="both", expand=True, padx=8, pady=6)

    # Ligne 1 : icône + titre + timestamp + bouton fermer
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

    # Ligne 2 : contexte (client · opération · cause)
    ctx_parts = []
    if client_ip:  ctx_parts.append(f"Client: {client_ip}")
    if operation:  ctx_parts.append(f"Opération: {operation}")
    if cause:      ctx_parts.append(f"Cause: {cause}")
    if ctx_parts:
        row2 = tk.Frame(inner, bg=bg_clr)
        row2.pack(fill="x", pady=(2, 0))
        tk.Label(row2, text="  " + "  ·  ".join(ctx_parts), fg=self.text_color,
                 bg=bg_clr, font=("Segoe UI", 8), anchor="w").pack(side="left")

    # Ligne 3 : suggestion
    if suggestion:
        row3 = tk.Frame(inner, bg=bg_clr)
        row3.pack(fill="x", pady=(2, 0))
        tk.Label(row3, text=f"  → {suggestion}", fg=self.accent_color,
                 bg=bg_clr, font=("Segoe UI", 8), anchor="w").pack(side="left")

    notif.pack(fill="x", pady=2)
    self._notif_widgets.append(notif)

    # Mettre à jour le compteur d'alertes si erreur/warning
    if level in ("error", "warning", "timeout"):
        self._alert_count += 1
        self._alert_badge.config(text=f"⚠ {self._alert_count} alerte{'s' if self._alert_count > 1 else ''}")
        if hasattr(self, "_stat_alerts"):
            self._stat_alerts.config(text=str(self._alert_count))

    # Auto-dismiss après 30s pour succès/info
    if level in ("success", "info"):
        self.root.after(30000, lambda: self._dismiss_notification(notif))

def _dismiss_notification(self, notif):
    try:
        notif.destroy()
        if notif in self._notif_widgets:
            self._notif_widgets.remove(notif)
    except Exception:
        pass
```

- [ ] **Step 2 : Mettre à jour `log_message` pour aussi déclencher une notification pour les erreurs**

Remplacer `log_message` (lignes 571–583) :

```python
def log_message(self, msg, level="info", client_ip=None, operation=None,
                cause=None, suggestion=None):
    try:
        self.console.config(state="normal")
        colors   = {"info": self.text_color, "success": self.success_color,
                    "warning": self.warning_color, "error": self.error_color}
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

    # Notification visuelle pour erreurs et avertissements
    if level in ("error", "warning", "timeout") and (client_ip or cause or suggestion):
        self.root.after(0, lambda: self.show_notification(
            level, msg, client_ip=client_ip, operation=operation,
            cause=cause, suggestion=suggestion))
```

- [ ] **Step 3 : Remplacer les messages d'erreur génériques dans `_handle_special` (lignes 807–855)**

Remplacer les lignes `self.root.after(0, lambda: self.log_message("Screenshot failed", "error"))` et similaires :

```python
# Dans _handle_special, bloc screenshot (remplacer ligne ~808) :
else:
    self.root.after(0, lambda: self.log_message(
        "Screenshot échoué", "error",
        client_ip=self.clients.get(self.current_client_id, {}).get("address", ("?",))[0],
        operation="capture_ecran",
        cause="Réponse FAIL du client (pyautogui peut-être absent)",
        suggestion="pip install pyautogui sur le client cible"
    ))

# Dans _handle_special, bloc webcam (remplacer ligne ~822) :
else:
    self.root.after(0, lambda: self.log_message(
        "Webcam échouée", "error",
        client_ip=self.clients.get(self.current_client_id, {}).get("address", ("?",))[0],
        operation="capture_webcam",
        cause="Réponse FAIL du client (opencv-python peut-être absent)",
        suggestion="pip install opencv-python sur le client cible"
    ))

# Dans _handle_special, bloc stream (remplacer ligne ~830) :
self.streaming = False
self.root.after(0, lambda: self.log_message(
    "Stream échoué", "error",
    client_ip=self.clients.get(self.current_client_id, {}).get("address", ("?",))[0],
    operation="stream_start",
    cause="Réponse FAIL du client (pyautogui/PIL peut-être absent)",
    suggestion="pip install pyautogui pillow sur le client cible"
))
return
```

- [ ] **Step 4 : Remplacer les erreurs dans `_send_recv` (lignes 696–704)**

```python
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
        self.log_message("Timeout commande", "timeout",
                          client_ip=self.clients.get(self.current_client_id, {}).get("address", ("?",))[0],
                          operation=cmd[:30],
                          cause="Délai de réponse dépassé (15s)",
                          suggestion="Augmenter timeout dans Paramètres ou vérifier la connexion")
        self._drop_client()
        return None
    except (ConnectionResetError, BrokenPipeError) as e:
        self.log_message("Connexion perdue", "error",
                          client_ip=self.clients.get(self.current_client_id, {}).get("address", ("?",))[0],
                          operation=cmd[:30],
                          cause=f"Connexion réinitialisée ({type(e).__name__})",
                          suggestion="Le client s'est déconnecté — il tentera de se reconnecter automatiquement")
        self._drop_client()
        return None
    except Exception as e:
        self.log_message("Erreur réseau", "error",
                          client_ip=self.clients.get(self.current_client_id, {}).get("address", ("?",))[0],
                          operation=cmd[:30],
                          cause=str(e),
                          suggestion="Vérifier la connexion réseau et relancer le client")
        self._drop_client()
        return None
```

- [ ] **Step 5 : Remplacer les erreurs dans `_do_upload` et `_do_download`**

Dans `_do_upload` (remplacer le bloc except à la ligne ~1143) :

```python
except Exception as e:
    ip = self.clients.get(self.current_client_id, {}).get("address", ("?",))[0]
    err_msg = str(e)
    self.root.after(0, lambda: self.log_message(
        "Erreur upload", "error",
        client_ip=ip, operation=f"upload {os.path.basename(filepath)}",
        cause=err_msg,
        suggestion="Vérifier les permissions sur le client et la connexion réseau"
    ))
```

Dans `_do_download` (remplacer le `"Not found"` et le bloc except) :

```python
if status == "FAIL":
    ip = self.clients.get(self.current_client_id, {}).get("address", ("?",))[0]
    self.root.after(0, lambda: self.log_message(
        "Fichier introuvable", "error",
        client_ip=ip, operation=f"download {remote}",
        cause=f"Le client ne trouve pas: {remote}",
        suggestion="Vérifier le chemin exact avec 'listdir' dans Terminal"
    ))
    return
# ...
except Exception as e:
    ip = self.clients.get(self.current_client_id, {}).get("address", ("?",))[0]
    err_msg = str(e)
    self.root.after(0, lambda: self.log_message(
        "Erreur download", "error",
        client_ip=ip, operation=f"download {remote}",
        cause=err_msg,
        suggestion="Vérifier les permissions sur le fichier distant"
    ))
```

- [ ] **Step 6 : Remplacer l'erreur de démarrage serveur dans `start_server` (ligne ~594)**

```python
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
```

- [ ] **Step 7 : Vérifier les notifications**

```bash
python server_gui.py
```

Tester : cliquer "Démarrer serveur" sans client → vérifier notification en haut du contenu. Tenter screenshot sans client → notification contextuelle avec suggestion.

- [ ] **Step 8 : Commit**

```bash
git add server_gui.py
git commit -m "feat(ui): système de notifications contextuelles avec cause et suggestion"
```

---

## Task 6 : Migrer les sections existantes vers le nouveau layout

**Files:**
- Modify: `server_gui.py` — adapter `_setup_stream`, `_setup_screenshots`, `_setup_webcam`, `_setup_keylogger`, `_setup_clipboard`, `_setup_files`, `_setup_scanner`, `_setup_persistence`, `_setup_sysinfo`, `_setup_defense`, `_setup_report`, `_setup_settings`, `_setup_help`

- [ ] **Step 1 : Ajouter un helper `_section_header` pour uniformiser les titres**

```python
def _section_header(self, parent, title, subtitle=None):
    hdr = tk.Frame(parent, bg=self.bg_main)
    hdr.pack(fill="x", pady=(0, 10))
    tk.Label(hdr, text=title, fg=self.accent_color, bg=self.bg_main,
             font=("Segoe UI", 13, "bold")).pack(side="left")
    if subtitle:
        tk.Label(hdr, text=subtitle, fg=self.text_muted, bg=self.bg_main,
                 font=("Segoe UI", 9)).pack(side="left", padx=10)
    return hdr

def _make_text_area(self, parent, height=None, readonly=True):
    frame = tk.Frame(parent, bg=self.bg_card,
                      highlightbackground=self.border_color, highlightthickness=1)
    frame.pack(fill="both", expand=True)
    text = tk.Text(frame, bg=self.bg_console, fg=self.text_color,
                   font=("Consolas", 9), borderwidth=0, highlightthickness=0,
                   wrap="word")
    if height:
        text.config(height=height)
    if readonly:
        text.config(state="disabled")
    sb = tk.Scrollbar(frame, orient="vertical", command=text.yview)
    sb.pack(side="right", fill="y")
    text.config(yscrollcommand=sb.set)
    text.pack(fill="both", expand=True, padx=6, pady=6)
    return text
```

- [ ] **Step 2 : Modifier chaque `_setup_*` pour utiliser `bg=self.bg_main` et `_section_header`**

Pour **chaque méthode** parmi `_setup_stream`, `_setup_screenshots`, `_setup_webcam`, `_setup_keylogger`, `_setup_clipboard`, `_setup_files`, `_setup_scanner`, `_setup_persistence`, `_setup_sysinfo`, `_setup_defense`, `_setup_report`, `_setup_settings`, `_setup_help` :

Ajouter en première ligne : `parent.configure(bg=self.bg_main)`

Remplacer toutes les occurrences de :
- `bg="#3B4252"` → `bg=self.bg_console`
- `bg="#2E3440"` → `bg=self.bg_main`
- `bg=self.bg_color` → `bg=self.bg_main`

Exemple pour `_setup_stream` :

```python
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
```

Répéter le même principe pour toutes les autres sections en remplaçant les couleurs hardcodées.

- [ ] **Step 3 : Mettre à jour les `scrolledtext.ScrolledText` restants**

Remplacer chaque `scrolledtext.ScrolledText(parent, bg="#3B4252", ...)` par `self._make_text_area(parent)` pour les zones en lecture seule, ou un `tk.Text` avec `bg=self.bg_console` pour les zones modifiables.

Assigner les résultats aux bons attributs : `self.keylog_text`, `self.clipboard_text`, `self.scanner_text`, `self.persist_text`, `self.sysinfo_text`, `self.report_text`.

- [ ] **Step 4 : Retirer l'import `scrolledtext` s'il n'est plus utilisé**

```python
# Vérifier ligne 6 — retirer scrolledtext de l'import si plus utilisé
from tkinter import ttk, filedialog, messagebox
```

- [ ] **Step 5 : Lancer et vérifier toutes les sections**

```bash
python server_gui.py
```

Cliquer sur chaque item de la sidebar. Attendu : toutes les sections s'affichent avec le nouveau fond sombre, sans erreur de widget manquant.

- [ ] **Step 6 : Commit**

```bash
git add server_gui.py
git commit -m "refactor(ui): migration de toutes les sections vers le nouveau layout dark"
```

---

## Task 7 : Indicateur de statut animé et polissage final

**Files:**
- Modify: `server_gui.py`

- [ ] **Step 1 : Ajouter l'animation pulse sur le badge de statut**

Ajouter après `_update_indicator` :

```python
def _pulse_status(self):
    if not hasattr(self, "_status_badge"):
        return
    if "ACTIF" in self._status_badge.cget("text") or "ÉCOUTE" in self._status_badge.cget("text"):
        current = self._status_badge.cget("fg")
        toggle = self.success_color if current == self.text_muted else self.text_muted
        self._status_badge.config(fg=toggle)
        self.root.after(1000, self._pulse_status)
```

Appeler `self._pulse_status()` à la fin de `start_server` (après `threading.Thread(...).start()`).

- [ ] **Step 2 : Ajouter le titre de la fenêtre dynamique**

Dans `_on_connected`, ajouter :

```python
self.root.title(f"EduRAT Console — {len(self.clients)} client(s) connecté(s)")
```

Dans `stop_server`, ajouter :

```python
self.root.title("EduRAT Console — Serveur arrêté")
```

- [ ] **Step 3 : Améliorer `_handshake` pour notifier l'authentification échouée avec contexte**

Remplacer la ligne ~653 :

```python
self.root.after(0, lambda: self.log_message(
    "Authentification échouée", "warning",
    client_ip=addr[0],
    operation="handshake",
    cause="Credentials incorrects (username/password refusé)",
    suggestion="Vérifier AUTH_USERNAME et AUTH_PASSWORD dans Paramètres"
))
```

- [ ] **Step 4 : Test complet**

```bash
python server_gui.py
```

Checklist :
- [ ] Sidebar avec tous les groupes, item actif surligné en cyan
- [ ] Dashboard avec stats, liste clients, console
- [ ] Terminal : envoi de commande, réponse affichée
- [ ] Notifications contextuelles : erreur screenshot sans client affiche suggestion pip
- [ ] Toutes les 16 sections s'affichent sans erreur
- [ ] Thème cohérent : pas de couleur `#3B4252` ou `#2E3440` visible

- [ ] **Step 5 : Commit final**

```bash
git add server_gui.py
git commit -m "feat(ui): animation statut, titre dynamique, authentification contextuelle — refonte UI complète"
```

---

## Auto-review de la spec

**Couverture spec → plan :**

| Exigence spec | Tâche |
|---|---|
| Sidebar avec 5 groupes nommés | Task 2 |
| Dashboard avec métriques | Task 3 |
| Dark theme `#0f1117` / 3 niveaux | Task 1 |
| Messages erreur : client + opération + cause + suggestion | Task 5 |
| 10 cas d'erreur documentés | Task 5 (screenshot, webcam, stream, timeout, connexion, upload, download, port, auth, aucun client) |
| Animations hover sidebar + pulse | Task 2 + Task 7 |
| Migration toutes sections | Task 6 |
| Composants réutilisables | Task 3 (`_make_stat_card`) + Task 6 (`_section_header`, `_make_text_area`) |
| Logique réseau inchangée | Aucune modification des méthodes réseau |
| `server.py` hors scope | Aucune modification de `server.py` |
