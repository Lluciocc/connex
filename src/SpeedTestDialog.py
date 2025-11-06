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
from speedtest import SpeedTest

gi.require_version("Gtk", "3.0")
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Notify', '0.7')
from gi.repository import Gtk, GObject, GLib, Gdk, Notify, AppIndicator3

# Configuration
CONFIG_DIR = Path.home() / ".config" / "connex"
HISTORY_FILE = CONFIG_DIR / "history.log"
DEBUG_MODE = False

class SpeedTestDialog(Gtk.Dialog):
    """Dialog for running speed test"""
    def __init__(self, parent, SPEEDTEST_AVAILABLE):
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
        self.start_test(SPEEDTEST_AVAILABLE)
    
    def on_response(self, dialog, response):
        """Handle dialog response"""
        if response == Gtk.ResponseType.CANCEL and self.test_running:
            if self.test:
                self.test.cancel()
                self.status_label.set_markup("<span color='orange'>⚠ Test cancelled</span>")
                self.test_running = False
    
    def start_test(self, SPEEDTEST_AVAILABLE):
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
