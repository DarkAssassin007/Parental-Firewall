#!/usr/bin/env python3
"""
Firewall Management Dashboard
Modern control panel for the WiFi Firewall engine.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
import threading
import subprocess
from datetime import datetime
import os

from wifi_firewall import WiFiFirewall, SCAPY_AVAILABLE


class FirewallDashboard:
    # ------------------------------------------------------------------ theme
    C = {
        "bg":        "#0e1420",
        "surface":   "#151d2e",
        "surface2":  "#1b2538",
        "border":    "#263349",
        "text":      "#e9eef6",
        "muted":     "#8fa0b8",
        "accent":    "#3dd6b5",
        "accent_fg": "#04241f",
        "danger":    "#ff6b7a",
        "danger_fg": "#2b0d12",
        "warn":      "#ffc65c",
    }
    FONT = "Segoe UI"
    MONO = "Consolas"

    def __init__(self, root):
        self.root = root
        self.root.title("WiFi Firewall — Hotspot Control Panel")
        self.root.geometry("1080x720")
        self.root.minsize(940, 620)
        self.root.configure(bg=self.C["bg"])

        self.config_file = "firewall_config.json"
        self.firewall = None
        self.firewall_thread = None
        self.is_running = False
        self.started_at = None
        self._device_jobs = {}

        self.load_config()
        self.setup_style()
        self.build_ui()
        self.refresh_devices(initial=True)
        self.tick()

    # ------------------------------------------------------------------ config
    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "filter_enabled": True,
                "hotspot_filtering_enabled": True,
                "blocked_domains": [], "blocked_ips": [],
                "blocked_keywords": [], "allowed_ips": ["127.0.0.1"],
            }

    def save_config(self, quiet=False):
        self.config["filter_enabled"] = self.filter_var.get()
        self.config["hotspot_filtering_enabled"] = self.hotspot_var.get()
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, indent=4, fp=f)
        if not quiet:
            messagebox.showinfo("Saved", "Configuration saved successfully!")

    # ------------------------------------------------------------------ style
    def setup_style(self):
        C = self.C
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=C["bg"], foreground=C["text"],
                        font=(self.FONT, 10))
        style.configure("TFrame", background=C["bg"])
        style.configure("Card.TFrame", background=C["surface"])
        style.configure("TLabel", background=C["bg"], foreground=C["text"])
        style.configure("Card.TLabel", background=C["surface"], foreground=C["text"])
        style.configure("Muted.TLabel", foreground=C["muted"])
        style.configure("CardMuted.TLabel", background=C["surface"], foreground=C["muted"])
        style.configure("Entry.TEntry", fieldbackground=C["surface2"], foreground=C["text"],
                        insertcolor=C["text"], borderwidth=0, padding=8)
        style.configure("TButton", background=C["surface2"], foreground=C["text"],
                        borderwidth=0, padding=(14, 9))
        style.map("TButton", background=[("active", C["border"])])
        style.configure("Accent.TButton", background=C["accent"], foreground=C["accent_fg"],
                        font=(self.FONT, 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#66e3c8"), ("disabled", C["surface2"])])
        style.configure("Danger.TButton", background=C["danger"], foreground=C["danger_fg"],
                        font=(self.FONT, 10, "bold"))
        style.map("Danger.TButton", background=[("active", "#ff92a0"), ("disabled", C["surface2"])])
        style.configure("Ghost.TButton", background=C["surface"], foreground=C["muted"])
        style.map("Ghost.TButton", background=[("active", C["surface2"])], foreground=[("active", C["text"])])
        style.configure("Nav.TButton", background=C["bg"], foreground=C["muted"],
                        font=(self.FONT, 10, "bold"), padding=(16, 10), anchor="w")
        style.map("Nav.TButton",
                  background=[("selected", C["surface2"]), ("active", C["surface2"])],
                  foreground=[("selected", C["accent"]), ("active", C["text"])])
        style.configure("Treeview", background=C["surface"], foreground=C["text"],
                        fieldbackground=C["surface"], borderwidth=0, rowheight=30)
        style.configure("Treeview.Heading", background=C["surface2"], foreground=C["muted"],
                        borderwidth=0, font=(self.FONT, 9, "bold"))
        style.map("Treeview", background=[("selected", C["border"])])
        style.configure("Switch.TCheckbutton", background=C["surface"], foreground=C["text"])
        style.map("Switch.TCheckbutton", background=[("active", C["surface"])])
        style.configure("TScrollbar", background=C["surface2"], borderwidth=0)
        style.configure("Horizontal.TProgressbar", background=C["accent"], borderwidth=0)

    # ------------------------------------------------------------------ build
    def build_ui(self):
        C = self.C
        # Sidebar -------------------------------------------------------
        sidebar = tk.Frame(self.root, bg=C["bg"], width=230)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="WIFI FIREWALL", font=(self.FONT, 10, "bold"),
                 bg=C["bg"], fg=C["accent"]).pack(anchor="w", padx=20, pady=(24, 0))
        tk.Label(sidebar, text="Hotspot Control", font=(self.FONT, 17, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w", padx=20, pady=(0, 18))

        self.nav_buttons = {}
        pages = [("dashboard", "Dashboard"), ("domains", "Blocked Sites"),
                 ("keywords", "Keywords"), ("devices", "Devices"),
                 ("logs", "Activity Log"), ("settings", "Settings")]
        for key, label in pages:
            btn = ttk.Button(sidebar, text=f"  {label}", style="Nav.TButton",
                             command=lambda k=key: self.show_page(k))
            btn.pack(fill=tk.X, padx=12, pady=2)
            self.nav_buttons[key] = btn

        footer = tk.Frame(sidebar, bg=C["bg"])
        footer.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=14)
        self.start_btn = ttk.Button(footer, text="▶  START PROTECTION",
                                    style="Accent.TButton", command=self.start_firewall)
        self.start_btn.pack(fill=tk.X, pady=(0, 6))
        self.stop_btn = ttk.Button(footer, text="■  STOP PROTECTION",
                                   style="Danger.TButton", command=self.stop_firewall,
                                   state=tk.DISABLED)
        self.stop_btn.pack(fill=tk.X)

        # Main area -----------------------------------------------------
        main = tk.Frame(self.root, bg=C["bg"])
        main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        topbar = tk.Frame(main, bg=C["bg"])
        topbar.pack(fill=tk.X, padx=28, pady=(22, 8))
        self.page_title = tk.Label(topbar, text="Dashboard", font=(self.FONT, 20, "bold"),
                                   bg=C["bg"], fg=C["text"])
        self.page_title.pack(side=tk.LEFT)
        self.status_pill = tk.Label(topbar, text="●  STOPPED", font=(self.FONT, 10, "bold"),
                                    bg=C["surface"], fg=C["danger"], padx=14, pady=6)
        self.status_pill.pack(side=tk.RIGHT)

        self.pages = {}
        container = tk.Frame(main, bg=C["bg"])
        container.pack(fill=tk.BOTH, expand=True, padx=28, pady=(0, 22))
        for key, builder in [("dashboard", self.build_dashboard_page),
                             ("domains", self.build_domains_page),
                             ("keywords", self.build_keywords_page),
                             ("devices", self.build_devices_page),
                             ("logs", self.build_logs_page),
                             ("settings", self.build_settings_page)]:
            page = tk.Frame(container, bg=C["bg"])
            builder(page)
            self.pages[key] = page

        self.show_page("dashboard")

    def show_page(self, key):
        for k, page in self.pages.items():
            page.pack_forget()
        self.pages[key].pack(fill=tk.BOTH, expand=True)
        titles = {"dashboard": "Dashboard", "domains": "Blocked Sites",
                  "keywords": "Blocked Keywords", "devices": "Connected Devices",
                  "logs": "Activity Log", "settings": "Settings"}
        self.page_title.config(text=titles.get(key, key))
        for k, btn in self.nav_buttons.items():
            btn.state(["pressed"] if k == key else ["!pressed"])

    # ----------------------------------------------------------- dashboard
    def build_dashboard_page(self, parent):
        C = self.C
        cards = tk.Frame(parent, bg=C["bg"])
        cards.pack(fill=tk.X)
        self.stat_cards = {}
        for i, (key, label, color) in enumerate([
                ("domains", "Blocked Sites", C["accent"]),
                ("keywords", "Keywords", C["warn"]),
                ("packets", "Packets Blocked", C["danger"]),
                ("clients", "Hotspot Devices", "#7aa2f7")]):
            card = tk.Frame(cards, bg=C["surface"], padx=16, pady=14)
            card.grid(row=0, column=i, sticky="nsew", padx=(0, 12))
            cards.grid_columnconfigure(i, weight=1)
            tk.Label(card, text=label.upper(), font=(self.FONT, 9, "bold"),
                     bg=C["surface"], fg=C["muted"]).pack(anchor="w")
            value = tk.Label(card, text="0", font=(self.FONT, 26, "bold"),
                             bg=C["surface"], fg=color)
            value.pack(anchor="w")
            self.stat_cards[key] = value

        body = tk.Frame(parent, bg=C["bg"])
        body.pack(fill=tk.BOTH, expand=True, pady=(16, 0))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        # Recent activity
        left = tk.Frame(body, bg=C["surface"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        tk.Label(left, text="RECENT ACTIVITY", font=(self.FONT, 9, "bold"),
                 bg=C["surface"], fg=C["muted"]).pack(anchor="w", padx=16, pady=(14, 8))
        cols = ("time", "device", "reason", "site")
        self.activity_tree = ttk.Treeview(left, columns=cols, show="headings", height=10)
        for col, text, w in [("time", "Time", 70), ("device", "Device", 120),
                             ("reason", "Reason", 110), ("site", "Domain / IP", 180)]:
            self.activity_tree.heading(col, text=text)
            self.activity_tree.column(col, width=w, anchor="w")
        self.activity_tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 14))

        # Live status panel
        right = tk.Frame(body, bg=C["surface"])
        right.grid(row=0, column=0, columnspan=2, sticky="nsew")
        right.lower()
        tk.Label(right, text="PROTECTION STATUS", font=(self.FONT, 9, "bold"),
                 bg=C["surface"], fg=C["muted"]).pack(anchor="w", padx=16, pady=(14, 8))
        self.status_lines = tk.Label(right, text="", font=(self.MONO, 10), justify=tk.LEFT,
                                     bg=C["surface"], fg=C["text"])
        self.status_lines.pack(anchor="w", padx=16, pady=(0, 16))

        # Quick add on dashboard
        quick = tk.Frame(body, bg=C["surface"])
        quick.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        tk.Label(quick, text="QUICK BLOCK", font=(self.FONT, 9, "bold"),
                 bg=C["surface"], fg=C["muted"]).pack(anchor="w", padx=16, pady=(12, 4))
        row = tk.Frame(quick, bg=C["surface"])
        row.pack(fill=tk.X, padx=16, pady=(0, 14))
        self.quick_entry = ttk.Entry(row, style="Entry.TEntry")
        self.quick_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.quick_entry.bind("<Return>", lambda e: self.quick_block())
        ttk.Button(row, text="BLOCK SITE", style="Accent.TButton",
                   command=self.quick_block).pack(side=tk.LEFT)
        tk.Label(quick, text="Enter a domain (e.g. instagram.com) — it is blocked for every "
                             "device on this PC's hotspot.", font=(self.FONT, 9),
                 bg=C["surface"], fg=C["muted"]).pack(anchor="w", padx=16, pady=(0, 14))
        body.grid_rowconfigure(1, weight=0)

    # ------------------------------------------------------------ rule pages
    def build_rule_page(self, parent, key, title, hint, entry_name, add_cmd, remove_cmd):
        C = self.C
        card = tk.Frame(parent, bg=C["surface"])
        card.pack(fill=tk.BOTH, expand=True)
        tk.Label(card, text=title, font=(self.FONT, 12, "bold"),
                 bg=C["surface"], fg=C["text"]).pack(anchor="w", padx=18, pady=(16, 2))
        tk.Label(card, text=hint, font=(self.FONT, 9),
                 bg=C["surface"], fg=C["muted"]).pack(anchor="w", padx=18, pady=(0, 12))
        wrap = tk.Frame(card, bg=C["surface"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 14))
        scrollbar = ttk.Scrollbar(wrap)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox = tk.Listbox(wrap, yscrollcommand=scrollbar.set, font=(self.FONT, 10),
                             bg=C["surface2"], fg=C["text"], selectbackground=C["border"],
                             selectforeground=C["text"], relief=tk.FLAT, borderwidth=0,
                             highlightthickness=0, activestyle="none")
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.config(command=listbox.yview)
        setattr(self, f"{key}_listbox", listbox)
        row = tk.Frame(card, bg=C["surface"])
        row.pack(fill=tk.X, padx=18, pady=(0, 18))
        entry = ttk.Entry(row, style="Entry.TEntry")
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        entry.bind("<Return>", lambda e: add_cmd())
        setattr(self, entry_name, entry)
        ttk.Button(row, text="＋ ADD", style="Accent.TButton", command=add_cmd).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row, text="REMOVE SELECTED", command=remove_cmd).pack(side=tk.LEFT)
        self.refresh_rule_list(key)

    def refresh_rule_list(self, key):
        listbox = getattr(self, f"{key}_listbox", None)
        if not listbox:
            return
        listbox.delete(0, tk.END)
        values = {"domains": "blocked_domains", "keywords": "blocked_keywords",
                  "ips": "blocked_ips"}[key]
        for item in self.config.get(values, []):
            listbox.insert(tk.END, item)
        if "domains" in self.stat_cards:
            self.stat_cards["domains"].config(text=str(len(self.config.get("blocked_domains", []))))
            self.stat_cards["keywords"].config(text=str(len(self.config.get("blocked_keywords", []))))

    def build_domains_page(self, parent):
        self.build_rule_page(
            parent, "domains", "Blocked Sites",
            "Devices on the hotspot cannot reach these sites (DNS + HTTPS + HTTP blocked).",
            "domain_entry", self.add_domain, self.remove_domain)

    def build_keywords_page(self, parent):
        self.build_rule_page(
            parent, "keywords", "Blocked Keywords",
            "Unencrypted traffic containing these words is cut off.",
            "keyword_entry", self.add_keyword, self.remove_keyword)

    def add_domain(self):
        self.add_rule("blocked_domains", "domains", self.domain_entry, "Domain")

    def add_keyword(self):
        self.add_rule("blocked_keywords", "keywords", self.keyword_entry, "Keyword")

    def add_rule(self, config_key, list_key, entry, label):
        value = entry.get().strip().lower().lstrip('.')
        if not value:
            return
        items = self.config.setdefault(config_key, [])
        if value in items:
            messagebox.showwarning("Duplicate", f"{label} already in the list.")
            return
        items.append(value)
        entry.delete(0, tk.END)
        self.refresh_rule_list(list_key)
        self.save_config(quiet=True)
        self.apply_live_rules()
        self.log_event(f"Added {label.lower()}: {value}")

    def remove_rule(self, config_key, list_key, label):
        listbox = getattr(self, f"{list_key}_listbox")
        selection = listbox.curselection()
        if not selection:
            return
        value = listbox.get(selection[0])
        self.config[config_key].remove(value)
        self.refresh_rule_list(list_key)
        self.save_config(quiet=True)
        self.apply_live_rules()
        self.log_event(f"Removed {label.lower()}: {value}")

    def remove_domain(self):
        self.remove_rule("blocked_domains", "domains", "Domain")

    def remove_keyword(self):
        self.remove_rule("blocked_keywords", "keywords", "Keyword")

    def quick_block(self):
        value = self.quick_entry.get().strip().lower().lstrip('.')
        if not value:
            return
        items = self.config.setdefault("blocked_domains", [])
        if value not in items:
            items.append(value)
            self.save_config(quiet=True)
            self.apply_live_rules()
            self.refresh_rule_list("domains")
            self.log_event(f"Quick-blocked site: {value}")
        self.quick_entry.delete(0, tk.END)

    def apply_live_rules(self):
        """Push rule changes into a running firewall without restarting."""
        if self.is_running and self.firewall:
            self.firewall.blocked_domains = [d.lower().lstrip('.') for d in self.config["blocked_domains"]]
            self.firewall.blocked_keywords = [k.lower() for k in self.config["blocked_keywords"]]
            self.firewall.blocked_ips = self.config["blocked_ips"]
            self.firewall.filter_enabled = self.filter_var.get()

    # -------------------------------------------------------------- devices
    def build_devices_page(self, parent):
        C = self.C
        card = tk.Frame(parent, bg=C["surface"])
        card.pack(fill=tk.BOTH, expand=True)
        head = tk.Frame(card, bg=C["surface"])
        head.pack(fill=tk.X, padx=18, pady=(16, 8))
        tk.Label(head, text="Devices on this PC's hotspot", font=(self.FONT, 12, "bold"),
                 bg=C["surface"], fg=C["text"]).pack(side=tk.LEFT)
        ttk.Button(head, text="REFRESH", command=lambda: self.refresh_devices(force=True)).pack(side=tk.RIGHT)
        tk.Label(card, text="Block ALL internet access for a device, or allow it again. "
                            "Site-level blocking (Blocked Sites) applies to every device.",
                 font=(self.FONT, 9), bg=C["surface"], fg=C["muted"]).pack(anchor="w", padx=18, pady=(0, 10))
        cols = ("ip", "status")
        self.devices_tree = ttk.Treeview(card, columns=cols, show="headings", height=12)
        self.devices_tree.heading("ip", text="Device IP")
        self.devices_tree.heading("status", text="Internet Access")
        self.devices_tree.column("ip", width=240, anchor="w")
        self.devices_tree.column("status", width=180, anchor="w")
        self.devices_tree.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 10))
        btns = tk.Frame(card, bg=C["surface"])
        btns.pack(fill=tk.X, padx=18, pady=(0, 18))
        ttk.Button(btns, text="✂  CUT OFF INTERNET", style="Danger.TButton",
                   command=self.cutoff_selected).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btns, text="✔  RESTORE INTERNET", style="Accent.TButton",
                   command=self.restore_selected).pack(side=tk.LEFT)

    def refresh_devices(self, initial=False, force=False):
        """Poll hotspot clients in the background and refresh the table."""
        def worker():
            if not hasattr(self, "_discovery_fw"):
                self._discovery_fw = WiFiFirewall(config_file=self.config_file)
            try:
                clients = self._discovery_fw.get_hotspot_clients()
            except Exception:
                clients = []
            self.root.after(0, lambda: self.render_devices(clients))
        if initial:
            self.root.after(1500, worker)
        else:
            threading.Thread(target=worker, daemon=True).start()
        if self.is_running or force or initial:
            self.root.after(15000, lambda: self.refresh_devices(force=True))

    def render_devices(self, clients):
        if not hasattr(self, "devices_tree"):
            return
        self.devices_tree.delete(*self.devices_tree.get_children())
        if not clients:
            self.devices_tree.insert("", tk.END, values=("No devices connected", "—"))
        for ip in clients:
            cut = self.firewall and ip in self.firewall._cut_off_clients
            self.devices_tree.insert("", tk.END, values=(ip, "BLOCKED" if cut else "Allowed"))
        if "clients" in self.stat_cards:
            self.stat_cards["clients"].config(text=str(len(clients)))

    def cutoff_selected(self):
        self._device_action(True)

    def restore_selected(self):
        self._device_action(False)

    def _device_action(self, block):
        if not self.is_running:
            messagebox.showwarning("Firewall stopped", "Start protection first.")
            return
        selection = self.devices_tree.selection()
        if not selection:
            messagebox.showinfo("Select a device", "Pick a device row first.")
            return
        ip = self.devices_tree.item(selection[0])["values"][0]
        if str(ip).startswith("No devices"):
            return
        try:
            if block:
                if self.firewall.block_client_internet(str(ip)):
                    self.log_event(f"Cut off internet for {ip}")
                else:
                    messagebox.showerror("Failed", f"Could not block {ip} (needs Administrator).")
            else:
                self.firewall.unblock_client_internet(str(ip))
                self.log_event(f"Restored internet for {ip}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        self.render_devices(self.firewall.get_hotspot_clients())

    # ----------------------------------------------------------------- logs
    def build_logs_page(self, parent):
        C = self.C
        card = tk.Frame(parent, bg=C["surface"])
        card.pack(fill=tk.BOTH, expand=True)
        head = tk.Frame(card, bg=C["surface"])
        head.pack(fill=tk.X, padx=18, pady=(14, 6))
        tk.Label(head, text="Live firewall activity", font=(self.FONT, 12, "bold"),
                 bg=C["surface"], fg=C["text"]).pack(side=tk.LEFT)
        for text, cmd in (("EXPORT", self.export_logs), ("CLEAR", self.clear_logs),
                          ("REFRESH", self.refresh_logs)):
            ttk.Button(head, text=text, style="Ghost.TButton", command=cmd).pack(side=tk.RIGHT, padx=(6, 0))
        self.log_text = scrolledtext.ScrolledText(
            card, wrap=tk.WORD, font=(self.MONO, 9), bg=C["surface2"], fg=C["text"],
            relief=tk.FLAT, borderwidth=0, highlightthickness=0)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 8))
        self.log_text.tag_config("block", foreground=C["danger"])
        self.log_text.tag_config("info", foreground="#7fd7c8")
        self.log_text.tag_config("error", foreground=C["warn"])
        self.refresh_logs()

    def refresh_logs(self):
        if not hasattr(self, "log_text"):
            return
        try:
            if not os.path.exists("firewall.log"):
                return
            with open("firewall.log", 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            current = self.log_text.get(1.0, tk.END)
            if content == current:
                return
            self.log_text.delete(1.0, tk.END)
            for line in content.splitlines():
                if "BLOCKED" in line or "Blocked" in line or "sinkhole" in line:
                    self.log_text.insert(tk.END, line + "\n", "block")
                elif "ERROR" in line:
                    self.log_text.insert(tk.END, line + "\n", "error")
                elif line.strip():
                    self.log_text.insert(tk.END, line + "\n", "info")
            self.log_text.see(tk.END)
        except Exception:
            pass

    def clear_logs(self):
        if messagebox.askyesno("Confirm", "Clear the activity log?"):
            self.log_text.delete(1.0, tk.END)
            open("firewall.log", 'w').close()

    def export_logs(self):
        filename = filedialog.asksaveasfilename(defaultextension=".txt",
                                                filetypes=[("Text files", "*.txt")])
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_text.get(1.0, tk.END))
            messagebox.showinfo("Exported", f"Logs saved to {filename}")

    def log_event(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("firewall.log", 'a', encoding='utf-8') as f:
            f.write(f"{timestamp} - INFO - {message}\n")
        self.refresh_logs()

    # ------------------------------------------------------------- settings
    def build_settings_page(self, parent):
        C = self.C
        card = tk.Frame(parent, bg=C["surface"])
        card.pack(fill=tk.BOTH, expand=True)
        tk.Label(card, text="Filtering options", font=(self.FONT, 12, "bold"),
                 bg=C["surface"], fg=C["text"]).pack(anchor="w", padx=18, pady=(16, 8))
        self.filter_var = tk.BooleanVar(value=self.config.get("filter_enabled", True))
        self.hotspot_var = tk.BooleanVar(value=self.config.get("hotspot_filtering_enabled", True))
        ttk.Checkbutton(card, style="Switch.TCheckbutton",
                        text="Enable content filtering (site & keyword blocks)",
                        variable=self.filter_var,
                        command=self.apply_live_rules).pack(anchor="w", padx=18, pady=4)
        ttk.Checkbutton(card, style="Switch.TCheckbutton",
                        text="Only filter devices on this PC's hotspot (uncheck = filter all traffic)",
                        variable=self.hotspot_var,
                        command=self.apply_live_rules).pack(anchor="w", padx=18, pady=4)
        ttk.Button(card, text="SAVE SETTINGS", style="Accent.TButton",
                   command=self.save_config).pack(anchor="w", padx=18, pady=(14, 4))
        info = tk.Label(card, text="", font=(self.FONT, 9), justify=tk.LEFT,
                        bg=C["surface"], fg=C["muted"])
        info.pack(anchor="w", padx=18, pady=(16, 18))
        self.settings_info = info

    # ---------------------------------------------------------- engine control
    def start_firewall(self):
        if self.is_running:
            return
        if not SCAPY_AVAILABLE:
            messagebox.showerror("Missing dependency",
                                 "Scapy is not installed.\nRun: pip install -r requirements.txt")
            return
        self.save_config(quiet=True)
        try:
            self.firewall = WiFiFirewall(config_file=self.config_file)
            self.firewall.filter_enabled = self.filter_var.get()
            self.firewall.hotspot_enabled = self.hotspot_var.get()
            self.firewall_thread = threading.Thread(target=self._run_engine, daemon=True)
            self.firewall_thread.start()
            self.is_running = True
            self.started_at = datetime.now()
            self.status_pill.config(text="●  PROTECTED", fg=self.C["accent"])
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.log_event("Protection started")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start firewall:\n{e}\n\nRun as Administrator.")

    def _run_engine(self):
        try:
            self.firewall.start_monitoring()
        except Exception as e:
            self.root.after(0, lambda: self._engine_failed(str(e)))

    def _engine_failed(self, error):
        self.is_running = False
        self.status_pill.config(text="●  ERROR", fg=self.C["warn"])
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.log_event(f"Engine error: {error}")
        messagebox.showerror("Firewall error", f"{error}\n\nRun as Administrator and check Npcap.")

    def stop_firewall(self):
        if not self.is_running:
            return
        try:
            if self.firewall:
                self.firewall.stop_monitoring()
        finally:
            self.is_running = False
            self.status_pill.config(text="●  STOPPED", fg=self.C["danger"])
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.log_event("Protection stopped")

    # ---------------------------------------------------------------- ticker
    def tick(self):
        if self.is_running and self.firewall:
            stats, events = self.firewall.get_stats()
            if "packets" in self.stat_cards:
                self.stat_cards["packets"].config(text=str(sum(stats.values())))
            # activity table
            for item in list(self.activity_tree.get_children()):
                pass
            existing = {self.activity_tree.item(i)["values"][:4] for i in self.activity_tree.get_children()}
            for ev in reversed(events):
                row = (ev["time"], ev["src"], ev["reason"], ev["domain"] or ev["dst"])
                if row not in existing:
                    self.activity_tree.insert("", 0, values=row)
            self.activity_tree.delete(*[i for i in self.activity_tree.get_children()][60:])
            self.status_lines.config(text=(
                f"Status       : RUNNING\n"
                f"Interface    : {self.firewall.interface or 'auto'}\n"
                f"Uptime       : {self.firewall.get_uptime()}\n"
                f"Hotspot subnet: {self.firewall.hotspot_subnet}\n"
                f"Devices cut off: {len(self.firewall._cut_off_clients)}\n"
                f"Packets blocked: {sum(stats.values())}"))
            if self.settings_info:
                self.settings_info.config(text=(
                    f"Blocked domains: {len(self.firewall.blocked_domains)}    "
                    f"Keywords: {len(self.firewall.blocked_keywords)}\n"
                    f"Hotspot subnet: {self.firewall.hotspot_subnet}    "
                    f"Scapy: {'available' if SCAPY_AVAILABLE else 'missing'}"))
            self.refresh_logs()
        self.root.after(1500, self.tick)

    def update_runtime_stats(self):
        pass


def main():
    root = tk.Tk()
    app = FirewallDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
