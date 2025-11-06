#!/usr/bin/env python3
"""
connex - Modern Wi-Fi Manager for Hyprland/ArchLinux
Enhanced version with advanced features
Dependencies: python-gobject gtk3 networkmanager libappindicator-gtk3
"""
import gi
import subprocess
import shlex
import threading
import argparse
import sys
import os
sys.path.append('/usr/lib/connex')

import json
from datetime import datetime
from pathlib import Path

# Importing classes from files 
from src.HiddenNetworkDialog import HiddenNetworkDialog
from src.SpeedTestDialog import SpeedTestDialog
from src.PasswordDialog import PasswordDialog
from src.LogViewerDialog import LogViewerDialog
from src.WifiWindow import WifiWindow
from src.SystemTrayApp import SystemTrayApp

gi.require_version("Gtk", "3.0")
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Notify', '0.7')
from gi.repository import Gtk, GObject, GLib, Gdk, Notify, AppIndicator3



# Configuration
CONFIG_DIR = Path.home() / ".config" / "connex"
HISTORY_FILE = CONFIG_DIR / "history.log"
DEBUG_MODE = False

def log_debug(msg):
    """Log debug messages"""
    if DEBUG_MODE:
        print(f"[DEBUG] {msg}")

try:
    from speedtest import SpeedTest 
    SPEEDTEST_AVAILABLE = True
except ImportError:
    SPEEDTEST_AVAILABLE = False 
    log_debug("Custom speedtest module not available")

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

def cli_mode(args):
    """CLI mode for scripting"""
    if args.cli_action == "list":
        code, out, err = run_cmd_sync("nmcli -t -f SSID,SIGNAL,SECURITY device wifi list")
        if code == 0:
            print("SSID\t\tSignal\tSecurity")
            print("-" * 50)
            for line in out.splitlines():
                if line.strip():
                    parts = line.split(':')
                    ssid = parts[0] if parts[0] else "<Hidden>"
                    signal = parts[1] if len(parts) > 1 else "?"
                    sec = parts[2] if len(parts) > 2 else "Open"
                    print(f"{ssid}\t{signal}%\t{sec}")
        return 0
    
    elif args.cli_action == "connect":
        if not args.ssid:
            print("Error: SSID required for connect")
            return 1
        
        cmd_args = ["nmcli", "device", "wifi", "connect", args.ssid]
        if args.password:
            cmd_args += ["password", args.password]
        
        try:
            result = subprocess.run(cmd_args, capture_output=True, text=True, timeout=20)
            if result.returncode == 0:
                print(f"✓ Connected to {args.ssid}")
                return 0
            else:
                print(f"✗ Failed: {result.stderr}")
                return 1
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    elif args.cli_action == "disconnect":
        if not args.ssid:
            print("Error: SSID required for disconnect")
            return 1
        
        code, out, err = run_cmd_sync(f"nmcli connection down '{args.ssid}'")
        if code == 0:
            print(f"✓ Disconnected from {args.ssid}")
            return 0
        else:
            print(f"✗ Failed: {err}")
            return 1
    
    elif args.cli_action == "status":
        code, out, err = run_cmd_sync("nmcli -t -f GENERAL,IP4 device show")
        if code == 0:
            print("Network Status:")
            print("-" * 50)
            for line in out.splitlines()[:15]:
                if any(x in line for x in ["CONNECTION", "STATE", "IP4.ADDRESS", "IP4.GATEWAY"]):
                    print(line.replace(":", ": "))
        return 0

    elif args.cli_action == "speedtest":
        if not SPEEDTEST_AVAILABLE:
            print("Error: speedtest module not available")
            print("Make sure speedtest.py is in the same directory")
            return 1
        
        from speedtest import cli_speedtest
        return cli_speedtest()


    return 0


def run_cmd_sync(cmd):
    """Synchronous command execution for CLI"""
    try:
        res = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=10)
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def main():
    global DEBUG_MODE
    
    parser = argparse.ArgumentParser(description="connex - Modern Wi-Fi Manager")
    # Connex args
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-scan", action="store_true", help="Disable auto scanning")
    # tray args
    parser.add_argument("--tray", action="store_true", help="Start in system tray and window")
    parser.add_argument("--tray-only",action="store_true", help="Start only the tray")

    #CLI only
    parser.add_argument("--cli", dest="cli_action",
     choices=["list", "connect", "disconnect", "status", "speedtest"],
     help="CLI mode"
    )
    parser.add_argument("--ssid", help="SSID for CLI connect/disconnect")
    parser.add_argument("--password", help="Password for CLI connect")

    args = parser.parse_args()
    
    DEBUG_MODE = args.debug
    
    ensure_config_dir()
    
    # CLI mode
    if args.cli_action:
        return cli_mode(args)
    
    # Set up CSS for better styling
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(b"""
        .info-bar {
            border-radius: 0;
        }
        window {
            background-color: #1e1e2e;
        }
        headerbar {
            background: linear-gradient(to bottom, #2e3440, #242831);
            color: #eceff4;
        }
        treeview {
            background-color: #2e3440;
            color: #eceff4;
        }
        treeview:selected {
            background-color: #5e81ac;
        }
    """)
    
    screen = Gdk.Screen.get_default()
    style_context = Gtk.StyleContext()
    style_context.add_provider_for_screen(
        screen, css_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    
    # Tray mode
    if args.tray or args.tray_only:
        tray = SystemTrayApp()
        if not args.tray_only:
            tray.show_window()
        Notify.init("connex")
        if not args.tray_only:
            Notify.Notification.new("connex", "Running in tray mode", "network-wireless").show()
        Gtk.main()
    else:
        # Normal window mode
        win = WifiWindow(no_scan=args.no_scan)
        win.connect("destroy", Gtk.main_quit)
        Gtk.main()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
