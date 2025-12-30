import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


class BluetoothDeviceDialog(Gtk.Dialog):
    
    def __init__(self, parent, device):
        super().__init__(title=f"Device - {device['name']}", parent=parent, modal=True)
        self.add_button("Close", Gtk.ResponseType.CLOSE)
        self.set_default_size(450, 400)
        
        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        
        icon_name = self.get_device_icon(device['type'])
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
        icon.set_pixel_size(64)
        box.pack_start(icon, False, False, 0)
        
        name_label = Gtk.Label()
        name_label.set_markup(f"<big><b>{device['name']}</b></big>")
        box.pack_start(name_label, False, False, 0)
        
        type_label = Gtk.Label()
        type_label.set_markup(f"<i>{device['type']}</i>")
        type_label.get_style_context().add_class("dim-label")
        box.pack_start(type_label, False, False, 0)
        
        box.pack_start(Gtk.Separator(), False, False, 0)
        
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(8)
        
        row = 0
        
        mac_label = Gtk.Label(label="MAC Address:")
        mac_label.set_xalign(0)
        mac_label.get_style_context().add_class("dim-label")
        mac_value = Gtk.Label(label=device['mac'])
        mac_value.set_xalign(0)
        mac_value.set_selectable(True)
        grid.attach(mac_label, 0, row, 1, 1)
        grid.attach(mac_value, 1, row, 1, 1)
        row += 1
        
        status_label = Gtk.Label(label="Status:")
        status_label.set_xalign(0)
        status_label.get_style_context().add_class("dim-label")
        
        status_text = []
        if device['connected']:
            status_text.append("Connected")
        if device['paired']:
            status_text.append("Paired")
        if device['trusted']:
            status_text.append("Trusted")
        
        status_value = Gtk.Label()
        status_str = ", ".join(status_text) if status_text else "Not connected"
        status_value.set_markup(f"<b>{status_str}</b>")
        status_value.set_xalign(0)
        grid.attach(status_label, 0, row, 1, 1)
        grid.attach(status_value, 1, row, 1, 1)
        row += 1
        
        if device.get('rssi'):
            rssi_label = Gtk.Label(label="Signal Strength:")
            rssi_label.set_xalign(0)
            rssi_label.get_style_context().add_class("dim-label")
            rssi_value = Gtk.Label(label=device['rssi'])
            rssi_value.set_xalign(0)
            grid.attach(rssi_label, 0, row, 1, 1)
            grid.attach(rssi_value, 1, row, 1, 1)
            row += 1
        
        if device.get('battery'):
            battery_label = Gtk.Label(label="Battery:")
            battery_label.set_xalign(0)
            battery_label.get_style_context().add_class("dim-label")
            battery_value = Gtk.Label(label=device['battery'])
            battery_value.set_xalign(0)
            grid.attach(battery_label, 0, row, 1, 1)
            grid.attach(battery_value, 1, row, 1, 1)
            row += 1
        
        box.pack_start(grid, True, True, 0)
        
        self.show_all()
    
    def get_device_icon(self, device_type):
        icon_map = {
            'Audio': 'audio-card-symbolic',
            'Headset': 'audio-headset-symbolic',
            'Headphones': 'audio-headphones-symbolic',
            'Phone': 'phone-symbolic',
            'Computer': 'computer-symbolic',
            'Keyboard': 'input-keyboard-symbolic',
            'Mouse': 'input-mouse-symbolic',
            'Tablet': 'input-tablet-symbolic',
            'Game Controller': 'input-gaming-symbolic',
            'Camera': 'camera-photo-symbolic',
            'Printer': 'printer-symbolic'
        }
        return icon_map.get(device_type, 'bluetooth-symbolic')


class BluetoothPinDialog(Gtk.Dialog):
    
    def __init__(self, parent, device_name):
        super().__init__(title="Bluetooth Pairing", parent=parent, modal=True)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Pair", Gtk.ResponseType.OK)
        self.set_default_size(400, 200)
        
        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        
        info = Gtk.Label()
        info.set_markup(f"<b>Pairing with {device_name}</b>\n\n"
                       "Enter PIN if requested by the device:")
        info.set_xalign(0)
        box.pack_start(info, False, False, 0)
        
        pin_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pin_label = Gtk.Label(label="PIN:")
        pin_label.set_width_chars(10)
        
        self.pin_entry = Gtk.Entry()
        self.pin_entry.set_placeholder_text("0000 or 1234")
        self.pin_entry.set_max_length(16)
        self.pin_entry.set_activates_default(True)
        
        pin_box.pack_start(pin_label, False, False, 0)
        pin_box.pack_start(self.pin_entry, True, True, 0)
        box.pack_start(pin_box, False, False, 0)
        
        note = Gtk.Label()
        note.set_markup("<small><i>Most modern devices pair automatically without a PIN</i></small>")
        note.set_xalign(0)
        box.pack_start(note, False, False, 0)
        
        self.set_default_response(Gtk.ResponseType.OK)
        self.show_all()
    
    def get_pin(self):
        return self.pin_entry.get_text()