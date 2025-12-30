# 🔴 This is the DEV branch  🔴
> [!NOTE]
> This branch is not as stable as master is. It contain things/ features that are WIP and may be unstable
# connex - Modern Wi-Fi Manager

**Connex** is a modern and intuitive **Wi-Fi manager** for **Linux**, powered by NetworkManager, offering a clean interface, a full **CLI mode**, seamless **desktop integration**, **VPN and proxy management**, hidden network support, **QR-code pairing**, and even a **built-in speedtest** for a complete networking experience.


## Features

- Simple and modern interface  
- Connect, disconnect, and manage Wi-Fi networks  
- Hidden network support  
- Connection history  
- Built-in speedtest  
- Command-line mode 
- QR code connection 
- Proxy system 
- VPN Management (WIP)

## Installation

You can install using this one-line command (recommended):
```bash
curl -sSL https://raw.githubusercontent.com/Lluciocc/connex/master/install.sh | bash -s -- --clone
```

You can also install it manually by cloning the repository and running the installer:
```bash
git clone https://github.com/lluciocc/connex.git
cd connex
chmod +x ./install.sh
./install.sh
```

## Compatibility

| Distribution        | Status |
| ------------------- | :----: |
| Arch Linux          |   ✅   |
| Linux Mint          |   ✅   |
| Ubuntu              |   ✅   |
| Debian              |   ❓   |
| Fedora              |   ❓   |
| openSUSE            |   ❓   |
| Manjaro             |   ❓   |
| Pop!_OS             |   ❓   |
| Elementary OS       |   ❓   |
| Zorin OS            |   ❓   |
| Kali Linux          |   ❓   |
| EndeavourOS         |   ❓   |
| Rocky Linux         |   ❓   |

> [!NOTE]
> Everything marked with ❓ has not been tested yet, your help would be greatly appreciated!

## Usage

### GUI Mode
```bash
# Launch main window
connex

# Launch with debug logging
connex --debug

# Launch in system tray and window
connex --tray

# Launch only the tray
connex --tray-only
```

### CLI Mode
```bash
# List available networks
connex --cli list

# Connect to a network
connex --cli connect --ssid "MyNetwork" --password "mypassword"

# Disconnect from current network
connex --cli disconnect --ssid "MyNetwork"

# Show connection status
connex --cli status

# Run a speedtest
connex --cli speedtest
```

### Troubleshooting
```bash
#Enable Debug Mode
connex --debug

# Launch without automatic scan
connex --no-scan
```

## Configuration

connex stores its configuration and logs in:
- **Config Directory**: `~/.config/connex/`
- **Connection History**: `~/.config/connex/history.log`

## Dependencies

- `python` (>=3.9)
- `python-gobject`
- `gtk3`
- `networkmanager`
- `libappindicator-gtk3`
- `libnotify`
- `python-qrcode`

### Optional Dependencies
- `papirus-icon-theme` - For better icon aesthetics
- `hyprland` - Recommended window manager

## Keyboard Shortcuts

- **CTRL + H** - Open Hidden Network  dialog
- **CTRL + R** - Refresh the network list
- **CTRL + F** - Focus on the search bar
- **CTRL + Q** - Quit

## Screenshot
![screenshot](https://github.com/Lluciocc/connex/blob/271480cd7ee49023c803a679a88d3709e1ee6b71/screenshot01.png)
![screenshot](https://github.com/Lluciocc/connex/blob/master/screenshot02.jpg)


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support
If you like my work, please consider buying me a coffee :)

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/L3L01E41M0)
<a href="https://buymeacoffee.com/lluciocc" target="_blank">
    <img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="50">
</a>


**Made with ❤️ for the Linux communities**
