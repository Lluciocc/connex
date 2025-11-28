import gi
import threading
import webbrowser
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, GLib, Gdk, Notify, AppIndicator3, GdkPixbuf
from assets.utils.debug import HISTORY_FILE
from assets.core.speedtest import SpeedTest
from assets.core.proxies import ProxyManager
from assets.core.vpn_manager import VPNManager
try:
    import qrcode
    from PIL import Image
    from io import BytesIO
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

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

class QRCodeDialog(Gtk.Dialog):
    """Dialog to display WiFi QR code"""
    def __init__(self, parent, ssid, password, security):
        super().__init__(title=f"QR Code - {ssid}", parent=parent, modal=True)
        self.add_button("Save Image", Gtk.ResponseType.APPLY)
        self.add_button("Close", Gtk.ResponseType.CLOSE)
        self.set_default_size(450, 550)
        
        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        
        # Title
        title = Gtk.Label()
        title.set_markup(f"<b>Scan to connect to:</b>\n{ssid}")
        title.set_xalign(0.5)
        box.pack_start(title, False, False, 0)
        
        # Generate QR code
        qr_data = self.generate_wifi_qr_data(ssid, password, security)
        qr_image = self.create_qr_image(qr_data)
        
        # Display QR code
        self.qr_pixbuf = self.pil_to_pixbuf(qr_image)
        qr_gtk_image = Gtk.Image.new_from_pixbuf(self.qr_pixbuf)
        
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.IN)
        frame.add(qr_gtk_image)
        box.pack_start(frame, True, True, 0)
        
        # Info label
        info = Gtk.Label()
        security_text = "Open Network" if security == "Open" else f"Security: {security}"
        info.set_markup(f"<small>{security_text}</small>")
        info.set_xalign(0.5)
        box.pack_start(info, False, False, 0)
        
        # Instructions
        instructions = Gtk.Label()
        instructions.set_markup(
            "<small><i>Scan this QR code with your phone's camera\n"
            "to connect automatically</i></small>"
        )
        instructions.set_xalign(0.5)
        instructions.set_line_wrap(True)
        box.pack_start(instructions, False, False, 0)
        
        self.ssid = ssid
        self.qr_image = qr_image
        
        self.connect("response", self.on_response)
        self.show_all()
    
    def generate_wifi_qr_data(self, ssid, password, security):
        """Generate WiFi QR code data string"""
        # Escape special characters
        ssid_escaped = ssid.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace(":", "\\:")
        password_escaped = password.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace(":", "\\:")
        
        # https://qrcode-library.readthedocs.io/en/stable/formats/wifi/
        if security == "Open" or not password:
            auth_type = "nopass"
            qr_string = f"WIFI:T:{auth_type};S:{ssid_escaped};;"
        else:
            if "WEP" in security.upper():
                auth_type = "WEP"
            else:
                auth_type = "WPA"
            qr_string = f"WIFI:T:{auth_type};S:{ssid_escaped};P:{password_escaped};;"
        
        return qr_string
    
    def create_qr_image(self, data):
        """Create QR code image"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        return img
    
    def pil_to_pixbuf(self, pil_image):
        """Convert PIL Image to GdkPixbuf"""
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Save to bytes
        buffer = BytesIO()
        pil_image.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Load into pixbuf
        loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        loader.write(buffer.read())
        loader.close()
        
        return loader.get_pixbuf()
    
    def on_response(self, dialog, response):
        """Handle dialog response"""
        if response == Gtk.ResponseType.APPLY:
            # Save QR code
            file_dialog = Gtk.FileChooserDialog(
                title="Save QR Code",
                parent=self,
                action=Gtk.FileChooserAction.SAVE
            )
            file_dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            file_dialog.add_button("Save", Gtk.ResponseType.OK)
            file_dialog.set_current_name(f"wifi_qr_{self.ssid}.png")
            
            # Add filter for PNG
            filter_png = Gtk.FileFilter()
            filter_png.set_name("PNG images")
            filter_png.add_mime_type("image/png")
            file_dialog.add_filter(filter_png)
            
            response = file_dialog.run()
            if response == Gtk.ResponseType.OK:
                filename = file_dialog.get_filename()
                if not filename.endswith('.png'):
                    filename += '.png'
                try:
                    self.qr_image.save(filename)
                    notification = Notify.Notification.new(
                        "QR Code Saved",
                        f"Saved to {filename}",
                        "document-save"
                    )
                    notification.show()
                except Exception as e:
                    error_dialog = Gtk.MessageDialog(
                        parent=self,
                        modal=True,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text="Save Failed"
                    )
                    error_dialog.format_secondary_text(str(e))
                    error_dialog.run()
                    error_dialog.destroy()
            
            file_dialog.destroy()

class AddVPNDialog(Gtk.Dialog):
    
    VPN_TYPES = [
        ("OpenVPN", "openvpn"),
        ("WireGuard", "wireguard"),
        ("L2TP/IPsec", "l2tp"),
        ("PPTP", "pptp"),
        ("Import from file", "import")
    ]
    
    def __init__(self, parent):
        super().__init__(title="Add VPN Connection", parent=parent, modal=True)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Next", Gtk.ResponseType.OK)
        self.set_default_size(500, 400)
        
        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        
        # Title
        title = Gtk.Label()
        title.set_markup("<b>Choose VPN Type</b>")
        title.set_xalign(0)
        box.pack_start(title, False, False, 0)
        
        # VPN type selection
        self.vpn_type_combo = Gtk.ComboBoxText()
        for display_name, _ in self.VPN_TYPES:
            self.vpn_type_combo.append_text(display_name)
        self.vpn_type_combo.set_active(0)
        self.vpn_type_combo.connect("changed", self.on_type_changed)
        
        type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        type_label = Gtk.Label(label="VPN Type:")
        type_label.set_width_chars(15)
        type_box.pack_start(type_label, False, False, 0)
        type_box.pack_start(self.vpn_type_combo, True, True, 0)
        box.pack_start(type_box, False, False, 0)
        
        # Stack for different config types
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(200)
        
        # OpenVPN config
        self.openvpn_box = self.create_openvpn_config()
        self.stack.add_named(self.openvpn_box, "openvpn")
        
        # WireGuard config
        self.wireguard_box = self.create_wireguard_config()
        self.stack.add_named(self.wireguard_box, "wireguard")
        
        # Import config
        self.import_box = self.create_import_config()
        self.stack.add_named(self.import_box, "import")
        
        # Generic config (L2TP, PPTP)
        self.generic_box = self.create_generic_config()
        self.stack.add_named(self.generic_box, "generic")
        
        box.pack_start(self.stack, True, True, 0)
        
        self.show_all()
    
    def create_openvpn_config(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        # Connection name
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="Connection Name:")
        name_label.set_width_chars(18)
        self.openvpn_name = Gtk.Entry()
        self.openvpn_name.set_placeholder_text("My VPN")
        name_box.pack_start(name_label, False, False, 0)
        name_box.pack_start(self.openvpn_name, True, True, 0)
        box.pack_start(name_box, False, False, 0)
        
        # Gateway/Server
        gateway_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        gateway_label = Gtk.Label(label="Gateway:")
        gateway_label.set_width_chars(18)
        self.openvpn_gateway = Gtk.Entry()
        self.openvpn_gateway.set_placeholder_text("vpn.example.com")
        gateway_box.pack_start(gateway_label, False, False, 0)
        gateway_box.pack_start(self.openvpn_gateway, True, True, 0)
        box.pack_start(gateway_box, False, False, 0)
        
        # Username
        user_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        user_label = Gtk.Label(label="Username:")
        user_label.set_width_chars(18)
        self.openvpn_user = Gtk.Entry()
        self.openvpn_user.set_placeholder_text("Optional")
        user_box.pack_start(user_label, False, False, 0)
        user_box.pack_start(self.openvpn_user, True, True, 0)
        box.pack_start(user_box, False, False, 0)
        
        # Password
        pass_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pass_label = Gtk.Label(label="Password:")
        pass_label.set_width_chars(18)
        self.openvpn_pass = Gtk.Entry()
        self.openvpn_pass.set_visibility(False)
        self.openvpn_pass.set_placeholder_text("Optional")
        pass_box.pack_start(pass_label, False, False, 0)
        pass_box.pack_start(self.openvpn_pass, True, True, 0)
        box.pack_start(pass_box, False, False, 0)
        
        # Info
        info = Gtk.Label()
        info.set_markup("<small><i>For advanced OpenVPN configs, use 'Import from file'</i></small>")
        info.set_xalign(0)
        box.pack_start(info, False, False, 0)
        
        return box
    
    def create_wireguard_config(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        # Connection name
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="Connection Name:")
        name_label.set_width_chars(18)
        self.wg_name = Gtk.Entry()
        self.wg_name.set_placeholder_text("My WireGuard")
        name_box.pack_start(name_label, False, False, 0)
        name_box.pack_start(self.wg_name, True, True, 0)
        box.pack_start(name_box, False, False, 0)
        
        # Private key
        key_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        key_label = Gtk.Label(label="Private Key:")
        key_label.set_width_chars(18)
        self.wg_private_key = Gtk.Entry()
        self.wg_private_key.set_visibility(False)
        self.wg_private_key.set_placeholder_text("base64 encoded key")
        key_box.pack_start(key_label, False, False, 0)
        key_box.pack_start(self.wg_private_key, True, True, 0)
        box.pack_start(key_box, False, False, 0)
        
        # Address
        addr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        addr_label = Gtk.Label(label="IP Address:")
        addr_label.set_width_chars(18)
        self.wg_address = Gtk.Entry()
        self.wg_address.set_placeholder_text("10.0.0.2/24")
        addr_box.pack_start(addr_label, False, False, 0)
        addr_box.pack_start(self.wg_address, True, True, 0)
        box.pack_start(addr_box, False, False, 0)
        
        # Peer public key
        peer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        peer_label = Gtk.Label(label="Peer Public Key:")
        peer_label.set_width_chars(18)
        self.wg_peer = Gtk.Entry()
        self.wg_peer.set_placeholder_text("Server public key")
        peer_box.pack_start(peer_label, False, False, 0)
        peer_box.pack_start(self.wg_peer, True, True, 0)
        box.pack_start(peer_box, False, False, 0)
        
        # Endpoint
        endpoint_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        endpoint_label = Gtk.Label(label="Endpoint:")
        endpoint_label.set_width_chars(18)
        self.wg_endpoint = Gtk.Entry()
        self.wg_endpoint.set_placeholder_text("server.com:51820")
        endpoint_box.pack_start(endpoint_label, False, False, 0)
        endpoint_box.pack_start(self.wg_endpoint, True, True, 0)
        box.pack_start(endpoint_box, False, False, 0)
        
        return box
    
    def create_import_config(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        info = Gtk.Label()
        info.set_markup("<b>Import VPN Configuration</b>\n\n"
                       "Supported formats:\n"
                       "• OpenVPN (.ovpn, .conf)\n"
                       "• WireGuard (.conf)")
        info.set_xalign(0)
        box.pack_start(info, False, False, 0)
        
        # File chooser
        self.file_chooser = Gtk.FileChooserButton(title="Select VPN Config")
        self.file_chooser.set_action(Gtk.FileChooserAction.OPEN)
        
        # Add filters
        filter_ovpn = Gtk.FileFilter()
        filter_ovpn.set_name("OpenVPN configs")
        filter_ovpn.add_pattern("*.ovpn")
        filter_ovpn.add_pattern("*.conf")
        self.file_chooser.add_filter(filter_ovpn)
        
        filter_all = Gtk.FileFilter()
        filter_all.set_name("All files")
        filter_all.add_pattern("*")
        self.file_chooser.add_filter(filter_all)
        
        box.pack_start(self.file_chooser, False, False, 0)
        
        # Connection name
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="Connection Name:")
        name_label.set_width_chars(18)
        self.import_name = Gtk.Entry()
        self.import_name.set_placeholder_text("Optional")
        name_box.pack_start(name_label, False, False, 0)
        name_box.pack_start(self.import_name, True, True, 0)
        box.pack_start(name_box, False, False, 0)
        
        return box
    
    def create_generic_config(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        # Connection name
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="Connection Name:")
        name_label.set_width_chars(18)
        self.generic_name = Gtk.Entry()
        name_box.pack_start(name_label, False, False, 0)
        name_box.pack_start(self.generic_name, True, True, 0)
        box.pack_start(name_box, False, False, 0)
        
        # Gateway
        gateway_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        gateway_label = Gtk.Label(label="Gateway:")
        gateway_label.set_width_chars(18)
        self.generic_gateway = Gtk.Entry()
        gateway_box.pack_start(gateway_label, False, False, 0)
        gateway_box.pack_start(self.generic_gateway, True, True, 0)
        box.pack_start(gateway_box, False, False, 0)
        
        # Username
        user_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        user_label = Gtk.Label(label="Username:")
        user_label.set_width_chars(18)
        self.generic_user = Gtk.Entry()
        user_box.pack_start(user_label, False, False, 0)
        user_box.pack_start(self.generic_user, True, True, 0)
        box.pack_start(user_box, False, False, 0)
        
        # Password
        pass_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pass_label = Gtk.Label(label="Password:")
        pass_label.set_width_chars(18)
        self.generic_pass = Gtk.Entry()
        self.generic_pass.set_visibility(False)
        pass_box.pack_start(pass_label, False, False, 0)
        pass_box.pack_start(self.generic_pass, True, True, 0)
        box.pack_start(pass_box, False, False, 0)
        
        return box
    
    def on_type_changed(self, combo):
        index = combo.get_active()
        if index < 0:
            return
        
        _, vpn_type = self.VPN_TYPES[index]
        
        if vpn_type == "openvpn":
            self.stack.set_visible_child_name("openvpn")
        elif vpn_type == "wireguard":
            self.stack.set_visible_child_name("wireguard")
        elif vpn_type == "import":
            self.stack.set_visible_child_name("import")
        else:
            self.stack.set_visible_child_name("generic")
    
    def get_config(self):
        index = self.vpn_type_combo.get_active()
        _, vpn_type = self.VPN_TYPES[index]
        
        if vpn_type == "import":
            filename = self.file_chooser.get_filename()
            return {
                'type': 'import',
                'file': filename,
                'name': self.import_name.get_text()
            }
        elif vpn_type == "wireguard":
            return {
                'type': 'wireguard',
                'name': self.wg_name.get_text(),
                'private_key': self.wg_private_key.get_text(),
                'address': self.wg_address.get_text(),
                'peer': self.wg_peer.get_text(),
                'endpoint': self.wg_endpoint.get_text()
            }
        elif vpn_type == "openvpn":
            return {
                'type': 'openvpn',
                'name': self.openvpn_name.get_text(),
                'gateway': self.openvpn_gateway.get_text(),
                'username': self.openvpn_user.get_text(),
                'password': self.openvpn_pass.get_text()
            }
        else:
            return {
                'type': vpn_type,
                'name': self.generic_name.get_text(),
                'gateway': self.generic_gateway.get_text(),
                'username': self.generic_user.get_text(),
                'password': self.generic_pass.get_text()
            }

class VPNDetailsDialog(Gtk.Dialog):
    def __init__(self, parent, vpn_name, details, status):
        super().__init__(title=f"VPN Details - {vpn_name}", parent=parent, modal=True)
        self.add_button("Close", Gtk.ResponseType.CLOSE)
        self.set_default_size(500, 450)
        
        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        
        # Title
        title = Gtk.Label()
        title.set_markup(f"<b>{vpn_name}</b>")
        title.set_xalign(0)
        box.pack_start(title, False, False, 0)
        
        # Status
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_icon = Gtk.Image()
        if status['connected']:
            status_icon.set_from_icon_name("network-vpn-symbolic", Gtk.IconSize.BUTTON)
            status_text = f"<span color='green'>● Connected</span>"
        else:
            status_icon.set_from_icon_name("network-vpn-offline-symbolic", Gtk.IconSize.BUTTON)
            status_text = "○ Disconnected"
        
        status_label = Gtk.Label()
        status_label.set_markup(status_text)
        status_box.pack_start(status_icon, False, False, 0)
        status_box.pack_start(status_label, False, False, 0)
        box.pack_start(status_box, False, False, 0)
        
        # Details notebook
        notebook = Gtk.Notebook()
        
        # Connection tab
        conn_scroll = Gtk.ScrolledWindow()
        conn_text = Gtk.TextView()
        conn_text.set_editable(False)
        conn_text.set_monospace(True)
        conn_text.set_wrap_mode(Gtk.WrapMode.WORD)
        
        conn_buffer = conn_text.get_buffer()
        conn_info = []
        
        if status['connected']:
            if status['ip']:
                conn_info.append(f"IP Address: {status['ip']}")
            if status['gateway']:
                conn_info.append(f"Gateway: {status['gateway']}")
            if status['dns']:
                conn_info.append(f"DNS Servers: {', '.join(status['dns'])}")
        else:
            conn_info.append("Not connected")
        
        conn_buffer.set_text("\n".join(conn_info))
        conn_scroll.add(conn_text)
        notebook.append_page(conn_scroll, Gtk.Label(label="Status"))
        
        # Configuration tab
        config_scroll = Gtk.ScrolledWindow()
        config_text = Gtk.TextView()
        config_text.set_editable(False)
        config_text.set_monospace(True)
        config_text.set_wrap_mode(Gtk.WrapMode.WORD)
        
        config_buffer = config_text.get_buffer()
        config_lines = []
        for key, val in details.items():
            if val and val != '--':
                config_lines.append(f"{key}: {val}")
        
        config_buffer.set_text("\n".join(config_lines) if config_lines else "No configuration available")
        config_scroll.add(config_text)
        notebook.append_page(config_scroll, Gtk.Label(label="Configuration"))
        
        box.pack_start(notebook, True, True, 0)
        
        self.show_all()

class VPNManagerDialog(Gtk.Dialog):    
    def __init__(self, parent):
        super().__init__(title="VPN Manager", parent=parent, modal=True)
        self.add_button("Close", Gtk.ResponseType.CLOSE)
        self.set_default_size(400, 300)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_keep_above(True)
        self.set_decorated(True)
        self.set_opacity(0.97)
        self.set_resizable(False)
        
        # Add action buttons in header
        add_button = self.add_button("Add VPN", Gtk.ResponseType.NONE)
        add_button.connect("clicked", self.on_add_vpn)
        add_button.get_style_context().add_class("suggested-action")
        
        box = self.get_content_area()
        box.set_spacing(0)
        
        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.set_margin_start(12)
        toolbar.set_margin_end(12)
        toolbar.set_margin_top(12)
        toolbar.set_margin_bottom(6)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup("<b>VPN Connections</b>")
        title_label.set_xalign(0)
        toolbar.pack_start(title_label, True, True, 0)
        
        # Refresh button
        refresh_button = Gtk.Button()
        refresh_icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        refresh_button.set_image(refresh_icon)
        refresh_button.set_tooltip_text("Refresh")
        refresh_button.connect("clicked", lambda x: self.load_vpn_list())
        refresh_button.set_relief(Gtk.ReliefStyle.NONE)
        toolbar.pack_end(refresh_button, False, False, 0)
        
        box.pack_start(toolbar, False, False, 0)
        
        # Status bar
        self.status_revealer = Gtk.Revealer()
        self.status_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.status_revealer.set_transition_duration(200)
        
        self.status_bar = Gtk.InfoBar()
        self.status_bar.set_message_type(Gtk.MessageType.INFO)
        self.status_label = Gtk.Label(label="Ready")
        status_content = self.status_bar.get_content_area()
        status_content.add(self.status_label)
        self.status_bar.set_show_close_button(True)
        self.status_bar.connect("response", lambda x, y: self.status_revealer.set_reveal_child(False))
        
        self.status_revealer.add(self.status_bar)
        self.status_revealer.set_reveal_child(False)
        box.pack_start(self.status_revealer, False, False, 0)
        
        # VPN list
        self.store = Gtk.ListStore(str, str, str, str, bool)  # Name, Type, UUID, Status, Connected
        
        tree = Gtk.TreeView(model=self.store)
        tree.set_headers_visible(True)
        tree.set_enable_search(True)
        tree.set_search_column(0)
        
        # Status icon column
        icon_renderer = Gtk.CellRendererPixbuf()
        icon_column = Gtk.TreeViewColumn("", icon_renderer)
        icon_column.set_cell_data_func(icon_renderer, self.status_icon_func)
        icon_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        icon_column.set_fixed_width(40)
        tree.append_column(icon_column)
        
        # Name column
        name_renderer = Gtk.CellRendererText()
        name_renderer.set_property("ellipsize", 3)
        name_column = Gtk.TreeViewColumn("VPN Name", name_renderer, text=0)
        name_column.set_expand(True)
        name_column.set_sort_column_id(0)
        tree.append_column(name_column)
        
        # Type column
        type_renderer = Gtk.CellRendererText()
        type_column = Gtk.TreeViewColumn("Type", type_renderer, text=1)
        type_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        type_column.set_fixed_width(120)
        tree.append_column(type_column)
        
        # Status column with markup
        status_renderer = Gtk.CellRendererText()
        status_column = Gtk.TreeViewColumn("Status", status_renderer)
        status_column.set_cell_data_func(status_renderer, self.status_text_func)
        status_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        status_column.set_fixed_width(120)
        tree.append_column(status_column)
        
        tree.connect("row-activated", self.on_row_activated)
        tree.connect("button-press-event", self.on_tree_button_press)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_margin_start(12)
        scroll.set_margin_end(12)
        scroll.set_margin_bottom(12)
        scroll.set_margin_top(6)
        scroll.add(tree)
        
        box.pack_start(scroll, True, True, 0)
        
        self.tree = tree
        self.manager = VPNManager()
        
        # Empty state
        self.empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.empty_box.set_valign(Gtk.Align.CENTER)
        self.empty_box.set_margin_top(40)
        self.empty_box.set_margin_bottom(40)
        
        empty_icon = Gtk.Image.new_from_icon_name("network-vpn-symbolic", Gtk.IconSize.DIALOG)
        empty_icon.set_pixel_size(64)
        self.empty_box.pack_start(empty_icon, False, False, 0)
        
        empty_label = Gtk.Label()
        empty_label.set_markup("<big><b>No VPN Connections</b></big>\n\n"
                              "Click 'Add VPN' to create your first connection")
        empty_label.set_justify(Gtk.Justification.CENTER)
        self.empty_box.pack_start(empty_label, False, False, 0)
        
        scroll.add_with_viewport(self.empty_box)
        self.empty_box.hide()
        
        self.show_all()
        
        # Load VPN list
        GLib.idle_add(self.load_vpn_list)
        
        self.connect("response", self.on_dialog_response)
        
        self.auto_refresh_id = GLib.timeout_add_seconds(8, self.auto_refresh_vpns)
    
    def status_icon_func(self, column, cell, model, iter, data):
        """Display status icon"""
        connected = model.get_value(iter, 4)
        
        if connected:
            cell.set_property("icon-name", "network-vpn-symbolic")
        else:
            cell.set_property("icon-name", "network-vpn-offline-symbolic")
    
    def status_text_func(self, column, cell, model, iter, data):
        connected = model.get_value(iter, 4)
        
        if connected:
            cell.set_property("markup", "<span color='green'>● Connected</span>")
        else:
            cell.set_property("text", "○ Disconnected")
    
    def set_status(self, message, message_type=Gtk.MessageType.INFO):
        """Set status bar message"""
        self.status_label.set_text(message)
        self.status_bar.set_message_type(message_type)
        self.status_revealer.set_reveal_child(True)
        
        # Auto-hide after 4 seconds for info messages
        if message_type == Gtk.MessageType.INFO:
            GLib.timeout_add_seconds(4, lambda: self.status_revealer.set_reveal_child(False))
    
    def load_vpn_list(self):
        def load_thread():
            vpns = self.manager.get_vpn_list()
            active_vpn = self.manager.get_active_vpn()
            GLib.idle_add(self.update_vpn_list, vpns, active_vpn)
        
        threading.Thread(target=load_thread, daemon=True).start()
        return False
    
    def update_vpn_list(self, vpns, active_vpn):
        self.store.clear()
        
        if not vpns:
            self.tree.hide()
            self.empty_box.show_all()
            self.set_status("No VPN connections configured", Gtk.MessageType.INFO)
            return False
        
        self.empty_box.hide()
        self.tree.show()
        
        for vpn in vpns:
            connected = (vpn['name'] == active_vpn)
            
            # Format type
            vpn_type = vpn['type']
            if 'wireguard' in vpn_type.lower():
                type_display = "WireGuard"
            elif 'openvpn' in vpn_type.lower():
                type_display = "OpenVPN"
            elif 'l2tp' in vpn_type.lower():
                type_display = "L2TP/IPsec"
            elif 'pptp' in vpn_type.lower():
                type_display = "PPTP"
            else:
                type_display = vpn_type
            
            status_text = "Connected" if connected else "Disconnected"
            
            self.store.append([
                vpn['name'],
                type_display,
                vpn['uuid'],
                status_text,
                connected
            ])
        
        count = len(vpns)
        connected_count = sum(1 for vpn in vpns if vpn['name'] == active_vpn)
        
        if connected_count > 0:
            self.set_status(f"{count} VPN{'s' if count != 1 else ''} ({connected_count} connected)")
        else:
            self.set_status(f"{count} VPN connection{'s' if count != 1 else ''}")
        
        return False
    
    def auto_refresh_vpns(self):
        if self.get_visible():
            self.load_vpn_list()
            return True
        return False
    
    def on_row_activated(self, tree, path, col):
        model = tree.get_model()
        vpn_name = model[path][0]
        connected = model[path][4]
        
        if connected:
            response = self.show_question(
                f"Disconnect from {vpn_name}?",
                "This will terminate your VPN connection."
            )
            if response == Gtk.ResponseType.YES:
                self.disconnect_vpn(vpn_name)
        else:
            self.connect_vpn(vpn_name)
    
    def connect_vpn(self, name):
        self.set_status(f"Connecting to {name}...", Gtk.MessageType.INFO)
        
        def connect_thread():
            success, message = self.manager.connect_vpn(name)
            GLib.idle_add(self.on_connect_done, success, name, message)
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def on_connect_done(self, success, name, message):
        if success:
            self.set_status(f"✓ Connected to {name}", Gtk.MessageType.INFO)
            
            notification = Notify.Notification.new(
                "VPN Connected",
                f"Successfully connected to {name}",
                "network-vpn"
            )
            notification.show()
        else:
            self.set_status(f"✗ Connection failed: {message}", Gtk.MessageType.ERROR)
            
            notification = Notify.Notification.new(
                "VPN Connection Failed",
                f"Could not connect to {name}",
                "network-vpn-offline"
            )
            notification.show()
        
        GLib.timeout_add(1000, self.load_vpn_list)
        return False
    
    def disconnect_vpn(self, name):
        self.set_status(f"Disconnecting from {name}...", Gtk.MessageType.INFO)
        
        def disconnect_thread():
            success, message = self.manager.disconnect_vpn(name)
            GLib.idle_add(self.on_disconnect_done, success, name, message)
        
        threading.Thread(target=disconnect_thread, daemon=True).start()
    
    def on_disconnect_done(self, success, name, message):
        if success:
            self.set_status(f"✓ Disconnected from {name}", Gtk.MessageType.INFO)
            
            notification = Notify.Notification.new(
                "VPN Disconnected",
                f"Disconnected from {name}",
                "network-vpn-offline"
            )
            notification.show()
        else:
            self.set_status(f"✗ {message}", Gtk.MessageType.ERROR)
        
        GLib.timeout_add(1000, self.load_vpn_list)
        return False
    
    def on_tree_button_press(self, widget, event):
        if event.button == 3:  # right click
            path = widget.get_path_at_pos(int(event.x), int(event.y))
            if path:
                widget.set_cursor(path[0])
                self.show_context_menu(widget, event, path[0])
            return True
        return False
    
    def show_context_menu(self, widget, event, path):
        model = widget.get_model()
        vpn_name = model[path][0]
        connected = model[path][4]
        
        menu = Gtk.Menu()
        
        if connected:
            disconnect_item = Gtk.MenuItem(label="Disconnect")
            disconnect_item.connect("activate", lambda x: self.disconnect_vpn(vpn_name))
            menu.append(disconnect_item)
        else:
            connect_item = Gtk.MenuItem(label="Connect")
            connect_item.connect("activate", lambda x: self.connect_vpn(vpn_name))
            menu.append(connect_item)
        
        menu.append(Gtk.SeparatorMenuItem())
        
        details_item = Gtk.MenuItem(label="View Details")
        details_item.connect("activate", lambda x: self.show_vpn_details(vpn_name))
        menu.append(details_item)
        
        menu.append(Gtk.SeparatorMenuItem())
        
        delete_item = Gtk.MenuItem(label="Delete VPN")
        delete_item.connect("activate", lambda x: self.delete_vpn(vpn_name))
        menu.append(delete_item)
        
        menu.show_all()
        menu.popup_at_pointer(event)
    
    def show_vpn_details(self, name):
        def load_details_thread():
            details = self.manager.get_vpn_details(name)
            status = self.manager.get_vpn_status(name)
            GLib.idle_add(self.display_vpn_details, name, details, status)
        
        threading.Thread(target=load_details_thread, daemon=True).start()
    
    def display_vpn_details(self, name, details, status):
        dialog = VPNDetailsDialog(self, name, details, status)
        dialog.run()
        dialog.destroy()
        return False
    
    def delete_vpn(self, name):
        response = self.show_question(
            f"Delete VPN '{name}'?",
            "This will permanently remove this VPN configuration."
        )
        
        if response == Gtk.ResponseType.YES:
            success, message = self.manager.delete_vpn(name)
            
            if success:
                self.set_status(f"✓ Deleted {name}", Gtk.MessageType.INFO)
                self.load_vpn_list()
            else:
                self.set_status(f"✗ {message}", Gtk.MessageType.ERROR)
    
    def on_add_vpn(self, *_):
        dialog = AddVPNDialog(self)
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            config = dialog.get_config()
            dialog.destroy()
            
            if config:
                self.process_add_vpn(config)
        else:
            dialog.destroy()
    
    def process_add_vpn(self, config):
        self.set_status("Adding VPN connection...", Gtk.MessageType.INFO)
        
        def add_thread():
            if config['type'] == 'import':
                if not config.get('file'):
                    GLib.idle_add(self.set_status, "No file selected", Gtk.MessageType.ERROR)
                    return
                
                success, message = self.manager.import_openvpn(
                    config['file'],
                    config.get('name', '')
                )
            elif config['type'] == 'wireguard':
                if not config.get('name'):
                    GLib.idle_add(self.set_status, "Name is required", Gtk.MessageType.ERROR)
                    return
                
                wg_config = {
                    'private_key': config.get('private_key', ''),
                    'address': config.get('address', ''),
                    'peer': config.get('peer', ''),
                    'endpoint': config.get('endpoint', '')
                }
                success, message = self.manager.create_wireguard(config['name'], wg_config)
            else:
                # Generic VPN types
                GLib.idle_add(self.set_status, 
                            "Manual configuration not yet supported. Use import or WireGuard.",
                            Gtk.MessageType.WARNING)
                return
            
            GLib.idle_add(self.on_add_vpn_done, success, message)
        
        threading.Thread(target=add_thread, daemon=True).start()
    
    def on_add_vpn_done(self, success, message):
        if success:
            self.set_status(f"✓ {message}", Gtk.MessageType.INFO)
            self.load_vpn_list()
            
            notification = Notify.Notification.new(
                "VPN Added",
                message,
                "network-vpn"
            )
            notification.show()
        else:
            self.set_status(f"✗ {message}", Gtk.MessageType.ERROR)
        
        return False
    
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
    
    def on_dialog_response(self, dialog, response):
        if self.auto_refresh_id:
            GLib.source_remove(self.auto_refresh_id)
            self.auto_refresh_id = None

class AboutDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="About", parent=parent, modal=True)
        css = b"""
        .link-btn {
            background-color: #1E88E5; /*double background color bc idk why its not working wihtout both*/
            background: #1E88E5;
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
            border: none;
            text-decoration: none;
        }

        .link-btn:hover {
            background-color: #1565C0;
        }

        .link-btn:active {
            background-color: #0D47A1;
        }
        """

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)

        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )



        self.set_default_size(380, 320)
        self.set_resizable(False)
        
        # Popup style
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_keep_above(True)
        self.set_decorated(True)
        self.set_opacity(0.97)
        
        box = self.get_content_area()
        box.set_spacing(20)
        box.set_margin_start(40)
        box.set_margin_end(40)
        box.set_margin_top(30)
        box.set_margin_bottom(30)
        
        # App icon
        icon = Gtk.Image.new_from_icon_name("network-wireless-symbolic", Gtk.IconSize.INVALID)
        icon.set_pixel_size(64)
        box.pack_start(icon, False, False, 0)
        
        # App name & version
        name_label = Gtk.Label()
        name_label.set_markup("<span size='x-large' weight='bold'>Connex</span>")
        box.pack_start(name_label, False, False, 0)
        
        version_label = Gtk.Label()
        version_label.set_markup("<span size='small'>Version 1.4.0</span>")
        box.pack_start(version_label, False, False, 0)
        
        # Description
        desc_label = Gtk.Label()
        desc_label.set_markup("<span size='small'>Wi-Fi Manager for Linux</span>")
        desc_label.set_opacity(0.7)
        box.pack_start(desc_label, False, False, 0)
        
        # Author
        author_label = Gtk.Label()
        author_label.set_markup("<span size='small'>by Lluciocc</span>")
        author_label.set_opacity(0.6)
        box.pack_start(author_label, False, False, 0)
        
        # Links
        github_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        github_box.set_halign(Gtk.Align.CENTER)
        github_button = Gtk.Button(label="GitHub")
        github_button.get_style_context().add_class("link-btn")
        github_button.connect("clicked", lambda w: webbrowser.open("https://github.com/Lluciocc/connex"))
        github_box.pack_start(github_button, False, False, 0)
        box.pack_start(github_box, False, False, 0)

        coffee_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        coffee_box.set_halign(Gtk.Align.CENTER)
        coffee_button = Gtk.Button(label="☕ Buy me a coffee")
        coffee_button.get_style_context().add_class("link-btn")
        coffee_button.connect("clicked", lambda w: webbrowser.open("https://buymeacoffee.com/lluciocc"))

        coffee_box.pack_start(coffee_button, False, False, 0)  
        box.pack_start(coffee_box, False, False, 0)
        
        # License
        license_label = Gtk.Label()
        license_label.set_markup("<span size='small' alpha='50%'>MIT License</span>")
        box.pack_start(license_label, False, False, 0)
        
        # Close button
        close_button = Gtk.Button(label="Close")
        close_button.set_size_request(100, -1)
        close_button.connect("clicked", lambda x: self.response(Gtk.ResponseType.CLOSE))
        
        button_box = Gtk.Box()
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.pack_start(close_button, False, False, 0)
        box.pack_start(button_box, False, False, 0)
        
        self.connect("response", lambda d, r: self.destroy())
        self.show_all()
