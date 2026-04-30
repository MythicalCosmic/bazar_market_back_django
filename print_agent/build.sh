#!/bin/bash
echo "========================================"
echo "  Building Bazar Market Print Agent"
echo "========================================"
echo

pip install pyinstaller websockets python-escpos pyusb pillow
echo

pyinstaller agent.spec --clean
echo

if [ -f "dist/BazarMarketPrinter" ]; then
    echo "========================================"
    echo "  Build successful!"
    echo "  Output: dist/BazarMarketPrinter"
    echo "========================================"
else
    echo "Build failed. Check errors above."
fi
