import gi
import threading
import webbrowser
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, GLib, Gdk, Notify, AppIndicator3, GdkPixbuf
from assets.utils.debug import HISTORY_FILE
from assets.core.speedtest import SpeedTest


try:
    import qrcode
    from PIL import Image
    from io import BytesIO
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

VERSION = "1.4.1"


class SpeedTestDialog(Gtk.Dialog):
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

class QRCodeDialog(Gtk.Dialog):
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
        version_label.set_markup(f"<span size='small'>Version {VERSION}</span>")
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
