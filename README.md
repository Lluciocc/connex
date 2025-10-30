# connex - Modern Wi-Fi Manager

A beautiful and modern Wi-Fi manager designed for Hyprland and ArchLinux, built with GTK3 and NetworkManager.

## ✨ Features

- 🎨 **Modern GTK3 Interface** - Clean, dark-themed UI designed for Hyprland
- 🔒 **Secure Password Handling** - Visual password strength indicator with revealer animation
- 📡 **Network Management** - Connect, disconnect, and forget networks with ease
- 🔍 **Smart Search** - Real-time network filtering
- 🌐 **Hidden Network Support** - Connect to hidden SSIDs
- 🔔 **Desktop Notifications** - Connection status updates
- 📊 **Connection History** - Full log of all connection attempts with timestamps
- 🎯 **System Tray Integration** - AppIndicator for quick access
- 🌐 **Internet Connectivity Check** - Automatic ping test after connection
- 🎨 **Adaptive Theming** - Auto-detects system dark/light theme preference
- 💻 **CLI Mode** - Script-friendly command-line interface
- 🐛 **Debug Mode** - Detailed logging for troubleshooting

## 📦 Installation

### From AUR
```bash
yay -S connex
# or
paru -S connex
```

### Manual Installation
```bash
git clone https://github.com/lluciocc/connex.git
cd connex
makepkg -si
```

## 🚀 Usage

### GUI Mode
```bash
# Launch main window
connex

# Launch with debug logging
connex --debug

# Launch in system tray
connex --tray
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
```

## ⚙️ Configuration

connex stores its configuration and logs in:
- **Config Directory**: `~/.config/connex/`
- **Connection History**: `~/.config/connex/history.log`

## 🔧 Dependencies

- `python` (>=3.9)
- `python-gobject`
- `gtk3`
- `networkmanager`
- `libappindicator-gtk3`
- `libnotify`

### Optional Dependencies
- `papirus-icon-theme` - For better icon aesthetics
- `hyprland` - Recommended window manager

## ⌨️ Keyboard Shortcuts

- **Double-click** - Connect to network
- **Right-click** - Context menu (Connect/Disconnect/Forget)

## 🎨 Features in Detail

### Password Dialog
- Secure password entry with show/hide toggle
- Real-time password strength indicator
- Smooth reveal animation using GTK Revealer

### System Tray
- Quick access to main window
- Fast network scanning
- Connection status indicator
- Right-click menu for common actions

### Connection History
- Timestamped log of all connections
- Success/failure status
- Signal strength recording
- Error message tracking
- Clear history option

### Smart Network Detection
- Automatic signal strength sorting
- Connected network highlighting (● indicator)
- Open vs secured network identification
- WPA/WPA2/WPA3 security display

## 🐛 Troubleshooting

### Enable Debug Mode
```bash
connex --debug
```

### Check NetworkManager Service
```bash
systemctl status NetworkManager
```

### View Connection History
Open connex → Menu → View History

## Screenshot
![screenshot](https://github.com/Lluciocc/connex/blob/271480cd7ee49023c803a679a88d3709e1ee6b71/screenshot01.png)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with GTK3 and Python GObject
- Uses NetworkManager for network operations
- Inspired by modern Linux desktop environments
- Designed for the Hyprland community

## 📧 Contact

Project Link: [https://github.com/lluciocc/connex](https://github.com/lluciocc/connex)

---

**Made with ❤️ for the ArchLinux and Hyprland communities**
