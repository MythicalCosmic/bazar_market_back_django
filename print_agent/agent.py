#!/usr/bin/env python3
"""
Bazar Market Print Agent
========================
Standalone agent that runs on the shop machine.
Connects to the server via WebSocket, receives print jobs, prints receipts.

Can be run as a Python script or built into a standalone .exe with PyInstaller.
Zero-config: just run it. Override defaults with config.json if needed.
"""

import argparse
import asyncio
import json
import logging
import os
import platform
import sys
from datetime import datetime
from decimal import Decimal

# ── Defaults (baked in for .exe builds) ────────────────────────

DEFAULT_SERVER = "wss://api.bazarmarket.org/ws/printer/"
DEFAULT_TOKEN = "ebc2c31bdffff994c0a0027f7ead9e3d8a156dc1f80d0ed5840056434da17946"
DEFAULT_PRINTER_ID = "default"

APP_NAME = "Bazar Market Print Agent"
APP_VERSION = "1.0.0"

# ── Logging ────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("print_agent")

RECEIPT_WIDTH = 32


# ── Config file loading ───────────────────────────────────────

def _get_base_dir():
    """Get the directory where the executable or script lives."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_config() -> dict:
    """Load config.json from next to the exe/script. Falls back to defaults."""
    config_path = os.path.join(_get_base_dir(), "config.json")
    config = {
        "server": DEFAULT_SERVER,
        "token": DEFAULT_TOKEN,
        "printer_id": DEFAULT_PRINTER_ID,
        "printer": None,
    }
    if os.path.isfile(config_path):
        try:
            with open(config_path) as f:
                overrides = json.load(f)
            config.update(overrides)
            logger.info(f"Loaded config from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config.json: {e}, using defaults")
    return config


# ── Printer detection ──────────────────────────────────────────

def detect_printers() -> list[dict]:
    """Auto-detect connected USB/thermal printers."""
    system = platform.system()
    printers = []

    if system == "Linux":
        printers.extend(_detect_linux())
    elif system == "Windows":
        printers.extend(_detect_windows())
    else:
        logger.warning(f"Unsupported OS for auto-detection: {system}")

    return printers


def _detect_linux() -> list[dict]:
    import glob

    found = []
    for path in sorted(glob.glob("/dev/usb/lp*")):
        found.append({"name": f"USB: {path}", "path": path, "type": "file"})
    for path in sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")):
        found.append({"name": f"Serial: {path}", "path": path, "type": "file"})
    return found


def _detect_windows() -> list[dict]:
    found = []

    # USB via pyusb
    try:
        import usb.core

        PRINTER_VENDORS = {
            0x04B8, 0x0519, 0x0416, 0x0DD4, 0x1504,
            0x1A86, 0x0525, 0x0483, 0x0FE6, 0x0456,
            0x067B, 0x1FC9, 0x20D1, 0x0FE6, 0x154F,
        }
        devices = usb.core.find(find_all=True)
        for dev in devices:
            if dev.idVendor in PRINTER_VENDORS:
                name = f"USB: {dev.idVendor:04x}:{dev.idProduct:04x}"
                try:
                    if dev.manufacturer and dev.product:
                        name = f"USB: {dev.manufacturer} {dev.product}"
                except Exception:
                    pass
                found.append({
                    "name": name,
                    "vendor_id": dev.idVendor,
                    "product_id": dev.idProduct,
                    "type": "usb",
                })
    except Exception as e:
        logger.debug(f"USB detection: {e}")

    # Windows shared printers via win32print
    try:
        import win32print

        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        for printer in win32print.EnumPrinters(flags):
            found.append({
                "name": f"Windows: {printer[2]}",
                "path": printer[2],
                "type": "win32",
            })
    except ImportError:
        pass

    return found


def get_printer(printer_path=None):
    """Get an ESC/POS printer instance."""
    from escpos.printer import File, Usb

    if printer_path:
        if ":" in printer_path and len(printer_path.split(":")) == 2:
            parts = printer_path.split(":")
            try:
                vendor = int(parts[0], 16)
                product = int(parts[1], 16)
                return Usb(vendor, product)
            except ValueError:
                pass
        return File(printer_path)

    # Auto-detect
    printers = detect_printers()
    if not printers:
        return None

    logger.info(f"Detected {len(printers)} printer(s):")
    for i, p in enumerate(printers):
        logger.info(f"  [{i}] {p['name']}")

    p = printers[0]
    logger.info(f"Using: {p['name']}")

    if p["type"] == "usb":
        return Usb(p["vendor_id"], p["product_id"])
    elif p["type"] == "file":
        return File(p["path"])
    elif p["type"] == "win32":
        return File(p["path"])

    return None


# ── Receipt rendering ──────────────────────────────────────────

def _fmt(amount) -> str:
    return f"{Decimal(str(amount)):,.0f}"


def _line(left: str, right: str) -> str:
    gap = RECEIPT_WIDTH - len(left) - len(right)
    if gap < 1:
        gap = 1
    return left + " " * gap + right


def _sep() -> str:
    return "-" * RECEIPT_WIDTH


def _dsep() -> str:
    return "=" * RECEIPT_WIDTH


def _center(text: str) -> str:
    return text.center(RECEIPT_WIDTH)


def _print_logo(printer, logo_b64: str):
    if not logo_b64:
        return
    try:
        import base64
        from io import BytesIO
        from PIL import Image

        img_data = base64.b64decode(logo_b64)
        img = Image.open(BytesIO(img_data)).convert("RGBA")
        width = 576
        ratio = width / float(img.width)
        height = int(img.height * ratio)
        img = img.resize((width, height))

        printer.set(align="center")
        printer.image(img)
    except Exception as e:
        logger.debug(f"Logo print skipped: {e}")


def print_receipt(printer, data: dict):
    """Render and print a receipt from structured data."""
    try:
        _print_logo(printer, data.get("logo", ""))
        printer.text("\n")

        printer.set(align="center")
        printer.set(width=2, height=2)
        printer.text("BAZAR MARKET\n")
        printer.set(width=1, height=1)
        printer.text(_dsep() + "\n")

        printer.set(align="left")
        now = datetime.now()
        printer.text(_line("Buyurtma:", data["order_number"]) + "\n")
        printer.text(_line("Sana:", now.strftime("%d.%m.%Y  %H:%M")) + "\n")
        if data.get("payment_method"):
            printer.text(_line("To'lov:", data["payment_method"]) + "\n")
        printer.text(_sep() + "\n")

        printer.text(f"Mijoz:  {data['customer_name']}\n")
        if data.get("customer_phone"):
            printer.text(f"Tel:    {data['customer_phone']}\n")
        if data.get("address"):
            printer.text(f"Manzil: {data['address']}\n")
        if data.get("user_note"):
            printer.text(f"Izoh:   {data['user_note']}\n")
        printer.text(_sep() + "\n")

        printer.text(_center("MAHSULOTLAR") + "\n")
        printer.text(_sep() + "\n")

        for item in data.get("items", []):
            printer.text(f"{item['name']}\n")
            qty = item["qty"]
            detail = f"  {qty} {item['unit']} x {_fmt(item['unit_price'])}"
            printer.text(_line(detail, _fmt(item["total"])) + "\n")

        printer.text(_sep() + "\n")

        printer.text(_line("Jami:", f"{_fmt(data['subtotal'])} so'm") + "\n")

        delivery = Decimal(data.get("delivery_fee", "0"))
        if delivery > 0:
            printer.text(_line("Yetkazish:", f"{_fmt(delivery)} so'm") + "\n")

        discount = Decimal(data.get("discount", "0"))
        if discount > 0:
            printer.text(_line("Chegirma:", f"-{_fmt(discount)} so'm") + "\n")

        printer.text(_dsep() + "\n")
        printer.set(width=2, height=1)
        printer.text(_line("UMUMIY:", f"{_fmt(data['total'])} so'm") + "\n")
        printer.set(width=1, height=1)
        printer.text(_dsep() + "\n")

        printer.set(align="center")
        printer.text(f"[ {data.get('payment_status', '')} ]\n\n")
        printer.text(f"#{data['order_number']}\n\n")
        printer.text("Xaridingiz uchun rahmat!\n")
        printer.text("Sizni yana kutamiz.\n\n")

        printer.cut()
        logger.info(f"Printed receipt for order {data['order_number']}")

    except Exception as e:
        logger.error(f"Print failed: {e}")


# ── WebSocket client ───────────────────────────────────────────

async def run_agent(ws_url: str, token: str, printer_id: str, printer_path: str = None):
    """Connect to server WebSocket, listen for print jobs, print them."""
    import websockets

    printer = get_printer(printer_path)
    if not printer:
        logger.error(
            "No printer detected!\n"
            "  - Make sure a USB thermal printer is connected\n"
            "  - On Windows, install the WinUSB driver via Zadig\n"
            "  - Or specify a printer path in config.json"
        )
        print("\nPress Enter to exit...")
        input()
        sys.exit(1)

    # Build full URL with auth
    sep = "&" if "?" in ws_url else "?"
    full_url = f"{ws_url}{sep}token={token}&printer_id={printer_id}"

    reconnect_delay = 2

    while True:
        try:
            logger.info(f"Connecting to server...")
            async with websockets.connect(full_url, ping_interval=30, ping_timeout=10) as ws:
                logger.info("Connected! Waiting for print jobs...")
                reconnect_delay = 2

                async for message in ws:
                    try:
                        data = json.loads(message)
                        order_num = data.get("order_number", "?")
                        logger.info(f"Received print job: order #{order_num}")
                        print_receipt(printer, data)

                        await ws.send(json.dumps({
                            "status": "printed",
                            "order_number": order_num,
                        }))
                    except Exception as e:
                        logger.error(f"Error processing print job: {e}")

        except Exception as e:
            logger.warning(f"Connection lost: {e}")
            logger.info(f"Reconnecting in {reconnect_delay}s...")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--url", default=None, help="WebSocket server URL (overrides config/default)")
    parser.add_argument("--token", default=None, help="Printer secret token (overrides config/default)")
    parser.add_argument("--printer", default=None, help="Printer path (e.g. /dev/usb/lp0 or 04b8:0202)")
    parser.add_argument("--printer-id", default=None, help="Unique ID for this printer")
    parser.add_argument("--list-printers", action="store_true", help="List detected printers and exit")
    args = parser.parse_args()

    print(f"\n{'=' * 40}")
    print(f"  {APP_NAME} v{APP_VERSION}")
    print(f"  OS: {platform.system()} {platform.release()}")
    print(f"{'=' * 40}\n")

    if args.list_printers:
        printers = detect_printers()
        if not printers:
            print("No printers detected.")
        else:
            print(f"Detected {len(printers)} printer(s):")
            for i, p in enumerate(printers):
                detail = p.get("path") or f"{p.get('vendor_id', '?'):04x}:{p.get('product_id', '?'):04x}"
                print(f"  [{i}] {p['name']}  ({detail})")
        sys.exit(0)

    # Load config: CLI args > config.json > baked-in defaults
    config = load_config()

    url = args.url or config["server"]
    token = args.token or config["token"]
    printer_id = args.printer_id or config["printer_id"]
    printer_path = args.printer or config["printer"]

    logger.info(f"Server: {url}")
    logger.info(f"Printer ID: {printer_id}")

    asyncio.run(run_agent(url, token, printer_id, printer_path))


if __name__ == "__main__":
    main()
