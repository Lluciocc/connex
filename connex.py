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


class HiddenNetworkDialog(Gtk.Dialog):
    """Dialog for connecting to hidden networks"""
    def __init__(self, parent):
        super().__init__(title="Connect to Hidden Network", parent=parent, modal=True)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Connect", Gtk.ResponseType.OK)
        self.set_default_size(400, 200)
        
        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        
        # Info label
        info = Gtk.Label()
        info.set_markup("<b>Enter hidden network details:</b>")
        info.set_xalign(0)
        box.pack_start(info, False, False, 0)
        
        # SSID entry
        ssid_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        ssid_label = Gtk.Label(label="SSID:")
        ssid_label.set_width_chars(10)
        ssid_box.pack_start(ssid_label, False, False, 0)
        
        self.ssid_entry = Gtk.Entry()
        self.ssid_entry.set_placeholder_text("Network name")
        ssid_box.pack_start(self.ssid_entry, True, True, 0)
        box.pack_start(ssid_box, False, False, 0)
        
        # Password entry
        pwd_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pwd_label = Gtk.Label(label="Password:")
        pwd_label.set_width_chars(10)
        pwd_box.pack_start(pwd_label, False, False, 0)
        
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        self.password_entry.set_placeholder_text("Leave empty for open network")
        pwd_box.pack_start(self.password_entry, True, True, 0)
        
        # Show password toggle
        self.show_pwd_btn = Gtk.ToggleButton()
        eye_icon = Gtk.Image.new_from_icon_name("view-reveal-symbolic", Gtk.IconSize.BUTTON)
        self.show_pwd_btn.set_image(eye_icon)
        self.show_pwd_btn.connect("toggled", self.on_show_password_toggled)
        pwd_box.pack_start(self.show_pwd_btn, False, False, 0)
        
        box.pack_start(pwd_box, False, False, 0)
        
        self.set_default_response(Gtk.ResponseType.OK)
        self.show_all()
    
    def on_show_password_toggled(self, button):
        self.password_entry.set_visibility(button.get_active())
    
    def get_ssid(self):
        return self.ssid_entry.get_text()
    
    def get_password(self):
        return self.password_entry.get_text()

class SpeedTestDialog(Gtk.Dialog):
    """Dialog for running speed test"""
    def __init__(self, parent):
        super().__init__(title="Speed Test", parent=parent, modal=True)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Close", Gtk.ResponseType.CLOSE)
        self.set_default_size(500, 350)
        
        self.test = None
        self.test_running = False
        
        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        
        # Title
        title = Gtk.Label()
        title.set_markup("<b>Testing connection speed...</b>")
        title.set_xalign(0)
        box.pack_start(title, False, False, 0)
        
        # Progress bar
        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        self.progress.set_text("Ready to start")
        box.pack_start(self.progress, False, False, 0)
        
        # Status label
        self.status_label = Gtk.Label(label="")
        self.status_label.set_xalign(0)
        self.status_label.set_line_wrap(True)
        box.pack_start(self.status_label, False, False, 0)
        
        # Results area
        results_frame = Gtk.Frame(label="Results")
        results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        results_box.set_margin_start(12)
        results_box.set_margin_end(12)
        results_box.set_margin_top(12)
        results_box.set_margin_bottom(12)
        
        self.server_label = Gtk.Label(label="Server: --")
        self.server_label.set_xalign(0)
        self.server_label.set_line_wrap(True)
        results_box.pack_start(self.server_label, False, False, 0)
        
        self.ping_label = Gtk.Label(label="Ping: --")
        self.ping_label.set_xalign(0)
        results_box.pack_start(self.ping_label, False, False, 0)
        
        self.download_label = Gtk.Label(label="Download: --")
        self.download_label.set_xalign(0)
        results_box.pack_start(self.download_label, False, False, 0)
        
        self.upload_label = Gtk.Label(label="Upload: --")
        self.upload_label.set_xalign(0)
        results_box.pack_start(self.upload_label, False, False, 0)
        
        results_frame.add(results_box)
        box.pack_start(results_frame, True, True, 0)
        
        self.connect("response", self.on_response)
        self.show_all()
        
        # Start test
        self.start_test()
    
    def on_response(self, dialog, response):
        """Handle dialog response"""
        if response == Gtk.ResponseType.CANCEL and self.test_running:
            if self.test:
                self.test.cancel()
                self.status_label.set_markup("<span color='orange'>⚠ Test cancelled</span>")
                self.test_running = False
    
    def start_test(self):
        """Start the speed test"""
        if not SPEEDTEST_AVAILABLE:
            self.show_error("Custom speedtest module not available")
            return
        
        self.test_running = True
        self.test = SpeedTest(callback=self.on_progress)
        self.test_thread = threading.Thread(target=self.run_test, daemon=True)
        self.test_thread.start()
    
    def run_test(self):
        """Run test in background thread"""
        try:
            results = self.test.run_full_test()
            GLib.idle_add(self.display_results, results)
        except Exception as e:
            GLib.idle_add(self.show_error, f"Test error: {str(e)}")
        finally:
            self.test_running = False
    
    def on_progress(self, stage, progress, message):
        """Progress callback from speedtest"""
        GLib.idle_add(self.update_progress, progress, message)
    
    def update_progress(self, fraction, text):
        """Update progress bar"""
        self.progress.set_fraction(fraction)
        self.progress.set_text(text)
        
        # Update status
        if fraction < 0.3:
            stage = "Testing latency..."
        elif fraction < 0.7:
            stage = "Testing download..."
        elif fraction < 1.0:
            stage = "Testing upload..."
        else:
            stage = "Complete!"
        
        self.status_label.set_text(stage)
        return False
    
    def display_results(self, results):
        """Display test results"""
        if results.get('error'):
            self.show_error(results['error'])
            return False
        
        server = results.get('server', 'N/A')
        ping = results.get('ping', 0)
        download = results.get('download', 0)
        upload = results.get('upload', 0)
        
        self.server_label.set_markup(f"<b>Server:</b> {server}")
        
        # Color code ping
        if ping < 50:
            ping_color = "green"
        elif ping < 100:
            ping_color = "orange"
        else:
            ping_color = "red"
        self.ping_label.set_markup(
            f"<b>Ping:</b> <span color='{ping_color}'>{ping:.1f} ms</span>"
        )
        
        # Color code download
        if download > 50:
            dl_color = "green"
        elif download > 10:
            dl_color = "orange"
        else:
            dl_color = "red"
        self.download_label.set_markup(
            f"<b>Download:</b> <span color='{dl_color}'>{download:.2f} Mbps</span>"
        )
        
        if upload > 0:
            if upload > 20:
                ul_color = "green"
            elif upload > 5:
                ul_color = "orange"
            else:
                ul_color = "red"
            self.upload_label.set_markup(
                f"<b>Upload:</b> <span color='{ul_color}'>{upload:.2f} Mbps</span>"
            )
        else:
            self.upload_label.set_text("Upload: Not tested")
        
        self.progress.set_fraction(1.0)
        self.progress.set_text("Test complete!")
        self.status_label.set_markup("<span color='green'>✓ Test completed successfully</span>")
        
        return False
    
    def show_error(self, message):
        """Show error message"""
        self.progress.set_fraction(0)
        self.progress.set_text("Failed")
        self.status_label.set_markup(f"<span color='red'>{message}</span>")
        return False

class PasswordDialog(Gtk.Dialog):
    """Modern password input dialog with secure revealer"""
    def __init__(self, parent, ssid, security):
        super().__init__(title=f"Connect to {ssid}", parent=parent, modal=True)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Connect", Gtk.ResponseType.OK)
        self.set_default_size(400, 150)
        
        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        
        # Network info
        info_label = Gtk.Label()
        info_label.set_markup(f"<b>Network:</b> {ssid}\n<b>Security:</b> {security}")
        info_label.set_xalign(0)
        box.pack_start(info_label, False, False, 0)
        
        # Password entry
        pwd_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pwd_label = Gtk.Label(label="Password:")
        pwd_label.set_width_chars(10)
        pwd_box.pack_start(pwd_label, False, False, 0)
        
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        self.password_entry.set_activates_default(True)
        pwd_box.pack_start(self.password_entry, True, True, 0)
        
        # Show password with revealer
        self.show_pwd_btn = Gtk.ToggleButton()
        eye_icon = Gtk.Image.new_from_icon_name("view-reveal-symbolic", Gtk.IconSize.BUTTON)
        self.show_pwd_btn.set_image(eye_icon)
        self.show_pwd_btn.set_tooltip_text("Show/Hide password")
        self.show_pwd_btn.connect("toggled", self.on_show_password_toggled)
        pwd_box.pack_start(self.show_pwd_btn, False, False, 0)
        
        box.pack_start(pwd_box, False, False, 0)
        
        # Revealer for password strength indicator
        self.revealer = Gtk.Revealer()
        self.revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        
        self.strength_label = Gtk.Label()
        self.strength_label.set_xalign(0)
        self.revealer.add(self.strength_label)
        box.pack_start(self.revealer, False, False, 0)
        
        self.password_entry.connect("changed", self.on_password_changed)
        
        self.set_default_response(Gtk.ResponseType.OK)
        self.show_all()
    
    def on_show_password_toggled(self, button):
        visible = button.get_active()
        self.password_entry.set_visibility(visible)
        if visible:
            self.revealer.set_reveal_child(True)
        else:
            self.revealer.set_reveal_child(False)
    
    def on_password_changed(self, entry):
        """Show password strength"""
        pwd = entry.get_text()
        if len(pwd) < 8:
            self.strength_label.set_markup("<span color='red'>⚠ Weak (min 8 chars)</span>")
        elif len(pwd) < 12:
            self.strength_label.set_markup("<span color='orange'>⚡ Medium</span>")
        else:
            self.strength_label.set_markup("<span color='green'>✓ Strong</span>")
    
    def get_password(self):
        return self.password_entry.get_text()


class LogViewerDialog(Gtk.Dialog):
    """Dialog to view connection history"""
    def __init__(self, parent):
        super().__init__(title="Connection History", parent=parent, modal=True)
        self.add_button("Clear History", Gtk.ResponseType.APPLY)
        self.add_button("Close", Gtk.ResponseType.CLOSE)
        self.set_default_size(700, 400)
        
        box = self.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        
        # Text view for logs
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_monospace(True)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        
        scroll.add(self.text_view)
        box.pack_start(scroll, True, True, 0)
        
        self.load_history()
        self.show_all()
        
        self.connect("response", self.on_response)
    
    def load_history(self):
        """Load history from file"""
        buffer = self.text_view.get_buffer()
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r") as f:
                content = f.read()
                if content:
                    buffer.set_text(content)
                else:
                    buffer.set_text("No connection history yet.")
        else:
            buffer.set_text("No connection history yet.")
        
        # Scroll to end
        end_iter = buffer.get_end_iter()
        self.text_view.scroll_to_iter(end_iter, 0.0, False, 0.0, 0.0)
    
    def on_response(self, dialog, response):
        if response == Gtk.ResponseType.APPLY:
            # Clear history
            if HISTORY_FILE.exists():
                HISTORY_FILE.unlink()
            buffer = self.text_view.get_buffer()
            buffer.set_text("History cleared.")


class WifiWindow(Gtk.Window):
    def __init__(self, no_scan=False):
        super().__init__(title="connex")
        self.set_default_size(700, 550)
        self.set_border_width(0)

        self.apply_theme()
        
        # Header bar
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("connex")
        self.set_titlebar(header)

        # Header animation
        self.header_revealer = Gtk.Revealer()
        self.header_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_LEFT)
        self.header_revealer.set_transition_duration(300)

        # Spinner
        self.header_spinner = Gtk.Spinner()
        
        # Connection status in header
        self.header_status_box = Gtk.Box(spacing=6)
        self.header_status_icon = Gtk.Image.new_from_icon_name(
            "network-wireless-offline-symbolic", Gtk.IconSize.BUTTON
        )
        self.header_status_label = Gtk.Label(label="Disconnected")
        self.header_status_box.pack_start(self.header_status_icon, False, False, 0)
        self.header_status_box.pack_start(self.header_spinner, False, False, 0)
        self.header_status_box.pack_start(self.header_status_label, False, False, 0)

        self.header_revealer.add(self.header_status_box)
        header.set_custom_title(self.header_revealer)
        
        # Scan button in header
        self.scan_button = Gtk.Button()
        scan_icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        self.scan_button.set_image(scan_icon)
        self.scan_button.set_tooltip_text("Refresh Networks")
        self.scan_button.connect("clicked", self.on_scan_clicked)
        header.pack_start(self.scan_button)
        
        # Menu button
        menu_button = Gtk.MenuButton()
        menu_icon = Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON)
        menu_button.set_image(menu_icon)
        
        menu = Gtk.Menu()
        
        info_item = Gtk.MenuItem(label="Connection Info")
        info_item.connect("activate", self.show_connection_info)
        menu.append(info_item)
        
        history_item = Gtk.MenuItem(label="View History")
        history_item.connect("activate", self.show_history)
        menu.append(history_item)

        speedtest_item = Gtk.MenuItem(label="Speed Test")
        speedtest_item.connect("activate", self.show_speedtest)
        menu.append(speedtest_item)
        
        menu.append(Gtk.SeparatorMenuItem())
        
        hidden_item = Gtk.MenuItem(label="Connect to Hidden Network")
        hidden_item.connect("activate", self.connect_hidden_network)
        menu.append(hidden_item)
        
        menu.append(Gtk.SeparatorMenuItem())
        
        about_item = Gtk.MenuItem(label="About")
        about_item.connect("activate", self.show_about)
        menu.append(about_item)
        
        menu.show_all()
        menu_button.set_popup(menu)
        header.pack_end(menu_button)
        
        # Airplane mode toggle
        self.airplane_button = Gtk.ToggleButton()
        airplane_icon = Gtk.Image.new_from_icon_name("airplane-mode-symbolic", Gtk.IconSize.BUTTON)
        self.airplane_button.set_image(airplane_icon)
        self.airplane_button.set_tooltip_text("Airplane Mode (toggle WiFi)")
        self.airplane_button.connect("toggled", self.on_airplane_toggled)
        header.pack_start(self.airplane_button)
        
        # Update airplane button state
        self.update_airplane_state()

        # Window rezize
        self.last_resize_time = datetime.now()
        self.connect("configure-event", self.on_configure_event)
        self.connect("size-allocate", self.on_size_allocate)
        
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)
        
        # Status bar at top
        self.status_revealer = Gtk.Revealer()
        self.status_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.status_revealer.set_transition_duration(250)
        
        self.status_bar = Gtk.InfoBar()
        self.status_bar.set_message_type(Gtk.MessageType.INFO)
        self.status_label = Gtk.Label(label="Ready to scan")
        content = self.status_bar.get_content_area()
        content.add(self.status_label)
        self.status_bar.set_show_close_button(False)
        
        self.status_revealer.add(self.status_bar)
        self.status_revealer.set_reveal_child(True)
        main_box.pack_start(self.status_revealer, False, False, 0)
        
        # Search bar
        self.search_revealer = Gtk.Revealer()
        self.search_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.search_revealer.set_transition_duration(200)
        
        search_box = Gtk.Box(spacing=6)
        search_box.set_margin_start(12)
        search_box.set_margin_end(12)
        search_box.set_margin_top(12)
        search_box.set_margin_bottom(6)
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search networks...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        search_box.pack_start(self.search_entry, True, True, 0)
        
        self.search_revealer.add(search_box)
        self.search_revealer.set_reveal_child(False)
        main_box.pack_start(self.search_revealer, False, False, 0)

        GLib.timeout_add(500, lambda: self.search_revealer.set_reveal_child(True))
        
        # Networks list
        self.store = Gtk.ListStore(str, str, str, str, str, str)  # SSID, Signal, Security, Icon, Full info, Type
        self.filter = self.store.filter_new()
        self.filter.set_visible_func(self.filter_func)
        
        tree = Gtk.TreeView(model=self.filter)
        tree.set_headers_visible(True)
        tree.set_enable_search(False)
        tree.set_activate_on_single_click(False)
        
        # Icon column
        icon_renderer = Gtk.CellRendererPixbuf()
        icon_column = Gtk.TreeViewColumn("", icon_renderer)
        icon_column.set_cell_data_func(icon_renderer, self.signal_icon_func)
        icon_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        icon_column.set_fixed_width(40)
        tree.append_column(icon_column)
        
        # SSID column
        ssid_renderer = Gtk.CellRendererText()
        ssid_renderer.set_property("ellipsize", 3)
        ssid_column = Gtk.TreeViewColumn("Network Name", ssid_renderer, text=0)
        ssid_column.set_expand(True)
        ssid_column.set_sort_column_id(0)
        tree.append_column(ssid_column)
        
        # Signal column
        signal_renderer = Gtk.CellRendererText()
        signal_column = Gtk.TreeViewColumn("Signal", signal_renderer, text=1)
        signal_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        signal_column.set_fixed_width(80)
        signal_column.set_sort_column_id(1)
        tree.append_column(signal_column)
        
        # Security column
        sec_renderer = Gtk.CellRendererText()
        sec_column = Gtk.TreeViewColumn("Security", sec_renderer, text=2)
        sec_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        sec_column.set_fixed_width(120)
        tree.append_column(sec_column)
        
        # Type column (WiFi/Bluetooth/etc)
        type_renderer = Gtk.CellRendererText()
        type_column = Gtk.TreeViewColumn("Type", type_renderer, text=5)
        type_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        type_column.set_fixed_width(80)
        tree.append_column(type_column)
        
        tree.connect("row-activated", self.on_row_activated)
        tree.connect("button-press-event", self.on_tree_button_press)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_margin_start(12)
        scroll.set_margin_end(12)
        scroll.set_margin_bottom(12)
        scroll.add(tree)
        main_box.pack_start(scroll, True, True, 0)
        
        self.tree = tree
        self.selected_ssid = None
        self.selected_security = None
        self.current_connection = None
        self.current_ssid = None
        
        # Auto-refresh timer (every 10 seconds)
        self.no_scan = no_scan
        if not self.no_scan:
            self.auto_refresh = True
            GLib.timeout_add_seconds(10, self.auto_scan)
        else:
            self.auto_refresh = False
                
        # Update header status periodically
        GLib.timeout_add_seconds(5, self.update_header_status)
        
        # Initialize notifications
        Notify.init("connex")
        
        self.show_all()
        self.setup_keyboard_shortcuts()
        if not no_scan:
            GLib.idle_add(self.scan_networks)
        GLib.idle_add(self.update_header_status)
    
    def apply_theme(self):
        """Apply theme based on system settings"""
        settings = Gtk.Settings.get_default()
        
        # Try to detect system theme preference
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True, text=True, timeout=2
            )
            if "dark" in result.stdout.lower():
                settings.set_property("gtk-application-prefer-dark-theme", True)
            else:
                settings.set_property("gtk-application-prefer-dark-theme", False)
        except:
            # Default to dark theme for Hyprland
            settings.set_property("gtk-application-prefer-dark-theme", True)
    
    def update_header_status(self):
        """Update connection status in header (only when state changes)"""
        code, out, err = self.run_cmd("nmcli -t -f GENERAL.STATE device show")

        connected = "connected" in out.lower()
        new_ssid = self.get_current_connection() if connected else None

        if connected == getattr(self, "_last_connected", None) and new_ssid == getattr(self, "_last_ssid", None):
            return self.auto_refresh

        self._last_connected = connected
        self._last_ssid = new_ssid

        self.header_revealer.set_reveal_child(False)

        def update_and_reveal():
            if connected and new_ssid:
                self.header_status_icon.set_from_icon_name(
                    "network-wireless-signal-excellent-symbolic", Gtk.IconSize.BUTTON
                )

                if self.check_internet():
                    self.header_status_label.set_markup(
                        f"<b>{new_ssid}</b> <span color='green'>✓</span>"
                    )
                else:
                    self.header_status_label.set_markup(f"<b>{new_ssid}</b>")
            else:
                self.header_status_icon.set_from_icon_name(
                    "network-wireless-offline-symbolic", Gtk.IconSize.BUTTON
                )
                self.header_status_label.set_text("Disconnected")

            self.header_revealer.set_reveal_child(True)
            return False

        GLib.timeout_add(150, update_and_reveal)
        return self.auto_refresh

    

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        accel_group = Gtk.AccelGroup()
        self.add_accel_group(accel_group)
        
        # Ctrl+R: Refresh
        key, mod = Gtk.accelerator_parse("<Control>R")
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, 
                           lambda *_: self.on_scan_clicked())
        
        # Ctrl+F: Focus search
        key, mod = Gtk.accelerator_parse("<Control>F")
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, 
                           lambda *_: self.search_entry.grab_focus())
        
        # Ctrl+H: Hidden network
        key, mod = Gtk.accelerator_parse("<Control>H")
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, 
                           lambda *_: self.connect_hidden_network())
        
        # Ctrl+Q: Quit
        key, mod = Gtk.accelerator_parse("<Control>Q")
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, 
                           lambda *_: self.destroy())
        
        log_debug("Keyboard shortcuts initialized")
    
    def update_airplane_state(self):
        """Update airplane mode button state"""
        code, out, err = self.run_cmd("nmcli radio wifi")
        enabled = "enabled" in out.lower()
        self.airplane_button.set_active(not enabled)
        return True
    
    def on_airplane_toggled(self, button):
        """Toggle airplane mode avec animations"""
        active = button.get_active()
        
        self.header_revealer.set_reveal_child(False)
        self.status_revealer.set_reveal_child(False)
        
        def apply_mode():
            if active:
                code, out, err = self.run_cmd("nmcli radio wifi off")
                if code == 0:
                    self.status_label.set_text("✈ Airplane mode enabled")
                    self.status_bar.set_message_type(Gtk.MessageType.WARNING)
                    self.scan_button.set_sensitive(False)
                    self.auto_refresh = False
                    
                    notification = Notify.Notification.new(
                        "Airplane Mode",
                        "WiFi disabled",
                        "airplane-mode"
                    )
                    notification.show()
                else:
                    button.set_active(False)
                    self.show_error("Failed to disable WiFi")
            else:
                code, out, err = self.run_cmd("nmcli radio wifi on")
                if code == 0:
                    self.status_label.set_text("WiFi enabled")
                    self.status_bar.set_message_type(Gtk.MessageType.INFO)
                    self.scan_button.set_sensitive(True)
                    self.auto_refresh = not self.no_scan
                    
                    notification = Notify.Notification.new(
                        "WiFi Enabled",
                        "Scanning for networks...",
                        "network-wireless"
                    )
                    notification.show()
                    
                    GLib.timeout_add(1000, lambda: self.scan_networks())
                else:
                    button.set_active(True)
                    self.show_error("Failed to enable WiFi")
            
            self.header_revealer.set_reveal_child(True)
            self.status_revealer.set_reveal_child(True)
            return False
        
        GLib.timeout_add(150, apply_mode)
    
    def show_speedtest(self, *_):
        """Show speed test dialog"""
        dialog = SpeedTestDialog(self)
        dialog.run()
        dialog.destroy()


    def set_status_animated(self, message, message_type=Gtk.MessageType.INFO, show_spinner=False):
        """Update status with animation"""
        self.status_revealer.set_reveal_child(False)
        
        def update_and_show():
            self.status_label.set_text(message)
            self.status_bar.set_message_type(message_type)
            self.status_revealer.set_reveal_child(True)
            return False
        
        GLib.timeout_add(150, update_and_show)
        
        if show_spinner:
            self.header_spinner.start()
            self.header_spinner.show()
            self.header_status_icon.hide()
        else:
            self.header_spinner.stop()
            self.header_spinner.hide()
            self.header_status_icon.show()

    def check_internet(self):
        """Check if internet is accessible"""
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", "1.1.1.1"],
                capture_output=True, timeout=3
            )
            return result.returncode == 0
        except:
            return False
    
    def signal_icon_func(self, column, cell, model, iter, data):
        """Display signal strength icon"""
        signal_str = model.get_value(iter, 1)
        net_type = model.get_value(iter, 5)
        
        try:
            signal = int(signal_str.rstrip('%'))
            if net_type == "WiFi":
                if signal >= 75:
                    icon = "network-wireless-signal-excellent-symbolic"
                elif signal >= 50:
                    icon = "network-wireless-signal-good-symbolic"
                elif signal >= 25:
                    icon = "network-wireless-signal-ok-symbolic"
                else:
                    icon = "network-wireless-signal-weak-symbolic"
            else:
                icon = "network-wireless-symbolic"
        except:
            icon = "network-wireless-symbolic"
        
        cell.set_property("icon-name", icon)
    
    def filter_func(self, model, iter, data):
        """Filter networks based on search"""
        search_text = self.search_entry.get_text().lower()
        if not search_text:
            return True
        ssid = model.get_value(iter, 0).lower()
        return search_text in ssid
    
    def on_search_changed(self, entry):
        """Trigger filter refilter on search"""
        self.filter.refilter()
    
    def auto_scan(self):
        """Auto-refresh networks periodically"""
        if self.auto_refresh and self.is_visible():
            self.scan_networks(silent=True)
        return self.auto_refresh
    
    def run_cmd(self, cmd):
        """Execute shell command"""
        try:
            log_debug(f"Running: {cmd}")
            res = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=8)
            log_debug(f"Result: {res.returncode}, stdout: {res.stdout[:100]}")
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except subprocess.TimeoutExpired:
            log_debug("Command timed out")
            return 1, "", "Command timed out"
        except Exception as e:
            log_debug(f"Command error: {e}")
            return 1, "", str(e)
    
    def get_current_connection(self):
        """Get currently connected network"""
        code, out, err = self.run_cmd("nmcli -t -f NAME,TYPE,DEVICE connection show --active")
        for line in out.splitlines():
            parts = line.split(':')
            if len(parts) >= 2 and parts[1] == "802-11-wireless":
                self.current_ssid = parts[0]
                return parts[0]
        self.current_ssid = None
        return None
    
    def scan_networks(self, silent=False):
        """Scan for available networks"""

        if not silent:
            self.set_status_animated("Scanning networks...", Gtk.MessageType.INFO, show_spinner=True)
            self.status_bar.set_message_type(Gtk.MessageType.INFO)
            self.scan_button.set_sensitive(False)
        
        def scan_thread():
            # Trigger rescan
            subprocess.run(["nmcli", "device", "wifi", "rescan"], 
                         capture_output=True, timeout=5)
            
            code, out, err = self.run_cmd("nmcli -t -f SSID,SIGNAL,SECURITY device wifi list")
            GLib.idle_add(self.update_network_list, code, out, err, silent)
        
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def update_network_list(self, code, out, err, silent):
        """Update the network list (runs in main thread)"""

        if not self.is_visible() or not self.get_window().get_state() & Gdk.WindowState.FOCUSED:
            return False


        self.scan_button.set_sensitive(True)
        self.header_spinner.stop()
        self.header_spinner.hide()
        self.header_status_icon.show()
        
        if code != 0:
            if not silent:
                self.set_status_animated(f"Scan failed: {err or 'nmcli error'}", Gtk.MessageType.ERROR)
            return False
        
        self.tree.set_opacity(0.3)

        self.current_connection = self.get_current_connection()
        self.store.clear()
        
        seen_ssids = set()
        for line in out.splitlines():
            if not line.strip():
                continue
            parts = line.split(':')
            ssid = parts[0] if parts[0] else "<Hidden Network>"
            
            # Skip duplicates (same SSID)
            if ssid in seen_ssids:
                continue
            seen_ssids.add(ssid)
            
            signal = parts[1] if len(parts) > 1 else "0"
            sec = parts[2] if len(parts) > 2 else "Open"
            
            # Format security
            if not sec or sec == "--":
                sec_display = "Open"
            elif "WPA3" in sec:
                sec_display = "WPA3"
            elif "WPA2" in sec:
                sec_display = "WPA2"
            elif "WPA" in sec:
                sec_display = "WPA"
            else:
                sec_display = sec
            
            # Add connected indicator
            display_ssid = f"● {ssid}" if ssid == self.current_connection else ssid
            
            self.store.append([display_ssid, f"{signal}%", sec_display, signal, ssid, "WiFi"])
        
        # Sort by signal strength
        self.store.set_sort_column_id(3, Gtk.SortType.DESCENDING)
        
        def fade_in(opacity=0.3):
            if opacity < 1.0:
                self.tree.set_opacity(opacity)
                GLib.timeout_add(30, fade_in, opacity + 0.1)
            else:
                self.tree.set_opacity(1.0)
            return False
    
        GLib.timeout_add(50, fade_in)

        count = len(self.store)
        if not silent:
            self.set_status_animated(
                f"Found {count} network{'s' if count != 1 else ''}",
                Gtk.MessageType.INFO
            )
            
        return False
    
    def on_scan_clicked(self, *_):
        """Manual scan button clicked"""
        self.scan_networks()

    def on_configure_event(self, widget, event):
        """Pause auto-refresh when resizing"""
        self.auto_refresh = False
        self.last_resize_time = datetime.now()
        return False

    def on_size_allocate(self, widget, allocation):
        """Resume scanning a bit after resizing stops"""
        def reenable():
            if (datetime.now() - self.last_resize_time).total_seconds() > 1.5:
                self.auto_refresh = not self.no_scan
                return False
            return True
        GLib.timeout_add(1500, reenable)

    
    def connect_hidden_network(self, *_):
        """Connect to hidden network"""
        dialog = HiddenNetworkDialog(self)
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            ssid = dialog.get_ssid()
            password = dialog.get_password()
            dialog.destroy()
            
            if ssid:
                self.connect_to_network(ssid, password, hidden=True)
            else:
                self.show_error("SSID is required")
        else:
            dialog.destroy()
    
    def on_row_activated(self, tree, path, col):
        """Network double-clicked - initiate connection"""
        model = tree.get_model()
        ssid = model[path][4]  # Original SSID without indicator
        security = model[path][2]
        signal = model[path][3]
        
        if ssid == "<Hidden Network>":
            self.connect_hidden_network()
            return
        
        # Check if already connected
        if ssid == self.current_connection:
            response = self.show_question(
                f"Already connected to {ssid}",
                "Do you want to disconnect?"
            )
            if response == Gtk.ResponseType.YES:
                self.disconnect_network(ssid)
            return
        
        self.selected_ssid = ssid
        self.selected_security = security
        
        # If open network, connect directly
        if security == "Open":
            self.connect_to_network(ssid, "", signal=signal)
        else:
            # Show password dialog
            dialog = PasswordDialog(self, ssid, security)
            response = dialog.run()
            
            if response == Gtk.ResponseType.OK:
                password = dialog.get_password()
                dialog.destroy()
                if password:
                    self.connect_to_network(ssid, password, signal=signal)
                else:
                    self.show_error("Password required for secured networks")
            else:
                dialog.destroy()
    
    def connect_to_network(self, ssid, password, hidden=False, signal="0"):
        """Connect to a network"""
        self.set_status_animated(f"Connecting to {ssid}...", Gtk.MessageType.INFO, show_spinner=True)
        
        def connect_thread():
            # First delete forget the connection for this network
            self.forget_network(ssid, True)

            args = ["nmcli", "device", "wifi", "connect", ssid]
            if password:
                args += ["password", password]
            if hidden:
                args += ["hidden", "yes"]
            
            try:
                result = subprocess.run(args, capture_output=True, text=True, timeout=20)
                GLib.idle_add(self.on_connect_done, result.returncode, 
                            result.stdout, result.stderr, ssid, signal)
            except subprocess.TimeoutExpired:
                GLib.idle_add(self.on_connect_done, 1, "", "Connection timed out", ssid, signal)
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def on_connect_done(self, code, out, err, ssid, signal):
        """Connection attempt completed"""
        if code == 0:
            self.set_status_animated(f"✓ Connected to {ssid}", Gtk.MessageType.INFO)
            
            self.header_status_icon.set_from_icon_name(
                "network-wireless-signal-excellent-symbolic", Gtk.IconSize.BUTTON
            )

            def pulse(scale=1.0, direction=1):
                if scale > 1.2:
                    direction = -1
                elif scale < 1.0:
                    return False
                
                self.header_status_box.set_scale_factor(int(scale * 100) / 100)
                GLib.timeout_add(20, pulse, scale + 0.02 * direction, direction)
                return False
            
            # To fix
            #pulse()

            # notification
            notification = Notify.Notification.new(
                "Connected",
                f"Successfully connected to {ssid}",
                "network-wireless"
            )
            notification.show()
            
            # Log success
            log_connection(ssid, signal, True)
            
            # Refresh to show connected status
            GLib.timeout_add(1000, lambda: self.scan_networks(silent=True))
            GLib.timeout_add(1000, self.update_header_status)
        else:
            error_msg = err or out
            if "Secrets were required" in error_msg:
                error_msg = "Incorrect password"
            elif "No network with SSID" in error_msg:
                error_msg = "Network not found"
            
            self.set_status_animated(f"✗ Failed: {error_msg}", Gtk.MessageType.ERROR)
            
            def shake(offset=0, count=0):
                if count > 6:
                    self.status_bar.set_margin_start(12)
                    return False
                
                margin = 12 + int(10 * (1 - count/6) * (1 if count % 2 == 0 else -1))
                self.status_bar.set_margin_start(margin)
                GLib.timeout_add(50, shake, -offset, count + 1)
                return False
            
            shake()


            # Send notification
            notification = Notify.Notification.new(
                "Connection Failed",
                f"Could not connect to {ssid}: {error_msg}",
                "network-wireless-offline"
            )
            notification.show()
            
            # Log failure
            log_connection(ssid, signal, False, error_msg)
        
        return False
    
    def disconnect_network(self, ssid):
        """Disconnect from network"""
        code, out, err = self.run_cmd(f"nmcli connection down '{ssid}'")
        if code == 0:
            self.status_label.set_text(f"Disconnected from {ssid}")
            self.status_bar.set_message_type(Gtk.MessageType.INFO)
            
            notification = Notify.Notification.new(
                "Disconnected",
                f"Disconnected from {ssid}",
                "network-wireless-offline"
            )
            notification.show()
            
            GLib.timeout_add(1000, lambda: self.scan_networks(silent=True))
            GLib.timeout_add(500, self.update_header_status)
        else:
            self.show_error(f"Failed to disconnect: {err}")
    
    def on_tree_button_press(self, widget, event):
        """Handle right-click context menu"""
        if event.button == 3:  # Right click
            path = widget.get_path_at_pos(int(event.x), int(event.y))
            if path:
                widget.set_cursor(path[0])
                self.show_context_menu(widget, event, path[0])
            return True
        return False
    
    def show_context_menu(self, widget, event, path):
        """Show context menu for network"""
        model = widget.get_model()
        ssid = model[path][4]
        
        menu = Gtk.Menu()
        
        if ssid != "<Hidden Network>":
            connect_item = Gtk.MenuItem(label="Connect")
            connect_item.connect("activate", lambda x: self.on_row_activated(widget, path, None))
            menu.append(connect_item)
            
            if ssid == self.current_connection:
                disconnect_item = Gtk.MenuItem(label="Disconnect")
                disconnect_item.connect("activate", lambda x: self.disconnect_network(ssid))
                menu.append(disconnect_item)
            
            menu.append(Gtk.SeparatorMenuItem())
            
            forget_item = Gtk.MenuItem(label="Forget Network")
            forget_item.connect("activate", lambda x: self.forget_network(ssid))
            menu.append(forget_item)
        
        menu.show_all()
        menu.popup_at_pointer(event)
    
    def forget_network(self, ssid, quick=False):
        """Remove saved network connection"""
        # quick forget logic
        if quick:
            code, out, err = self.run_cmd(f"nmcli connection delete '{ssid}'")
            if code == 0:
                log_debug("Forgoted sucessfully")
            else:
                log_debug("Network not saved")
        else:
            response = self.show_question(
                f"Forget network '{ssid}'?",
                "This will remove the saved password and settings."
            )
            
            if response == Gtk.ResponseType.YES:
                code, out, err = self.run_cmd(f"nmcli connection delete '{ssid}'")
                if code == 0:
                    self.status_label.set_text(f"Forgot network {ssid}")
                    self.status_bar.set_message_type(Gtk.MessageType.INFO)
                else:
                    self.status_label.set_text(f"Network {ssid} was not saved")
                    self.status_bar.set_message_type(Gtk.MessageType.WARNING)
    
    def show_connection_info(self, *_):
        """Show current connection details"""
        code, out, err = self.run_cmd("nmcli -t -f GENERAL,IP4 device show")
        
        if code == 0 and out:
            dialog = Gtk.MessageDialog(
                parent=self,
                modal=True,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Network Information"
            )
            
            # Parse and format output
            info_lines = []
            for line in out.splitlines()[:20]:
                if any(x in line for x in ["IP4.ADDRESS", "IP4.GATEWAY", "IP4.DNS", 
                                           "GENERAL.CONNECTION", "GENERAL.STATE"]):
                    key, val = line.split(":", 1)
                    key = key.replace("GENERAL.", "").replace("IP4.", "")
                    info_lines.append(f"{key}: {val}")
            
            info_text = "\n".join(info_lines) if info_lines else "No active connection"
            
            dialog.format_secondary_text(info_text)
            dialog.run()
            dialog.destroy()
        else:
            self.show_error("Could not retrieve connection info")
    
    def show_history(self, *_):
        """Show connection history"""
        dialog = LogViewerDialog(self)
        dialog.run()
        dialog.destroy()
    
    def show_about(self, *_):
        """Show about dialog"""
        dialog = Gtk.AboutDialog(transient_for=self, modal=True)
        dialog.set_logo_icon_name("network-wireless-symbolic")
        dialog.set_program_name("connex")
        dialog.set_version("1.1.1")
        dialog.set_comments("Modern Wi-Fi Manager")
        dialog.set_website("https://github.com/Lluciocc/connex")
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.set_authors(["Lluciocc"])
        dialog.run()
        dialog.destroy()
    
    def show_error(self, message):
        """Show error dialog"""
        dialog = Gtk.MessageDialog(
            parent=self,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
    
    def show_question(self, primary, secondary):
        """Show yes/no question dialog"""
        dialog = Gtk.MessageDialog(
            parent=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=primary
        )
        dialog.format_secondary_text(secondary)
        response = dialog.run()
        dialog.destroy()
        return response
    
    def do_destroy(self):
        """Clean up on window close"""
        self.auto_refresh = False
        Gtk.Window.do_destroy(self)


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
