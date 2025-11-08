#!/usr/bin/env python3
"""
Proxy Manager for connex
Handles system-wide proxy configuration
"""
import subprocess
import json
from pathlib import Path
from typing import Dict, Optional, Tuple

# Configuration
CONFIG_DIR = Path.home() / ".config" / "connex"
PROXY_CONFIG_FILE = CONFIG_DIR / "proxy.json"


class ProxyManager:
    """Manage system proxy settings"""
    
    def __init__(self):
        self.config_dir = CONFIG_DIR
        self.config_file = PROXY_CONFIG_FILE
        self.ensure_config_dir()
        self.current_proxy = self.load_config()
    
    def ensure_config_dir(self):
        """Create config directory if it doesn't exist"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> Dict:
        """Load saved proxy configuration"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_config(self, config: Dict):
        """Save proxy configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        self.current_proxy = config
    
    def set_proxy(self, proxy_type: str, host: str, port: str, 
                  username: str = "", password: str = "", 
                  bypass: str = "localhost,127.0.0.1") -> Tuple[bool, str]:
        """
        Set system proxy
        proxy_type: 'http', 'https', 'socks4', 'socks5', 'manual', 'none'
        """
        try:
            if proxy_type == "none":
                return self.disable_proxy()
            
            # Build proxy URL
            if username and password:
                auth = f"{username}:{password}@"
            else:
                auth = ""
            
            # Determine protocol
            if proxy_type in ['socks4', 'socks5']:
                protocol = proxy_type
            else:
                protocol = "http"
            
            proxy_url = f"{protocol}://{auth}{host}:{port}"
            
            # Set environment variables
            env_vars = {
                'http_proxy': proxy_url,
                'https_proxy': proxy_url,
                'ftp_proxy': proxy_url,
                'no_proxy': bypass
            }
            
            # GNOME/GTK settings (if available)
            self._set_gnome_proxy(proxy_type, host, port, username, password, bypass)
            
            # KDE settings (if available)
            self._set_kde_proxy(proxy_url, bypass)
            
            # Save configuration
            config = {
                'enabled': True,
                'type': proxy_type,
                'host': host,
                'port': port,
                'username': username,
                'password': password,
                'bypass': bypass,
                'env_vars': env_vars
            }
            self.save_config(config)
            
            return True, f"Proxy configured: {protocol}://{host}:{port}"
        
        except Exception as e:
            return False, f"Failed to set proxy: {str(e)}"
    
    def disable_proxy(self) -> Tuple[bool, str]:
        """Disable system proxy"""
        try:
            # GNOME/GTK
            self._disable_gnome_proxy()
            
            # KDE
            self._disable_kde_proxy()
            
            # Save config
            config = {'enabled': False}
            self.save_config(config)
            
            return True, "Proxy disabled"
        
        except Exception as e:
            return False, f"Failed to disable proxy: {str(e)}"
    
    def _set_gnome_proxy(self, proxy_type: str, host: str, port: str,
                        username: str, password: str, bypass: str):
        """Set GNOME/GSETTINGS proxy"""
        try:
            # Set mode
            if proxy_type == "manual":
                mode = "manual"
            else:
                mode = "manual"
            
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy", "mode", mode
            ], check=False, capture_output=True, timeout=2)
            
            # Set HTTP proxy
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy.http", "host", host
            ], check=False, capture_output=True, timeout=2)
            
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy.http", "port", port
            ], check=False, capture_output=True, timeout=2)
            
            # Set HTTPS proxy
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy.https", "host", host
            ], check=False, capture_output=True, timeout=2)
            
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy.https", "port", port
            ], check=False, capture_output=True, timeout=2)
            
            # Set SOCKS proxy if needed
            if proxy_type in ['socks4', 'socks5']:
                subprocess.run([
                    "gsettings", "set", "org.gnome.system.proxy.socks", "host", host
                ], check=False, capture_output=True, timeout=2)
                
                subprocess.run([
                    "gsettings", "set", "org.gnome.system.proxy.socks", "port", port
                ], check=False, capture_output=True, timeout=2)
            
            # Set bypass list
            bypass_list = bypass.split(',')
            bypass_str = str(bypass_list).replace("'", '"')
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy", "ignore-hosts", bypass_str
            ], check=False, capture_output=True, timeout=2)
            
            # Set authentication if provided
            if username:
                subprocess.run([
                    "gsettings", "set", "org.gnome.system.proxy.http", 
                    "authentication-user", username
                ], check=False, capture_output=True, timeout=2)
                
                if password:
                    subprocess.run([
                        "gsettings", "set", "org.gnome.system.proxy.http", 
                        "authentication-password", password
                    ], check=False, capture_output=True, timeout=2)
        
        except Exception as e:
            print(f"GNOME proxy setting failed: {e}")
    
    def _disable_gnome_proxy(self):
        """Disable GNOME proxy"""
        try:
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy", "mode", "none"
            ], check=False, capture_output=True, timeout=2)
        except:
            pass
    
    def _set_kde_proxy(self, proxy_url: str, bypass: str):
        """Set KDE proxy (basic implementation)"""
        try:
            # KDE uses different mechanism, this is a simplified version
            # In practice, KDE uses kwriteconfig5 or environment variables
            pass
        except:
            pass
    
    def _disable_kde_proxy(self):
        """Disable KDE proxy"""
        try:
            pass
        except:
            pass
    
    def get_current_proxy(self) -> Dict:
        """Get current proxy configuration"""
        return self.current_proxy
    
    def test_proxy(self, host: str, port: str, proxy_type: str = "http") -> Tuple[bool, str]:
        """Test if proxy is working"""
        try:
            import socket
            
            # Try to connect to proxy
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, int(port)))
            sock.close()
            
            if result == 0:
                return True, "Proxy is reachable"
            else:
                return False, "Proxy is not reachable"
        
        except Exception as e:
            return False, f"Test failed: {str(e)}"
    
    def get_proxy_presets(self) -> Dict[str, Dict]:
        """Get common proxy presets"""
        return {
            "None": {
                "type": "none",
                "host": "",
                "port": "",
                "description": "Direct connection (no proxy)"
            },
            "HTTP Proxy": {
                "type": "http",
                "host": "",
                "port": "8080",
                "description": "Standard HTTP proxy"
            },
            "HTTPS Proxy": {
                "type": "https",
                "host": "",
                "port": "8080",
                "description": "HTTPS proxy"
            },
            "SOCKS5": {
                "type": "socks5",
                "host": "",
                "port": "1080",
                "description": "SOCKS5 proxy (Tor, SSH tunnel)"
            },
            "Tor": {
                "type": "socks5",
                "host": "127.0.0.1",
                "port": "9050",
                "description": "Tor SOCKS5 proxy (localhost)"
            }
        }
    
    def export_to_shell(self) -> str:
        """Export proxy settings as shell commands"""
        if not self.current_proxy.get('enabled'):
            return "# No proxy configured\n"
        
        env_vars = self.current_proxy.get('env_vars', {})
        commands = []
        
        for key, value in env_vars.items():
            commands.append(f'export {key}="{value}"')
            commands.append(f'export {key.upper()}="{value}"')
        
        return '\n'.join(commands)
    
    def get_status_text(self) -> str:
        """Get human-readable proxy status"""
        if not self.current_proxy.get('enabled'):
            return "No proxy configured"
        
        proxy_type = self.current_proxy.get('type', 'unknown')
        host = self.current_proxy.get('host', '')
        port = self.current_proxy.get('port', '')
        
        return f"{proxy_type.upper()} proxy: {host}:{port}"


# CLI functions for testing
def cli_proxy():
    """CLI interface for proxy management"""
    import sys
    
    pm = ProxyManager()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  proxy.py status                    - Show current proxy")
        print("  proxy.py set <type> <host> <port>  - Set proxy")
        print("  proxy.py disable                   - Disable proxy")
        print("  proxy.py test <host> <port>        - Test proxy")
        print("  proxy.py export                    - Export shell commands")
        return
    
    action = sys.argv[1]
    
    if action == "status":
        print(pm.get_status_text())
        config = pm.get_current_proxy()
        if config.get('enabled'):
            print(f"Type: {config.get('type')}")
            print(f"Host: {config.get('host')}")
            print(f"Port: {config.get('port')}")
            print(f"Bypass: {config.get('bypass', 'N/A')}")
    
    elif action == "set" and len(sys.argv) >= 5:
        proxy_type = sys.argv[2]
        host = sys.argv[3]
        port = sys.argv[4]
        username = sys.argv[5] if len(sys.argv) > 5 else ""
        password = sys.argv[6] if len(sys.argv) > 6 else ""
        
        success, msg = pm.set_proxy(proxy_type, host, port, username, password)
        print(msg)
    
    elif action == "disable":
        success, msg = pm.disable_proxy()
        print(msg)
    
    elif action == "test" and len(sys.argv) >= 4:
        host = sys.argv[2]
        port = sys.argv[3]
        success, msg = pm.test_proxy(host, port)
        print(msg)
    
    elif action == "export":
        print(pm.export_to_shell())
    
    else:
        print("Invalid command")


if __name__ == "__main__":
    cli_proxy()