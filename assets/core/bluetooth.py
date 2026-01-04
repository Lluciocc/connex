from typing import Dict, Any, Callable, Tuple, Optional
import dbus
import dbus.mainloop.glib
from gi.repository import GLib
from assets.utils.debug import log_debug

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

BLUEZ = "org.bluez"
ADAPTER_IFACE = "org.bluez.Adapter1"
DEVICE_IFACE = "org.bluez.Device1"
PROPS_IFACE = "org.freedesktop.DBus.Properties"
OBJ_MANAGER = "org.freedesktop.DBus.ObjectManager"


class BluetoothManager:
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.manager = dbus.Interface(self.bus.get_object(BLUEZ, "/"), OBJ_MANAGER)

        self.adapter_path = self._find_adapter()
        self.adapter = dbus.Interface(
            self.bus.get_object(BLUEZ, self.adapter_path), ADAPTER_IFACE
        )

        self._scanning = False
        self._scan_callback: Optional[Callable[[Dict[str, Any]], None]] = None

        self._receiver_installed = False

    def _find_adapter(self) -> str:
        objects = self.manager.GetManagedObjects()
        for path, ifaces in objects.items():
            if ADAPTER_IFACE in ifaces:
                return path
        raise RuntimeError("No Bluetooth adapter found")

    def is_bluetooth_available(self) -> bool:
        return self.adapter_path is not None

    def get_bluetooth_state(self) -> bool:
        props = dbus.Interface(
            self.bus.get_object(BLUEZ, self.adapter_path), PROPS_IFACE
        )
        return bool(props.Get(ADAPTER_IFACE, "Powered"))

    def set_bluetooth_state(self, enabled: bool) -> Tuple[bool, str]:
        try:
            props = dbus.Interface(
                self.bus.get_object(BLUEZ, self.adapter_path), PROPS_IFACE
            )
            props.Set(ADAPTER_IFACE, "Powered", enabled)
            return True, "Bluetooth enabled" if enabled else "Bluetooth disabled"
        except Exception as e:
            return False, str(e)

    def get_discoverable_state(self) -> bool:
        props = dbus.Interface(
            self.bus.get_object(BLUEZ, self.adapter_path), PROPS_IFACE
        )
        return bool(props.Get(ADAPTER_IFACE, "Discoverable"))

    def set_discoverable(self, enabled: bool) -> Tuple[bool, str]:
        try:
            props = dbus.Interface(
                self.bus.get_object(BLUEZ, self.adapter_path), PROPS_IFACE
            )
            props.Set(ADAPTER_IFACE, "Discoverable", enabled)
            return True, "Discoverable updated"
        except Exception as e:
            return False, str(e)


    def start_scan(self, on_device_found: Callable[[Dict[str, Any]], None] = None):
        if self._scanning:
            return

        self._scan_callback = on_device_found
        self._scanning = True

        if not self._receiver_installed:
            self.bus.add_signal_receiver(
                self._on_interfaces_added,
                dbus_interface=OBJ_MANAGER,
                signal_name="InterfacesAdded",
            )
            self._receiver_installed = True

        try:
            self.adapter.StartDiscovery()
            log_debug("Bluetooth discovery started")
        except Exception as e:
            self._scanning = False
            log_debug(f"StartDiscovery failed: {e}")

    def stop_scan(self):
        if not self._scanning:
            return

        try:
            self.adapter.StopDiscovery()
        except Exception:
            pass

        self._scanning = False
        log_debug("Bluetooth discovery stopped")

    def get_scan_results_snapshot(self) -> Dict[str, Dict[str, Any]]:
        devices: Dict[str, Dict[str, Any]] = {}
        objects = self.manager.GetManagedObjects()

        for path, ifaces in objects.items():
            dev = ifaces.get(DEVICE_IFACE)
            if not dev:
                continue

            device = self._device_from_bluez(path, dev)
            mac = device["mac"]
            if mac:
                devices[mac] = device

        return devices

    def _on_interfaces_added(self, path, interfaces):
        if not self._scanning:
            return

        dev = interfaces.get(DEVICE_IFACE)
        if not dev:
            return

        device = self._device_from_bluez(path, dev)

        if self._scan_callback and device["mac"]:
            self._scan_callback(device)


    def _device_from_bluez(self, path: str, d: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "path": path,
            "mac": str(d.get("Address", "")),
            "name": str(d.get("Name", d.get("Alias", "Unknown"))),
            "paired": bool(d.get("Paired", False)),
            "connected": bool(d.get("Connected", False)),
            "trusted": bool(d.get("Trusted", False)),
            "rssi": int(d.get("RSSI", 0)) if "RSSI" in d else None,
            "type": self._icon_to_type(str(d.get("Icon", ""))),
        }

    def _get_device_by_mac(self, mac: str) -> Optional[str]:
        objects = self.manager.GetManagedObjects()
        for path, ifaces in objects.items():
            dev = ifaces.get(DEVICE_IFACE)
            if dev and dev.get("Address") == mac:
                return path
        return None

    def get_connected_devices(self) -> Dict[str, str]:
        connected = {}
        objects = self.manager.GetManagedObjects()

        for _, ifaces in objects.items():
            dev = ifaces.get(DEVICE_IFACE)
            if dev and dev.get("Connected"):
                mac = str(dev.get("Address", ""))
                name = str(dev.get("Name", dev.get("Alias", "Unknown")))
                connected[mac] = name

        return connected

    def pair_device(self, mac: str) -> Tuple[bool, str]:
        path = self._get_device_by_mac(mac)
        if not path:
            return False, "Device not found"

        try:
            dbus.Interface(self.bus.get_object(BLUEZ, path), DEVICE_IFACE).Pair()
            return True, "Device paired"
        except Exception as e:
            return False, str(e)

    def connect_device(self, mac: str) -> Tuple[bool, str]:
        path = self._get_device_by_mac(mac)
        if not path:
            return False, "Device not found"

        try:
            dbus.Interface(self.bus.get_object(BLUEZ, path), DEVICE_IFACE).Connect()
            return True, "Device connected"
        except Exception as e:
            return False, str(e)

    def disconnect_device(self, mac: str) -> Tuple[bool, str]:
        path = self._get_device_by_mac(mac)
        if not path:
            return False, "Device not found"

        try:
            dbus.Interface(self.bus.get_object(BLUEZ, path), DEVICE_IFACE).Disconnect()
            return True, "Device disconnected"
        except Exception as e:
            return False, str(e)

    def trust_device(self, mac: str, trust: bool = True) -> Tuple[bool, str]:
        path = self._get_device_by_mac(mac)
        if not path:
            return False, "Device not found"

        try:
            props = dbus.Interface(self.bus.get_object(BLUEZ, path), PROPS_IFACE)
            props.Set(DEVICE_IFACE, "Trusted", trust)
            return True, "Device trusted" if trust else "Device untrusted"
        except Exception as e:
            return False, str(e)

    def remove_device(self, mac: str) -> Tuple[bool, str]:
        path = self._get_device_by_mac(mac)
        if not path:
            return False, "Device not found"

        try:
            self.adapter.RemoveDevice(path)
            return True, "Device removed"
        except Exception as e:
            return False, str(e)

    def get_device_info(self, mac: str) -> Dict[str, Any]:
        path = self._get_device_by_mac(mac)
        if not path:
            return {}

        props = dbus.Interface(self.bus.get_object(BLUEZ, path), PROPS_IFACE)

        return {
            "connected": bool(props.Get(DEVICE_IFACE, "Connected")),
            "paired": bool(props.Get(DEVICE_IFACE, "Paired")),
            "trusted": bool(props.Get(DEVICE_IFACE, "Trusted")),
        }


    def _icon_to_type(self, icon: str) -> str:
        return {
            "audio-card": "Audio",
            "audio-headset": "Headset",
            "audio-headphones": "Headphones",
            "phone": "Phone",
            "computer": "Computer",
            "input-keyboard": "Keyboard",
            "input-mouse": "Mouse",
            "input-gaming": "Game Controller",
        }.get(icon, "Unknown")
