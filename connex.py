#!/usr/bin/env python3
"""
connex - Wi-Fi Manager for Linux
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

gi.require_version("Gtk", "3.0")
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Notify', '0.7')
from gi.repository import Gtk, GObject, GLib, Gdk, Notify, AppIndicator3


# IMPORT

from assets.core.speedtest import SpeedTest
from assets.ui.main_window import WifiWindow
from assets.tray.system_tray import SystemTrayApp 
from assets.utils.debug import ensure_config_dir, get_os


def cli_mode(args):
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
        
        from assets.core.speedtest import cli_speedtest
        return cli_speedtest()


    return 0


def run_cmd_sync(cmd):
    try:
        res = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=10)
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def main():
    if not get_os():
        print("THIS PROGRAM IS NOT MADE FOR YOUR OS")
        return
    
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
    # proxies
    parser.add_argument("--proxy", dest="proxy_action",
     choices=["status", "set", "disable", "test"],
     help="Proxy configuration"
    )
    parser.add_argument("--proxy-type", help="Proxy type (http, https, socks5)")
    parser.add_argument("--proxy-host", help="Proxy host")
    parser.add_argument("--proxy-port", help="Proxy port")

    args = parser.parse_args()
    
    DEBUG_MODE_ARGS = args.debug
    
    ensure_config_dir()
    
    # CLI mode
    if args.cli_action:
        return cli_mode(args)
    
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

    # proxies
    if args.proxy_action:
        from assets.core.proxies import ProxyManager
        pm = ProxyManager()
        
        if args.proxy_action == "status":
            print(pm.get_status_text())
            config = pm.get_current_proxy()
            if config.get('enabled'):
                print(f"Type: {config.get('type')}")
                print(f"Host: {config.get('host')}")
                print(f"Port: {config.get('port')}")
        
        elif args.proxy_action == "set":
            if not args.proxy_type or not args.proxy_host or not args.proxy_port:
                print("Error: --proxy-type, --proxy-host, and --proxy-port required")
                return 1
            
            success, msg = pm.set_proxy(
                args.proxy_type, 
                args.proxy_host, 
                args.proxy_port
            )
            print(msg)
            return 0 if success else 1
        
        elif args.proxy_action == "disable":
            success, msg = pm.disable_proxy()
            print(msg)
            return 0 if success else 1
        
        elif args.proxy_action == "test":
            if not args.proxy_host or not args.proxy_port:
                print("Error: --proxy-host and --proxy-port required")
                return 1
            
            success, msg = pm.test_proxy(args.proxy_host, args.proxy_port)
            print(msg)
            return 0 if success else 1
    
    if args.tray or args.tray_only:
        tray = SystemTrayApp()
        if not args.tray_only:
            tray.show_window()
        Notify.init("connex")
        if not args.tray_only:
            Notify.Notification.new("connex", "Running in tray mode", "network-wireless").show()
        Gtk.main()
    else:
        win = WifiWindow(no_scan=args.no_scan)
        win.connect("destroy", Gtk.main_quit)
        Gtk.main()
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Interrupted by user. Exiting...")
    except Exception as e:
        print(f"[Connex] Unexpected error: {e}")
