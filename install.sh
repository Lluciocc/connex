#!/bin/bash
# connex Quick Installation Script
# For ArchLinux and derivatives

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════╗"
echo "║     connex Installation Script        ║"
echo "╚═══════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}✗ Please do not run this script as root${NC}"
    echo -e "${YELLOW}The script will ask for sudo when needed${NC}"
    exit 1
fi

# Check if on ArchLinux
if [ ! -f /etc/arch-release ]; then
    echo -e "${YELLOW}⚠  Warning: This script is designed for ArchLinux${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${BLUE}[1/4] Checking dependencies...${NC}"

MISSING_DEPS=()

# Check each dependency
check_dep() {
    if ! pacman -Qi "$1" &> /dev/null; then
        MISSING_DEPS+=("$1")
    fi
}

check_dep "python"
check_dep "python-gobject"
check_dep "gtk3"
check_dep "networkmanager"
check_dep "libappindicator-gtk3"
check_dep "libnotify"
check_dep "python-qrcode"

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo -e "${YELLOW}Missing dependencies: ${MISSING_DEPS[*]}${NC}"
    echo -e "${BLUE}Installing missing dependencies...${NC}"
    sudo pacman -S --needed "${MISSING_DEPS[@]}"
else
    echo -e "${GREEN}✓ All dependencies already installed${NC}"
fi

echo -e "${BLUE}[2/4] Installing connex...${NC}"

# Create directories if they don't exist
sudo mkdir -p /usr/bin
sudo mkdir -p /usr/lib/connex/assets/{core,tray,utils,ui}
sudo mkdir -p /usr/share/applications
sudo mkdir -p /usr/share/icons/hicolor/scalable/apps
sudo mkdir -p /etc/xdg/autostart
sudo mkdir -p /usr/share/licenses/connex
sudo mkdir -p /usr/share/doc/connex

# Install main script
sudo install -Dm755 connex.py /usr/bin/connex

# copy assets
sudo cp -a assets /usr/lib/connex/

# Desktop entry and autostart
sudo install -Dm644 connex.desktop /usr/share/applications/connex.desktop
sudo install -Dm644 connex-tray.desktop /etc/xdg/autostart/connex-tray.desktop

# Icon
sudo install -Dm644 connex.svg /usr/share/icons/hicolor/scalable/apps/connex.svg

# License & docs
sudo install -Dm644 LICENSE /usr/share/licenses/connex/LICENSE
sudo install -Dm644 README.md /usr/share/doc/connex/README.md

echo -e "${GREEN}✓ Files installed${NC}"

echo -e "${BLUE}[3/4] Updating icon cache...${NC}"
sudo gtk-update-icon-cache -f -t /usr/share/icons/hicolor/ 2>/dev/null || true

echo -e "${BLUE}[4/4] Checking NetworkManager status...${NC}"
if systemctl is-active --quiet NetworkManager; then
    echo -e "${GREEN}✓ NetworkManager is running${NC}"
else
    echo -e "${YELLOW}⚠ NetworkManager is not running${NC}"
    read -p "Start NetworkManager now? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        sudo systemctl start NetworkManager
        sudo systemctl enable NetworkManager
        echo -e "${GREEN}✓ NetworkManager started and enabled${NC}"
    fi
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      ✓ Installation Complete!         ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Usage:${NC}"
echo -e "  ${YELLOW}connex${NC}              - Launch GUI"
echo -e "  ${YELLOW}connex --tray${NC}       - Launch in system tray"
echo -e "  ${YELLOW}connex --cli list${NC}   - List networks (CLI mode)"
echo -e "  ${YELLOW}connex -h${NC}           - Show help
echo ""
echo -e "${BLUE}Documentation:${NC} /usr/share/doc/connex/README.md"
echo -e "${BLUE}Config directory:${NC} ~/.config/connex/"
echo ""
echo -e "Run ${YELLOW}connex${NC} to get started!"
