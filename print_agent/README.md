# Bazar Market Print Agent

Runs on the shop PC (Windows/Linux). Connects to the server via WebSocket, receives print jobs, prints receipts on the local USB thermal printer.

**Zero-config**: the server URL and token are baked in. Just run it.

## Quick Start (EXE)

1. Download `BazarMarketPrinter.exe`
2. Connect your USB thermal printer
3. Double-click the exe — it auto-detects the printer and connects

## Quick Start (Python)

```bash
pip install -r requirements.txt
python agent.py
```

## Build the EXE

On Windows:
```
build.bat
```

On Linux:
```
./build.sh
```

Output: `dist/BazarMarketPrinter.exe` (or `dist/BazarMarketPrinter` on Linux)

## Optional: config.json

Place a `config.json` next to the exe to override defaults:

```json
{
  "server": "wss://api.bazarmarket.org/ws/printer/",
  "token": "your-printer-secret",
  "printer_id": "kitchen",
  "printer": "04b8:0202"
}
```

## CLI Options

```bash
# List detected printers
python agent.py --list-printers

# Override server URL
python agent.py --url "wss://other-server.com/ws/printer/"

# Specify printer manually
python agent.py --printer /dev/usb/lp0          # Linux
python agent.py --printer 04b8:0202             # USB vendor:product

# Multi-printer setup
python agent.py --printer-id kitchen
python agent.py --printer-id counter
```

## Windows Notes

- Install [Zadig](https://zadig.akeo.ie/) if your printer isn't detected (WinUSB driver)
- The agent auto-reconnects if the server connection drops
