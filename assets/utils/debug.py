from pathlib import Path
from datetime import datetime

# Configuration
CONFIG_DIR = Path.home() / ".config" / "connex"
HISTORY_FILE = CONFIG_DIR / "history.log"
DEBUG_MODE = False

def log_debug(msg):
    """Log debug messages"""
    if DEBUG_MODE:
        print(f"[DEBUG] {msg}")

def ensure_config_dir():
    """Create config directory if it doesn't exist"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def log_connection(ssid, signal, success, error_msg=""):
    """Log connection attempt to history"""
    ensure_config_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "SUCCESS" if success else "FAILED"
    log_entry = f"{timestamp} | {status} | {ssid} | Signal: {signal}%"
    if error_msg:
        log_entry += f" | Error: {error_msg}"
    log_entry += "\n"
    
    with open(HISTORY_FILE, "a") as f:
        f.write(log_entry)
    log_debug(f"Logged: {log_entry.strip()}")