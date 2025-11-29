# connex - Modern Wi-Fi Manager

**Connex** is a modern Wi-Fi manager **Linux**, built with **NetworkManager**.  
It provides a clean interface, CLI mode, and smooth integration with Linux desktops.


## Features

- Simple and modern GTK3 interface  
- Connect, disconnect, and manage Wi-Fi networks  
- Hidden network support  
- Connection history  
- Built-in speedtest  
- Command-line mode 
- QR code connection 
- Proxy system (WIP)

## Installation

### From AUR
```bash
yay -S connex
# or
paru -S connex
```

### Manual installation
If you don’t use an AUR helper, you can install using this one-line command (recommended):
```bash
curl -sSL https://raw.githubusercontent.com/Lluciocc/connex/master/install.sh | bash
```

You can also install it manually by cloning the repository and running the installer:
```bash
git clone https://github.com/lluciocc/connex.git
cd connex
chmod +x ./install.sh
./install.sh
```

### Build from source
If you prefer to build the package yourselfs:
```bash
git clone https://github.com/lluciocc/connex.git
cd connex
makepkg -si
```

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
