#!/bin/bash
# Build a Windows .exe from Linux using Wine + PyInstaller.
# One-time setup downloads Windows Python into a local Wine prefix; subsequent
# runs reuse it. Output: dist/BazarMarketPrinter.exe (single-file, all deps baked in).

set -e

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

export WINEPREFIX="$HERE/.wine-build"
export WINEARCH=win64
export WINEDEBUG=-all
export DISPLAY="${DISPLAY:-}"

PYTHON_VERSION=3.12.7
PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-amd64.exe"
PYTHON_INSTALLER="$HERE/.cache/python-${PYTHON_VERSION}-amd64.exe"
WINE_PYTHON="$WINEPREFIX/drive_c/Python312/python.exe"

mkdir -p "$HERE/.cache"

echo "=========================================="
echo "  Bazar Market Print Agent - Windows build"
echo "=========================================="

# 1) Bootstrap wine prefix
if [ ! -d "$WINEPREFIX" ]; then
    echo "[1/5] Initializing Wine prefix at $WINEPREFIX ..."
    wineboot --init 2>&1 | grep -vE "^(fixme|wine:|winemenubuilder)" || true
    # Wait for prefix to settle
    wineserver -w
fi

# 2) Download Windows Python installer
if [ ! -f "$PYTHON_INSTALLER" ]; then
    echo "[2/5] Downloading Python ${PYTHON_VERSION} for Windows ..."
    curl -L --fail -o "$PYTHON_INSTALLER" "$PYTHON_URL"
else
    echo "[2/5] Python installer already cached."
fi

# 3) Install Python in Wine
if [ ! -f "$WINE_PYTHON" ]; then
    echo "[3/5] Installing Python in Wine (silent, may take a minute) ..."
    wine "$PYTHON_INSTALLER" /quiet \
        InstallAllUsers=1 \
        TargetDir='C:\Python312' \
        PrependPath=1 \
        Include_test=0 \
        Include_doc=0 \
        Include_launcher=0 \
        Include_tcltk=0 \
        2>&1 | grep -vE "^(fixme|wine:|err:)" || true
    wineserver -w
    if [ ! -f "$WINE_PYTHON" ]; then
        echo "ERROR: Python install failed. $WINE_PYTHON not found."
        exit 1
    fi
else
    echo "[3/5] Python already installed in Wine."
fi

# 4) Install build deps inside Wine python
echo "[4/5] Installing Python dependencies ..."
wine "$WINE_PYTHON" -m pip install --upgrade pip wheel 2>&1 \
    | grep -vE "^(fixme|wine:|err:|0[0-9a-f]{3}:)" || true
wine "$WINE_PYTHON" -m pip install \
    pyinstaller \
    websockets \
    python-escpos \
    pyusb \
    pillow \
    pywin32 \
    customtkinter \
    2>&1 | grep -vE "^(fixme|wine:|err:|0[0-9a-f]{3}:)" || true

# 5) Build the exe
echo "[5/5] Running PyInstaller ..."
rm -rf "$HERE/build" "$HERE/dist"
wine "$WINE_PYTHON" -m PyInstaller gui.spec --clean --noconfirm 2>&1 \
    | grep -vE "^(fixme|wine:|0[0-9a-f]{3}:)" || true

OUT="$HERE/dist/BazarMarketPrinter.exe"
if [ -f "$OUT" ]; then
    SIZE=$(du -h "$OUT" | cut -f1)
    echo ""
    echo "=========================================="
    echo "  Build successful!"
    echo "  Output: $OUT  ($SIZE)"
    echo "=========================================="
    echo ""
    echo "Share this single .exe with shop users. They just double-click it."
    echo "All defaults (server URL, token) are baked in via agent.py."
else
    echo ""
    echo "ERROR: Build failed — $OUT not found."
    exit 1
fi
