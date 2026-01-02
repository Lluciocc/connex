from assets.core.vpn_manager import VPNManager
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, GLib, Gdk, Notify, AppIndicator3, GdkPixbuf
import subprocess
import threading


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

        title = Gtk.Label()
        title.set_markup("<b>Choose VPN Type</b>")
        title.set_xalign(0)
        box.pack_start(title, False, False, 0)

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

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(200)

        self.openvpn_box = self.create_openvpn_config()
        self.stack.add_named(self.openvpn_box, "openvpn")

        self.wireguard_box = self.create_wireguard_config()
        self.stack.add_named(self.wireguard_box, "wireguard")

        self.import_box = self.create_import_config()
        self.stack.add_named(self.import_box, "import")

        self.generic_box = self.create_generic_config()
        self.stack.add_named(self.generic_box, "generic")
        
        box.pack_start(self.stack, True, True, 0)
        
        self.show_all()
    
    def create_openvpn_config(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="Connection Name:")
        name_label.set_width_chars(18)
        self.openvpn_name = Gtk.Entry()
        self.openvpn_name.set_placeholder_text("My VPN")
        name_box.pack_start(name_label, False, False, 0)
        name_box.pack_start(self.openvpn_name, True, True, 0)
        box.pack_start(name_box, False, False, 0)

        gateway_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        gateway_label = Gtk.Label(label="Gateway:")
        gateway_label.set_width_chars(18)
        self.openvpn_gateway = Gtk.Entry()
        self.openvpn_gateway.set_placeholder_text("vpn.example.com")
        gateway_box.pack_start(gateway_label, False, False, 0)
        gateway_box.pack_start(self.openvpn_gateway, True, True, 0)
        box.pack_start(gateway_box, False, False, 0)

        user_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        user_label = Gtk.Label(label="Username:")
        user_label.set_width_chars(18)
        self.openvpn_user = Gtk.Entry()
        self.openvpn_user.set_placeholder_text("Optional")
        user_box.pack_start(user_label, False, False, 0)
        user_box.pack_start(self.openvpn_user, True, True, 0)
        box.pack_start(user_box, False, False, 0)

        pass_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pass_label = Gtk.Label(label="Password:")
        pass_label.set_width_chars(18)
        self.openvpn_pass = Gtk.Entry()
        self.openvpn_pass.set_visibility(False)
        self.openvpn_pass.set_placeholder_text("Optional")
        pass_box.pack_start(pass_label, False, False, 0)
        pass_box.pack_start(self.openvpn_pass, True, True, 0)
        box.pack_start(pass_box, False, False, 0)

        info = Gtk.Label()
        info.set_markup("<small><i>For advanced OpenVPN configs, use 'Import from file'</i></small>")
        info.set_xalign(0)
        box.pack_start(info, False, False, 0)
        
        return box
    
    def create_wireguard_config(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="Connection Name:")
        name_label.set_width_chars(18)
        self.wg_name = Gtk.Entry()
        self.wg_name.set_placeholder_text("My WireGuard")
        name_box.pack_start(name_label, False, False, 0)
        name_box.pack_start(self.wg_name, True, True, 0)
        box.pack_start(name_box, False, False, 0)

        key_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        key_label = Gtk.Label(label="Private Key:")
        key_label.set_width_chars(18)
        self.wg_private_key = Gtk.Entry()
        self.wg_private_key.set_visibility(False)
        self.wg_private_key.set_placeholder_text("base64 encoded key")
        key_box.pack_start(key_label, False, False, 0)
        key_box.pack_start(self.wg_private_key, True, True, 0)
        box.pack_start(key_box, False, False, 0)

        addr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        addr_label = Gtk.Label(label="IP Address:")
        addr_label.set_width_chars(18)
        self.wg_address = Gtk.Entry()
        self.wg_address.set_placeholder_text("10.0.0.2/24")
        addr_box.pack_start(addr_label, False, False, 0)
        addr_box.pack_start(self.wg_address, True, True, 0)
        box.pack_start(addr_box, False, False, 0)

        peer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        peer_label = Gtk.Label(label="Peer Public Key:")
        peer_label.set_width_chars(18)
        self.wg_peer = Gtk.Entry()
        self.wg_peer.set_placeholder_text("Server public key")
        peer_box.pack_start(peer_label, False, False, 0)
        peer_box.pack_start(self.wg_peer, True, True, 0)
        box.pack_start(peer_box, False, False, 0)

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

        self.file_chooser = Gtk.FileChooserButton(title="Select VPN Config")
        self.file_chooser.set_action(Gtk.FileChooserAction.OPEN)

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

        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="Connection Name:")
        name_label.set_width_chars(18)
        self.generic_name = Gtk.Entry()
        name_box.pack_start(name_label, False, False, 0)
        name_box.pack_start(self.generic_name, True, True, 0)
        box.pack_start(name_box, False, False, 0)

        gateway_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        gateway_label = Gtk.Label(label="Gateway:")
        gateway_label.set_width_chars(18)
        self.generic_gateway = Gtk.Entry()
        gateway_box.pack_start(gateway_label, False, False, 0)
        gateway_box.pack_start(self.generic_gateway, True, True, 0)
        box.pack_start(gateway_box, False, False, 0)

        user_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        user_label = Gtk.Label(label="Username:")
        user_label.set_width_chars(18)
        self.generic_user = Gtk.Entry()
        user_box.pack_start(user_label, False, False, 0)
        user_box.pack_start(self.generic_user, True, True, 0)
        box.pack_start(user_box, False, False, 0)

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

        title = Gtk.Label()
        title.set_markup(f"<b>{vpn_name}</b>")
        title.set_xalign(0)
        box.pack_start(title, False, False, 0)

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

        notebook = Gtk.Notebook()

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
        self.set_default_size(600, 500)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_keep_above(True)
        self.set_decorated(True)
        self.set_opacity(0.97)
        self.set_resizable(False)
        
        add_button = self.add_button("Add VPN", Gtk.ResponseType.NONE)
        add_button.connect("clicked", self.on_add_vpn)
        add_button.get_style_context().add_class("suggested-action")
        
        box = self.get_content_area()
        box.set_spacing(0)
        
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.set_margin_start(12)
        toolbar.set_margin_end(12)
        toolbar.set_margin_top(12)
        toolbar.set_margin_bottom(6)
        
        title_label = Gtk.Label()
        title_label.set_markup("<b>VPN Connections</b>")
        title_label.set_xalign(0)
        toolbar.pack_start(title_label, True, True, 0)
        
        refresh_button = Gtk.Button()
        refresh_icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        refresh_button.set_image(refresh_icon)
        refresh_button.set_tooltip_text("Refresh")
        refresh_button.connect("clicked", lambda x: self.load_vpn_list())
        refresh_button.set_relief(Gtk.ReliefStyle.NONE)
        toolbar.pack_end(refresh_button, False, False, 0)
        
        box.pack_start(toolbar, False, False, 0)
        
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
        
        self.store = Gtk.ListStore(str, str, str, str, bool)  # Name, Type, UUID, Status, Connected
        
        tree = Gtk.TreeView(model=self.store)
        tree.set_headers_visible(True)
        tree.set_enable_search(True)
        tree.set_search_column(0)
        
        icon_renderer = Gtk.CellRendererPixbuf()
        icon_column = Gtk.TreeViewColumn("", icon_renderer)
        icon_column.set_cell_data_func(icon_renderer, self.status_icon_func)
        icon_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        icon_column.set_fixed_width(40)
        tree.append_column(icon_column)
        
        name_renderer = Gtk.CellRendererText()
        name_renderer.set_property("ellipsize", 3)
        name_column = Gtk.TreeViewColumn("VPN Name", name_renderer, text=0)
        name_column.set_expand(True)
        name_column.set_sort_column_id(0)
        tree.append_column(name_column)
        
        type_renderer = Gtk.CellRendererText()
        type_column = Gtk.TreeViewColumn("Type", type_renderer, text=1)
        type_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        type_column.set_fixed_width(120)
        tree.append_column(type_column)
        
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

        # fix a bug found abt GTK viewport
        self.empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.empty_box.set_valign(Gtk.Align.CENTER)
        self.empty_box.set_margin_top(40)
        self.empty_box.set_margin_bottom(40)
        
        empty_icon = Gtk.Image.new_from_icon_name("network-vpn-symbolic", Gtk.IconSize.DIALOG)
        empty_icon.set_pixel_size(64)
        self.empty_box.pack_start(empty_icon, False, False, 0)
        
        empty_label = Gtk.Label()
        empty_label.set_markup("<big><b>No VPN Connections</b></big>\n\nClick 'Add VPN' to create your first connection")
        empty_label.set_justify(Gtk.Justification.CENTER)
        self.empty_box.pack_start(empty_label, False, False, 0)
        
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(tree, "list")
        self.stack.add_named(self.empty_box, "empty")
        
        scroll.add(self.stack)
        box.pack_start(scroll, True, True, 0)
        
        self.tree = tree
        self.manager = VPNManager()
        
        self.show_all()
        
        GLib.idle_add(self.load_vpn_list)
        
        self.connect("response", self.on_dialog_response)
        
        self.auto_refresh_id = GLib.timeout_add_seconds(8, self.auto_refresh_vpns)

    
    def status_icon_func(self, column, cell, model, iter, data):
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
        self.status_label.set_text(message)
        self.status_bar.set_message_type(message_type)
        self.status_revealer.set_reveal_child(True)

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
            self.stack.set_visible_child_name("empty")
            self.set_status("No VPN connections configured", Gtk.MessageType.INFO)
            return False

        self.stack.set_visible_child_name("list")

        for vpn in vpns:
            connected = (vpn['name'] == active_vpn)

            vpn_type = vpn['type']
            lower = vpn_type.lower()

            if "wireguard" in lower:
                type_display = "WireGuard"
            elif "openvpn" in lower:
                type_display = "OpenVPN"
            elif "l2tp" in lower:
                type_display = "L2TP/IPsec"
            elif "pptp" in lower:
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
            self.set_status(
                f"{count} VPN{'s' if count != 1 else ''} ({connected_count} connected)"
            )
        else:
            self.set_status(
                f"{count} VPN connection{'s' if count != 1 else ''}"
            )

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
