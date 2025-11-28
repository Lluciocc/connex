PREFIX ?= /usr
BINDIR = $(PREFIX)/bin
LIBDIR = $(PREFIX)/lib/connex
DATADIR = $(PREFIX)/share
APPLICATIONSDIR = $(DATADIR)/applications
ICONSDIR = $(DATADIR)/icons/hicolor
LICENSEDIR = $(DATADIR)/licenses/connex
DOCDIR = $(DATADIR)/doc/connex
AUTOSTARTDIR = /etc/xdg/autostart

.PHONY: all install uninstall clean test build aur-test aur-gen help checkdeps release dev-install lint format

all: help

help:
	@echo "connex - Makefile commands:"
	@echo ""
	@echo "  make install       - Install connex system-wide"
	@echo "  make uninstall     - Uninstall connex"
	@echo "  make clean         - Clean build artifacts"
	@echo "  make test          - Run the application in test mode"
	@echo "  make build         - Test local PKGBUILD build"
	@echo "  make aur-test      - Test AUR PKGBUILD"
	@echo "  make aur-gen       - Generate .SRCINFO for AUR"
	@echo "  make checkdeps     - Check if dependencies are installed"
	@echo "  make release       - Tag and prepare release"
	@echo "  make dev-install   - Install locally (editable mode)"
	@echo "  make lint          - Run pylint"
	@echo "  make format        - Auto-format code with black"
	@echo ""

install:
	@echo "Installing connex..."
	# Main script
	install -Dm755 connex.py "$(DESTDIR)$(BINDIR)/connex"

	# Assets
	cp -a assets /usr/lib/connex/

	# Desktop entries & icons
	install -Dm644 connex.desktop "$(DESTDIR)$(APPLICATIONSDIR)/connex.desktop"
	install -Dm644 connex.svg "$(DESTDIR)$(ICONSDIR)/scalable/apps/connex.svg"
	install -Dm644 connex-tray.desktop "$(DESTDIR)$(AUTOSTARTDIR)/connex-tray.desktop"

	# License & docs
	install -Dm644 LICENSE "$(DESTDIR)$(LICENSEDIR)/LICENSE"
	install -Dm644 README.md "$(DESTDIR)$(DOCDIR)/README.md"

	@echo "✓ Installation complete!"
	@echo "Run 'connex' to start the application."

uninstall:
	@echo "Uninstalling connex..."
	rm -f "$(DESTDIR)$(BINDIR)/connex"
	rm -rf "$(DESTDIR)$(LIBDIR)"
	rm -f "$(DESTDIR)$(APPLICATIONSDIR)/connex.desktop"
	rm -f "$(DESTDIR)$(ICONSDIR)/scalable/apps/connex.svg"
	rm -f "$(DESTDIR)$(AUTOSTARTDIR)/connex-tray.desktop"
	rm -rf "$(DESTDIR)$(LICENSEDIR)"
	rm -rf "$(DESTDIR)$(DOCDIR)"
	@echo "✓ Uninstallation complete!"

clean:
	@echo "Cleaning build artifacts..."
	rm -rf pkg/ src/ *.tar.gz *.tar.xz *.pkg.tar.zst
	rm -rf __pycache__ *.pyc
	@echo "✓ Clean complete!"

test:
	@echo "Running connex in test mode..."
	python3 connex.py --debug

checkdeps:
	@echo "Checking dependencies..."
	@command -v python3 >/dev/null 2>&1 || { echo "✗ python3 not found"; exit 1; }
	@python3 -c "import gi" 2>/dev/null || { echo "✗ python-gobject not found"; exit 1; }
	@command -v nmcli >/dev/null 2>&1 || { echo "✗ networkmanager not found"; exit 1; }
	@echo "✓ All required dependencies found!"

build: checkdeps
	@echo "Testing PKGBUILD build..."
	makepkg -sf
	@echo "✓ Build complete! Test with: sudo pacman -U connex-*.pkg.tar.zst"

aur-test:
	@echo "Testing AUR PKGBUILD..."
	@if [ ! -f PKGBUILD ]; then echo "✗ PKGBUILD not found"; exit 1; fi
	makepkg -sf --check
	@echo "✓ AUR test complete!"

aur-gen:
	@echo "Generating .SRCINFO for AUR..."
	makepkg --printsrcinfo > .SRCINFO
	@echo "✓ .SRCINFO generated!"
	@echo "Don't forget to commit and push to AUR:"
	@echo "  git add PKGBUILD .SRCINFO"
	@echo "  git commit -m 'Update to version X.X.X'"
	@echo "  git push"

release: aur-gen
	@echo "Preparing release..."
	@if [ -z "$(VERSION)" ]; then \
		echo "✗ Please specify VERSION: make release VERSION=2.0.0"; \
		exit 1; \
	fi
	@echo "Creating release for version $(VERSION)..."
	git tag -a "v$(VERSION)" -m "Release version $(VERSION)"
	@echo "✓ Tag created! Push with: git push origin v$(VERSION)"

dev-install:
	@echo "Installing in development mode..."
	pip install --user -e .

lint:
	@echo "Checking code style..."
	@command -v pylint >/dev/null 2>&1 || { echo "Install pylint: pip install pylint"; exit 1; }
	pylint connex.py || true

format:
	@echo "Formatting code..."
	@command -v black >/dev/null 2>&1 || { echo "Install black: pip install black"; exit 1; }
	black connex.py
