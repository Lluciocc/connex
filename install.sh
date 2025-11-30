#!/bin/bash

set -e

CLONE="no"


CLONE="no"


while [[ $# -gt 0 ]]; do
    case "$1" in
    --clone)
        CLONE="yes"
        shift
        ;;
    -h)
        echo "Usage: install.sh [--clone] [--no-clone]"
        exit 0
        ;;
    *)
        echo "Unknown argument: $1"
        exit 1
        ;;
    esac
done


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

# clone if the argument was given
if [[ "$CLONE" == "yes" ]]; then
    echo -e "${BLUE}Cloning into the repository...${NC}"
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"


    curl -sSL https://github.com/Lluciocc/connex/archive/refs/heads/master.zip -o connex.zip
    unzip -qq connex.zip
    cd connex-master


    echo -e "${GREEN}✓ Repository downloaded${NC}"
fi

# Found this from many install.sh file

# Detect distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        DISTRO_FAMILY=$ID_LIKE
    elif [ -f /etc/arch-release ]; then
        DISTRO="arch"
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
    elif [ -f /etc/fedora-release ]; then
        DISTRO="fedora"
    elif [ -f /etc/gentoo-release ]; then
        DISTRO="gentoo"
    else
        DISTRO="unknown"
    fi
}

detect_distro

echo -e "${BLUE}Detected distribution: ${GREEN}$DISTRO${NC}"
echo ""

install_arch() {
    local packages=(
        "python"
        "python-gobject"
        "gtk3"
        "networkmanager"
        "libappindicator-gtk3"
        "libnotify"
        "python-qrcode"
    )
    
    MISSING_DEPS=()
    for pkg in "${packages[@]}"; do
        if ! pacman -Qi "$pkg" &> /dev/null; then
            MISSING_DEPS+=("$pkg")
        fi
    done
    
    if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
        echo -e "${YELLOW}Missing dependencies: ${MISSING_DEPS[*]}${NC}"
        echo -e "${BLUE}Installing missing dependencies...${NC}"
        sudo pacman -S --needed "${MISSING_DEPS[@]}"
    else
        echo -e "${GREEN}✓ All dependencies already installed${NC}"
    fi
}

install_debian() {
    local packages=(
        "python3"
        "python3-gi"
        "python3-gi-cairo"
        "gir1.2-gtk-3.0"
        "gir1.2-appindicator3-0.1"
        "network-manager"
        "libnotify-bin"
        "python3-qrcode"
        "python3-pil"
    )
    
    echo -e "${BLUE}Updating package list...${NC}"
    sudo apt-get update
    
    echo -e "${BLUE}Installing dependencies...${NC}"
    sudo apt-get install -y "${packages[@]}"
}

install_fedora() {
    local packages=(
        "python3"
        "python3-gobject"
        "gtk3"
        "NetworkManager"
        "libappindicator-gtk3"
        "libnotify"
        "python3-qrcode"
        "python3-pillow"
    )
    
    echo -e "${BLUE}Installing dependencies...${NC}"
    sudo dnf install -y "${packages[@]}"
}

install_opensuse() {
    local packages=(
        "python3"
        "python3-gobject"
        "python3-gobject-Gdk"
        "gtk3"
        "NetworkManager"
        "libappindicator3-1"
        "libnotify-tools"
        "python3-qrcode"
        "python3-Pillow"
    )
    
    echo -e "${BLUE}Installing dependencies...${NC}"
    sudo zypper install -y "${packages[@]}"
}

install_void() {
    local packages=(
        "python3"
        "python3-gobject"
        "gtk+3"
        "NetworkManager"
        "libappindicator"
        "libnotify"
        "python3-qrcode"
        "python3-Pillow"
    )
    
    echo -e "${BLUE}Installing dependencies...${NC}"
    sudo xbps-install -Sy "${packages[@]}"
}

install_alpine() {
    local packages=(
        "python3"
        "py3-gobject3"
        "gtk+3.0"
        "networkmanager"
        "libappindicator"
        "libnotify"
        "py3-qrcode"
        "py3-pillow"
    )
    
    echo -e "${BLUE}Installing dependencies...${NC}"
    sudo apk add "${packages[@]}"
}

install_gentoo() {
    local packages=(
        "dev-lang/python"
        "dev-python/pygobject"
        "x11-libs/gtk+"
        "net-misc/networkmanager"
        "dev-libs/libappindicator"
        "x11-libs/libnotify"
        "dev-python/qrcode"
        "dev-python/pillow"
    )
    
    echo -e "${BLUE}Installing dependencies...${NC}"
    echo -e "${YELLOW}Note: This may take a while on Gentoo${NC}"
    sudo emerge --ask --verbose "${packages[@]}"
}

echo -e "${BLUE}[1/4] Installing dependencies...${NC}"

# Inspired from this image
# https://www.reddit.com/r/linux/comments/1czajn0/linux_distro_family_chart_with_distros_based/
case "$DISTRO" in
    arch|manjaro|endeavouros|garuda)
        install_arch
        ;;
    debian|ubuntu|linuxmint|pop|elementary|zorin|kali)
        install_debian
        ;;
    fedora|rhel|centos|rocky|alma)
        install_fedora
        ;;
    opensuse*|suse)
        install_opensuse
        ;;
    void)
        install_void
        ;;
    alpine)
        install_alpine
        ;;
    gentoo|funtoo)
        install_gentoo
        ;;
    *)
        echo -e "${RED}✗ Unsupported distribution: $DISTRO${NC}"
        echo -e "${YELLOW}Please install dependencies manually:${NC}"
        echo "  - Python 3"
        echo "  - PyGObject (python-gobject)"
        echo "  - GTK 3"
        echo "  - NetworkManager"
        echo "  - libappindicator-gtk3"
        echo "  - libnotify"
        echo "  - python-qrcode"
        echo ""
        read -p "Continue with installation anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        ;;
esac

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

# Copy assets
if [ -d "assets" ]; then
    sudo cp -a assets /usr/lib/connex/
else
    echo -e "${YELLOW}⚠ Warning: assets directory not found${NC}"
fi

# Desktop entry and autostart
if [ -f "connex.desktop" ]; then
    sudo install -Dm644 connex.desktop /usr/share/applications/connex.desktop
fi

if [ -f "connex-tray.desktop" ]; then
    sudo install -Dm644 connex-tray.desktop /etc/xdg/autostart/connex-tray.desktop
fi

# Icon
if [ -f "connex.svg" ]; then
    sudo install -Dm644 connex.svg /usr/share/icons/hicolor/scalable/apps/connex.svg
fi

# License & docs
if [ -f "LICENSE" ]; then
    sudo install -Dm644 LICENSE /usr/share/licenses/connex/LICENSE
fi

if [ -f "README.md" ]; then
    sudo install -Dm644 README.md /usr/share/doc/connex/README.md
fi

echo -e "${GREEN}✓ Files installed${NC}"

echo -e "${BLUE}[3/4] Updating icon cache...${NC}"
if command -v gtk-update-icon-cache &> /dev/null; then
    sudo gtk-update-icon-cache -f -t /usr/share/icons/hicolor/ 2>/dev/null || true
    echo -e "${GREEN}✓ Icon cache updated${NC}"
else
    echo -e "${YELLOW}⚠ gtk-update-icon-cache not found, skipping${NC}"
fi

echo -e "${BLUE}[4/4] Checking NetworkManager status...${NC}"
if systemctl is-active --quiet NetworkManager 2>/dev/null; then
    echo -e "${GREEN}✓ NetworkManager is running${NC}"
elif command -v systemctl &> /dev/null; then
    echo -e "${YELLOW}⚠ NetworkManager is not running${NC}"
    read -p "Start NetworkManager now? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        sudo systemctl start NetworkManager
        sudo systemctl enable NetworkManager
        echo -e "${GREEN}✓ NetworkManager started and enabled${NC}"
    fi
else
    echo -e "${YELLOW}⚠ systemctl not available, please start NetworkManager manually${NC}"
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
echo -e "  ${YELLOW}connex -h${NC}           - Show help"
echo ""
echo -e "${BLUE}Documentation:${NC} /usr/share/doc/connex/README.md"
echo -e "${BLUE}Config directory:${NC} ~/.config/connex/"
echo ""
echo -e "Run ${YELLOW}connex${NC} to get started!"