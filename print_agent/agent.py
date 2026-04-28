#!/usr/bin/env python3
"""
Bazar Market Print Agent
========================
Standalone script that runs on the shop machine.
Connects to the server via WebSocket, receives print jobs, prints receipts.

Usage:
    pip install websockets python-escpos pyusb pillow
    python agent.py --url wss://your-server.com/ws/printer/ --token YOUR_SECRET

Auto-detects printers on Windows and Linux.
Supports multiple printers via --printer-id flag.
"""

import argparse
import asyncio
import json
import logging
import platform
import sys
from datetime import datetime
from decimal import Decimal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("print_agent")

RECEIPT_WIDTH = 32


# ── Printer detection ──────────────────────────────────────────

def detect_printers() -> list[dict]:
    """Auto-detect connected USB/thermal printers. Returns list of {name, path}."""
    system = platform.system()
    printers = []

    if system == "Linux":
        printers.extend(_detect_linux())
    elif system == "Windows":
        printers.extend(_detect_windows())
    else:
        logger.warning(f"Unsupported OS: {system}")

    return printers


def _detect_linux() -> list[dict]:
    import os
    import glob

    found = []

    # USB printers at /dev/usb/lp*
    for path in sorted(glob.glob("/dev/usb/lp*")):
        found.append({"name": f"USB: {path}", "path": path, "type": "file"})

    # Serial printers
    for path in sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")):
        found.append({"name": f"Serial: {path}", "path": path, "type": "file"})

    return found


def _detect_windows() -> list[dict]:
    found = []

    # Try USB via pyusb
    try:
        import usb.core
        devices = usb.core.find(find_all=True)
        for dev in devices:
            # Common thermal printer vendor IDs
            # 0x0416 = Winbond (many POS printers)
            # 0x0483 = STMicroelectronics
            # 0x04b8 = Epson
            # 0x0519 = Star Micronics
            # 0x0dd4 = Custom
            # 0x0fe6 = ICS
            # 0x1504 = various Chinese POS
            # 0x1a86 = QinHeng (CH340 USB-serial, many POS printers)
            # 0x0525 = Netchip (Gadget/POS)
            printer_vendors = {0x04b8, 0x0519, 0x0416, 0x0dd4, 0x1504, 0x1a86, 0x0525, 0x0483, 0x0fe6}
            if dev.idVendor in printer_vendors:
                name = f"USB: {dev.idVendor:04x}:{dev.idProduct:04x}"
                try:
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
        logger.debug(f"USB detection failed: {e}")

    # Try Windows shared printers via win32print
    try:
        import win32print
        for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS):
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
        # Explicit path
        if ":" in printer_path and len(printer_path.split(":")) == 2:
            # USB vendor:product format
            parts = printer_path.split(":")
            vendor = int(parts[0], 16)
            product = int(parts[1], 16)
            return Usb(vendor, product)
        else:
            return File(printer_path)

    # Auto-detect
    printers = detect_printers()
    if not printers:
        logger.error("No printers detected!")
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
        # For Windows shared printers, use File with the printer path
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
    """Decode base64 logo and print it."""
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
        # Logo
        _print_logo(printer, data.get("logo", ""))
        printer.text("\n")

        # Header
        printer.set(align="center")
        printer.set(width=2, height=2)
        printer.text("BAZAR MARKET\n")
        printer.set(width=1, height=1)
        printer.text(_dsep() + "\n")

        # Order info
        printer.set(align="left")
        now = datetime.now()
        printer.text(_line("Buyurtma:", data["order_number"]) + "\n")
        printer.text(_line("Sana:", now.strftime("%d.%m.%Y  %H:%M")) + "\n")
        if data.get("payment_method"):
            printer.text(_line("To'lov:", data["payment_method"]) + "\n")
        printer.text(_sep() + "\n")

        # Customer
        printer.text(f"Mijoz:  {data['customer_name']}\n")
        if data.get("customer_phone"):
            printer.text(f"Tel:    {data['customer_phone']}\n")
        if data.get("address"):
            # Print full address — wrap long lines naturally
            addr = data["address"]
            printer.text(f"Manzil: {addr}\n")
        if data.get("user_note"):
            printer.text(f"Izoh:   {data['user_note']}\n")
        printer.text(_sep() + "\n")

        # Items
        printer.text(_center("MAHSULOTLAR") + "\n")
        printer.text(_sep() + "\n")

        for item in data.get("items", []):
            # Print full name — no truncation
            printer.text(f"{item['name']}\n")
            qty = item["qty"]
            detail = f"  {qty} {item['unit']} x {_fmt(item['unit_price'])}"
            printer.text(_line(detail, _fmt(item["total"])) + "\n")

        printer.text(_sep() + "\n")

        # Totals
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

        # Payment status
        printer.set(align="center")
        printer.text(f"[ {data.get('payment_status', '')} ]\n\n")

        # Order ID
        printer.set(align="center")
        printer.text(f"#{data['order_number']}\n\n")

        # Footer
        printer.text("Xaridingiz uchun rahmat!\n")
        printer.text("Sizni yana kutamiz.\n\n")

        printer.cut()
        logger.info(f"Printed receipt for order {data['order_number']}")

    except Exception as e:
        logger.error(f"Print failed: {e}")


# ── WebSocket client ───────────────────────────────────────────

async def run_agent(ws_url: str, printer_path: str = None):
    """Connect to server WebSocket, listen for print jobs, print them."""
    import websockets

    printer = get_printer(printer_path)
    if not printer:
        logger.error("Cannot start agent: no printer available")
        sys.exit(1)

    reconnect_delay = 2

    while True:
        try:
            logger.info(f"Connecting to {ws_url} ...")
            async with websockets.connect(ws_url, ping_interval=30, ping_timeout=10) as ws:
                logger.info("Connected! Waiting for print jobs...")
                reconnect_delay = 2

                async for message in ws:
                    try:
                        data = json.loads(message)
                        logger.info(f"Received print job: order {data.get('order_number', '?')}")
                        print_receipt(printer, data)

                        # Send ack
                        await ws.send(json.dumps({
                            "status": "printed",
                            "order_number": data.get("order_number"),
                        }))
                    except Exception as e:
                        logger.error(f"Error processing print job: {e}")

        except Exception as e:
            logger.warning(f"Connection lost: {e}. Reconnecting in {reconnect_delay}s...")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Bazar Market Print Agent")
    parser.add_argument("--url", default=None, help="WebSocket URL, e.g. wss://your-server.com/ws/printer/?token=SECRET")
    parser.add_argument("--printer", default=None, help="Printer path (e.g. /dev/usb/lp0 or 04b8:0202). Auto-detects if not set.")
    parser.add_argument("--printer-id", default="default", help="Unique ID for this printer (for multi-printer setups)")
    parser.add_argument("--list-printers", action="store_true", help="List detected printers and exit")
    args = parser.parse_args()

    if args.list_printers:
        printers = detect_printers()
        if not printers:
            print("No printers detected.")
        else:
            print(f"Detected {len(printers)} printer(s):")
            for i, p in enumerate(printers):
                print(f"  [{i}] {p['name']} ({p.get('path', p.get('vendor_id', '?'))})")
        sys.exit(0)

    if not args.url:
        parser.error("--url is required (unless using --list-printers)")

    # Append printer_id to URL query
    url = args.url
    sep = "&" if "?" in url else "?"
    url += f"{sep}printer_id={args.printer_id}"

    asyncio.run(run_agent(url, args.printer))


if __name__ == "__main__":
    main()
