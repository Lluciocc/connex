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
# Not sure if this is used, but copied just in case
CONFIG_DIR = Path.home() / ".config" / "connex"
HISTORY_FILE = CONFIG_DIR / "history.log"
DEBUG_MODE = False

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
