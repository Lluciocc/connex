from pathlib import Path
from datetime import datetime
import platform
import argparse

from assets.utils.config import Configuration
# Configuration
CONFIG_DIR = Path.home() / ".config" / "connex"
HISTORY_FILE = CONFIG_DIR / "history.log"
config = Configuration().get_config()
parser = argparse.ArgumentParser()
parser.add_argument("--debug", action="store_true", help="Enable debug mode")
DEBUG_MODE = (config.getboolean('GENERAL', 'debug', fallback=False) if config else False) or parser.parse_args().debug


def log_debug(msg):    
    if DEBUG_MODE:
        print(f"[DEBUG] {msg}")

def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def log_connection(ssid, signal, success, error_msg=""):
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

def get_os() -> bool:
    if platform.system() in ("Windows", "Darwin"):
        return False
    elif platform.system() == "Linux":
        return True
    else:
        return False

def get_distro()-> str:
    if get_os():
        info = platform.release()
        return info