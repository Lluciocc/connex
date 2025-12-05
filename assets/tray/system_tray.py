import gi
import subprocess
import threading

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Notify, AppIndicator3

from assets.utils.debug import log_debug, log_connection
from assets.ui.main_window import WifiWindow
from assets.ui.other_ui import SpeedTestDialog
from assets.ui.proxy_ui import ProxyDialog
from assets.ui.vpn_ui import VPNManagerDialog
from assets.ui.wifi_ui import LogViewerDialog, HiddenNetworkDialog, PasswordDialog


def run_nmcli(args, timeout=3, text=True):
    try:
        return subprocess.run(
            ["nmcli"] + args,
            capture_output=True,
            timeout=timeout,
            text=text
        )
    except:
        return None


class SystemTrayApp:
    def __init__(self):
        self.window = None
        self.current_networks = []
        self.current_ssid = None

        Notify.init("connex")

        self.indicator = AppIndicator3.Indicator.new(
            "connex",
            "network-wireless-symbolic",
            AppIndicator3.IndicatorCategory.SYSTEM_SERVICES
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_title("connex")

        self.update_menu()
        GLib.timeout_add_seconds(5, self.update_icon)
        GLib.timeout_add_seconds(10, self.update_menu_networks)

    def get_connection_status(self):
        result = run_nmcli(["-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"])
        if not result:
            return None, False

        for line in result.stdout.splitlines():
            parts = line.split(':')
            if len(parts) >= 2 and parts[1] == "802-11-wireless":
                return parts[0], True
        return None, False

    def get_available_networks(self):
        run_nmcli(["device", "wifi", "rescan"], timeout=3)
        result = run_nmcli(["-t", "-f", "SSID,SIGNAL,SECURITY,IN-USE", "device", "wifi", "list"], timeout=4)
        if not result:
            return []

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

        networks.sort(key=lambda x: x['signal'], reverse=True)
        return networks[:15]

    def update_menu(self):
        menu = Gtk.Menu()
        self.current_ssid, connected = self.get_connection_status()

        if connected and self.current_ssid:
            item = Gtk.MenuItem(label=f"✓ Connected to {self.current_ssid}")
            item.set_sensitive(False)
            menu.append(item)

            dis = Gtk.MenuItem(label=f"Disconnect from {self.current_ssid}")
            dis.connect("activate", self.disconnect_current)
            menu.append(dis)
        else:
            item = Gtk.MenuItem(label="○ No connection")
            item.set_sensitive(False)
            menu.append(item)

        menu.append(Gtk.SeparatorMenuItem())

        connect_item = Gtk.MenuItem(label="Connect to Wi-Fi ▸")
        submenu = Gtk.Menu()
        self.current_networks = self.get_available_networks()

        if self.current_networks:
            for net in self.current_networks:
                s = net['signal']
                if s >= 75: icon = "●●●"
                elif s >= 50: icon = "●●○"
                elif s >= 25: icon = "●○○"
                else: icon = "○○○"

                label = f"{icon} {net['ssid']} ({net['security']})"
                entry = Gtk.MenuItem(label=label)

                if net['connected']:
                    entry.set_sensitive(False)
                    entry.set_label(f"✓ {net['ssid']} ({net['security']})")
                else:
                    entry.connect("activate", self.connect_to_network, net['ssid'], net['security'])
                submenu.append(entry)
        else:
            none_item = Gtk.MenuItem(label="No networks found")
            none_item.set_sensitive(False)
            submenu.append(none_item)

        submenu.append(Gtk.SeparatorMenuItem())
        hidden_item = Gtk.MenuItem(label="Connect to Hidden Network...")
        hidden_item.connect("activate", self.show_hidden_connect_dialog)
        submenu.append(hidden_item)

        submenu.show_all()
        connect_item.set_submenu(submenu)
        menu.append(connect_item)

        menu.append(Gtk.SeparatorMenuItem())

        info_item = Gtk.MenuItem(label="Connection Information")
        info_item.connect("activate", self.show_connection_info)
        info_item.set_sensitive(connected)
        menu.append(info_item)

        proxy_item = Gtk.MenuItem(label="Proxy Settings")
        proxy_item.connect("activate", self.show_proxy_settings)
        menu.append(proxy_item)

        vpn_item = Gtk.MenuItem(label="VPN Manager")
        vpn_item.connect("activate", self.show_vpn_manager)
        menu.append(vpn_item)

        menu.append(Gtk.SeparatorMenuItem())

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
        self.update_menu()
        return True

    def connect_to_network(self, widget, ssid, security):
        if ssid == self.current_ssid:
            return

        if security == "Open":
            threading.Thread(target=self._connect_thread, args=(ssid, None), daemon=True).start()
        else:
            self.show_password_dialog(ssid, security)

    def show_password_dialog(self, ssid, security):
        dialog = PasswordDialog(None, ssid, security)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            password = dialog.get_password()
            dialog.destroy()
            if password:
                threading.Thread(target=self._connect_thread, args=(ssid, password), daemon=True).start()
        else:
            dialog.destroy()

    def show_proxy_settings(self, widget):
        dialog = ProxyDialog(None)
        dialog.run()
        dialog.destroy()

    def show_vpn_manager(self, *_):
        dialog = VPNManagerDialog(None)
        dialog.run()
        dialog.destroy()

    def show_hidden_connect_dialog(self, widget):
        dialog = HiddenNetworkDialog(None)
        dialog.run()
        dialog.destroy()

    def _connect_thread(self, ssid, password):
        run_nmcli(["connection", "delete", ssid], timeout=2)

        args = ["device", "wifi", "connect", ssid]
        if password:
            args += ["password", password]

        result = run_nmcli(args, timeout=20)

        if result and result.returncode == 0:
            GLib.idle_add(self.show_notification, "Connected", f"Successfully connected to {ssid}", "network-wireless")
            GLib.idle_add(self.update_menu)
        else:
            msg = "Incorrect password" if result and "Secrets" in result.stderr else "Connection failed"
            GLib.idle_add(self.show_notification, "Connection Failed", f"Could not connect to {ssid}: {msg}", "network-wireless-offline")

    def disconnect_current(self, widget):
        if self.current_ssid:
            run_nmcli(["connection", "down", self.current_ssid], timeout=4)
            self.show_notification("Disconnected", f"Disconnected from {self.current_ssid}", "network-wireless-offline")
            GLib.timeout_add(1000, self.update_menu)

    def show_connection_info(self, widget):
        result = run_nmcli(["-t", "-f", "GENERAL,IP4", "device", "show"], timeout=4)
        if not result:
            return

        dialog = Gtk.MessageDialog(
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Network Information"
        )

        info = []
        for line in result.stdout.splitlines()[:20]:
            if any(x in line for x in ["IP4.ADDRESS", "IP4.GATEWAY", "IP4.DNS", "GENERAL.CONNECTION", "GENERAL.STATE"]):
                key, val = line.split(":", 1)
                key = key.replace("GENERAL.", "").replace("IP4.", "")
                info.append(f"{key}: {val}")

        dialog.format_secondary_text("\n".join(info) if info else "No info available")
        dialog.run()
        dialog.destroy()

    def show_notification(self, title, message, icon):
        try:
            n = Notify.Notification.new(title, message, icon)
            n.show()
        except:
            pass
        return False

    def show_window(self, *_):
        if self.window is None or not self.window.get_visible():
            self.window = WifiWindow()
            self.window.connect("delete-event", self.on_window_delete)
            self.window.show_all()
        else:
            self.window.present()

    def on_window_delete(self, widget, event):
        widget.hide()
        return True

    def update_icon(self):
        ssid, connected = self.get_connection_status()

        if connected:
            result = run_nmcli(["-t", "-f", "IN-USE,SIGNAL", "device", "wifi", "list"], timeout=3)
            signal = 0
            if result:
                for line in result.stdout.splitlines():
                    if line.startswith('*'):
                        parts = line.split(':')
                        signal = int(parts[1]) if len(parts) > 1 else 0
                        break

            if signal >= 75:
                icon = "network-wireless-signal-excellent-symbolic"
            elif signal >= 50:
                icon = "network-wireless-signal-good-symbolic"
            elif signal >= 25:
                icon = "network-wireless-signal-ok-symbolic"
            else:
                icon = "network-wireless-signal-weak-symbolic"
        else:
            icon = "network-wireless-offline-symbolic"

        self.indicator.set_icon_full(icon, "")
        return True

    def quit(self, *_):
        if self.window:
            self.window.auto_refresh = False
        Gtk.main_quit()
