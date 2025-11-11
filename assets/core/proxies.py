"""
Proxy Manager for connex - Integrated System & Application Proxy
Synchronizes proxy settings across system and connex application
"""
import subprocess
import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple, List

# Configuration
CONFIG_DIR = Path.home() / ".config" / "connex"
PROXY_CONFIG_FILE = CONFIG_DIR / "proxy.json"


class ProxyManager:
    """Manage system and application proxy settings"""
    
    def __init__(self):
        self.config_dir = CONFIG_DIR
        self.config_file = PROXY_CONFIG_FILE
        self.ensure_config_dir()
        self.current_proxy = self.load_config()
    
    def ensure_config_dir(self):
        """Create config directory if it doesn't exist"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create config directory: {e}")
    
    def load_config(self) -> Dict:
        """Load saved proxy configuration"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load config: {e}")
                return {}
        return {}
    
    def save_config(self, config: Dict):
        """Save proxy configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            self.current_proxy = config
        except Exception as e:
            print(f"Warning: Could not save config: {e}")
    
    def set_proxy(self, proxy_type: str, host: str, port: str, 
                  username: str = "", password: str = "", 
                  bypass: str = "localhost,127.0.0.1") -> Tuple[bool, str]:
        """
        Set system proxy with immediate application restart
        proxy_type: 'http', 'https', 'socks4', 'socks5', 'none'
        """
        try:
            if proxy_type == "none":
                return self.disable_proxy()
            
            # Validate inputs
            if not host or not port:
                return False, "Host and port are required"
            
            try:
                port_int = int(port)
                if port_int < 1 or port_int > 65535:
                    return False, "Port must be between 1 and 65535"
            except ValueError:
                return False, "Port must be a number"
            
            # Build proxy URL
            if username and password:
                auth = f"{username}:{password}@"
            else:
                auth = ""
            
            # Determine protocol for URL
            if proxy_type in ['socks4', 'socks5']:
                protocol = proxy_type
            elif proxy_type == 'https':
                protocol = 'https'
            else:
                protocol = 'http'
            
            proxy_url = f"{protocol}://{auth}{host}:{port}"
            
            # Set environment variables (all variations)
            env_vars = {
                'http_proxy': proxy_url,
                'https_proxy': proxy_url,
                'ftp_proxy': proxy_url,
                'HTTP_PROXY': proxy_url,
                'HTTPS_PROXY': proxy_url,
                'FTP_PROXY': proxy_url,
                'no_proxy': bypass,
                'NO_PROXY': bypass,
                'all_proxy': proxy_url,
                'ALL_PROXY': proxy_url
            }
            
            # Apply to current process
            for key, value in env_vars.items():
                os.environ[key] = value
            
            # Save configuration FIRST
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
            
            # Apply to system components
            results = []
            
            # 1. Profile files
            if self._write_profile_files(env_vars):
                results.append("Profile OK")
            
            # 2. Environment.d
            if self._set_environment_d(env_vars):
                results.append("environment.d OK")
            
            # 3. GNOME
            if self._set_gnome_proxy(proxy_type, host, port, username, password, bypass):
                results.append("GNOME OK")
            
            # 4. KDE
            if self._set_kde_proxy(proxy_url, bypass):
                results.append("KDE OK")
            
            # 5. APT (for Debian/Ubuntu)
            if self._set_apt_proxy(proxy_url):
                results.append("APT OK")
            
            # 6. Git
            if self._set_git_proxy(proxy_url):
                results.append("Git OK")
            
            # 7. NPM (if installed)
            if self._set_npm_proxy(proxy_url):
                results.append("NPM OK")
            
            # 8. Docker (if installed)
            if self._set_docker_proxy(proxy_url):
                results.append("Docker OK")
            
            status = f"✓ Proxy configured: {protocol}://{host}:{port}"
            if results:
                status += f"\n  Applied to: {', '.join(results)}"
            
            # Show how to apply immediately
            status += f"\n\n⚠ To apply NOW in current shell:\n  source <(python {sys.argv[0]} export)"
            status += "\n\n⚠ To apply system-wide: Logout/Login required"
            
            return True, status
        
        except Exception as e:
            return False, f"Failed to set proxy: {str(e)}"
    
    def disable_proxy(self) -> Tuple[bool, str]:
        """Disable all proxy settings"""
        try:
            # Clear environment variables
            env_vars_to_clear = [
                'http_proxy', 'https_proxy', 'ftp_proxy',
                'HTTP_PROXY', 'HTTPS_PROXY', 'FTP_PROXY',
                'no_proxy', 'NO_PROXY', 'all_proxy', 'ALL_PROXY'
            ]
            
            for var in env_vars_to_clear:
                os.environ.pop(var, None)
            
            # Remove configuration files
            self._remove_profile_files()
            self._remove_environment_d()
            self._disable_gnome_proxy()
            self._disable_kde_proxy()
            self._remove_apt_proxy()
            self._remove_git_proxy()
            self._remove_npm_proxy()
            self._remove_docker_proxy()
            
            # Save config
            config = {'enabled': False}
            self.save_config(config)
            
            return True, "✓ Proxy disabled (logout/login for full effect)"
        
        except Exception as e:
            return False, f"Failed to disable proxy: {str(e)}"
    
    # ============== PROFILE FILES ==============
    
    def _write_profile_files(self, env_vars: Dict[str, str]) -> bool:
        """Write proxy settings to shell profile files"""
        try:
            proxy_script = "# Connex Proxy Configuration\n"
            proxy_script += "# Auto-generated - DO NOT EDIT MANUALLY\n\n"
            for key, value in env_vars.items():
                proxy_script += f'export {key}="{value}"\n'
            
            # Write to user's profile directory
            profile_dir = Path.home() / ".profile.d"
            profile_dir.mkdir(parents=True, exist_ok=True)
            profile_file = profile_dir / "connex-proxy.sh"
            
            with open(profile_file, 'w') as f:
                f.write(proxy_script)
            
            profile_file.chmod(0o644)
            
            # Update .bashrc
            self._update_shell_rc(".bashrc", profile_file)
            
            # Update .zshrc
            self._update_shell_rc(".zshrc", profile_file)
            
            return True
        except Exception as e:
            print(f"Failed to write profile files: {e}")
            return False
    
    def _update_shell_rc(self, rc_name: str, profile_file: Path):
        """Update shell RC file to source proxy config"""
        rc_file = Path.home() / rc_name
        if rc_file.exists():
            try:
                with open(rc_file, 'r') as f:
                    content = f.read()
                
                marker = "# Connex Proxy Configuration"
                source_line = f"\n{marker}\nif [ -f {profile_file} ]; then\n    . {profile_file}\nfi\n"
                
                if marker not in content:
                    with open(rc_file, 'a') as f:
                        f.write(source_line)
            except Exception as e:
                print(f"Failed to update {rc_name}: {e}")
    
    def _remove_profile_files(self):
        """Remove proxy profile files"""
        try:
            profile_file = Path.home() / ".profile.d" / "connex-proxy.sh"
            if profile_file.exists():
                profile_file.unlink()
        except Exception as e:
            print(f"Failed to remove profile files: {e}")
    
    # ============== ENVIRONMENT.D ==============
    
    def _set_environment_d(self, env_vars: Dict[str, str]) -> bool:
        """Set proxy in systemd user environment"""
        try:
            env_dir = Path.home() / ".config" / "environment.d"
            env_dir.mkdir(parents=True, exist_ok=True)
            
            env_file = env_dir / "connex-proxy.conf"
            
            with open(env_file, 'w') as f:
                f.write("# Connex Proxy Configuration\n")
                for key, value in env_vars.items():
                    f.write(f'{key}={value}\n')
            
            return True
        except Exception as e:
            print(f"Failed to set environment.d: {e}")
            return False
    
    def _remove_environment_d(self):
        """Remove systemd environment file"""
        try:
            env_file = Path.home() / ".config" / "environment.d" / "connex-proxy.conf"
            if env_file.exists():
                env_file.unlink()
        except Exception as e:
            print(f"Failed to remove environment.d: {e}")
    
    # ============== GNOME ==============
    
    def _set_gnome_proxy(self, proxy_type: str, host: str, port: str,
                        username: str, password: str, bypass: str) -> bool:
        """Set GNOME/GSETTINGS proxy"""
        try:
            result = subprocess.run(
                ["which", "gsettings"],
                capture_output=True,
                timeout=2
            )
            if result.returncode != 0:
                return False
            
            # Set mode to manual
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy", "mode", "manual"
            ], check=False, capture_output=True, timeout=2)
            
            # Set HTTP proxy
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy.http", "host", host
            ], check=False, capture_output=True, timeout=2)
            
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy.http", "port", str(port)
            ], check=False, capture_output=True, timeout=2)
            
            # Set HTTPS proxy
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy.https", "host", host
            ], check=False, capture_output=True, timeout=2)
            
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy.https", "port", str(port)
            ], check=False, capture_output=True, timeout=2)
            
            # Set SOCKS proxy if needed
            if proxy_type in ['socks4', 'socks5']:
                subprocess.run([
                    "gsettings", "set", "org.gnome.system.proxy.socks", "host", host
                ], check=False, capture_output=True, timeout=2)
                
                subprocess.run([
                    "gsettings", "set", "org.gnome.system.proxy.socks", "port", str(port)
                ], check=False, capture_output=True, timeout=2)
            
            # Set bypass list
            if bypass:
                bypass_list = [f"'{item.strip()}'" for item in bypass.split(',')]
                bypass_str = "[" + ", ".join(bypass_list) + "]"
                subprocess.run([
                    "gsettings", "set", "org.gnome.system.proxy", "ignore-hosts", bypass_str
                ], check=False, capture_output=True, timeout=2)
            
            # Set authentication
            if username:
                subprocess.run([
                    "gsettings", "set", "org.gnome.system.proxy.http", 
                    "use-authentication", "true"
                ], check=False, capture_output=True, timeout=2)
                
                subprocess.run([
                    "gsettings", "set", "org.gnome.system.proxy.http", 
                    "authentication-user", username
                ], check=False, capture_output=True, timeout=2)
                
                if password:
                    subprocess.run([
                        "gsettings", "set", "org.gnome.system.proxy.http", 
                        "authentication-password", password
                    ], check=False, capture_output=True, timeout=2)
            
            return True
        
        except Exception as e:
            return False
    
    def _disable_gnome_proxy(self) -> bool:
        """Disable GNOME proxy"""
        try:
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy", "mode", "none"
            ], check=False, capture_output=True, timeout=2)
            return True
        except:
            return False
    
    # ============== KDE ==============
    
    def _set_kde_proxy(self, proxy_url: str, bypass: str) -> bool:
        """Set KDE proxy"""
        try:
            result = subprocess.run(
                ["which", "kwriteconfig5"],
                capture_output=True,
                timeout=2
            )
            if result.returncode != 0:
                return False
            
            subprocess.run([
                "kwriteconfig5", "--file", "kioslaverc",
                "--group", "Proxy Settings",
                "--key", "ProxyType", "1"
            ], check=False, capture_output=True, timeout=2)
            
            subprocess.run([
                "kwriteconfig5", "--file", "kioslaverc",
                "--group", "Proxy Settings",
                "--key", "httpProxy", proxy_url
            ], check=False, capture_output=True, timeout=2)
            
            subprocess.run([
                "kwriteconfig5", "--file", "kioslaverc",
                "--group", "Proxy Settings",
                "--key", "httpsProxy", proxy_url
            ], check=False, capture_output=True, timeout=2)
            
            if bypass:
                subprocess.run([
                    "kwriteconfig5", "--file", "kioslaverc",
                    "--group", "Proxy Settings",
                    "--key", "NoProxyFor", bypass
                ], check=False, capture_output=True, timeout=2)
            
            return True
        except:
            return False
    
    def _disable_kde_proxy(self) -> bool:
        """Disable KDE proxy"""
        try:
            subprocess.run([
                "kwriteconfig5", "--file", "kioslaverc",
                "--group", "Proxy Settings",
                "--key", "ProxyType", "0"
            ], check=False, capture_output=True, timeout=2)
            return True
        except:
            return False
    
    # ============== APT ==============
    
    def _set_apt_proxy(self, proxy_url: str) -> bool:
        """Set APT proxy"""
        try:
            apt_conf = Path("/etc/apt/apt.conf.d/95connex-proxy")
            content = f'Acquire::http::Proxy "{proxy_url}";\nAcquire::https::Proxy "{proxy_url}";\n'
            
            # Try to write with sudo
            result = subprocess.run(
                ["sudo", "tee", str(apt_conf)],
                input=content.encode(),
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def _remove_apt_proxy(self):
        """Remove APT proxy"""
        try:
            subprocess.run(
                ["sudo", "rm", "-f", "/etc/apt/apt.conf.d/95connex-proxy"],
                capture_output=True,
                timeout=5
            )
        except:
            pass
    
    # ============== GIT ==============
    
    def _set_git_proxy(self, proxy_url: str) -> bool:
        """Set Git proxy"""
        try:
            subprocess.run(
                ["git", "config", "--global", "http.proxy", proxy_url],
                capture_output=True,
                timeout=2
            )
            subprocess.run(
                ["git", "config", "--global", "https.proxy", proxy_url],
                capture_output=True,
                timeout=2
            )
            return True
        except:
            return False
    
    def _remove_git_proxy(self):
        """Remove Git proxy"""
        try:
            subprocess.run(
                ["git", "config", "--global", "--unset", "http.proxy"],
                capture_output=True,
                timeout=2
            )
            subprocess.run(
                ["git", "config", "--global", "--unset", "https.proxy"],
                capture_output=True,
                timeout=2
            )
        except:
            pass
    
    # ============== NPM ==============
    
    def _set_npm_proxy(self, proxy_url: str) -> bool:
        """Set NPM proxy"""
        try:
            result = subprocess.run(
                ["which", "npm"],
                capture_output=True,
                timeout=2
            )
            if result.returncode != 0:
                return False
            
            subprocess.run(
                ["npm", "config", "set", "proxy", proxy_url],
                capture_output=True,
                timeout=2
            )
            subprocess.run(
                ["npm", "config", "set", "https-proxy", proxy_url],
                capture_output=True,
                timeout=2
            )
            return True
        except:
            return False
    
    def _remove_npm_proxy(self):
        """Remove NPM proxy"""
        try:
            subprocess.run(
                ["npm", "config", "delete", "proxy"],
                capture_output=True,
                timeout=2
            )
            subprocess.run(
                ["npm", "config", "delete", "https-proxy"],
                capture_output=True,
                timeout=2
            )
        except:
            pass
    
    # ============== DOCKER ==============
    
    def _set_docker_proxy(self, proxy_url: str) -> bool:
        """Set Docker proxy"""
        try:
            docker_dir = Path.home() / ".docker"
            docker_dir.mkdir(parents=True, exist_ok=True)
            
            config_file = docker_dir / "config.json"
            
            config = {}
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
            
            config['proxies'] = {
                'default': {
                    'httpProxy': proxy_url,
                    'httpsProxy': proxy_url,
                    'noProxy': 'localhost,127.0.0.1'
                }
            }
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            return True
        except:
            return False
    
    def _remove_docker_proxy(self):
        """Remove Docker proxy"""
        try:
            config_file = Path.home() / ".docker" / "config.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                if 'proxies' in config:
                    del config['proxies']
                
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)
        except:
            pass
    
    # ============== UTILITY FUNCTIONS ==============
    
    def get_current_proxy(self) -> Dict:
        """Get current proxy configuration"""
        return self.current_proxy.copy()
    
    def test_proxy(self, host: str = None, port: str = None) -> Tuple[bool, str]:
        """Test if proxy is working"""
        try:
            import socket
            
            if host is None or port is None:
                if not self.current_proxy.get('enabled'):
                    return False, "No proxy configured"
                host = self.current_proxy.get('host')
                port = self.current_proxy.get('port')
            
            if not host or not port:
                return False, "Invalid proxy configuration"
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, int(port)))
            sock.close()
            
            if result == 0:
                return True, f"✓ Proxy {host}:{port} is reachable"
            else:
                return False, f"✗ Proxy {host}:{port} is not reachable"
        
        except Exception as e:
            return False, f"✗ Test failed: {str(e)}"
    
    def export_to_shell(self) -> str:
        """Export proxy settings as shell commands"""
        if not self.current_proxy.get('enabled'):
            return "# No proxy configured\nunset http_proxy https_proxy ftp_proxy HTTP_PROXY HTTPS_PROXY FTP_PROXY no_proxy NO_PROXY all_proxy ALL_PROXY\n"
        
        env_vars = self.current_proxy.get('env_vars', {})
        commands = ["# Connex Proxy Configuration - Apply to current shell"]
        
        for key, value in env_vars.items():
            commands.append(f'export {key}="{value}"')
        
        commands.append("\necho '✓ Proxy applied to current shell'")
        
        return '\n'.join(commands)
    
    def get_status_text(self) -> str:
        """Get human-readable proxy status"""
        if not self.current_proxy.get('enabled'):
            return "✗ No proxy configured"
        
        proxy_type = self.current_proxy.get('type', 'unknown')
        host = self.current_proxy.get('host', '')
        port = self.current_proxy.get('port', '')
        username = self.current_proxy.get('username', '')
        
        status = f"✓ {proxy_type.upper()} proxy: {host}:{port}"
        if username:
            status += f" (user: {username})"
        
        return status
    
    def get_proxy_presets(self) -> Dict[str, Dict]:
        """Get common proxy presets"""
        return {
            "None": {
                "type": "none",
                "host": "",
                "port": "",
                "description": "Direct connection (no proxy)"
            },
            "HTTP": {
                "type": "http",
                "host": "127.0.0.1",
                "port": "8080",
                "description": "Standard HTTP proxy"
            },
            "HTTPS": {
                "type": "https",
                "host": "127.0.0.1",
                "port": "10808",
                "description": "HTTPS proxy (like in screenshot)"
            },
            "SOCKS5": {
                "type": "socks5",
                "host": "127.0.0.1",
                "port": "1080",
                "description": "SOCKS5 proxy"
            },
            "Tor": {
                "type": "socks5",
                "host": "127.0.0.1",
                "port": "9050",
                "description": "Tor SOCKS5 proxy"
            }
        }


# ============== CLI INTERFACE ==============

def cli_proxy():
    """CLI interface for proxy management"""
    pm = ProxyManager()
    
    if len(sys.argv) < 2:
        print("╔══════════════════════════════════════════════╗")
        print("║            Connex Proxy Manager              ║")
        print("╚══════════════════════════════════════════════╝")
        print("\n📋 Usage:")
        print("  status                                - Show current proxy")
        print("  set <type> <host> <port> [user] [pass] - Set proxy")
        print("  disable                               - Disable proxy")
        print("  test [host] [port]                    - Test proxy")
        print("  export                                - Export shell commands")
        print("  apply                                 - Show how to apply")
        print("  presets                               - Show presets")
        print("\nProxy types: http, https, socks4, socks5")
        print("\nQuick start:")
        print("  python proxy.py set https 127.0.0.1 10808")
        print("  source <(python proxy.py export)")
        return
    
    action = sys.argv[1]
    
    if action == "status":
        print(pm.get_status_text())
        config = pm.get_current_proxy()
        if config.get('enabled'):
            print(f"\nDetails:")
            print(f"  Type: {config.get('type')}")
            print(f"  Host: {config.get('host')}")
            print(f"  Port: {config.get('port')}")
            print(f"  Bypass: {config.get('bypass', 'N/A')}")
            if config.get('username'):
                print(f"  Username: {config.get('username')}")
    
    elif action == "set":
        if len(sys.argv) < 5:
            print("Error: Missing arguments")
            print("Usage: proxy.py set <type> <host> <port> [username] [password]")
            return
        
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
    
    elif action == "test":
        if len(sys.argv) >= 4:
            host = sys.argv[2]
            port = sys.argv[3]
            success, msg = pm.test_proxy(host, port)
        else:
            success, msg = pm.test_proxy()
        print(msg)
    
    elif action == "export":
        print(pm.export_to_shell())
    
    elif action == "apply":
        config = pm.get_current_proxy()
        if not config.get('enabled'):
            print("No proxy configured")
            return
        
        print("To apply proxy to current terminal:")
        print(f"\n  source <(python {sys.argv[0]} export)")
        print("\nOr copy and paste these commands:")
        print(pm.export_to_shell())
    
    elif action == "presets":
        print("Available presets:\n")
        presets = pm.get_proxy_presets()
        for name, preset in presets.items():
            print(f"  {name}:")
            print(f"    Type: {preset['type']}")
            if preset['host']:
                print(f"    Host: {preset['host']}")
            if preset['port']:
                print(f"    Port: {preset['port']}")
            print(f"    Description: {preset['description']}")
            print()
    
    else:
        print(f"Unknown command: {action}")
        print("Run without arguments to see usage")


if __name__ == "__main__":
    cli_proxy()