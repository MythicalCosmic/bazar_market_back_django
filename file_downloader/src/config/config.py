from dotenv import load_dotenv
from pathlib import Path
import os


load_dotenv(override=True)


API_TOKEN = os.getenv("API_TOKEN", None)

# Project root = two levels up from this file (src/config/config.py -> project root)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Where uploaded file blobs live. Override with STORAGE_DIR in .env if you want.
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", PROJECT_ROOT / "data" / "files"))
TMP_DIR = STORAGE_DIR / "tmp"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)
