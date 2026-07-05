#!/bin/bash
# setup.sh - Install dependencies for linux-autotyper
# Supports: apt (Debian/Ubuntu), dnf (Fedora), pacman (Arch), zypper (openSUSE)

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Detect package manager
detect_pm() {
    if command -v apt &>/dev/null; then
        PM="apt"
        INSTALL="sudo apt update && sudo apt install -y"
    elif command -v dnf &>/dev/null; then
        PM="dnf"
        INSTALL="sudo dnf install -y"
    elif command -v pacman &>/dev/null; then
        PM="pacman"
        INSTALL="sudo pacman -S --noconfirm"
    elif command -v zypper &>/dev/null; then
        PM="zypper"
        INSTALL="sudo zypper install -y"
    else
        log_error "No supported package manager found (apt/dnf/pacman/zypper)"
        exit 1
    fi
    log_info "Detected package manager: $PM"
}

# Package mappings per distro
# Format: PKG_<pm>=<package list>
PKG_apt="xdotool ydotool wl-clipboard wtype python3-pip python3-venv"
PKG_dnf="xdotool ydotool wl-clipboard wtype python3-pip python3-virtualenv"
PKG_pacman="xdotool ydotool wl-clipboard wtype python-pip python-virtualenv"
PKG_zypper="xdotool ydotool wl-clipboard wtype python3-pip python3-virtualenv"

install_system_deps() {
    local pkgs_var="PKG_${PM}"
    local pkgs="${!pkgs_var}"
    
    if [[ -z "$pkgs" ]]; then
        log_warn "No package mapping for $PM, skipping system deps"
        return
    fi
    
    log_info "Installing system packages: $pkgs"
    eval "$INSTALL $pkgs"
}

setup_python_venv() {
    local venv_dir=".venv"
    
    if [[ -d "$venv_dir" ]]; then
        log_info "Virtualenv already exists at $venv_dir"
    else
        log_info "Creating virtualenv at $venv_dir"
        python3 -m venv "$venv_dir"
    fi
    
    log_info "Installing Python dependencies"
    "$venv_dir/bin/pip" install --upgrade pip
    "$venv_dir/bin/pip" install -r requirements.txt
    
    log_info "Python deps installed. Activate with: source .venv/bin/activate"
}

setup_ydotool() {
    if ! command -v ydotoold &>/dev/null; then
        log_warn "ydotoold not found, skipping ydotool setup"
        return
    fi
    
    log_info "Setting up ydotool..."
    
    # Check if ydotoold service exists
    if systemctl list-unit-files | grep -q ydotoold; then
        log_info "Enabling ydotoold service"
        sudo systemctl enable --now ydotoold
    else
        log_warn "ydotoold service not found (may need manual start)"
    fi
    
    # Add user to input group
    if ! groups "$USER" | grep -q '\binput\b'; then
        log_info "Adding user to 'input' group for uinput access"
        sudo usermod -aG input "$USER"
        log_warn "You must log out and back in for group changes to take effect"
    else
        log_info "User already in 'input' group"
    fi
}

main() {
    log_info "=== linux-autotyper Setup ==="
    
    detect_pm
    install_system_deps
    setup_python_venv
    setup_ydotool
    
    log_info "=== Setup Complete ==="
    echo ""
    echo "Next steps:"
    echo "  1. If you installed ydotool: log out and back in (for input group)"
    echo "  2. Activate venv: source .venv/bin/activate"
    echo "  3. Run: python autotyper.py --list-backends"
    echo "  4. Test: python autotyper.py"
}

main "$@"