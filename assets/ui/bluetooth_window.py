import time
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Notify
import threading
from datetime import datetime

from assets.core.bluetooth import BluetoothManager
from assets.ui.bluetooth_ui import BluetoothDeviceDialog, BluetoothPinDialog
from assets.utils.debug import log_debug


class BluetoothWindow(Gtk.Dialog):
    
    def __init__(self, parent):
        super().__init__(title="Bluetooth Manager", parent=parent, modal=True)
        self.add_button("Close", Gtk.ResponseType.CLOSE)
        self.set_default_size(700, 550)
        
        self.manager = BluetoothManager()
        self.scanning = False
        
        if not self.manager.is_bluetooth_available():
            self.show_bluetooth_unavailable()
            return
        
        box = self.get_content_area()
        box.set_spacing(0)
        
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.set_margin_start(12)
        toolbar.set_margin_end(12)
        toolbar.set_margin_top(12)
        toolbar.set_margin_bottom(6)
        
        self.bt_switch = Gtk.Switch()
        self.bt_switch.set_active(self.manager.get_bluetooth_state())
        self.bt_switch.connect("notify::active", self.on_bluetooth_toggled)
        
        bt_label = Gtk.Label(label="Bluetooth")
        bt_label.set_margin_end(6)
        
        toolbar.pack_start(bt_label, False, False, 0)
        toolbar.pack_start(self.bt_switch, False, False, 0)
        
        self.discoverable_switch = Gtk.Switch()
        self.discoverable_switch.set_active(self.manager.get_discoverable_state())
        self.discoverable_switch.connect("notify::active", self.on_discoverable_toggled)
        self.discoverable_switch.set_tooltip_text("Make this device visible to others")
        
        disc_label = Gtk.Label(label="Discoverable")
        disc_label.set_margin_start(12)
        disc_label.set_margin_end(6)
        
        toolbar.pack_start(disc_label, False, False, 0)
        toolbar.pack_start(self.discoverable_switch, False, False, 0)
        
        
        self.scan_button = Gtk.Button()
        scan_icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        self.scan_button.set_image(scan_icon)
        self.scan_button.set_tooltip_text("Scan for devices")
        self.scan_button.connect("clicked", self.on_scan_clicked)
        toolbar.pack_end(self.scan_button, False, False, 0)
        
        self.scan_spinner = Gtk.Spinner()
        toolbar.pack_end(self.scan_spinner, False, False, 0)
        
        box.pack_start(toolbar, False, False, 0)
        
        self.status_revealer = Gtk.Revealer()
        self.status_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.status_revealer.set_transition_duration(250)
        
        self.status_bar = Gtk.InfoBar()
        self.status_bar.set_message_type(Gtk.MessageType.INFO)
        self.status_label = Gtk.Label(label="Ready to scan")
        status_content = self.status_bar.get_content_area()
        status_content.add(self.status_label)
        self.status_bar.set_show_close_button(True)
        self.status_bar.connect("response", lambda x, y: self.status_revealer.set_reveal_child(False))
        
        self.status_revealer.add(self.status_bar)
        self.status_revealer.set_reveal_child(True)
        box.pack_start(self.status_revealer, False, False, 0)
        
        self.search_revealer = Gtk.Revealer()
        self.search_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.search_revealer.set_transition_duration(200)
        
        search_box = Gtk.Box(spacing=6)
        search_box.set_margin_start(12)
        search_box.set_margin_end(12)
        search_box.set_margin_top(6)
        search_box.set_margin_bottom(6)
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search devices...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        search_box.pack_start(self.search_entry, True, True, 0)
        
        self.search_revealer.add(search_box)
        self.search_revealer.set_reveal_child(True)
        box.pack_start(self.search_revealer, False, False, 0)
        
        self.store = Gtk.ListStore(str, str, str, str, bool, bool, str)  
        
        self.filter = self.store.filter_new()
        self.filter.set_visible_func(self.filter_func)
        
        tree = Gtk.TreeView(model=self.filter)
        tree.set_headers_visible(True)
        tree.set_enable_search(False)
        tree.set_activate_on_single_click(False)
        
        icon_renderer = Gtk.CellRendererPixbuf()
        icon_column = Gtk.TreeViewColumn("", icon_renderer)
        icon_column.set_cell_data_func(icon_renderer, self.device_icon_func)
        icon_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        icon_column.set_fixed_width(40)
        tree.append_column(icon_column)
        
        name_renderer = Gtk.CellRendererText()
        name_renderer.set_property("ellipsize", 3)
        name_column = Gtk.TreeViewColumn("Device Name", name_renderer, text=0)
        name_column.set_expand(True)
        name_column.set_sort_column_id(0)
        tree.append_column(name_column)
        
        type_renderer = Gtk.CellRendererText()
        type_column = Gtk.TreeViewColumn("Type", type_renderer, text=1)
        type_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        type_column.set_fixed_width(120)
        tree.append_column(type_column)
        
        status_renderer = Gtk.CellRendererText()
        status_column = Gtk.TreeViewColumn("Status", status_renderer, text=3)
        status_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        status_column.set_fixed_width(100)
        tree.append_column(status_column)
        
        signal_renderer = Gtk.CellRendererText()
        signal_column = Gtk.TreeViewColumn("Signal", signal_renderer, text=6)
        signal_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        signal_column.set_fixed_width(80)
        tree.append_column(signal_column)
        
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
        
        Notify.init("connex-bluetooth")
        
        self.show_all()
        
        GLib.idle_add(self.scan_devices)
        
        self.auto_refresh = True
        GLib.timeout_add_seconds(8, self.auto_scan)
        
        self.connect("response", self.on_dialog_response)
    
    def show_bluetooth_unavailable(self):
        box = self.get_content_area()
        
        error_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        error_box.set_valign(Gtk.Align.CENTER)
        error_box.set_margin_top(40)
        error_box.set_margin_bottom(40)
        
        icon = Gtk.Image.new_from_icon_name("bluetooth-disabled-symbolic", Gtk.IconSize.DIALOG)
        icon.set_pixel_size(64)
        error_box.pack_start(icon, False, False, 0)
        
        label = Gtk.Label()
        label.set_markup("<big><b>Bluetooth Not Available</b></big>\n\n"
                        "Please check:\n"
                        "• Bluetooth adapter is installed\n"
                        "• bluetooth service is running\n"
                        "• bluez is installed")
        label.set_justify(Gtk.Justification.CENTER)
        error_box.pack_start(label, False, False, 0)
        
        box.pack_start(error_box, True, True, 0)
        self.show_all()
    
    def device_icon_func(self, column, cell, model, iter, data):
        device_type = model.get_value(iter, 1)
        connected = model.get_value(iter, 5)
        
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
        icon = icon_map.get(device_type, 'bluetooth-symbolic')
        
        if connected and '-symbolic' in icon:
            icon = icon.replace('-symbolic', '-active-symbolic')
        
        cell.set_property("icon-name", icon)
    
    def filter_func(self, model, iter, data):
        search_text = self.search_entry.get_text().lower()
        if not search_text:
            return True
        
        name = model.get_value(iter, 0).lower()
        device_type = model.get_value(iter, 1).lower()
        mac = model.get_value(iter, 2).lower()
        
        return (search_text in name or 
                search_text in device_type or 
                search_text in mac)
    
    def on_search_changed(self, entry):
        self.filter.refilter()
    
    def set_status(self, message, message_type=Gtk.MessageType.INFO):
        self.status_label.set_text(message)
        self.status_bar.set_message_type(message_type)
        self.status_revealer.set_reveal_child(True)
        
        if message_type == Gtk.MessageType.INFO:
            GLib.timeout_add_seconds(5, lambda: self.status_revealer.set_reveal_child(False))
    
    def on_bluetooth_toggled(self, switch, gparam):
        enabled = switch.get_active()
        
        def toggle_thread():
            success, message = self.manager.set_bluetooth_state(enabled)
            GLib.idle_add(self.on_bluetooth_toggled_done, success, message, enabled)
        
        threading.Thread(target=toggle_thread, daemon=True).start()
    
    def on_bluetooth_toggled_done(self, success, message, enabled):
        if success:
            self.set_status(message, Gtk.MessageType.INFO)
            
            if enabled:
                GLib.timeout_add(500, self.scan_devices)
            else:
                self.store.clear()
                self.set_status("Bluetooth disabled", Gtk.MessageType.WARNING)
        else:
            self.set_status(f"Failed: {message}", Gtk.MessageType.ERROR)
            self.bt_switch.set_active(not enabled)
        
        return False
    
    def on_discoverable_toggled(self, switch, gparam):
        enabled = switch.get_active()
        
        def toggle_thread():
            success, message = self.manager.set_discoverable(enabled)
            GLib.idle_add(self.on_discoverable_done, success, message, enabled)
        
        threading.Thread(target=toggle_thread, daemon=True).start()
    
    def on_discoverable_done(self, success, message, enabled):
        if success:
            status = "visible" if enabled else "hidden"
            self.set_status(f"Device is now {status}", Gtk.MessageType.INFO)
        else:
            self.set_status(f"Failed: {message}", Gtk.MessageType.ERROR)
            self.discoverable_switch.set_active(not enabled)
        
        return False
    
    def on_scan_clicked(self, button):
        self.scan_devices()
    
    def scan_devices(self):
        if not self.bt_switch.get_active():
            self.set_status("Enable Bluetooth to scan", Gtk.MessageType.WARNING)
            return False
        
        self.scanning = True
        self.scan_button.set_sensitive(False)
        self.scan_spinner.start()
        self.scan_spinner.show()
        
        self.set_status("Scanning for devices...", Gtk.MessageType.INFO)
        
        def scan_thread():
            self.manager.start_scan()
            time.sleep(5)

            self.manager.stop_scan()
            time.sleep(0.5)

            devices = self.manager.get_devices()
            GLib.idle_add(self.update_device_list, devices)
        
        threading.Thread(target=scan_thread, daemon=True).start()
        return False
    
    def update_device_list(self, devices):
        self.scan_button.set_sensitive(True)
        self.scan_spinner.stop()
        self.scan_spinner.hide()
        self.scanning = False
        
        self.tree.set_opacity(0.3)
        
        self.store.clear()
        
        paired_devices = [d for d in devices if d['paired']]
        unpaired_devices = [d for d in devices if not d['paired']]
        
        for device in paired_devices:
            status_parts = []
            if device['connected']:
                status_parts.append("Connected")
            else:
                status_parts.append("Paired")
            
            if device['trusted']:
                status_parts.append("Trusted")
            
            status = ", ".join(status_parts)
            
            display_name = f"● {device['name']}" if device['connected'] else device['name']
            
            self.store.append([
                display_name,
                device['type'],
                device['mac'],
                status,
                device['paired'],
                device['connected'],
                device.get('rssi', '')
            ])
        
        for device in unpaired_devices:
            self.store.append([
                device['name'],
                device['type'],
                device['mac'],
                "Not paired",
                False,
                False,
                device.get('rssi', '')
            ])
        
        def fade_in(opacity=0.3):
            if opacity < 1.0:
                self.tree.set_opacity(opacity)
                GLib.timeout_add(30, fade_in, opacity + 0.1)
            else:
                self.tree.set_opacity(1.0)
            return False
        
        GLib.timeout_add(50, fade_in)
        
        count = len(devices)
        paired_count = len(paired_devices)
        
        if count == 0:
            self.set_status("No devices found - try scanning again", Gtk.MessageType.WARNING)
        else:
            if paired_count > 0:
                self.set_status(f"Found {count} device{'s' if count != 1 else ''} ({paired_count} paired)")
            else:
                self.set_status(f"Found {count} device{'s' if count != 1 else ''}")
        
        return False
    
    def auto_scan(self):
        if self.auto_refresh and self.get_visible() and self.bt_switch.get_active():
            if not self.scanning:
                self.scan_devices()
        return self.auto_refresh
    
    def on_row_activated(self, tree, path, col):
        model = tree.get_model()
        device = {
            'type': model[path][1],
            'mac': model[path][2],
            'status': model[path][3],
            'paired': model[path][4],
            'connected': model[path][5],
            'rssi': model[path][6]
        }
        
        if device['connected']:
            response = self.show_question(
                f"Disconnect from {device['name']}?",
                "This will disconnect the device."
            )
            if response == Gtk.ResponseType.YES:
                self.disconnect_device(device['mac'], device['name'])
        elif device['paired']:
            self.connect_device(device['mac'], device['name'])
        else:
            self.pair_device(device['mac'], device['name'])
    
    def pair_device(self, mac, name):
        self.set_status(f"Pairing with {name}...", Gtk.MessageType.INFO)
        
        def pair_thread():
            success, message = self.manager.pair_device(mac)
            GLib.idle_add(self.on_pair_done, success, message, mac, name)
        
        threading.Thread(target=pair_thread, daemon=True).start()
    
    def on_pair_done(self, success, message, mac, name):
        if success:
            self.set_status(f"✓ Paired with {name}", Gtk.MessageType.INFO)
            
            notification = Notify.Notification.new(
                "Bluetooth Paired",
                f"Successfully paired with {name}",
                "bluetooth"
            )
            notification.show()
            
            GLib.timeout_add(500, lambda: self.connect_device(mac, name))
            
            GLib.timeout_add(1000, self.scan_devices)
        else:
            self.set_status(f"✗ Pairing failed: {message}", Gtk.MessageType.ERROR)
            
            notification = Notify.Notification.new(
                "Bluetooth Pairing Failed",
                f"Could not pair with {name}",
                "bluetooth-disabled"
            )
            notification.show()
        
        return False
    
    def connect_device(self, mac, name):
        self.set_status(f"Connecting to {name}...", Gtk.MessageType.INFO)
        
        def connect_thread():
            success, message = self.manager.connect_device(mac)
            GLib.idle_add(self.on_connect_done, success, message, name)
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def on_connect_done(self, success, message, name):
        if success:
            self.set_status(f"✓ Connected to {name}", Gtk.MessageType.INFO)
            
            notification = Notify.Notification.new(
                "Bluetooth Connected",
                f"Successfully connected to {name}",
                "bluetooth"
            )
            notification.show()
        else:
            self.set_status(f"✗ Connection failed: {message}", Gtk.MessageType.ERROR)
            
            notification = Notify.Notification.new(
                "Bluetooth Connection Failed",
                message,
                "bluetooth-disabled"
            )
            notification.show()
        
        GLib.timeout_add(1000, self.scan_devices)
        return False
    
    def disconnect_device(self, mac, name):
        self.set_status(f"Disconnecting from {name}...", Gtk.MessageType.INFO)
        
        def disconnect_thread():
            success, message = self.manager.disconnect_device(mac)
            GLib.idle_add(self.on_disconnect_done, success, message, name)
        
        threading.Thread(target=disconnect_thread, daemon=True).start()
    
    def on_disconnect_done(self, success, message, name):
        if success:
            self.set_status(f"✓ Disconnected from {name}", Gtk.MessageType.INFO)
            
            notification = Notify.Notification.new(
                "Bluetooth Disconnected",
                f"Disconnected from {name}",
                "bluetooth-disabled"
            )
            notification.show()
        else:
            self.set_status(f"✗ {message}", Gtk.MessageType.ERROR)
        
        GLib.timeout_add(1000, self.scan_devices)
        return False
    
    def on_tree_button_press(self, widget, event):
        if event.button == 3:
            path = widget.get_path_at_pos(int(event.x), int(event.y))
            if path:
                widget.set_cursor(path[0])
                self.show_context_menu(widget, event, path[0])
            return True
        return False
    
    def show_context_menu(self, widget, event, path):
        model = widget.get_model()
        device = {
            'name': model[path][0].replace("● ", ""),
            'type': model[path][1],
            'mac': model[path][2],
            'paired': model[path][4],
            'connected': model[path][5],
            'trusted': "Trusted" in model[path][3]
        }
        
        menu = Gtk.Menu()
        
        if device['connected']:
            disconnect_item = Gtk.MenuItem(label="Disconnect")
            disconnect_item.connect("activate", 
                lambda x: self.disconnect_device(device['mac'], device['name']))
            menu.append(disconnect_item)
        elif device['paired']:
            connect_item = Gtk.MenuItem(label="Connect")
            connect_item.connect("activate", 
                lambda x: self.connect_device(device['mac'], device['name']))
            menu.append(connect_item)
        else:
            pair_item = Gtk.MenuItem(label="Pair")
            pair_item.connect("activate", 
                lambda x: self.pair_device(device['mac'], device['name']))
            menu.append(pair_item)
        
        menu.append(Gtk.SeparatorMenuItem())
        
        if device['paired']:
            if device['trusted']:
                trust_item = Gtk.MenuItem(label="Untrust Device")
                trust_item.connect("activate", 
                    lambda x: self.trust_device(device['mac'], device['name'], False))
            else:
                trust_item = Gtk.MenuItem(label="Trust Device")
                trust_item.connect("activate", 
                    lambda x: self.trust_device(device['mac'], device['name'], True))
            menu.append(trust_item)
        
        info_item = Gtk.MenuItem(label="Device Information")
        info_item.connect("activate", lambda x: self.show_device_info(device))
        menu.append(info_item)
        
        menu.append(Gtk.SeparatorMenuItem())
        
        if device['paired']:
            remove_item = Gtk.MenuItem(label="Remove Device")
            remove_item.connect("activate", 
                lambda x: self.remove_device(device['mac'], device['name']))
            menu.append(remove_item)
        
        menu.show_all()
        menu.popup_at_pointer(event)
    
    def trust_device(self, mac, name, trust):
        action = "trusting" if trust else "untrusting"
        self.set_status(f"{action.capitalize()} {name}...", Gtk.MessageType.INFO)
        
        def trust_thread():
            success, message = self.manager.trust_device(mac, trust)
            GLib.idle_add(self.on_trust_done, success, message, name)
        
        threading.Thread(target=trust_thread, daemon=True).start()
    
    def on_trust_done(self, success, message, name):
        if success:
            self.set_status(f"✓ {message}: {name}", Gtk.MessageType.INFO)
            GLib.timeout_add(500, self.scan_devices)
        else:
            self.set_status(f"✗ {message}", Gtk.MessageType.ERROR)
        
        return False
    
    def show_device_info(self, device):
        def info_thread():
            full_info = self.manager.get_device_info(device['mac'])
            device.update(full_info)
            GLib.idle_add(self.display_device_info, device)
        
        threading.Thread(target=info_thread, daemon=True).start()
    
    def display_device_info(self, device):
        dialog = BluetoothDeviceDialog(self, device)
        dialog.run()
        dialog.destroy()
        return False
    
    def remove_device(self, mac, name):
        response = self.show_question(
            f"Remove {name}?",
            "This will unpair the device and remove all saved settings."
        )
        
        if response == Gtk.ResponseType.YES:
            self.set_status(f"Removing {name}...", Gtk.MessageType.INFO)
            
            def remove_thread():
                success, message = self.manager.remove_device(mac)
                GLib.idle_add(self.on_remove_done, success, message, name)
            
            threading.Thread(target=remove_thread, daemon=True).start()
    
    def on_remove_done(self, success, message, name):
        if success:
            self.set_status(f"✓ Removed {name}", Gtk.MessageType.INFO)
            GLib.timeout_add(500, self.scan_devices)
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
        self.auto_refresh = False
        self.manager.stop_scan()