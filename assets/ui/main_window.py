import gi
import subprocess
import threading
import shlex
import time
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, GLib, Gdk, Notify, AppIndicator3
from datetime import datetime
from assets.utils.debug import log_debug, log_connection, get_distro
from assets.ui.dialogs import (
        PasswordDialog,
        HiddenNetworkDialog,
        SpeedTestDialog,
        LogViewerDialog,
        ProxyDialog,
        QRCodeDialog,
        QR_AVAILABLE, 
        VPNManagerDialog,
        AboutDialog
    )

class WifiWindow(Gtk.Window):
    def __init__(self, no_scan=False):
        super().__init__(title="connex")
        self.set_default_size(700, 550)
        self.set_border_width(0)

        self.apply_theme()
        
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("connex")
        self.set_titlebar(header)

        self.header_revealer = Gtk.Revealer()
        self.header_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_LEFT)
        self.header_revealer.set_transition_duration(300)

        self.header_spinner = Gtk.Spinner()
        
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
        
        self.scan_button = Gtk.Button()
        scan_icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        self.scan_button.set_image(scan_icon)
        self.scan_button.set_tooltip_text("Refresh Networks")
        self.scan_button.connect("clicked", self.on_scan_clicked)
        header.pack_start(self.scan_button)
        
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

        proxy_item = Gtk.MenuItem(label="Proxy Settings")
        proxy_item.connect("activate", self.show_proxy_settings)
        menu.append(proxy_item)

        vpn_item = Gtk.MenuItem(label="VPN Manager")
        vpn_item.connect("activate", self.show_vpn_manager)
        menu.append(vpn_item)
        
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
        
        self.airplane_button = Gtk.ToggleButton()
        airplane_icon = Gtk.Image.new_from_icon_name("airplane-mode-symbolic", Gtk.IconSize.BUTTON)
        self.airplane_button.set_image(airplane_icon)
        self.airplane_button.set_tooltip_text("Airplane Mode (toggle WiFi)")
        self.airplane_button.connect("toggled", self.on_airplane_toggled)
        header.pack_start(self.airplane_button)
        
        self.update_airplane_state()

        self.last_resize_time = datetime.now()
        self.freeze_updates = False
        self.connect("configure-event", self.on_configure_event)
        self.connect("size-allocate", self.on_size_allocate)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)
        
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
        
        self.store = Gtk.ListStore(str, str, str, str, str, str)  # SSID, Signal, Security, Icon, Full info, Type
        self.filter = self.store.filter_new()
        self.filter.set_visible_func(self.filter_func)
        
        tree = Gtk.TreeView(model=self.filter)
        tree.set_headers_visible(True)
        tree.set_enable_search(False)
        tree.set_activate_on_single_click(False)
        
        icon_renderer = Gtk.CellRendererPixbuf()
        icon_column = Gtk.TreeViewColumn("", icon_renderer)
        icon_column.set_cell_data_func(icon_renderer, self.signal_icon_func)
        icon_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        icon_column.set_fixed_width(40)
        tree.append_column(icon_column)
        
        ssid_renderer = Gtk.CellRendererText()
        ssid_renderer.set_property("ellipsize", 3)
        ssid_column = Gtk.TreeViewColumn("Network Name", ssid_renderer, text=0)
        ssid_column.set_expand(True)
        ssid_column.set_sort_column_id(0)
        tree.append_column(ssid_column)
        
        signal_renderer = Gtk.CellRendererText()
        signal_column = Gtk.TreeViewColumn("Signal", signal_renderer, text=1)
        signal_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        signal_column.set_fixed_width(80)
        signal_column.set_sort_column_id(1)
        tree.append_column(signal_column)
        
        sec_renderer = Gtk.CellRendererText()
        sec_column = Gtk.TreeViewColumn("Security", sec_renderer, text=2)
        sec_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        sec_column.set_fixed_width(120)
        tree.append_column(sec_column)
        
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
        
        self.no_scan = no_scan
        self.scan_in_progress = False
        self.last_wifi_list = ""
        self.last_wifi_time = 0

        if not self.no_scan:
            self.auto_refresh = True
            GLib.timeout_add_seconds(10, self.auto_scan)
        else:
            self.auto_refresh = False
                
        GLib.timeout_add_seconds(5, self.update_header_status)
        
        Notify.init("connex")
        
        self.show_all()
        self.setup_keyboard_shortcuts()
        if not no_scan:
            GLib.idle_add(self.scan_networks)
        GLib.idle_add(self.update_header_status)
    
    def apply_theme(self):
        settings = Gtk.Settings.get_default()
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
            settings.set_property("gtk-application-prefer-dark-theme", True)
    
    def update_header_status(self):
        if self.freeze_updates:
            return self.auto_refresh

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
        accel_group = Gtk.AccelGroup()
        self.add_accel_group(accel_group)
        
        key, mod = Gtk.accelerator_parse("<Control>R")
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, 
                           lambda *_: self.on_scan_clicked())
        
        key, mod = Gtk.accelerator_parse("<Control>F")
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, 
                           lambda *_: self.search_entry.grab_focus())
        
        key, mod = Gtk.accelerator_parse("<Control>H")
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, 
                           lambda *_: self.connect_hidden_network())
        
        key, mod = Gtk.accelerator_parse("<Control>Q")
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, 
                           lambda *_: self.destroy())
        
        log_debug("Keyboard shortcuts initialized")
    
    def update_airplane_state(self):
        code, out, err = self.run_cmd("nmcli radio wifi")
        enabled = "enabled" in out.lower()
        self.airplane_button.set_active(not enabled)
        return True
    
    def on_airplane_toggled(self, button):
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
        dialog = SpeedTestDialog(self)
        dialog.run()
        dialog.destroy()

    def show_proxy_settings(self, *_):
        dialog = ProxyDialog(self)
        dialog.run()
        dialog.destroy()

    def show_vpn_manager(self, *_):
        dialog = VPNManagerDialog(self)
        dialog.run()
        dialog.destroy()

    def set_status_animated(self, message, message_type=Gtk.MessageType.INFO, show_spinner=False):
        if self.freeze_updates:
            return

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
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", "1.1.1.1"],
                capture_output=True, timeout=3
            )
            return result.returncode == 0
        except:
            return False
    
    def signal_icon_func(self, column, cell, model, iter, data):
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
        search_text = self.search_entry.get_text().lower()
        if not search_text:
            return True
        ssid = model.get_value(iter, 0).lower()
        return search_text in ssid
    
    def on_search_changed(self, entry):
        self.filter.refilter()
    
    def auto_scan(self):
        if self.auto_refresh and self.is_visible():
            self.scan_networks(silent=True)
        return self.auto_refresh
    
    def run_cmd(self, cmd):
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
        code, out, err = self.run_cmd("nmcli -t -f NAME,TYPE,DEVICE connection show --active")
        for line in out.splitlines():
            parts = line.split(':')
            if len(parts) >= 2 and parts[1] == "802-11-wireless":
                self.current_ssid = parts[0]
                return parts[0]
        self.current_ssid = None
        return None
    
    def scan_networks(self, silent=False, do_rescan=False):
        if self.scan_in_progress:
            return

        now = time.time()
        if self.last_wifi_list and now - self.last_wifi_time < 5:
            self.update_network_list(0, self.last_wifi_list, "", silent)
            return

        if not silent:
            self.set_status_animated("Scanning networks...", Gtk.MessageType.INFO, show_spinner=True)
            self.status_bar.set_message_type(Gtk.MessageType.INFO)
            self.scan_button.set_sensitive(False)
        
        def scan_thread():
            self.scan_in_progress = True
            if do_rescan:
                subprocess.run(["nmcli", "device", "wifi", "rescan"], capture_output=True, timeout=5)
            
            code, out, err = self.run_cmd("nmcli -t -f SSID,SIGNAL,SECURITY device wifi list")
            self.last_wifi_list = out
            self.last_wifi_time = time.time()
            self.scan_in_progress = False
            GLib.idle_add(self.update_network_list, code, out, err, silent)
        
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def update_network_list(self, code, out, err, silent):
        if self.freeze_updates:
            return False

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
        
        self.current_connection = self.get_current_connection()
        self.store.clear()
        
        seen_ssids = set()
        for line in out.splitlines():
            if not line.strip():
                continue
            parts = line.split(':')
            ssid = parts[0] if parts[0] else "<Hidden Network>"
            
            if ssid in seen_ssids:
                continue
            seen_ssids.add(ssid)
            
            signal = parts[1] if len(parts) > 1 else "0"
            sec = parts[2] if len(parts) > 2 else "Open"
            
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
            
            display_ssid = f"● {ssid}" if ssid == self.current_connection else ssid
            
            self.store.append([display_ssid, f"{signal}%", sec_display, signal, ssid, "WiFi"])
        
        self.store.set_sort_column_id(3, Gtk.SortType.DESCENDING)

        count = len(self.store)
        if not silent:
            self.set_status_animated(
                f"Found {count} network{'s' if count != 1 else ''}",
                Gtk.MessageType.INFO
            )
            
        return False
    
    def on_scan_clicked(self, *_):
        self.scan_networks(do_rescan=True)

    def on_configure_event(self, widget, event):
        self.auto_refresh = False
        self.last_resize_time = datetime.now()
        self.freeze_updates = True
        return False

    def on_size_allocate(self, widget, allocation):
        def reenable():
            if (datetime.now() - self.last_resize_time).total_seconds() > 1.5:
                self.auto_refresh = not self.no_scan
                self.freeze_updates = False
                return False
            return True
        GLib.timeout_add(1500, reenable)

    
    def connect_hidden_network(self, *_):
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
        model = tree.get_model()
        ssid = model[path][4]
        security = model[path][2]
        signal = model[path][3]

        if "EAP" in security or "8021x" in security or ssid.lower() == "eduroam":
            self.set_status_animated(f"Connecting to {ssid} using system profile...",Gtk.MessageType.INFO, show_spinner=True)
            def eap_connect():
                code, out, err = self.run_cmd(f"nmcli connection up '{ssid}'")
                GLib.idle_add(self.on_connect_done, code, out, err, ssid, "0")

            threading.Thread(target=eap_connect, daemon=True).start()
            return

        
        if ssid == "<Hidden Network>":
            self.connect_hidden_network()
            return
        
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
        
        if security == "Open":
            self.connect_to_network(ssid, "", signal=signal)
        else:
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
        self.set_status_animated(f"Connecting to {ssid}...", Gtk.MessageType.INFO, show_spinner=True)
        
        def connect_thread():
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
        if code == 0:
            self.set_status_animated(f"✓ Connected to {ssid}", Gtk.MessageType.INFO)
            
            self.header_status_icon.set_from_icon_name(
                "network-wireless-signal-excellent-symbolic", Gtk.IconSize.BUTTON
            )

            notification = Notify.Notification.new(
                "Connected",
                f"Successfully connected to {ssid}",
                "network-wireless"
            )
            notification.show()
            
            log_connection(ssid, signal, True)
            
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

            notification = Notify.Notification.new(
                "Connection Failed",
                f"Could not connect to {ssid}: {error_msg}",
                "network-wireless-offline"
            )
            notification.show()
            
            log_connection(ssid, signal, False, error_msg)
        
        return False
    
    def disconnect_network(self, ssid):
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
        if event.button == 3:
            path = widget.get_path_at_pos(int(event.x), int(event.y))
            if path:
                widget.set_cursor(path[0])
                self.show_context_menu(widget, event, path[0])
            return True
        return False
    
    def show_context_menu(self, widget, event, path):
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

            qr_item = Gtk.MenuItem(label="Generate QR Code")
            qr_item.connect("activate", lambda x: self.show_qr_code(ssid, model[path][2]))
            menu.append(qr_item)
        
        menu.show_all()
        menu.popup_at_pointer(event)

    def show_qr_code(self, ssid, security):
        password = ""
        if not QR_AVAILABLE:
            if get_distro() == "arch":
                self.show_error("QR code generation requires: pacman -S python-qrcode python-pillow")
            else:
                self.show_error("QR code generation requires: pip install qrcode[pil] pillow")
            return
        
        if security != "Open":
            code, out, err = self.run_cmd(f"nmcli -s -g 802-11-wireless-security.psk connection show '{ssid}'")
            if code == 0 and out:
                password = out.strip()
            else:
                dialog = PasswordDialog(self, ssid, security)
                response = dialog.run()
                if response == Gtk.ResponseType.OK:
                    password = dialog.get_password()
                    dialog.destroy()
                else:
                    dialog.destroy()
                    return
        
        qr_dialog = QRCodeDialog(self, ssid, password, security)
        qr_dialog.run()
        qr_dialog.destroy()
    
    def forget_network(self, ssid, quick=False):
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
        code, out, err = self.run_cmd("nmcli -t -f GENERAL,IP4 device show")
        
        if code == 0 and out:
            dialog = Gtk.MessageDialog(
                parent=self,
                modal=True,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Network Information"
            )
            
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
        dialog = LogViewerDialog(self)
        dialog.run()
        dialog.destroy()
    
    def show_about(self, *_):
        dialog = AboutDialog(self)
        dialog.run()
        dialog.destroy()
    
    def show_error(self, message):
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
        self.auto_refresh = False
        Gtk.Window.do_destroy(self)
