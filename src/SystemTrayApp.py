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

from .WifiWindow import WifiWindow

gi.require_version("Gtk", "3.0")
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Notify', '0.7')
from gi.repository import Gtk, GObject, GLib, Gdk, Notify, AppIndicator3



# Configuration
CONFIG_DIR = Path.home() / ".config" / "connex"
HISTORY_FILE = CONFIG_DIR / "history.log"
DEBUG_MODE = False

class SystemTrayApp:
    """System tray integration"""
    def __init__(self):
        self.window = None
        self.indicator = AppIndicator3.Indicator.new(
            "connex",
            "network-wireless-symbolic",
            AppIndicator3.IndicatorCategory.SYSTEM_SERVICES
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_title("connex")
        self.indicator.set_icon_full("network-wireless-symbolic", "")
        
        self.current_networks = []
        self.current_ssid = None
        
        # Create and set initial menu
        self.update_menu()
        
        # Update menu and icon periodically
        GLib.timeout_add_seconds(5, self.update_icon)
        GLib.timeout_add_seconds(10, self.update_menu_networks)
    
    def get_connection_status(self):
        """Get current connection status"""
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"],
                capture_output=True, text=True, timeout=2
            )
            for line in result.stdout.splitlines():
                parts = line.split(':')
                if len(parts) >= 2 and parts[1] == "802-11-wireless":
                    return parts[0], True
            return None, False
        except:
            return None, False
    
    def get_available_networks(self):
        """Get list of available networks"""
        try:
            # Trigger scan
            subprocess.run(
                ["nmcli", "device", "wifi", "rescan"],
                capture_output=True, timeout=3
            )
            
            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,IN-USE", "device", "wifi", "list"],
                capture_output=True, text=True, timeout=3
            )
            
            networks = []
            seen = set()
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                parts = line.split(':')
                ssid = parts[0] if parts[0] else None
                
                if not ssid or ssid in seen:
                    continue
                seen.add(ssid)
                
                signal = int(parts[1]) if len(parts) > 1 and parts[1] else 0
                security = parts[2] if len(parts) > 2 else ""
                in_use = parts[3] if len(parts) > 3 else ""
                
                # Security type
                if not security or security == "--":
                    sec_type = "Open"
                elif "WPA3" in security:
                    sec_type = "WPA3"
                elif "WPA2" in security:
                    sec_type = "WPA2"
                else:
                    sec_type = "WPA"
                
                networks.append({
                    'ssid': ssid,
                    'signal': signal,
                    'security': sec_type,
                    'connected': in_use == '*'
                })
            
            # Sort by signal strength
            networks.sort(key=lambda x: x['signal'], reverse=True)
            return networks[:15]  # Top 15 networks
        except:
            return []
    
    def update_menu(self):
        menu = Gtk.Menu()
        self.current_ssid, connected = self.get_connection_status()

        if connected and self.current_ssid:
            status_item = Gtk.MenuItem(label=f"✓ Connected to {self.current_ssid}")
            status_item.set_sensitive(False)
            menu.append(status_item)

            disconnect_item = Gtk.MenuItem(label=f"Disconnect from {self.current_ssid}")
            disconnect_item.connect("activate", self.disconnect_current)
            menu.append(disconnect_item)
        else:
            status_item = Gtk.MenuItem(label="○ No connection")
            status_item.set_sensitive(False)
            menu.append(status_item)
        
        menu.append(Gtk.SeparatorMenuItem())

        connect_item = Gtk.MenuItem(label="Connect to Wi-Fi ▸")
        submenu = Gtk.Menu()

        self.current_networks = self.get_available_networks()

        if self.current_networks:
            for net in self.current_networks:
                signal = net['signal']
                if signal >= 75:
                    icon = "●●●"
                elif signal >= 50:
                    icon = "●●○"
                elif signal >= 25:
                    icon = "●○○"
                else:
                    icon = "○○○"
                
                net_item = Gtk.MenuItem(label=f"{icon} {net['ssid']} ({net['security']})")
                if net['connected']:
                    net_item.set_sensitive(False)
                    net_item.set_label(f"✓ {net['ssid']} ({net['security']})")
                else:
                    net_item.connect("activate", self.connect_to_network, net['ssid'], net['security'])
                submenu.append(net_item)
        else:
            none_item = Gtk.MenuItem(label="No networks found")
            none_item.set_sensitive(False)
            submenu.append(none_item)

        submenu.append(Gtk.SeparatorMenuItem())
        hidden_item = Gtk.MenuItem(label="Connect to Hidden Network...")
        hidden_item.connect("activate", self.connect_hidden)
        submenu.append(hidden_item)

        submenu.show_all()
        connect_item.set_submenu(submenu)
        menu.append(connect_item)

        menu.append(Gtk.SeparatorMenuItem())

        info_item = Gtk.MenuItem(label="Connection Information")
        info_item.connect("activate", self.show_connection_info)
        info_item.set_sensitive(connected)
        menu.append(info_item)

        settings_item = Gtk.MenuItem(label="Open Connex Window")
        settings_item.connect("activate", self.show_window)
        menu.append(settings_item)

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self.quit)
        menu.append(quit_item)

        menu.show_all()
        self.indicator.set_menu(menu)
        return True

    
    def update_menu_networks(self):
        """Update menu with fresh network list"""
        self.update_menu()
        return True
    
    def connect_to_network(self, widget, ssid, security):
        """Connect to selected network from tray"""
        if ssid == self.current_ssid:
            return
        
        if security == "Open":
            # Connect directly
            threading.Thread(
                target=self._connect_thread, 
                args=(ssid, None),
                daemon=True
            ).start()
        else:
            # Show password dialog
            self.show_password_dialog(ssid, security)
    
    def show_password_dialog(self, ssid, security):
        """Show modern password dialog"""
        dialog = PasswordDialog(None, ssid, security)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            password = dialog.get_password()
            dialog.destroy()
            if password:
                threading.Thread(
                    target=self._connect_thread,
                    args=(ssid, password),
                    daemon=True
                ).start()
        else:
            dialog.destroy()

    
    def _connect_thread(self, ssid, password):
        """Connect in background thread"""
        # Forget network first
        subprocess.run(
            ["nmcli", "connection", "delete", ssid],
            capture_output=True
        )
        
        args = ["nmcli", "device", "wifi", "connect", ssid]
        if password:
            args += ["password", password]
        
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=20)
            
            if result.returncode == 0:
                GLib.idle_add(self.show_notification, 
                             "Connected", 
                             f"Successfully connected to {ssid}",
                             "network-wireless")
                GLib.idle_add(self.update_menu)
            else:
                error = "Incorrect password" if "Secrets" in result.stderr else "Connection failed"
                GLib.idle_add(self.show_notification,
                             "Connection Failed",
                             f"Could not connect to {ssid}: {error}",
                             "network-wireless-offline")
        except:
            GLib.idle_add(self.show_notification,
                         "Connection Failed",
                         f"Timeout connecting to {ssid}",
                         "network-wireless-offline")
    
    def disconnect_current(self, widget):
        """Disconnect from current network"""
        if self.current_ssid:
            try:
                subprocess.run(
                    ["nmcli", "connection", "down", self.current_ssid],
                    capture_output=True, timeout=5
                )
                self.show_notification(
                    "Disconnected",
                    f"Disconnected from {self.current_ssid}",
                    "network-wireless-offline"
                )
                GLib.timeout_add(1000, self.update_menu)
            except:
                pass
    
    def connect_hidden(self, widget):
        """Connect to hidden network"""
        dialog = Gtk.Dialog(
            title="Connect to Hidden Network",
            flags=Gtk.DialogFlags.MODAL
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Connect", Gtk.ResponseType.OK)
        dialog.set_default_size(350, 200)
        
        box = dialog.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        
        # SSID
        ssid_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        ssid_label = Gtk.Label(label="SSID:")
        ssid_label.set_width_chars(10)
        ssid_box.pack_start(ssid_label, False, False, 0)
        
        ssid_entry = Gtk.Entry()
        ssid_entry.set_placeholder_text("Network name")
        ssid_box.pack_start(ssid_entry, True, True, 0)
        box.pack_start(ssid_box, False, False, 0)
        
        # Password
        pwd_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pwd_label = Gtk.Label(label="Password:")
        pwd_label.set_width_chars(10)
        pwd_box.pack_start(pwd_label, False, False, 0)
        
        password_entry = Gtk.Entry()
        password_entry.set_visibility(False)
        password_entry.set_placeholder_text("Leave empty for open network")
        pwd_box.pack_start(password_entry, True, True, 0)
        box.pack_start(pwd_box, False, False, 0)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            ssid = ssid_entry.get_text()
            password = password_entry.get_text()
            dialog.destroy()
            
            if ssid:
                def connect_hidden_thread():
                    args = ["nmcli", "device", "wifi", "connect", ssid, "hidden", "yes"]
                    if password:
                        args += ["password", password]
                    
                    try:
                        result = subprocess.run(args, capture_output=True, timeout=20)
                        if result.returncode == 0:
                            GLib.idle_add(self.show_notification,
                                        "Connected",
                                        f"Connected to {ssid}",
                                        "network-wireless")
                            GLib.idle_add(self.update_menu)
                        else:
                            GLib.idle_add(self.show_notification,
                                        "Failed",
                                        "Could not connect to hidden network",
                                        "network-wireless-offline")
                    except:
                        pass
                
                threading.Thread(target=connect_hidden_thread, daemon=True).start()
        else:
            dialog.destroy()
    
    def show_connection_info(self, widget):
        """Show connection information"""
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "GENERAL,IP4", "device", "show"],
                capture_output=True, text=True, timeout=3
            )
            
            dialog = Gtk.MessageDialog(
                flags=Gtk.DialogFlags.MODAL,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Network Information"
            )
            
            info_lines = []
            for line in result.stdout.splitlines()[:20]:
                if any(x in line for x in ["IP4.ADDRESS", "IP4.GATEWAY", "IP4.DNS",
                                           "GENERAL.CONNECTION", "GENERAL.STATE"]):
                    key, val = line.split(":", 1)
                    key = key.replace("GENERAL.", "").replace("IP4.", "")
                    info_lines.append(f"{key}: {val}")
            
            dialog.format_secondary_text("\n".join(info_lines) if info_lines else "No info available")
            dialog.run()
            dialog.destroy()
        except:
            pass
    
    def show_notification(self, title, message, icon):
        """Show desktop notification"""
        try:
            notification = Notify.Notification.new(title, message, icon)
            notification.show()
        except:
            pass
        return False
    
    def show_window(self, *_):
        """Show main window"""
        if self.window is None or not self.window.get_visible():
            self.window = WifiWindow()
            self.window.connect("delete-event", self.on_window_delete)
            self.window.show_all()
        else:
            self.window.present()
    
    def on_window_delete(self, widget, event):
        """Hide window instead of destroying"""
        widget.hide()
        return True
    
    def update_icon(self):
        """Update tray icon based on connection status"""
        ssid, connected = self.get_connection_status()
        
        if connected:
            # Get signal strength of connected network
            try:
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "IN-USE,SIGNAL", "device", "wifi", "list"],
                    capture_output=True, text=True, timeout=2
                )
                signal = 0
                for line in result.stdout.splitlines():
                    if line.startswith('*'):
                        signal = int(line.split(':')[1]) if ':' in line else 0
                        break
                
                if signal >= 75:
                    self.indicator.set_icon_full("network-wireless-signal-excellent-symbolic", "")
                elif signal >= 50:
                    self.indicator.set_icon_full("network-wireless-signal-good-symbolic", "")
                elif signal >= 25:
                    self.indicator.set_icon_full("network-wireless-signal-ok-symbolic","")
                else:
                    self.indicator.set_icon_full("network-wireless-signal-weak-symbolic","")
            except:
                self.indicator.set_icon_full("network-wireless-symbolic","")
        else:
            self.indicator.set_icon_full("network-wireless-offline-symbolic","")
        
        return True
    
    def quit(self, *_):
        """Quit application"""
        if self.window:
            self.window.auto_refresh = False
        Gtk.main_quit()
