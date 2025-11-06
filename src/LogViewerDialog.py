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
