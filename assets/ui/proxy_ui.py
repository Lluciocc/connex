import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, GLib, Gdk, Notify, AppIndicator3, GdkPixbuf
import subprocess
import threading
from assets.core.proxies import ProxyManager

class ProxyDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="Proxy Settings", parent=parent, modal=True)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Disable", Gtk.ResponseType.REJECT)
        self.add_button("Test", Gtk.ResponseType.APPLY)
        self.add_button("Apply", Gtk.ResponseType.OK)
        self.set_default_size(550, 450)

        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_decorated(True)
        self.set_opacity(0.97)
        self.set_resizable(False)
        
        self.proxy_manager = ProxyManager()
        
        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)

        status_frame = Gtk.Frame(label="Current Status")
        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        status_box.set_margin_start(12)
        status_box.set_margin_end(12)
        status_box.set_margin_top(12)
        status_box.set_margin_bottom(12)
        
        self.status_label = Gtk.Label()
        self.status_label.set_xalign(0)
        self.status_label.set_line_wrap(True)
        self.update_status_label()
        status_box.pack_start(self.status_label, False, False, 0)
        
        status_frame.add(status_box)
        box.pack_start(status_frame, False, False, 0)

        type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        type_label = Gtk.Label(label="Proxy Type:")
        type_label.set_width_chars(15)
        type_box.pack_start(type_label, False, False, 0)
        
        self.type_combo = Gtk.ComboBoxText()
        self.type_combo.append_text("None (Direct)")
        self.type_combo.append_text("HTTP")
        self.type_combo.append_text("HTTPS")
        self.type_combo.append_text("SOCKS5")
        self.type_combo.append_text("Tor (SOCKS5)")
        self.type_combo.set_active(0)
        self.type_combo.connect("changed", self.on_type_changed)
        type_box.pack_start(self.type_combo, True, True, 0)
        
        box.pack_start(type_box, False, False, 0)

        host_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        host_label = Gtk.Label(label="Host:")
        host_label.set_width_chars(15)
        host_box.pack_start(host_label, False, False, 0)
        
        self.host_entry = Gtk.Entry()
        self.host_entry.set_placeholder_text("proxy.example.com or 127.0.0.1")
        host_box.pack_start(self.host_entry, True, True, 0)
        box.pack_start(host_box, False, False, 0)

        port_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        port_label = Gtk.Label(label="Port:")
        port_label.set_width_chars(15)
        port_box.pack_start(port_label, False, False, 0)
        
        self.port_entry = Gtk.Entry()
        self.port_entry.set_placeholder_text("8080 or 10808")
        self.port_entry.set_width_chars(10)
        port_box.pack_start(self.port_entry, False, False, 0)
        box.pack_start(port_box, False, False, 0)

        auth_expander = Gtk.Expander(label="Authentication (Optional)")
        auth_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        auth_box.set_margin_start(12)
        auth_box.set_margin_top(6)

        user_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        user_label = Gtk.Label(label="Username:")
        user_label.set_width_chars(15)
        user_box.pack_start(user_label, False, False, 0)
        
        self.username_entry = Gtk.Entry()
        self.username_entry.set_placeholder_text("Optional")
        user_box.pack_start(self.username_entry, True, True, 0)
        auth_box.pack_start(user_box, False, False, 0)

        pass_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pass_label = Gtk.Label(label="Password:")
        pass_label.set_width_chars(15)
        pass_box.pack_start(pass_label, False, False, 0)
        
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_placeholder_text("Optional")
        pass_box.pack_start(self.password_entry, True, True, 0)
        auth_box.pack_start(pass_box, False, False, 0)
        
        auth_expander.add(auth_box)
        box.pack_start(auth_expander, False, False, 0)

        bypass_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bypass_label = Gtk.Label(label="No Proxy For:")
        bypass_label.set_width_chars(15)
        bypass_box.pack_start(bypass_label, False, False, 0)
        
        self.bypass_entry = Gtk.Entry()
        self.bypass_entry.set_text("localhost,127.0.0.1")
        self.bypass_entry.set_placeholder_text("localhost,127.0.0.1")
        bypass_box.pack_start(self.bypass_entry, True, True, 0)
        box.pack_start(bypass_box, False, False, 0)

        self.test_revealer = Gtk.Revealer()
        self.test_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        
        result_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        result_box.set_margin_top(6)
        
        self.test_result_label = Gtk.Label()
        self.test_result_label.set_xalign(0)
        self.test_result_label.set_line_wrap(True)
        self.test_result_label.set_selectable(True)
        result_box.pack_start(self.test_result_label, False, False, 0)
        
        self.test_revealer.add(result_box)
        box.pack_start(self.test_revealer, False, False, 0)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        
        info1 = Gtk.Label()
        info1.set_markup("<small><b>Note:</b> Proxy settings apply system-wide</small>")
        info1.set_xalign(0)
        info_box.pack_start(info1, False, False, 0)
        
        info2 = Gtk.Label()
        info2.set_markup("<small><i>• Changes take effect immediately for GNOME apps</i></small>")
        info2.set_xalign(0)
        info_box.pack_start(info2, False, False, 0)
        
        info3 = Gtk.Label()
        info3.set_markup("<small><i>• Terminal apps: restart or re-login required</i></small>")
        info3.set_xalign(0)
        info_box.pack_start(info3, False, False, 0)
        
        box.pack_start(info_box, False, False, 0)

        self.load_current_config()
        
        self.connect("response", self.on_response)
        self.show_all()
    
    def update_status_label(self):
        if not self.proxy_manager:
            self.status_label.set_markup("<b>Status:</b> ✗ Proxy module unavailable")
            return
        
        status = self.proxy_manager.get_status_text()
        config = self.proxy_manager.get_current_proxy()
        
        if "No proxy" in status or not config.get('enabled'):
            markup = f"<b>Status:</b> <span color='orange'>✗ No proxy configured</span>\n"
            markup += "<small>Using direct connection</small>"
            self.status_label.set_markup(markup)
        else:
            proxy_type = config.get('type', 'unknown').upper()
            host = config.get('host', '')
            port = config.get('port', '')
            
            markup = f"<b>Status:</b> <span color='green'>✓ Proxy Active</span>\n"
            markup += f"<small>{proxy_type} → {host}:{port}</small>"
            
            if config.get('username'):
                markup += f"\n<small>Username: {config.get('username')}</small>"
            
            self.status_label.set_markup(markup)
    
    def load_current_config(self):
        if not self.proxy_manager:
            return
        
        config = self.proxy_manager.get_current_proxy()
        if config.get('enabled'):
            proxy_type = config.get('type', 'http')

            type_map = {
                'none': 0,
                'http': 1,
                'https': 2,
                'socks5': 3
            }
            
            # check if it's Tor
            if proxy_type == 'socks5' and config.get('host') == '127.0.0.1' and config.get('port') == '9050':
                self.type_combo.set_active(4)  # Tor
            else:
                self.type_combo.set_active(type_map.get(proxy_type, 0))
            
            self.host_entry.set_text(config.get('host', ''))
            self.port_entry.set_text(str(config.get('port', '')))
            self.username_entry.set_text(config.get('username', ''))
            self.password_entry.set_text(config.get('password', ''))
            self.bypass_entry.set_text(config.get('bypass', 'localhost,127.0.0.1'))
    
    def on_type_changed(self, combo):
        active = combo.get_active()
        
        if active == 0:  # None
            self.host_entry.set_sensitive(False)
            self.port_entry.set_sensitive(False)
            self.username_entry.set_sensitive(False)
            self.password_entry.set_sensitive(False)
            self.bypass_entry.set_sensitive(False)
        elif active == 4:  # Tor
            self.host_entry.set_text("127.0.0.1")
            self.port_entry.set_text("9050")
            self.host_entry.set_sensitive(False)
            self.port_entry.set_sensitive(False)
            self.username_entry.set_sensitive(False)
            self.password_entry.set_sensitive(False)
            self.bypass_entry.set_sensitive(True)
        else:
            self.host_entry.set_sensitive(True)
            self.port_entry.set_sensitive(True)
            self.username_entry.set_sensitive(True)
            self.password_entry.set_sensitive(True)
            self.bypass_entry.set_sensitive(True)

            if active == 1:  # HTTP
                if not self.port_entry.get_text():
                    self.port_entry.set_text("8080")
            elif active == 2:  # HTTPS
                if not self.port_entry.get_text():
                    self.port_entry.set_text("10808")  # Common HTTPS proxy port
            elif active == 3:  # SOCKS5
                if not self.port_entry.get_text():
                    self.port_entry.set_text("1080")
    
    def on_response(self, dialog, response):
        if response == Gtk.ResponseType.APPLY:
            self.emit_stop_by_name("response")
            self.test_proxy()
            return
        
        if response == Gtk.ResponseType.OK:
            self.emit_stop_by_name("response")
            self.apply_proxy()
            return

        if response == Gtk.ResponseType.REJECT:
            self.emit_stop_by_name("response")
            self.type_combo.set_active(0)
            self.apply_proxy()
    
    def test_proxy(self):
        if not self.proxy_manager:
            self.show_test_result(False, "Proxy module unavailable")
            return
        
        host = self.host_entry.get_text().strip()
        port = self.port_entry.get_text().strip()
        
        if not host or not port:
            self.show_test_result(False, "Please enter host and port")
            return
        
        self.test_result_label.set_markup("<i>⏳ Testing connection...</i>")
        self.test_revealer.set_reveal_child(True)
        
        def test_thread():
            success, msg = self.proxy_manager.test_proxy(host, port)
            GLib.idle_add(self.show_test_result, success, msg)
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def show_test_result(self, success, message):
        clean_msg = message.replace("✓ ", "").replace("✗ ", "")
        
        if success:
            markup = f"<span color='#4CAF50' weight='bold'>✓ Success</span>\n"
            markup += f"<small>{clean_msg}</small>"
        else:
            markup = f"<span color='#F44336' weight='bold'>✗ Failed</span>\n"
            markup += f"<small>{clean_msg}</small>"
        
        self.test_result_label.set_markup(markup)
        self.test_revealer.set_reveal_child(True)
        return False
    
    def apply_proxy(self):
        if not self.proxy_manager:
            return
        
        active = self.type_combo.get_active()
        
        if active == 0:  # None
            success, msg = self.proxy_manager.disable_proxy()
        else:
            type_map = {
                1: 'http',
                2: 'https',
                3: 'socks5',
                4: 'socks5'  # Tor
            }
            
            proxy_type = type_map.get(active, 'http')
            host = self.host_entry.get_text().strip()
            port = self.port_entry.get_text().strip()
            username = self.username_entry.get_text().strip()
            password = self.password_entry.get_text().strip()
            bypass = self.bypass_entry.get_text().strip()
            
            if not host or not port:
                self.show_test_result(False, "Host and port are required")
                return
            
            success, msg = self.proxy_manager.set_proxy(
                proxy_type, host, port, username, password, bypass
            )
        
        self.update_status_label()
        
        if success:
            lines = msg.split('\n')
            main_msg = lines[0]
            
            markup = f"<span color='#4CAF50' weight='bold'>✓ Applied Successfully</span>\n"
            markup += f"<small>{main_msg}</small>"

            if len(lines) > 1:
                for line in lines[1:]:
                    if line.strip():
                        markup += f"\n<small><i>{line.strip()}</i></small>"
            
            self.test_result_label.set_markup(markup)
        else:
            self.show_test_result(False, msg)
        
        self.test_revealer.set_reveal_child(True)

        if success:
            def close_later():
                import time
                time.sleep(2)
                GLib.idle_add(self.response, Gtk.ResponseType.CLOSE)
            
            threading.Thread(target=close_later, daemon=True).start()

