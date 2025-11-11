import gi
import threading
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, GLib, Gdk, Notify, AppIndicator3
from assets.utils.debug import HISTORY_FILE
from assets.core.speedtest import SpeedTest
from assets.core.proxies import ProxyManager

class HiddenNetworkDialog(Gtk.Dialog):
    """Dialog for connecting to hidden networks"""
    def __init__(self, parent):
        super().__init__(title="Connect to Hidden Network", parent=parent, modal=True)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Connect", Gtk.ResponseType.OK)
        self.set_default_size(400, 200)
        # popup style
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_keep_above(True)
        self.set_decorated(True)
        self.set_opacity(0.97)
        self.set_resizable(False)
        
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
        # Make it like a "popup"
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_decorated(True)
        self.set_opacity(0.97)
        self.set_resizable(False)

        
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

class ProxyDialog(Gtk.Dialog):
    """Dialog for proxy configuration"""
    def __init__(self, parent):
        super().__init__(title="Proxy Settings", parent=parent, modal=True)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Disable", Gtk.ResponseType.REJECT)
        self.add_button("Test", Gtk.ResponseType.APPLY)
        self.add_button("Apply", Gtk.ResponseType.OK)
        self.set_default_size(550, 450)
        
        # Popup style
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
        
        # Current status with more details
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
        
        # Proxy type selector
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
        
        # Host
        host_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        host_label = Gtk.Label(label="Host:")
        host_label.set_width_chars(15)
        host_box.pack_start(host_label, False, False, 0)
        
        self.host_entry = Gtk.Entry()
        self.host_entry.set_placeholder_text("proxy.example.com or 127.0.0.1")
        host_box.pack_start(self.host_entry, True, True, 0)
        box.pack_start(host_box, False, False, 0)
        
        # Port
        port_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        port_label = Gtk.Label(label="Port:")
        port_label.set_width_chars(15)
        port_box.pack_start(port_label, False, False, 0)
        
        self.port_entry = Gtk.Entry()
        self.port_entry.set_placeholder_text("8080 or 10808")
        self.port_entry.set_width_chars(10)
        port_box.pack_start(self.port_entry, False, False, 0)
        box.pack_start(port_box, False, False, 0)
        
        # Authentication section
        auth_expander = Gtk.Expander(label="Authentication (Optional)")
        auth_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        auth_box.set_margin_start(12)
        auth_box.set_margin_top(6)
        
        # Username
        user_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        user_label = Gtk.Label(label="Username:")
        user_label.set_width_chars(15)
        user_box.pack_start(user_label, False, False, 0)
        
        self.username_entry = Gtk.Entry()
        self.username_entry.set_placeholder_text("Optional")
        user_box.pack_start(self.username_entry, True, True, 0)
        auth_box.pack_start(user_box, False, False, 0)
        
        # Password
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
        
        # Bypass list
        bypass_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bypass_label = Gtk.Label(label="No Proxy For:")
        bypass_label.set_width_chars(15)
        bypass_box.pack_start(bypass_label, False, False, 0)
        
        self.bypass_entry = Gtk.Entry()
        self.bypass_entry.set_text("localhost,127.0.0.1")
        self.bypass_entry.set_placeholder_text("localhost,127.0.0.1")
        bypass_box.pack_start(self.bypass_entry, True, True, 0)
        box.pack_start(bypass_box, False, False, 0)
        
        # Test result area
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
        
        # Info label with instructions
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
        
        # Load current config
        self.load_current_config()
        
        self.connect("response", self.on_response)
        self.show_all()
    
    def update_status_label(self):
        """Update status label with current proxy"""
        if not self.proxy_manager:
            self.status_label.set_markup("<b>Status:</b> ⚠️ Proxy module unavailable")
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
        """Load current proxy configuration"""
        if not self.proxy_manager:
            return
        
        config = self.proxy_manager.get_current_proxy()
        if config.get('enabled'):
            proxy_type = config.get('type', 'http')
            
            # Set combo box
            type_map = {
                'none': 0,
                'http': 1,
                'https': 2,
                'socks5': 3
            }
            
            # Check if it's Tor
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
        """Handle proxy type change"""
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
            
            # Set default ports based on type
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
        """Handle dialog response"""
        if response == Gtk.ResponseType.APPLY:
            # Test proxy
            self.emit_stop_by_name("response")
            self.test_proxy()
            return
        
        if response == Gtk.ResponseType.OK:
            # Apply proxy settings
            self.emit_stop_by_name("response")
            self.apply_proxy()
            return

        if response == Gtk.ResponseType.REJECT:
            # Disable proxy
            self.emit_stop_by_name("response")
            self.type_combo.set_active(0)
            self.apply_proxy()
    
    def test_proxy(self):
        """Test proxy connection"""
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
        """Show test result with enhanced formatting"""
        # Clean up the message to remove internal markers
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
        """Apply proxy settings"""
        if not self.proxy_manager:
            return
        
        active = self.type_combo.get_active()
        
        if active == 0:  # None
            success, msg = self.proxy_manager.disable_proxy()
        else:
            # Get values
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
        
        # Update status
        self.update_status_label()
        
        # Show result with better formatting
        if success:
            # Parse the multi-line message
            lines = msg.split('\n')
            main_msg = lines[0]
            
            markup = f"<span color='#4CAF50' weight='bold'>✓ Applied Successfully</span>\n"
            markup += f"<small>{main_msg}</small>"
            
            # Add any additional info
            if len(lines) > 1:
                for line in lines[1:]:
                    if line.strip():
                        markup += f"\n<small><i>{line.strip()}</i></small>"
            
            self.test_result_label.set_markup(markup)
        else:
            self.show_test_result(False, msg)
        
        self.test_revealer.set_reveal_child(True)
        
        # Auto-close after successful 
        if success:
            def close_later():
                import time
                time.sleep(2)
                GLib.idle_add(self.response, Gtk.ResponseType.CLOSE)
            
            threading.Thread(target=close_later, daemon=True).start()