# Bazar Market Print Agent

Runs on the shop PC (Windows/Linux). Connects to the server, receives print jobs, and prints receipts on the local USB thermal printer.

There are two ways to run it:

- **Desktop app (`gui.py`)** — a real window with buttons. This is what shop staff use. Pick a printer, press **Connect**, done. *(This is what the `.exe` build ships.)*
- **Headless agent (`agent.py`)** — the same engine with no window, for unattended/auto-start setups and advanced CLI options.

Both print identical receipts (the GUI reuses `agent.py`'s logic).

## Desktop App (recommended)

Download and double-click `BazarMarketPrinter.exe`. The window has everything:

| Control | What it does |
|---|---|
| **Status banner** | Live colored indicator: grey = disconnected, orange = connecting, green = connected and ready. |
| **Printer dropdown + Refresh** | Choose which printer to use, or leave it on *Auto-detect*. Press **Refresh** after plugging one in. |
| **Connect / Disconnect** | Starts (or stops) listening for orders from the server and printing them. |
| **Test Connection** | One-click check that the server is reachable and the token is accepted — without starting to print. |
| **Test Print** | Prints a sample receipt on the selected printer so you can confirm it works. |
| **Save Settings** | Remembers your server, token, printer, and auto-connect choice in `config.json`. |
| **Connect automatically** | When ticked, the app connects on its own every time it opens. |
| **Activity log** | Plain-language messages so you can see what's happening at a glance. |

The server URL and token come pre-filled with sensible defaults, so most shops just press **Connect**.

### Run from source

```bash
pip install -r requirements.txt
python gui.py
```

## Build the EXE

The build now produces the **windowed desktop app** (no terminal window).

On Windows:
```
build.bat
```

On Linux (native binary):
```
./build.sh
```

On Linux, cross-compiling a Windows `.exe` via Wine:
```
./build_windows.sh
```

Output: `dist/BazarMarketPrinter.exe` (or `dist/BazarMarketPrinter` on Linux).

> Builds use `gui.spec`. To build the old console-only agent instead, run `pyinstaller agent.spec`.

## Headless agent (advanced)

For machines that should just start printing on boot with no UI:

```bash
python agent.py
```

### CLI Options

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

## config.json

Both the app and the agent read `config.json` from next to the exe/script. The app writes it for you via **Save Settings**; you can also edit it by hand:

```json
{
  "server": "wss://api.bazarmarket.org/ws/printer/",
  "token": "your-printer-secret",
  "printer_id": "kitchen",
  "printer": "04b8:0202",
  "auto_connect": true
}
```

## Windows Notes

- If your USB printer doesn't appear in the dropdown, install its Windows driver (it then shows up as a `Windows:` printer), or install the WinUSB driver with [Zadig](https://zadig.akeo.ie/) so it shows up as a `USB:` device. Press **Refresh** afterwards.
- The app auto-reconnects if the server connection drops.
