import json
import os
import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Tuple

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas


DB_PATH = os.path.join("data", "clients.db")
DEFAULT_ACCENT = "#1f2937"


class Database:
    def __init__(self, path: str = DB_PATH):
        self.path = path
        self._ensure_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _ensure_db(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kundennummer TEXT UNIQUE NOT NULL,
                    ma TEXT,
                    name TEXT,
                    strasse TEXT,
                    plz TEXT,
                    ort TEXT,
                    geburtsdatum TEXT,
                    pg TEXT,
                    versicherungsnummer TEXT,
                    pflegekasse TEXT,
                    telefon TEXT,
                    preise TEXT,
                    fahrtkosten TEXT,
                    bemerkungen TEXT,
                    extra_fields TEXT
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                """
            )

    def _hash_password(self, password: str, salt: str) -> str:
        import hashlib

        hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
        return hashed.hex()

    def create_user(self, username: str, password: str) -> bool:
        import secrets

        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                    (username, password_hash, salt),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def validate_user(self, username: str, password: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT password_hash, salt FROM users WHERE username = ?", (username,)
            ).fetchone()
        if not row:
            return False
        password_hash, salt = row
        return password_hash == self._hash_password(password, salt)

    def _next_kundennummer(self) -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT MAX(id) FROM clients").fetchone()
        next_id = (row[0] or 0) + 1
        return f"K-{next_id:05d}"

    def save_client(self, data: Dict[str, str], extra_fields: Dict[str, str]) -> None:
        kundennummer = data.get("kundennummer") or self._next_kundennummer()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO clients (
                    kundennummer, ma, name, strasse, plz, ort, geburtsdatum, pg,
                    versicherungsnummer, pflegekasse, telefon, preise, fahrtkosten,
                    bemerkungen, extra_fields
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    kundennummer,
                    data.get("ma"),
                    data.get("name"),
                    data.get("strasse"),
                    data.get("plz"),
                    data.get("ort"),
                    data.get("geburtsdatum"),
                    data.get("pg"),
                    data.get("versicherungsnummer"),
                    data.get("pflegekasse"),
                    data.get("telefon"),
                    data.get("preise"),
                    data.get("fahrtkosten"),
                    data.get("bemerkungen"),
                    json.dumps(extra_fields, ensure_ascii=False),
                ),
            )

    def list_clients(self) -> List[Dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT kundennummer, ma, name, strasse, plz, ort, geburtsdatum, pg,
                       versicherungsnummer, pflegekasse, telefon, preise, fahrtkosten,
                       bemerkungen, extra_fields
                FROM clients ORDER BY id DESC
                """
            ).fetchall()
        clients: List[Dict[str, str]] = []
        for row in rows:
            client = {
                "kundennummer": row[0],
                "ma": row[1] or "",
                "name": row[2] or "",
                "strasse": row[3] or "",
                "plz": row[4] or "",
                "ort": row[5] or "",
                "geburtsdatum": row[6] or "",
                "pg": row[7] or "",
                "versicherungsnummer": row[8] or "",
                "pflegekasse": row[9] or "",
                "telefon": row[10] or "",
                "preise": row[11] or "",
                "fahrtkosten": row[12] or "",
                "bemerkungen": row[13] or "",
            }
            extra = json.loads(row[14] or "{}")
            client.update(extra)
            clients.append(client)
        return clients

    def save_setting(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def load_setting(self, key: str, default: str = "") -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        if row:
            return row[0]
        return default


class AuthWindow(tk.Toplevel):
    def __init__(self, master: "ClientApp", db: Database):
        super().__init__(master)
        self.db = db
        self.title("Anmeldung")
        self.configure(bg="white")
        self.resizable(False, False)
        self._build_ui()

    def _build_ui(self) -> None:
        container = tk.Frame(self, bg="white", padx=20, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        title = tk.Label(container, text="Willkommen", bg="white", fg=DEFAULT_ACCENT, font=("SF Pro Display", 18, "bold"))
        title.pack(pady=(0, 10))

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        tk.Label(container, text="Benutzername", bg="white").pack(anchor="w")
        tk.Entry(container, textvariable=self.username_var, highlightthickness=1, relief="flat", highlightbackground="#d1d5db", highlightcolor=DEFAULT_ACCENT).pack(fill=tk.X, pady=(0, 10))

        tk.Label(container, text="Passwort", bg="white").pack(anchor="w")
        tk.Entry(container, textvariable=self.password_var, show="*", highlightthickness=1, relief="flat", highlightbackground="#d1d5db", highlightcolor=DEFAULT_ACCENT).pack(fill=tk.X, pady=(0, 20))

        actions = tk.Frame(container, bg="white")
        actions.pack(fill=tk.X)

        login_btn = tk.Button(actions, text="Anmelden", command=self._handle_login, bg=DEFAULT_ACCENT, fg="white", relief="flat", padx=12, pady=8)
        login_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        register_btn = tk.Button(actions, text="Registrieren", command=self._handle_register, bg="#e5e7eb", fg="#111827", relief="flat", padx=12, pady=8)
        register_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

    def _handle_login(self) -> None:
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        if not username or not password:
            messagebox.showwarning("Hinweis", "Bitte Benutzername und Passwort eingeben.")
            return
        if self.db.validate_user(username, password):
            self.master.on_login_success(username)
            self.destroy()
        else:
            messagebox.showerror("Fehler", "Ungültige Zugangsdaten.")

    def _handle_register(self) -> None:
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        if not username or not password:
            messagebox.showwarning("Hinweis", "Bitte Benutzername und Passwort eingeben.")
            return
        created = self.db.create_user(username, password)
        if created:
            messagebox.showinfo("Erfolg", "Konto erstellt. Sie können sich jetzt anmelden.")
        else:
            messagebox.showerror("Fehler", "Benutzername bereits vergeben.")


class SignaturePad(tk.Canvas):
    def __init__(self, master: tk.Widget, **kwargs):
        super().__init__(master, **kwargs)
        self.strokes: List[List[Tuple[int, int]]] = []
        self.current_stroke: List[Tuple[int, int]] = []
        self.bind("<ButtonPress-1>", self._start)
        self.bind("<B1-Motion>", self._draw)
        self.bind("<ButtonRelease-1>", self._end)

    def _start(self, event: tk.Event) -> None:
        self.current_stroke = [(event.x, event.y)]

    def _draw(self, event: tk.Event) -> None:
        last_point = self.current_stroke[-1]
        self.create_line(last_point[0], last_point[1], event.x, event.y, width=2, fill="#111827", capstyle=tk.ROUND)
        self.current_stroke.append((event.x, event.y))

    def _end(self, _: tk.Event) -> None:
        if self.current_stroke:
            self.strokes.append(self.current_stroke)
            self.current_stroke = []

    def clear(self) -> None:
        self.delete("all")
        self.strokes = []


class ClientApp(tk.Tk):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.title("Kundenverwaltung")
        self.geometry("1000x720")
        self.configure(bg="white")
        self.accent_color = self.db.load_setting("accent_color", DEFAULT_ACCENT)
        self.company_name = self.db.load_setting("company_name", "")
        self.logo_path = self.db.load_setting("logo_path", "")
        self.extra_field_rows: List[Tuple[tk.Entry, tk.Entry]] = []
        self._build_login()

    def _build_login(self) -> None:
        AuthWindow(self, self.db)
        self.withdraw()

    def on_login_success(self, username: str) -> None:
        self.deiconify()
        self.username = username
        self._build_ui()

    def _build_ui(self) -> None:
        for child in self.winfo_children():
            child.destroy()

        top_bar = tk.Frame(self, bg="white", padx=20, pady=10)
        top_bar.pack(fill=tk.X)
        title_text = "Kundenverwaltung"
        if self.company_name:
            title_text = f"{self.company_name} – Kundenverwaltung"
        tk.Label(top_bar, text=title_text, bg="white", fg=self.accent_color, font=("SF Pro Display", 20, "bold")).pack(side=tk.LEFT)

        settings_btn = tk.Button(
            top_bar,
            text="Branding",
            bg="#e5e7eb",
            relief="flat",
            command=self._open_settings,
            padx=10,
            pady=6,
        )
        settings_btn.pack(side=tk.RIGHT, padx=5)

        export_btn = tk.Button(
            top_bar,
            text="Als Excel exportieren",
            bg=self.accent_color,
            fg="white",
            relief="flat",
            command=self._export_excel,
            padx=10,
            pady=6,
        )
        export_btn.pack(side=tk.RIGHT, padx=5)

        content = tk.Frame(self, bg="white", padx=20, pady=10)
        content.pack(fill=tk.BOTH, expand=True)

        form_frame = tk.Frame(content, bg="white")
        form_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.form_frame = form_frame

        self.form_vars: Dict[str, tk.StringVar] = {
            "kundennummer": tk.StringVar(value=self.db._next_kundennummer()),
            "ma": tk.StringVar(),
            "name": tk.StringVar(),
            "strasse": tk.StringVar(),
            "plz": tk.StringVar(),
            "ort": tk.StringVar(),
            "geburtsdatum": tk.StringVar(),
            "pg": tk.StringVar(),
            "versicherungsnummer": tk.StringVar(),
            "pflegekasse": tk.StringVar(),
            "telefon": tk.StringVar(),
            "preise": tk.StringVar(),
            "fahrtkosten": tk.StringVar(),
            "bemerkungen": tk.StringVar(),
        }

        fields = [
            ("Kundennummer", "kundennummer"),
            ("MA", "ma"),
            ("Name des Kunden", "name"),
            ("Straße", "strasse"),
            ("PLZ", "plz"),
            ("Ort", "ort"),
            ("Geburtsdatum", "geburtsdatum"),
            ("PG", "pg"),
            ("Versicherungs-Nr.", "versicherungsnummer"),
            ("Pflegekasse", "pflegekasse"),
            ("Telefon", "telefon"),
            ("Preise", "preise"),
            ("Fahrtkosten", "fahrtkosten"),
            ("Bemerkungen", "bemerkungen"),
        ]

        self.base_field_count = len(fields)
        for idx, (label_text, key) in enumerate(fields):
            row = tk.Frame(form_frame, bg="white")
            row.grid(row=idx, column=0, sticky="ew", pady=4)
            tk.Label(row, text=label_text, width=16, anchor="w", bg="white").pack(side=tk.LEFT)
            entry_state = "disabled" if key == "kundennummer" else "normal"
            tk.Entry(
                row,
                textvariable=self.form_vars[key],
                state=entry_state,
                highlightthickness=1,
                relief="flat",
                highlightbackground="#d1d5db",
                highlightcolor=self.accent_color,
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.extra_fields_container = tk.Frame(form_frame, bg="white")
        self.extra_fields_container.grid(row=len(fields), column=0, sticky="ew")

        add_field_btn = tk.Button(
            form_frame,
            text="Weiteres Feld hinzufügen",
            command=self._add_extra_field,
            bg="#e5e7eb",
            relief="flat",
            padx=8,
            pady=6,
        )
        add_field_btn.grid(row=len(fields) + 1, column=0, sticky="w", pady=6)

        save_btn = tk.Button(
            form_frame,
            text="Speichern",
            command=self._save_client,
            bg=self.accent_color,
            fg="white",
            relief="flat",
            padx=12,
            pady=8,
        )
        save_btn.grid(row=len(fields) + 2, column=0, sticky="w")

        list_frame = tk.Frame(content, bg="white")
        list_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        columns = (
            "kundennummer",
            "name",
            "plz",
            "ort",
            "telefon",
            "pg",
            "pflegekasse",
        )
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=20)
        headings = {
            "kundennummer": "Kundennummer",
            "name": "Name",
            "plz": "PLZ",
            "ort": "Ort",
            "telefon": "Telefon",
            "pg": "PG",
            "pflegekasse": "Pflegekasse",
        }
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=120)
        self.tree.pack(fill=tk.BOTH, expand=True)

        actions = tk.Frame(list_frame, bg="white", pady=8)
        actions.pack(fill=tk.X)

        refresh_btn = tk.Button(actions, text="Liste aktualisieren", command=self._load_clients, bg="#e5e7eb", relief="flat", padx=8, pady=6)
        refresh_btn.pack(side=tk.LEFT, padx=4)

        contract_btn = tk.Button(
            actions,
            text="Vertrag erstellen",
            command=self._open_contract_window,
            bg=self.accent_color,
            fg="white",
            relief="flat",
            padx=8,
            pady=6,
        )
        contract_btn.pack(side=tk.LEFT, padx=4)

        self._load_clients()

    def _add_extra_field(self) -> None:
        idx = len(self.extra_field_rows)
        field_row = tk.Frame(self.extra_fields_container, bg="white")
        field_row.grid(row=idx, column=0, sticky="ew", pady=4)

        name_entry = tk.Entry(
            field_row,
            highlightthickness=1,
            relief="flat",
            highlightbackground="#d1d5db",
            highlightcolor=self.accent_color,
            width=16,
        )
        name_entry.insert(0, "Feldname")
        name_entry.pack(side=tk.LEFT, padx=(0, 6))

        value_entry = tk.Entry(
            field_row,
            highlightthickness=1,
            relief="flat",
            highlightbackground="#d1d5db",
            highlightcolor=self.accent_color,
        )
        value_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.extra_field_rows.append((name_entry, value_entry))

    def _save_client(self) -> None:
        data = {key: var.get().strip() for key, var in self.form_vars.items()}
        if not data.get("name"):
            messagebox.showwarning("Hinweis", "Bitte geben Sie mindestens den Namen des Kunden ein.")
            return
        extra_fields: Dict[str, str] = {}
        for name_entry, value_entry in self.extra_field_rows:
            name = name_entry.get().strip()
            value = value_entry.get().strip()
            if name:
                extra_fields[name] = value
        self.db.save_client(data, extra_fields)
        messagebox.showinfo("Gespeichert", "Kunde gespeichert.")
        self.form_vars["kundennummer"].set(self.db._next_kundennummer())
        for key, var in self.form_vars.items():
            if key != "kundennummer":
                var.set("")
        for name_entry, value_entry in self.extra_field_rows:
            name_entry.destroy()
            value_entry.destroy()
        self.extra_field_rows = []
        self._load_clients()

    def _load_clients(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for client in self.db.list_clients():
            self.tree.insert("", tk.END, values=(
                client.get("kundennummer"),
                client.get("name"),
                client.get("plz"),
                client.get("ort"),
                client.get("telefon"),
                client.get("pg"),
                client.get("pflegekasse"),
            ))

    def _export_excel(self) -> None:
        clients = self.db.list_clients()
        if not clients:
            messagebox.showinfo("Hinweis", "Keine Kunden zum Exportieren.")
            return
        workbook = Workbook()
        sheet = workbook.active
        headers = list(clients[0].keys())
        sheet.append(headers)
        for client in clients:
            sheet.append([client.get(h, "") for h in headers])
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if not file_path:
            return
        workbook.save(file_path)
        messagebox.showinfo("Erfolg", f"Excel wurde gespeichert: {file_path}")

    def _open_contract_window(self) -> None:
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Hinweis", "Bitte wählen Sie einen Kunden aus.")
            return
        values = self.tree.item(selected, "values")
        kundennummer = values[0]
        client = next((c for c in self.db.list_clients() if c.get("kundennummer") == kundennummer), None)
        if not client:
            messagebox.showerror("Fehler", "Kunde nicht gefunden.")
            return
        ContractWindow(self, client, self.company_name, self.logo_path, self.accent_color)

    def _open_settings(self) -> None:
        SettingsWindow(self, self.db)


class ContractWindow(tk.Toplevel):
    def __init__(self, master: ClientApp, client: Dict[str, str], company_name: str, logo_path: str, accent_color: str):
        super().__init__(master)
        self.client = client
        self.company_name = company_name
        self.logo_path = logo_path
        self.accent_color = accent_color
        self.title("Vertrag erstellen")
        self.configure(bg="white")
        self._build_ui()

    def _build_ui(self) -> None:
        container = tk.Frame(self, bg="white", padx=20, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        heading = tk.Label(container, text="Vertrag", font=("SF Pro Display", 18, "bold"), fg=self.accent_color, bg="white")
        heading.pack(anchor="w")

        info_text = tk.Text(container, height=12, bg="#f9fafb", relief="flat", wrap="word")
        info_text.pack(fill=tk.BOTH, expand=True, pady=10)
        info_text.insert(tk.END, self._compose_contract_text())
        info_text.configure(state="disabled")

        tk.Label(container, text="Signatur", bg="white").pack(anchor="w")
        self.signature_pad = SignaturePad(container, width=400, height=160, bg="#f3f4f6", highlightthickness=1, highlightbackground="#d1d5db")
        self.signature_pad.pack(fill=tk.X, pady=6)

        actions = tk.Frame(container, bg="white")
        actions.pack(fill=tk.X)

        clear_btn = tk.Button(actions, text="Signatur löschen", command=self.signature_pad.clear, bg="#e5e7eb", relief="flat", padx=8, pady=6)
        clear_btn.pack(side=tk.LEFT, padx=4)

        export_btn = tk.Button(actions, text="Als PDF exportieren", command=self._export_pdf, bg=self.accent_color, fg="white", relief="flat", padx=8, pady=6)
        export_btn.pack(side=tk.RIGHT, padx=4)

    def _compose_contract_text(self) -> str:
        lines = [
            f"Kundennummer: {self.client.get('kundennummer', '')}",
            f"Name: {self.client.get('name', '')}",
            f"Straße / Ort: {self.client.get('strasse', '')}, {self.client.get('plz', '')} {self.client.get('ort', '')}",
            f"Geburtsdatum: {self.client.get('geburtsdatum', '')}",
            f"Pflegegrad: {self.client.get('pg', '')}",
            f"Versicherungs-Nr.: {self.client.get('versicherungsnummer', '')}",
            f"Pflegekasse: {self.client.get('pflegekasse', '')}",
            "",
            "Dieser Vertrag bestätigt die Erbringung der vereinbarten Leistungen.",
            "Die Konditionen richten sich nach den hinterlegten Preisen und Fahrtkosten.",
            "Bitte prüfen Sie die Angaben und unterzeichnen Sie digital.",
        ]
        if self.company_name:
            lines.append("")
            lines.append(f"Anbieter: {self.company_name}")
        if self.logo_path:
            lines.append(f"Logo-Datei: {self.logo_path}")
        return "\n".join(lines)

    def _export_pdf(self) -> None:
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not file_path:
            return
        pdf = pdf_canvas.Canvas(file_path, pagesize=A4)
        width, height = A4
        y = height - 60
        pdf.setFont("Helvetica-Bold", 14)
        pdf.setFillColorRGB(0.12, 0.16, 0.22)
        pdf.drawString(50, y, "Vertrag")
        y -= 20
        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, y, f"Kundennummer: {self.client.get('kundennummer', '')}")
        y -= 16
        pdf.drawString(50, y, f"Name: {self.client.get('name', '')}")
        y -= 16
        pdf.drawString(50, y, f"Adresse: {self.client.get('strasse', '')}, {self.client.get('plz', '')} {self.client.get('ort', '')}")
        y -= 16
        pdf.drawString(50, y, f"Geburtsdatum: {self.client.get('geburtsdatum', '')}")
        y -= 16
        pdf.drawString(50, y, f"Pflegegrad: {self.client.get('pg', '')}")
        y -= 16
        pdf.drawString(50, y, f"Versicherungs-Nr.: {self.client.get('versicherungsnummer', '')}")
        y -= 16
        pdf.drawString(50, y, f"Pflegekasse: {self.client.get('pflegekasse', '')}")
        y -= 30
        pdf.drawString(50, y, "Mit der Unterzeichnung bestätigen beide Parteien den Vertrag.")
        y -= 40
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, "Signatur")
        y -= 10
        pdf.setLineWidth(2)
        for stroke in self.signature_pad.strokes:
            for i in range(len(stroke) - 1):
                p1 = stroke[i]
                p2 = stroke[i + 1]
                pdf.line(50 + p1[0], y + p1[1], 50 + p2[0], y + p2[1])
        pdf.showPage()
        pdf.save()
        messagebox.showinfo("Erfolg", f"PDF gespeichert: {file_path}")


class SettingsWindow(tk.Toplevel):
    def __init__(self, master: ClientApp, db: Database):
        super().__init__(master)
        self.db = db
        self.master_app = master
        self.title("Branding")
        self.configure(bg="white")
        self._build_ui()

    def _build_ui(self) -> None:
        container = tk.Frame(self, bg="white", padx=20, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text="Unternehmensname", bg="white").pack(anchor="w")
        self.company_var = tk.StringVar(value=self.db.load_setting("company_name", ""))
        tk.Entry(container, textvariable=self.company_var, highlightthickness=1, relief="flat", highlightbackground="#d1d5db", highlightcolor=self.master_app.accent_color).pack(fill=tk.X, pady=(0, 10))

        tk.Label(container, text="Logo-Datei (Pfad)", bg="white").pack(anchor="w")
        self.logo_var = tk.StringVar(value=self.db.load_setting("logo_path", ""))
        logo_row = tk.Frame(container, bg="white")
        logo_row.pack(fill=tk.X, pady=(0, 10))
        tk.Entry(logo_row, textvariable=self.logo_var, highlightthickness=1, relief="flat", highlightbackground="#d1d5db", highlightcolor=self.master_app.accent_color).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(logo_row, text="Wählen", bg="#e5e7eb", relief="flat", command=self._pick_logo).pack(side=tk.LEFT, padx=6)

        tk.Label(container, text="Akzentfarbe (HEX)", bg="white").pack(anchor="w")
        self.color_var = tk.StringVar(value=self.db.load_setting("accent_color", DEFAULT_ACCENT))
        tk.Entry(container, textvariable=self.color_var, highlightthickness=1, relief="flat", highlightbackground="#d1d5db", highlightcolor=self.master_app.accent_color).pack(fill=tk.X, pady=(0, 20))

        save_btn = tk.Button(container, text="Speichern", command=self._save, bg=self.master_app.accent_color, fg="white", relief="flat", padx=10, pady=8)
        save_btn.pack(anchor="e")

    def _pick_logo(self) -> None:
        file_path = filedialog.askopenfilename(filetypes=[("Bilddateien", "*.png;*.jpg;*.jpeg;*.svg"), ("Alle Dateien", "*.*")])
        if file_path:
            self.logo_var.set(file_path)

    def _save(self) -> None:
        self.db.save_setting("company_name", self.company_var.get().strip())
        self.db.save_setting("logo_path", self.logo_var.get().strip())
        self.db.save_setting("accent_color", self.color_var.get().strip() or DEFAULT_ACCENT)
        self.master_app.accent_color = self.db.load_setting("accent_color", DEFAULT_ACCENT)
        self.master_app.company_name = self.db.load_setting("company_name", "")
        self.master_app.logo_path = self.db.load_setting("logo_path", "")
        messagebox.showinfo("Gespeichert", "Branding aktualisiert. Starten Sie neu, um Farben vollständig zu übernehmen.")
        self.destroy()


def main() -> None:
    db = Database()
    app = ClientApp(db)
    app.mainloop()


if __name__ == "__main__":
    main()
