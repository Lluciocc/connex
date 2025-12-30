#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}Uninstalling connex...${NC}"
echo ""

if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}Error: Do not run this script as root${NC}"
    echo -e "${YELLOW}The script will ask for sudo when needed${NC}"
    exit 1
fi

if ! command -v connex &> /dev/null; then
    echo -e "${RED}Error: connex is not installed${NC}"
    exit 1
fi

echo -e "${YELLOW}This will remove connex from your system${NC}"
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${CYAN}Uninstallation cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${CYAN}Step 1/4: Stopping connex processes${NC}"
if pgrep -f "connex" > /dev/null; then
    echo -e "${CYAN}Stopping running connex processes...${NC}"
    pkill -f "connex" 2>/dev/null || true
    echo -e "${CYAN}Processes stopped${NC}"
else
    echo -e "${CYAN}No running processes found${NC}"
fi

echo ""
echo -e "${CYAN}Step 2/4: Removing files${NC}"

if [ -f "/usr/local/bin/connex" ]; then
    echo -e "${CYAN}Removing main executable...${NC}"
    sudo rm -f /usr/local/bin/connex
fi

if [ -d "/usr/local/lib/connex" ]; then
    echo -e "${CYAN}Removing application files...${NC}"
    sudo rm -rf /usr/local/lib/connex
fi

if [ -f "/usr/local/share/applications/connex.desktop" ]; then
    echo -e "${CYAN}Removing desktop entry...${NC}"
    sudo rm -f /usr/local/share/applications/connex.desktop
fi

if [ -f "/etc/xdg/autostart/connex-tray.desktop" ]; then
    echo -e "${CYAN}Removing autostart entry...${NC}"
    sudo rm -f /etc/xdg/autostart/connex-tray.desktop
fi

if [ -f "/usr/local/share/icons/hicolor/scalable/apps/connex.svg" ]; then
    echo -e "${CYAN}Removing icon...${NC}"
    sudo rm -f /usr/local/share/icons/hicolor/scalable/apps/connex.svg
fi

if [ -d "/usr/local/share/licenses/connex" ]; then
    sudo rm -rf /usr/local/share/licenses/connex
fi

if [ -d "/usr/local/share/doc/connex" ]; then
    sudo rm -rf /usr/local/share/doc/connex
fi

echo -e "${CYAN}System files removed${NC}"

echo ""
echo -e "${CYAN}Step 3/4: Updating icon cache${NC}"
if command -v gtk-update-icon-cache &> /dev/null; then
    sudo gtk-update-icon-cache -f -t /usr/local/share/icons/hicolor/ 2>/dev/null || true
    echo -e "${CYAN}Icon cache updated${NC}"
else
    echo -e "${YELLOW}gtk-update-icon-cache not found, skipping${NC}"
fi

echo ""
echo -e "${CYAN}Step 4/4: User configuration${NC}"
if [ -d "$HOME/.config/connex" ]; then
    echo -e "${YELLOW}Configuration directory found: $HOME/.config/connex${NC}"
    read -p "Remove configuration? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$HOME/.config/connex"
        echo -e "${CYAN}Configuration removed${NC}"
    else
        echo -e "${CYAN}Configuration kept${NC}"
    fi
else
    echo -e "${CYAN}No user configuration found${NC}"
fi

echo ""
echo -e "${GREEN}Uninstallation completed successfully!${NC}"
echo ""
echo -e "${CYAN}connex has been removed from your system${NC}"