import subprocess
import shlex
from typing import List, Dict, Optional, Tuple
from assets.utils.debug import log_debug

# sudo pacman -S networkmanager openvpn networkmanager-openvpn wireguard-tools

class VPNManager:
    @staticmethod
    def run_cmd(cmd: str, timeout: int = 10) -> Tuple[int, str, str]:
        try:
            log_debug(f"VPN cmd: {cmd}")
            result = subprocess.run(
                shlex.split(cmd),
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
    def get_vpn_list() -> List[Dict[str, str]]:
        code, out, err = VPNManager.run_cmd(
            "nmcli -t -f NAME,TYPE,UUID,DEVICE connection show"
        )
        
        vpns = []
        if code == 0:
            for line in out.splitlines():
                if not line.strip():
                    continue
                parts = line.split(':')
                if len(parts) >= 2:
                    conn_type = parts[1]
                    if 'vpn' in conn_type.lower() or 'wireguard' in conn_type.lower():
                        vpns.append({
                            'name': parts[0],
                            'type': conn_type,
                            'uuid': parts[2] if len(parts) > 2 else '',
                            'device': parts[3] if len(parts) > 3 else '',
                            'connected': bool(parts[3]) if len(parts) > 3 else False
                        })
        
        log_debug(f"Found {len(vpns)} VPN connections")
        return vpns
    
    @staticmethod
    def get_active_vpn() -> Optional[str]:
        code, out, err = VPNManager.run_cmd(
            "nmcli -t -f NAME,TYPE connection show --active"
        )
        
        if code == 0:
            for line in out.splitlines():
                parts = line.split(':')
                if len(parts) >= 2 and 'vpn' in parts[1].lower():
                    return parts[0]
        return None
    
    @staticmethod
    def connect_vpn(name: str) -> Tuple[bool, str]:
        code, out, err = VPNManager.run_cmd(f"nmcli connection up '{name}'", timeout=30)
        
        if code == 0:
            return True, f"Connected to {name}"
        else:
            error = err or out
            if "already active" in error.lower():
                return True, f"{name} is already connected"
            return False, error or "Connection failed"
    
    @staticmethod
    def disconnect_vpn(name: str) -> Tuple[bool, str]:
        code, out, err = VPNManager.run_cmd(f"nmcli connection down '{name}'")
        
        if code == 0:
            return True, f"Disconnected from {name}"
        else:
            return False, err or "Disconnect failed"
    
    @staticmethod
    def delete_vpn(name: str) -> Tuple[bool, str]:
        code, out, err = VPNManager.run_cmd(f"nmcli connection delete '{name}'")
        
        if code == 0:
            return True, f"Deleted {name}"
        else:
            return False, err or "Delete failed"
    
    @staticmethod
    def get_vpn_details(name: str) -> Dict[str, str]:
        code, out, err = VPNManager.run_cmd(f"nmcli -s connection show '{name}'")
        
        details = {}
        if code == 0:
            for line in out.splitlines():
                if ':' in line:
                    key, val = line.split(':', 1)
                    key = key.strip()
                    val = val.strip()
                    
                    # Filter relevant VPN settings
                    if any(x in key.lower() for x in ['vpn', 'connection', 'ipv4', 'gateway', 'server']):
                        details[key] = val
        
        return details
    
    @staticmethod
    def import_openvpn(config_path: str, name: str) -> Tuple[bool, str]:
        code, out, err = VPNManager.run_cmd(
            f"nmcli connection import type openvpn file '{config_path}'"
        )
        
        if code == 0:
            # Rename if name provided
            if name:
                imported_name = out.split("'")[1] if "'" in out else ""
                if imported_name:
                    VPNManager.run_cmd(f"nmcli connection modify '{imported_name}' connection.id '{name}'")
            return True, "OpenVPN config imported successfully"
        else:
            return False, err or "Import failed"
    
    @staticmethod
    def create_wireguard(name: str, config: Dict[str, str]) -> Tuple[bool, str]:
        cmd = f"nmcli connection add type wireguard con-name '{name}' ifname '{name}'"
        code, out, err = VPNManager.run_cmd(cmd)
        
        if code != 0:
            return False, err or "Failed to create WireGuard connection"
        
        # Configure WireGuard settings
        if 'private_key' in config:
            VPNManager.run_cmd(
                f"nmcli connection modify '{name}' wireguard.private-key '{config['private_key']}'"
            )
        
        if 'address' in config:
            VPNManager.run_cmd(
                f"nmcli connection modify '{name}' ipv4.addresses '{config['address']}'"
            )
        
        if 'peer' in config:
            VPNManager.run_cmd(
                f"nmcli connection modify '{name}' wireguard.peer '{config['peer']}'"
            )
        
        return True, f"WireGuard VPN '{name}' created"
    
    @staticmethod
    def get_vpn_status(name: str) -> Dict[str, any]:
        """Get VPN connection status and statistics"""
        active = VPNManager.get_active_vpn()
        is_active = (active == name)
        
        status = {
            'connected': is_active,
            'name': name,
            'ip': None,
            'gateway': None,
            'dns': [],
            'uptime': None
        }
        
        if is_active:
            # Get IP info
            code, out, err = VPNManager.run_cmd(f"nmcli -t -f IP4.ADDRESS connection show '{name}'")
            if code == 0 and out:
                status['ip'] = out.split(':')[1] if ':' in out else out
            
            # Get gateway
            code, out, err = VPNManager.run_cmd(f"nmcli -t -f IP4.GATEWAY connection show '{name}'")
            if code == 0 and out:
                status['gateway'] = out.split(':')[1] if ':' in out else out
            
            # Get DNS
            code, out, err = VPNManager.run_cmd(f"nmcli -t -f IP4.DNS connection show '{name}'")
            if code == 0 and out:
                for line in out.splitlines():
                    dns = line.split(':')[1] if ':' in line else line
                    if dns:
                        status['dns'].append(dns)
        
        return status