from escpos.printer import File
from pprint import pformat
from PIL import Image
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(BASE_DIR, "..", "base_images", "phrolova.jpg")

printer = File("/dev/usb/lp0")

def printTextOnCall(text):
    formatted = pformat(text)
    printImage(image_path)
    printer.text(formatted + "\n")
    printer.cut()



def printImage(path):
    img = Image.open(path)
    img = img.convert("L")
    img = img.point(lambda x: 0 if x < 128 else 255, '1')

    width = 576
    ratio = width / img.width
    height = int(img.height * ratio)
    img = img.resize((width, height))

    printer.set(align='center')
    printer.image(img)


printTextOnCall(".")
