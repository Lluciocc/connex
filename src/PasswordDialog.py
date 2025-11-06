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
