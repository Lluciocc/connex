import subprocess
import shlex
from typing import List, Dict, Optional, Tuple
from assets.utils.debug import log_debug


class BluetoothManager:
    @staticmethod
    def run_cmd(cmd: str, timeout: int = 10) -> Tuple[int, str, str]:
        try:
            log_debug(f"BT cmd: {cmd}")
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except Exception as e:
            return 1, "", str(e)
    
    @staticmethod
    def is_bluetooth_available() -> bool:
        code, out, err = BluetoothManager.run_cmd("bluetoothctl show")
        return code == 0 and out
    
    @staticmethod
    def get_bluetooth_state() -> bool:
        code, out, err = BluetoothManager.run_cmd("bluetoothctl show")
        if code == 0:
            for line in out.splitlines():
                if "Powered:" in line:
                    return "yes" in line.lower()
        return False
    
    @staticmethod
    def set_bluetooth_state(enabled: bool) -> Tuple[bool, str]:
        cmd = "bluetoothctl power on" if enabled else "bluetoothctl power off"
        code, out, err = BluetoothManager.run_cmd(cmd, timeout=5)
        
        if code == 0 or "succeeded" in out.lower():
            state = "enabled" if enabled else "disabled"
            return True, f"Bluetooth {state}"
        else:
            return False, err or "Failed to change bluetooth state"
    
    @staticmethod
    def get_discoverable_state() -> bool:
        code, out, err = BluetoothManager.run_cmd("bluetoothctl show")
        if code == 0:
            for line in out.splitlines():
                if "Discoverable:" in line:
                    return "yes" in line.lower()
        return False
    
    @staticmethod
    def set_discoverable(enabled: bool) -> Tuple[bool, str]:
        cmd = "bluetoothctl discoverable on" if enabled else "bluetoothctl discoverable off"
        code, out, err = BluetoothManager.run_cmd(cmd, timeout=5)
        
        if code == 0 or "succeeded" in out.lower():
            return True, "Discoverable mode updated"
        else:
            return False, err or "Failed to change discoverable mode"
    
    @staticmethod
    def start_scan() -> Tuple[bool, str]:
        # Start scan in background
        subprocess.Popen(
            ["bluetoothctl", "scan", "on"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True, "Scanning started"
    
    @staticmethod
    def stop_scan() -> Tuple[bool, str]:
        code, out, err = BluetoothManager.run_cmd("bluetoothctl scan off", timeout=3)
        return True, "Scanning stopped"
    
    @staticmethod
    def get_devices() -> List[Dict[str, str]]:
        devices = []
        
        # Get paired devices
        code, out, err = BluetoothManager.run_cmd("bluetoothctl devices Paired")
        paired_macs = set()
        
        if code == 0:
            for line in out.splitlines():
                if line.startswith("Device"):
                    parts = line.split(maxsplit=2)
                    if len(parts) >= 3:
                        mac = parts[1]
                        name = parts[2]
                        paired_macs.add(mac)
                        
                        # Get device info
                        info = BluetoothManager.get_device_info(mac)
                        devices.append({
                            'mac': mac,
                            'name': name,
                            'paired': True,
                            'connected': info.get('connected', False),
                            'trusted': info.get('trusted', False),
                            'type': info.get('type', 'Unknown'),
                            'rssi': info.get('rssi', ''),
                            'battery': info.get('battery', '')
                        })
        
        # Get all discovered devices (including unpaired)
        code, out, err = BluetoothManager.run_cmd("bluetoothctl devices")
        
        if code == 0:
            for line in out.splitlines():
                if line.startswith("Device"):
                    parts = line.split(maxsplit=2)
                    if len(parts) >= 3:
                        mac = parts[1]
                        name = parts[2]
                        
                        # Skip if already added as paired
                        if mac in paired_macs:
                            continue
                        
                        info = BluetoothManager.get_device_info(mac)
                        devices.append({
                            'mac': mac,
                            'name': name,
                            'paired': False,
                            'connected': False,
                            'trusted': False,
                            'type': info.get('type', 'Unknown'),
                            'rssi': info.get('rssi', ''),
                            'battery': ''
                        })
        
        log_debug(f"Found {len(devices)} bluetooth devices")
        return devices
    
    @staticmethod
    def get_device_info(mac: str) -> Dict[str, any]:
        code, out, err = BluetoothManager.run_cmd(f"bluetoothctl info {mac}")
        
        info = {
            'connected': False,
            'paired': False,
            'trusted': False,
            'type': 'Unknown',
            'rssi': '',
            'battery': ''
        }
        
        if code == 0:
            for line in out.splitlines():
                line = line.strip()
                
                if "Connected:" in line:
                    info['connected'] = "yes" in line.lower()
                elif "Paired:" in line:
                    info['paired'] = "yes" in line.lower()
                elif "Trusted:" in line:
                    info['trusted'] = "yes" in line.lower()
                elif "Icon:" in line:
                    icon = line.split(":", 1)[1].strip()
                    info['type'] = BluetoothManager.icon_to_type(icon)
                elif "RSSI:" in line:
                    try:
                        rssi = line.split(":", 1)[1].strip()
                        info['rssi'] = f"{rssi} dBm"
                    except:
                        pass
                elif "Battery Percentage:" in line:
                    try:
                        battery = line.split(":", 1)[1].strip()
                        info['battery'] = battery
                    except:
                        pass
        
        return info
    
    @staticmethod
    def icon_to_type(icon: str) -> str:
        type_map = {
            'audio-card': 'Audio',
            'audio-headset': 'Headset',
            'audio-headphones': 'Headphones',
            'phone': 'Phone',
            'computer': 'Computer',
            'input-gaming': 'Game Controller',
            'input-keyboard': 'Keyboard',
            'input-mouse': 'Mouse',
            'input-tablet': 'Tablet',
            'camera-photo': 'Camera',
            'printer': 'Printer',
            'network-wireless': 'Network'
        }
        return type_map.get(icon, icon.replace('-', ' ').title())
    
    @staticmethod
    def pair_device(mac: str) -> Tuple[bool, str]:
        code, out, err = BluetoothManager.run_cmd(f"bluetoothctl pair {mac}", timeout=30)
        
        if code == 0 or "successful" in out.lower() or "already paired" in out.lower():
            return True, "Device paired successfully"
        else:
            error = err or out
            if "No such device" in error:
                return False, "Device not found"
            elif "Connection refused" in error:
                return False, "Device refused pairing"
            elif "Authentication" in error:
                return False, "Authentication failed"
            else:
                return False, error or "Pairing failed"
    
    @staticmethod
    def connect_device(mac: str) -> Tuple[bool, str]:
        code, out, err = BluetoothManager.run_cmd(f"bluetoothctl connect {mac}", timeout=20)
        
        if code == 0 or "successful" in out.lower():
            return True, "Device connected"
        else:
            error = err or out
            if "Failed to connect" in error:
                return False, "Connection failed - device may be out of range"
            elif "not available" in error:
                return False, "Device not available"
            else:
                return False, error or "Connection failed"
    
    @staticmethod
    def disconnect_device(mac: str) -> Tuple[bool, str]:
        code, out, err = BluetoothManager.run_cmd(f"bluetoothctl disconnect {mac}", timeout=10)
        
        if code == 0 or "successful" in out.lower():
            return True, "Device disconnected"
        else:
            return False, err or "Disconnect failed"
    
    @staticmethod
    def trust_device(mac: str, trust: bool = True) -> Tuple[bool, str]:
        cmd = f"bluetoothctl trust {mac}" if trust else f"bluetoothctl untrust {mac}"
        code, out, err = BluetoothManager.run_cmd(cmd, timeout=5)
        
        if code == 0 or "succeeded" in out.lower():
            action = "trusted" if trust else "untrusted"
            return True, f"Device {action}"
        else:
            return False, err or "Failed to change trust status"
    
    @staticmethod
    def remove_device(mac: str) -> Tuple[bool, str]:
        code, out, err = BluetoothManager.run_cmd(f"bluetoothctl remove {mac}", timeout=10)
        
        if code == 0 or "removed" in out.lower():
            return True, "Device removed"
        else:
            return False, err or "Failed to remove device"
    
    @staticmethod
    def get_adapter_info() -> Dict[str, str]:
        code, out, err = BluetoothManager.run_cmd("bluetoothctl show")
        
        info = {
            'name': 'Bluetooth',
            'address': '',
            'powered': False,
            'discoverable': False,
            'pairable': False
        }
        
        if code == 0:
            for line in out.splitlines():
                line = line.strip()
                
                if line.startswith("Controller"):
                    info['address'] = line.split()[1]
                elif "Name:" in line:
                    info['name'] = line.split(":", 1)[1].strip()
                elif "Powered:" in line:
                    info['powered'] = "yes" in line.lower()
                elif "Discoverable:" in line:
                    info['discoverable'] = "yes" in line.lower()
                elif "Pairable:" in line:
                    info['pairable'] = "yes" in line.lower()
        
        return info