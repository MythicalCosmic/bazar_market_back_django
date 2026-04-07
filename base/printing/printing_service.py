from escpos.printer import File
from PIL import Image
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(BASE_DIR, "..", "base_images", "image.png")

try:
    printer = File("/dev/usb/lp0")
except Exception as e:
    print('Printer not found')


def printImage(path):
    img = Image.open(path).convert("RGBA")
    
    # white_bg = Image.new("RGBA", img.size, "WHITE")
    
    # flattened_img = Image.alpha_composite(white_bg, img)
    
    # final_print = flattened_img.convert("L").point(lambda x: 0 if x < 128 else 255, '1')

    width = 576
    ratio = width / float(img.width)
    height = int(img.height * ratio)
    img = img.resize((width, height))

    printer.set(align='center')
    printer.image(img) 

def print_receipt(
    client_name: str,
    client_phone: str,
    client_address: str,
    ordered_items: list[str] | str,
    total: str,
    discount: str = "0",
    thanks_message: str = "Thank you for choosing our printing service!\nWe appreciate your business ❤️",
):
    printImage(image_path)

    printer.set(align='center')
    printer.set(width=2, height=2)
    printer.text("\n\nPRINTING SERVICE\n")
    printer.set(width=1, height=1)
    printer.text("================================\n\n")

    printer.set(align='left')
    printer.text("CLIENT INFORMATION\n")
    printer.text(f"Name     : {client_name}\n")
    printer.text(f"Phone    : {client_phone}\n")
    printer.text(f"Address  : {client_address}\n\n")

    printer.set(align='left')
    printer.text("WHAT YOU ORDERED:\n")

    if isinstance(ordered_items, list):
        for item in ordered_items:
            printer.text(f"  • {item}\n")
    else:
        printer.text(f"  {ordered_items}\n")

    printer.text("\n")

    printer.set(align='left')
    printer.text(f"Total      : {total}\n")
    printer.text(f"Discount   : -{discount}\n")
    printer.text("================================\n\n")

    printer.set(align='center')
    printer.text(thanks_message + "\n\n")

    printer.cut()


print_receipt(
    client_name="Cosmic",
    client_phone="+998 XX XXX XX XX",
    client_address="Tashkent, Uzbekistan",
    ordered_items=[
        "4x6 Photo Print x 2",
        "A4 Custom Poster x 1",
        "Business Cards (100 pcs)"
    ],
    total="450000 UZS",
    discount="45000 UZS",
    thanks_message="Thank you for your order!\nSee you again soon ❤️"
)