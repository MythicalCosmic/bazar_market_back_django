from __future__ import annotations

import os
import sys
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "..", "base_images", "image.png")

# ── Thermal receipt: 32 chars for 58 mm paper, 48 chars for 80 mm ──
RECEIPT_WIDTH = 32


# ---------------------------------------------------------------------------
# Printer abstraction — safe to import on machines without a thermal printer
# ---------------------------------------------------------------------------

def _get_printer():
    """Return an ESC/POS printer instance, or a console fallback."""
    printer_enabled = getattr(settings, "PRINTER_ENABLED", False)
    printer_path = getattr(settings, "PRINTER_PATH", "/dev/usb/lp0")

    if printer_enabled:
        try:
            from escpos.printer import File
            return File(printer_path)
        except Exception as exc:
            print(f"[printing] Could not open {printer_path}: {exc}", file=sys.stderr)

    return _ConsolePrinter()


class _ConsolePrinter:
    """Drop-in replacement that writes to stdout instead of a thermal printer.
    Useful for development / testing without hardware."""

    def set(self, **kwargs):
        pass

    def text(self, txt):
        print(txt, end="")

    def image(self, _img):
        print("[LOGO IMAGE]")

    def barcode(self, data, bc_type, **kwargs):
        print(f"[BARCODE: {data}]")

    def qr(self, data, **kwargs):
        print(f"[QR: {data}]")

    def cut(self):
        print("\n" + "=" * RECEIPT_WIDTH)
        print("[CUT]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(amount: Decimal | int | float | None) -> str:
    """Format a monetary amount: 1_350_000 -> '1,350,000'"""
    if amount is None:
        return "0"
    return f"{Decimal(amount):,.0f}"


def _line(left: str, right: str) -> str:
    """Left-right justified line within RECEIPT_WIDTH."""
    gap = RECEIPT_WIDTH - len(left) - len(right)
    if gap < 1:
        gap = 1
    return left + " " * gap + right


def _separator() -> str:
    return "─" * RECEIPT_WIDTH


def _double_separator() -> str:
    return "=" * RECEIPT_WIDTH


def _center(text: str) -> str:
    return text.center(RECEIPT_WIDTH)


# ---------------------------------------------------------------------------
# Logo
# ---------------------------------------------------------------------------

def _print_logo(printer):
    if not os.path.isfile(LOGO_PATH):
        return

    img = Image.open(LOGO_PATH).convert("RGBA")
    width = 576
    ratio = width / float(img.width)
    height = int(img.height * ratio)
    img = img.resize((width, height))

    printer.set(align="center")
    printer.image(img)


# ---------------------------------------------------------------------------
# Main receipt — takes an Order model instance
# ---------------------------------------------------------------------------

def print_order_receipt(order, *, store_name: str = "BAZAR MARKET"):
    """Print a receipt for the given Order.

    ``order`` must have its relations prefetched / available:
        order.user          — customer
        order.items.all()   — OrderItem queryset
    """
    printer = _get_printer()
    user = order.user
    items = order.items.all()

    # ── Logo ──
    _print_logo(printer)
    printer.text("\n")

    # ── Store header ──
    printer.set(align="center")
    printer.set(width=2, height=2)
    printer.text(f"{store_name}\n")
    printer.set(width=1, height=1)
    printer.text(_double_separator() + "\n")

    # ── Order info ──
    printer.set(align="left")
    now = datetime.now()
    printer.text(_line("Order:", order.order_number) + "\n")
    printer.text(_line("Date:", now.strftime("%d.%m.%Y  %H:%M")) + "\n")
    if order.payment_method:
        printer.text(_line("Payment:", order.get_payment_method_display()) + "\n")
    printer.text(_separator() + "\n")

    # ── Customer info ──
    full_name = f"{user.first_name} {user.last_name}".strip() or "—"
    printer.text(f"Client: {full_name}\n")
    if user.phone:
        printer.text(f"Phone:  {user.phone}\n")
    if order.delivery_address_text:
        printer.text(f"Addr:   {order.delivery_address_text}\n")
    printer.text(_separator() + "\n")

    # ── Items ──
    printer.text(_center("ITEMS") + "\n")
    printer.text(_separator() + "\n")

    for item in items:
        # Line 1: product name
        name = item.product_name
        if len(name) > RECEIPT_WIDTH:
            name = name[: RECEIPT_WIDTH - 1] + "…"
        printer.text(f"{name}\n")

        # Line 2: qty x price = total  (right-aligned)
        qty_str = f"{item.quantity:g}"
        detail = f"  {qty_str} {item.unit} x {_fmt(item.unit_price)}"
        subtotal = f"{_fmt(item.total)}"
        printer.text(_line(detail, subtotal) + "\n")

    printer.text(_separator() + "\n")

    # ── Totals ──
    printer.text(_line("Subtotal:", f"{_fmt(order.subtotal)} UZS") + "\n")

    if order.delivery_fee and order.delivery_fee > 0:
        printer.text(_line("Delivery:", f"{_fmt(order.delivery_fee)} UZS") + "\n")

    if order.discount and order.discount > 0:
        printer.text(_line("Discount:", f"-{_fmt(order.discount)} UZS") + "\n")

    printer.text(_double_separator() + "\n")
    printer.set(width=2, height=1)
    printer.text(_line("TOTAL:", f"{_fmt(order.total)} UZS") + "\n")
    printer.set(width=1, height=1)
    printer.text(_double_separator() + "\n")

    # ── Payment status ──
    printer.set(align="center")
    status_display = order.get_payment_status_display().upper()
    printer.text(f"[ {status_display} ]\n\n")

    # ── QR code with order number for lookup ──
    printer.qr(order.order_number, size=6)
    printer.text("\n")

    # ── Thank-you message ──
    printer.set(align="center")
    printer.text("Thank you for your order!\n")
    printer.text("We appreciate your business.\n\n")

    printer.cut()


# ---------------------------------------------------------------------------
# Lightweight receipt — for manual / quick use without an Order object
# ---------------------------------------------------------------------------

def print_receipt(
    client_name: str,
    client_phone: str,
    client_address: str,
    items: list[dict] | list[str],
    total: Decimal | str,
    discount: Decimal | str = 0,
    delivery_fee: Decimal | str = 0,
    payment_method: str = "",
    order_number: str = "",
    thanks_message: str = "Thank you for your order!\nWe appreciate your business.",
):
    """Standalone receipt that doesn't require a DB Order.

    ``items`` can be:
      - list of dicts: [{"name": "...", "qty": 2, "unit": "pcs", "price": 15000}]
      - list of plain strings (backwards-compatible)
    """
    printer = _get_printer()

    # ── Logo ──
    _print_logo(printer)
    printer.text("\n")

    # ── Header ──
    printer.set(align="center")
    printer.set(width=2, height=2)
    printer.text("BAZAR MARKET\n")
    printer.set(width=1, height=1)
    printer.text(_double_separator() + "\n")

    # ── Order info ──
    printer.set(align="left")
    now = datetime.now()
    if order_number:
        printer.text(_line("Order:", order_number) + "\n")
    printer.text(_line("Date:", now.strftime("%d.%m.%Y  %H:%M")) + "\n")
    if payment_method:
        printer.text(_line("Payment:", payment_method) + "\n")
    printer.text(_separator() + "\n")

    # ── Customer ──
    printer.text(f"Client: {client_name}\n")
    if client_phone:
        printer.text(f"Phone:  {client_phone}\n")
    if client_address:
        printer.text(f"Addr:   {client_address}\n")
    printer.text(_separator() + "\n")

    # ── Items ──
    printer.set(align="left")
    printer.text(_center("ITEMS") + "\n")
    printer.text(_separator() + "\n")

    subtotal = Decimal(0)
    for item in items:
        if isinstance(item, dict):
            name = item["name"]
            qty = item.get("qty", 1)
            unit = item.get("unit", "pcs")
            price = Decimal(item.get("price", 0))
            line_total = price * qty
            subtotal += line_total

            if len(name) > RECEIPT_WIDTH:
                name = name[: RECEIPT_WIDTH - 1] + "…"
            printer.text(f"{name}\n")
            qty_str = f"{qty:g}" if isinstance(qty, float) else str(qty)
            printer.text(_line(f"  {qty_str} {unit} x {_fmt(price)}", _fmt(line_total)) + "\n")
        else:
            printer.text(f"  * {item}\n")

    printer.text(_separator() + "\n")

    # ── Totals ──
    total_dec = Decimal(str(total)) if not isinstance(total, Decimal) else total
    discount_dec = Decimal(str(discount)) if not isinstance(discount, Decimal) else discount
    delivery_dec = Decimal(str(delivery_fee)) if not isinstance(delivery_fee, Decimal) else delivery_fee

    if subtotal > 0:
        printer.text(_line("Subtotal:", f"{_fmt(subtotal)} UZS") + "\n")

    if delivery_dec > 0:
        printer.text(_line("Delivery:", f"{_fmt(delivery_dec)} UZS") + "\n")

    if discount_dec > 0:
        printer.text(_line("Discount:", f"-{_fmt(discount_dec)} UZS") + "\n")

    printer.text(_double_separator() + "\n")
    printer.set(width=2, height=1)
    printer.text(_line("TOTAL:", f"{_fmt(total_dec)} UZS") + "\n")
    printer.set(width=1, height=1)
    printer.text(_double_separator() + "\n\n")

    # ── QR code ──
    if order_number:
        printer.set(align="center")
        printer.qr(order_number, size=6)
        printer.text("\n")

    # ── Thanks ──
    printer.set(align="center")
    printer.text(thanks_message + "\n\n")

    printer.cut()


# ---------------------------------------------------------------------------
# CLI test — only runs when executed directly: python printing_service.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print_receipt(
        client_name="Cosmic",
        client_phone="+998 XX XXX XX XX",
        client_address="Tashkent, Uzbekistan",
        items=[
            {"name": "4x6 Photo Print", "qty": 2, "unit": "pcs", "price": 75000},
            {"name": "A4 Custom Poster", "qty": 1, "unit": "pcs", "price": 80000},
            {"name": "Business Cards", "qty": 100, "unit": "pcs", "price": 2200},
        ],
        total="450000",
        discount="45000",
        order_number="ORD-20260420-0001",
        payment_method="Cash",
        thanks_message="Thank you for your order!\nSee you again soon!",
    )
