# Bazar Market Print Agent

Runs on the shop PC (Windows/Linux). Connects to the server via WebSocket, receives print jobs, prints receipts on the local USB thermal printer.

## Setup

```bash
pip install -r requirements.txt
```

On Windows, you may also need [Zadig](https://zadig.akeo.ie/) to install the WinUSB driver for your printer.

## Usage

```bash
# List detected printers
python agent.py --list-printers

# Start the agent (auto-detect printer)
python agent.py --url "wss://your-server.com/ws/printer/?token=YOUR_PRINTER_SECRET"

# Specify a printer
python agent.py --url "wss://your-server.com/ws/printer/?token=SECRET" --printer /dev/usb/lp0

# Windows USB (vendor:product hex IDs from --list-printers)
python agent.py --url "wss://your-server.com/ws/printer/?token=SECRET" --printer 04b8:0202

# Multi-printer setup
python agent.py --url "wss://..." --printer /dev/usb/lp0 --printer-id kitchen
python agent.py --url "wss://..." --printer /dev/usb/lp1 --printer-id counter
```

## Environment

Set `PRINTER_SECRET` on the server (.env) to match the `token` in the URL.

The agent auto-reconnects if the connection drops.
