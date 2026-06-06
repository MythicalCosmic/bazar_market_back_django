#!/usr/bin/env python3
"""
Bazar Market Print Agent — Desktop App
======================================
A modern, friendly graphical app for shop staff. No terminal, no commands.

Pick your printer from a list, press "Connect", and the app prints receipts
as orders come in. Buttons let you check the server connection and run a test
print so you can confirm everything works before the rush.

Built with CustomTkinter for a clean dark UI. Reuses all the printer detection
and receipt rendering logic from agent.py, so the GUI and the headless CLI
agent print identical receipts.

Run:    python gui.py
Build:  pyinstaller gui.spec  (produces a windowed BazarMarketPrinter.exe)
"""

import asyncio
import json
import logging
import os
import queue
import threading
from urllib.parse import urlparse

import customtkinter as ctk

# Core logic lives in agent.py — keep receipts identical between GUI and CLI.
import agent
from agent import (
    APP_VERSION,
    DEFAULT_PRINTER_ID,
    DEFAULT_SERVER,
    DEFAULT_TOKEN,
    _get_base_dir,
    detect_printers,
    get_printer,
    load_config,
    print_receipt,
)

APP_TITLE = "Bazar Market Print Agent"

# ── Palette ────────────────────────────────────────────────────
ACCENT = "#2563eb"
ACCENT_HOVER = "#1d4ed8"
GREEN = "#16a34a"
GREEN_HOVER = "#15803d"
RED = "#dc2626"
RED_HOVER = "#b91c1c"
SLATE = "#334155"
SLATE_HOVER = "#475569"
CARD = ("#ffffff", "#1e293b")
CARD_SOFT = ("#f1f5f9", "#0f172a")
MUTED = ("#64748b", "#94a3b8")

# status colors
C_IDLE = "#64748b"
C_CONNECTING = "#d97706"
C_OK = "#16a34a"
C_ERR = "#dc2626"

FONT = "Segoe UI"
MONO = "Consolas"


# ── Shared helpers ─────────────────────────────────────────────

def list_printer_options() -> list[dict]:
    """Return selectable printer options for the dropdown.

    Always offers Auto-detect first, then every detected device with a stable
    `path` value matching what agent.get_printer() expects.
    """
    options = [{"label": "Auto-detect (recommended)", "path": None}]
    for p in detect_printers():
        if p.get("type") == "usb":
            path = f"{p['vendor_id']:04x}:{p['product_id']:04x}"
        else:
            path = p.get("path")
        options.append({"label": p["name"], "path": path})
    return options


def build_ws_url(url: str, token: str, printer_id: str) -> str:
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}token={token}&printer_id={printer_id}"


def build_origin(url: str) -> str:
    parsed = urlparse(url)
    scheme = "https" if parsed.scheme == "wss" else "http"
    return f"{scheme}://{parsed.netloc}"


def save_config(data: dict) -> str:
    """Persist editable settings to config.json next to the exe/script."""
    path = os.path.join(_get_base_dir(), "config.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def sample_receipt() -> dict:
    """A realistic receipt used by the Test Print button."""
    return {
        "order_number": "TEST-0001",
        "customer_name": "Sinov Mijoz",
        "customer_phone": "+998 90 123 45 67",
        "address": "Toshkent sh., Sinov ko'chasi 1",
        "user_note": "Bu sinov chekidir",
        "payment_method": "Naqd",
        "payment_status": "TO'LANGAN",
        "items": [
            {"name": "Non", "qty": 2, "unit": "dona", "unit_price": 3000, "total": 6000},
            {"name": "Sut 1L", "qty": 1, "unit": "dona", "unit_price": 12000, "total": 12000},
            {"name": "Olma", "qty": 1.5, "unit": "kg", "unit_price": 15000, "total": 22500},
        ],
        "subtotal": 40500,
        "delivery_fee": 5000,
        "discount": 500,
        "total": 45000,
        "logo": "",
    }


# ── Logging bridge: route agent logs into the GUI ──────────────

class QueueLogHandler(logging.Handler):
    """Push log records onto a thread-safe queue the GUI drains on its own thread."""

    def __init__(self, q: "queue.Queue"):
        super().__init__()
        self.q = q

    def emit(self, record):
        try:
            self.q.put(("log", record.levelno, self.format(record)))
        except Exception:
            pass


# ── Background connection manager ──────────────────────────────

class ConnectionManager:
    """Runs the WebSocket print loop on a background asyncio thread.

    All UI updates are funneled through a queue so the Tk main thread stays the
    only thing touching widgets.
    """

    def __init__(self, q: "queue.Queue"):
        self.q = q
        self._thread = None
        self._loop = None
        self._stop = None
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def _emit_status(self, color: str, text: str):
        self.q.put(("status", color, text))

    def _emit_log(self, level: int, text: str):
        self.q.put(("log", level, text))

    def start(self, url, token, printer_id, printer_path):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run,
            args=(url, token, printer_id, printer_path),
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        """Signal the background loop to disconnect. Returns immediately."""
        if self._loop and self._stop and not self._stop.is_set():
            self._loop.call_soon_threadsafe(self._stop.set)

    def _run(self, url, token, printer_id, printer_path):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._stop = asyncio.Event()
        try:
            self._loop.run_until_complete(
                self._agent(url, token, printer_id, printer_path)
            )
        except Exception as e:
            self._emit_log(logging.ERROR, f"Connection thread crashed: {e}")
        finally:
            try:
                self._loop.close()
            except Exception:
                pass
            self._running = False
            self._emit_status(C_IDLE, "Disconnected")
            self._emit_log(logging.INFO, "Stopped.")
            self.q.put(("connection_ended", None, None))

    async def _agent(self, url, token, printer_id, printer_path):
        import websockets

        self._emit_log(logging.INFO, "Looking for the printer…")
        printer = get_printer(printer_path)
        if not printer:
            self._emit_status(C_ERR, "No printer found")
            self._emit_log(
                logging.ERROR,
                "No printer detected. Connect a USB thermal printer (or install "
                "its Windows driver) and press Refresh, then try again.",
            )
            return

        self._emit_log(logging.INFO, "Printer ready.")
        full_url = build_ws_url(url, token, printer_id)
        origin = build_origin(url)
        reconnect_delay = 2

        while not self._stop.is_set():
            try:
                self._emit_status(C_CONNECTING, "Connecting…")
                self._emit_log(logging.INFO, "Connecting to server…")
                async with websockets.connect(
                    full_url,
                    ping_interval=30,
                    ping_timeout=10,
                    origin=origin,
                    open_timeout=15,
                ) as ws:
                    self._emit_status(C_OK, "Connected — ready to print")
                    self._emit_log(logging.INFO, "Connected. Waiting for orders…")
                    reconnect_delay = 2

                    while not self._stop.is_set():
                        recv_task = asyncio.ensure_future(ws.recv())
                        stop_task = asyncio.ensure_future(self._stop.wait())
                        done, pending = await asyncio.wait(
                            {recv_task, stop_task},
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        for t in pending:
                            t.cancel()
                        if stop_task in done:
                            await ws.close()
                            return

                        message = recv_task.result()
                        await self._handle_message(printer, ws, message)

            except Exception as e:
                if self._stop.is_set():
                    break
                self._emit_status(C_CONNECTING, "Reconnecting…")
                self._emit_log(
                    logging.WARNING,
                    f"Connection lost ({e}). Retrying in {reconnect_delay}s…",
                )
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=reconnect_delay)
                    break  # stop requested during the wait
                except asyncio.TimeoutError:
                    reconnect_delay = min(reconnect_delay * 2, 60)

    async def _handle_message(self, printer, ws, message):
        try:
            data = json.loads(message)
            order_num = data.get("order_number", "?")
            self._emit_log(logging.INFO, f"Printing order #{order_num}…")
            await asyncio.get_event_loop().run_in_executor(
                None, print_receipt, printer, data
            )
            await ws.send(json.dumps({"status": "printed", "order_number": order_num}))
            self._emit_log(logging.INFO, f"Order #{order_num} printed.")
        except Exception as e:
            self._emit_log(logging.ERROR, f"Could not print this order: {e}")


# ── The app window ─────────────────────────────────────────────

class PrintAgentApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.q: "queue.Queue" = queue.Queue()
        self.manager = ConnectionManager(self.q)

        cfg = load_config()
        self.var_server = ctk.StringVar(value=cfg.get("server", DEFAULT_SERVER))
        self.var_token = ctk.StringVar(value=cfg.get("token", DEFAULT_TOKEN))
        self.var_printer_id = ctk.StringVar(value=cfg.get("printer_id", DEFAULT_PRINTER_ID))
        self.var_auto = ctk.BooleanVar(value=bool(cfg.get("auto_connect", False)))
        self._saved_printer_path = cfg.get("printer")
        self.printer_options: list[dict] = []

        self._route_agent_logs()
        self._build_ui()
        self._refresh_printers(select_path=self._saved_printer_path)

        self.after(100, self._drain_queue)
        if self.var_auto.get():
            self.after(500, self._connect)

    # ── logging wiring ─────────────────────────────────────────

    def _route_agent_logs(self):
        handler = QueueLogHandler(self.q)
        handler.setFormatter(logging.Formatter("%(message)s"))
        agent.logger.addHandler(handler)
        agent.logger.setLevel(logging.INFO)

    # ── UI construction ────────────────────────────────────────

    def _build_ui(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry("680x780")
        self.minsize(620, 720)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        pad = {"padx": 22}

        # ── Header ──────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(20, 6), **pad)
        header.grid_columnconfigure(0, weight=1)

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(title_box, text="🖨", font=(FONT, 30)).grid(row=0, column=0, rowspan=2, padx=(0, 12))
        ctk.CTkLabel(title_box, text="Bazar Market", font=(FONT, 22, "bold")).grid(
            row=0, column=1, sticky="w")
        ctk.CTkLabel(title_box, text=f"Print Agent  ·  v{APP_VERSION}",
                     font=(FONT, 12), text_color=MUTED).grid(row=1, column=1, sticky="w")

        # status pill (right side of header)
        self.status_pill = ctk.CTkFrame(header, corner_radius=20, fg_color=CARD)
        self.status_pill.grid(row=0, column=1, sticky="e")
        self.status_dot = ctk.CTkLabel(self.status_pill, text="●", text_color=C_IDLE,
                                       font=(FONT, 16))
        self.status_dot.grid(row=0, column=0, padx=(14, 6), pady=8)
        self.status_text = ctk.CTkLabel(self.status_pill, text="Disconnected",
                                        font=(FONT, 13, "bold"))
        self.status_text.grid(row=0, column=1, padx=(0, 16), pady=8)

        # ── Settings card ───────────────────────────────────────
        card = ctk.CTkFrame(self, corner_radius=16, fg_color=CARD)
        card.grid(row=1, column=0, sticky="ew", pady=(12, 0), **pad)
        card.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        inner.grid_columnconfigure(0, weight=1)

        def field_label(parent, text):
            return ctk.CTkLabel(parent, text=text.upper(), font=(FONT, 11, "bold"),
                                text_color=MUTED, anchor="w")

        # Server
        field_label(inner, "Server").grid(row=0, column=0, sticky="w")
        self.entry_server = ctk.CTkEntry(inner, textvariable=self.var_server, height=38,
                                         corner_radius=10, border_width=1)
        self.entry_server.grid(row=1, column=0, sticky="ew", pady=(4, 14))

        # Token (+ show toggle)
        token_head = ctk.CTkFrame(inner, fg_color="transparent")
        token_head.grid(row=2, column=0, sticky="ew")
        token_head.grid_columnconfigure(0, weight=1)
        field_label(token_head, "Token").grid(row=0, column=0, sticky="w")
        self.switch_show = ctk.CTkSwitch(token_head, text="Show", command=self._toggle_token,
                                         font=(FONT, 11), width=40)
        self.switch_show.grid(row=0, column=1, sticky="e")
        self.entry_token = ctk.CTkEntry(inner, textvariable=self.var_token, height=38,
                                        corner_radius=10, border_width=1, show="•")
        self.entry_token.grid(row=3, column=0, sticky="ew", pady=(4, 14))

        # Printer ID
        field_label(inner, "Printer ID").grid(row=4, column=0, sticky="w")
        self.entry_printer_id = ctk.CTkEntry(inner, textvariable=self.var_printer_id, height=38,
                                             corner_radius=10, border_width=1)
        self.entry_printer_id.grid(row=5, column=0, sticky="ew", pady=(4, 14))

        # Printer dropdown + refresh
        field_label(inner, "Printer").grid(row=6, column=0, sticky="w")
        printer_row = ctk.CTkFrame(inner, fg_color="transparent")
        printer_row.grid(row=7, column=0, sticky="ew", pady=(4, 14))
        printer_row.grid_columnconfigure(0, weight=1)
        self.option_printer = ctk.CTkOptionMenu(
            printer_row, values=["Auto-detect (recommended)"], height=38, corner_radius=10,
            fg_color=CARD_SOFT, button_color=SLATE, button_hover_color=SLATE_HOVER,
            dropdown_fg_color=CARD,
        )
        self.option_printer.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.btn_refresh = ctk.CTkButton(
            printer_row, text="↻  Refresh", width=110, height=38, corner_radius=10,
            fg_color=SLATE, hover_color=SLATE_HOVER, command=lambda: self._refresh_printers())
        self.btn_refresh.grid(row=0, column=1)

        # auto-connect switch
        self.switch_auto = ctk.CTkSwitch(
            inner, text="Connect automatically when the app starts",
            variable=self.var_auto, font=(FONT, 12))
        self.switch_auto.grid(row=8, column=0, sticky="w", pady=(2, 0))

        # ── Action buttons ──────────────────────────────────────
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", pady=(16, 6), **pad)
        actions.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_connect = ctk.CTkButton(
            actions, text="Connect", height=48, corner_radius=12,
            font=(FONT, 15, "bold"), fg_color=GREEN, hover_color=GREEN_HOVER,
            command=self._toggle_connect)
        self.btn_connect.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        self.btn_test_conn = ctk.CTkButton(
            actions, text="Test Connection", height=42, corner_radius=12,
            font=(FONT, 13), fg_color=SLATE, hover_color=SLATE_HOVER,
            command=self._test_connection)
        self.btn_test_conn.grid(row=1, column=0, sticky="ew", padx=(0, 6))

        self.btn_test_print = ctk.CTkButton(
            actions, text="Test Print", height=42, corner_radius=12,
            font=(FONT, 13), fg_color=SLATE, hover_color=SLATE_HOVER,
            command=self._test_print)
        self.btn_test_print.grid(row=1, column=1, sticky="ew", padx=6)

        self.btn_save = ctk.CTkButton(
            actions, text="Save Settings", height=42, corner_radius=12,
            font=(FONT, 13), fg_color="transparent", border_width=1,
            border_color=SLATE, text_color=MUTED, hover_color=CARD_SOFT,
            command=self._save_settings)
        self.btn_save.grid(row=1, column=2, sticky="ew", padx=(6, 0))

        # ── Activity log ────────────────────────────────────────
        log_card = ctk.CTkFrame(self, corner_radius=16, fg_color=CARD)
        log_card.grid(row=3, column=0, sticky="nsew", pady=(10, 18), **pad)
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(log_card, text="ACTIVITY", font=(FONT, 11, "bold"),
                     text_color=MUTED).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 0))
        self.log = ctk.CTkTextbox(log_card, font=(MONO, 12), corner_radius=10,
                                  fg_color=CARD_SOFT, wrap="word", activate_scrollbars=True)
        self.log.grid(row=1, column=0, sticky="nsew", padx=14, pady=(6, 14))
        self.log.tag_config("info", foreground="#cbd5e1")
        self.log.tag_config("good", foreground="#4ade80")
        self.log.tag_config("warn", foreground="#fbbf24")
        self.log.tag_config("error", foreground="#f87171")
        self.log.configure(state="disabled")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── helpers ────────────────────────────────────────────────

    def _toggle_token(self):
        self.entry_token.configure(show="" if self.switch_show.get() else "•")

    def _append_log(self, level: int, text: str):
        tag = "info"
        if level >= logging.ERROR:
            tag = "error"
        elif level >= logging.WARNING:
            tag = "warn"
        elif text.lstrip("✓ ").lower().startswith(
                ("connected", "order", "printer ready", "server reachable", "test receipt")):
            tag = "good"
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_status(self, color: str, text: str):
        self.status_dot.configure(text_color=color)
        self.status_text.configure(text=text)

    def _selected_printer_path(self):
        label = self.option_printer.get()
        for o in self.printer_options:
            if o["label"] == label:
                return o["path"]
        return None

    def _refresh_printers(self, select_path="__keep__"):
        if select_path == "__keep__":
            select_path = self._selected_printer_path()
        self._append_log(logging.INFO, "Scanning for printers…")
        self.printer_options = list_printer_options()
        labels = [o["label"] for o in self.printer_options]
        self.option_printer.configure(values=labels)

        target = labels[0]
        if select_path is not None:
            for o in self.printer_options:
                if o["path"] == select_path:
                    target = o["label"]
                    break
        self.option_printer.set(target)
        found = len(self.printer_options) - 1
        self._append_log(logging.INFO,
                         f"Found {found} printer(s)." if found else
                         "No printers found yet — auto-detect will retry on connect.")

    # ── button handlers ────────────────────────────────────────

    def _toggle_connect(self):
        if self.manager.running:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        url = self.var_server.get().strip()
        token = self.var_token.get().strip()
        printer_id = self.var_printer_id.get().strip() or DEFAULT_PRINTER_ID
        if not url or not token:
            self._append_log(logging.ERROR, "✗ Please fill in the Server and Token fields.")
            return
        self.btn_connect.configure(text="Disconnect", fg_color=RED, hover_color=RED_HOVER)
        self._set_inputs_enabled(False)
        self.manager.start(url, token, printer_id, self._selected_printer_path())

    def _disconnect(self):
        self._append_log(logging.INFO, "Disconnecting…")
        self.btn_connect.configure(state="disabled")
        self.manager.stop()

    def _on_connection_ended(self):
        self.btn_connect.configure(text="Connect", state="normal",
                                   fg_color=GREEN, hover_color=GREEN_HOVER)
        self._set_inputs_enabled(True)

    def _set_inputs_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        for w in (self.entry_server, self.entry_token, self.entry_printer_id,
                  self.option_printer, self.btn_refresh, self.switch_show, self.switch_auto):
            w.configure(state=state)

    def _test_connection(self):
        url = self.var_server.get().strip()
        token = self.var_token.get().strip()
        printer_id = self.var_printer_id.get().strip() or DEFAULT_PRINTER_ID
        if not url or not token:
            self._append_log(logging.ERROR, "✗ Please fill in the Server and Token fields.")
            return
        self.btn_test_conn.configure(state="disabled", text="Testing…")
        self._append_log(logging.INFO, "Testing connection to the server…")

        def worker():
            ok, detail = self._probe_connection(url, token, printer_id)
            self.q.put(("test_conn_result", ok, detail))

        threading.Thread(target=worker, daemon=True).start()

    def _probe_connection(self, url, token, printer_id):
        import websockets

        async def probe():
            full_url = build_ws_url(url, token, printer_id)
            origin = build_origin(url)
            async with websockets.connect(
                full_url, origin=origin, open_timeout=10, ping_interval=None
            ):
                return True

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(probe())
            return True, "Server reachable and token accepted."
        except Exception as e:
            return False, str(e)
        finally:
            loop.close()

    def _test_print(self):
        path = self._selected_printer_path()
        self.btn_test_print.configure(state="disabled", text="Printing…")
        self._append_log(logging.INFO, "Sending a test receipt to the printer…")

        def worker():
            try:
                printer = get_printer(path)
                if not printer:
                    self.q.put(("test_print_result", False,
                                "No printer found. Check the cable/driver and press Refresh."))
                    return
                print_receipt(printer, sample_receipt())
                self.q.put(("test_print_result", True,
                            "Test receipt sent. Check the printer."))
            except Exception as e:
                self.q.put(("test_print_result", False, f"Test print failed: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _save_settings(self):
        data = {
            "server": self.var_server.get().strip(),
            "token": self.var_token.get().strip(),
            "printer_id": self.var_printer_id.get().strip() or DEFAULT_PRINTER_ID,
            "printer": self._selected_printer_path(),
            "auto_connect": bool(self.var_auto.get()),
        }
        try:
            path = save_config(data)
            self._append_log(logging.INFO, f"✓ Settings saved to {path}")
        except Exception as e:
            self._append_log(logging.ERROR, f"✗ Could not save settings: {e}")

    # ── queue pump ─────────────────────────────────────────────

    def _drain_queue(self):
        try:
            while True:
                kind, a, b = self.q.get_nowait()
                if kind == "log":
                    self._append_log(a, b)
                elif kind == "status":
                    self._set_status(a, b)
                elif kind == "connection_ended":
                    self._on_connection_ended()
                elif kind == "test_conn_result":
                    self.btn_test_conn.configure(state="normal", text="Test Connection")
                    if a:
                        self._append_log(logging.INFO, "✓ " + b)
                    else:
                        self._append_log(logging.ERROR, "✗ Connection failed: " + b)
                elif kind == "test_print_result":
                    self.btn_test_print.configure(state="normal", text="Test Print")
                    if a:
                        self._append_log(logging.INFO, "✓ " + b)
                    else:
                        self._append_log(logging.ERROR, "✗ " + b)
        except queue.Empty:
            pass
        self.after(100, self._drain_queue)

    def _on_close(self):
        if self.manager.running:
            self.manager.stop()
        self.after(150, self.destroy)


def main():
    app = PrintAgentApp()
    app.mainloop()


if __name__ == "__main__":
    main()
