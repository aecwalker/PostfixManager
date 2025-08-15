#!/bin/bash

# PostfixManager Installation Script
# This script installs PostfixManager for managing Postfix email access control

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/postfixmanager"
SERVICE_USER="postfixmanager"
SERVICE_NAME="postfixmanager"
REPO_URL="${POSTFIXMANAGER_REPO_URL:-https://github.com/aecwalker/PostfixManager.git}"
CONFIG_DIR="/etc/postfix"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check for required commands
    local deps=("git" "python3" "pip3" "systemctl")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "$dep is required but not installed"
            exit 1
        fi
    done
    
    # Check Python version
    local python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    local min_version="3.6"
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3,6) else 1)"; then
        log_error "Python 3.6+ is required (found $python_version)"
        exit 1
    fi
    
    log_success "All dependencies satisfied"
}

create_user() {
    log_info "Creating service user..."
    
    if id "$SERVICE_USER" &>/dev/null; then
        log_warning "User $SERVICE_USER already exists"
    else
        useradd --system --home-dir "$INSTALL_DIR" --shell /bin/false "$SERVICE_USER"
        log_success "Created user $SERVICE_USER"
    fi
}

clone_repository() {
    log_info "Installing PostfixManager..."
    
    # Remove existing installation
    if [[ -d "$INSTALL_DIR" ]]; then
        log_warning "Removing existing installation at $INSTALL_DIR"
        rm -rf "$INSTALL_DIR"
    fi
    
    # Clone repository
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    
    log_success "PostfixManager installed to $INSTALL_DIR"
}

install_python_deps() {
    log_info "Installing Python dependencies..."
    
    cd "$INSTALL_DIR"
    
    # Try different installation methods based on system
    if sudo -u "$SERVICE_USER" pip3 install --user -r requirements.txt 2>/dev/null; then
        log_success "Python dependencies installed via pip --user"
    elif sudo -u "$SERVICE_USER" pip3 install --user --break-system-packages -r requirements.txt 2>/dev/null; then
        log_success "Python dependencies installed via pip --break-system-packages"
    else
        log_info "Attempting to install via system package manager..."
        
        # Install system packages for common dependencies
        if command -v apt &> /dev/null; then
            apt update
            apt install -y python3-flask python3-waitress python3-ipaddress
            log_success "Python dependencies installed via apt"
        elif command -v yum &> /dev/null; then
            yum install -y python3-flask python3-waitress
            log_success "Python dependencies installed via yum"
        elif command -v dnf &> /dev/null; then
            dnf install -y python3-flask python3-waitress
            log_success "Python dependencies installed via dnf"
        else
            log_error "Could not install Python dependencies"
            log_info "Please install Flask and Waitress manually:"
            log_info "  - Flask 2.3.3+"
            log_info "  - Waitress 2.1.2+"
            exit 1
        fi
    fi
}

setup_config_permissions() {
    log_info "Setting up configuration file permissions..."
    
    # Create config directory if it doesn't exist
    mkdir -p "$CONFIG_DIR"
    
    # Create empty config files if they don't exist
    local config_files=(
        "blackhole_recipients.conf"
        "denied_senders.conf" 
        "sender_restrictions.conf"
        "recipient_restrictions.conf"
        "relay_clients.cidr"
    )
    
    for config_file in "${config_files[@]}"; do
        local file_path="$CONFIG_DIR/$config_file"
        if [[ ! -f "$file_path" ]]; then
            touch "$file_path"
            log_info "Created $file_path"
        fi
        chown "$SERVICE_USER:postfix" "$file_path"
        chmod 640 "$file_path"
    done
    
    log_success "Configuration permissions set up"
}

install_systemd_service() {
    log_info "Installing systemd service..."
    
    cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=PostfixManager Web Interface
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=/home/$SERVICE_USER/.local/bin:\$PATH
ExecStart=/usr/bin/python3 $INSTALL_DIR/app.py
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$CONFIG_DIR
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    log_success "Systemd service installed and enabled"
}

setup_sudo_permissions() {
    log_info "Setting up sudo permissions for Postfix reload..."
    
    echo "$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/systemctl reload postfix" > "/etc/sudoers.d/$SERVICE_USER"
    chmod 440 "/etc/sudoers.d/$SERVICE_USER"
    
    log_success "Sudo permissions configured"
}

start_service() {
    log_info "Starting PostfixManager service..."
    
    systemctl start "$SERVICE_NAME"
    
    # Wait a moment and check status
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "PostfixManager service started successfully"
        log_info "Service is running on http://localhost:8080"
        log_info "Check status with: systemctl status $SERVICE_NAME"
    else
        log_error "Failed to start PostfixManager service"
        log_info "Check logs with: journalctl -u $SERVICE_NAME"
        exit 1
    fi
}

show_completion_message() {
    echo
    log_success "PostfixManager installation completed!"
    echo
    echo -e "${BLUE}Installation Details:${NC}"
    echo "  Install Directory: $INSTALL_DIR"
    echo "  Service User: $SERVICE_USER"
    echo "  Config Directory: $CONFIG_DIR"
    echo "  Service Name: $SERVICE_NAME"
    echo
    echo -e "${BLUE}Useful Commands:${NC}"
    echo "  Start service:   sudo systemctl start $SERVICE_NAME"
    echo "  Stop service:    sudo systemctl stop $SERVICE_NAME"
    echo "  Restart service: sudo systemctl restart $SERVICE_NAME"
    echo "  View logs:       sudo journalctl -u $SERVICE_NAME -f"
    echo "  Update:          sudo $INSTALL_DIR/update.sh"
    echo "  Uninstall:       sudo $INSTALL_DIR/uninstall.sh"
    echo
    echo -e "${BLUE}Web Interface:${NC}"
    echo "  URL: http://$(hostname -I | awk '{print $1}'):8080"
    echo "  Local: http://localhost:8080"
    echo
    echo -e "${YELLOW}Note:${NC} Make sure to configure your firewall to allow access to port 8080"
}

# Main installation process
main() {
    echo "=================================================="
    echo "       PostfixManager Installation Script"
    echo "=================================================="
    echo
    
    check_root
    check_dependencies
    create_user
    clone_repository
    install_python_deps
    setup_config_permissions
    install_systemd_service
    setup_sudo_permissions
    start_service
    show_completion_message
}

# Handle script arguments
case "${1:-install}" in
    "install")
        main
        ;;
    "help"|"-h"|"--help")
        echo "PostfixManager Installation Script"
        echo
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  install    Install PostfixManager (default)"
        echo "  help       Show this help message"
        echo
        echo "Environment Variables:"
        echo "  POSTFIXMANAGER_REPO_URL    Git repository URL"
        echo
        exit 0
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac