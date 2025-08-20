#!/bin/bash

# PostfixManager Uninstall Script
# This script completely removes PostfixManager from the system

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

confirm_uninstall() {
    echo "=================================================="
    echo "       PostfixManager Uninstall Script"
    echo "=================================================="
    echo
    log_warning "This will completely remove PostfixManager from your system"
    echo
    echo "The following will be removed:"
    echo "  - PostfixManager application ($INSTALL_DIR)"
    echo "  - System service ($SERVICE_NAME)"
    echo "  - Service user ($SERVICE_USER)"
    echo "  - Sudo permissions"
    echo
    echo "The following will be PRESERVED:"
    echo "  - Postfix configuration files in $CONFIG_DIR"
    echo "  - Postfix installation and main configuration"
    echo
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " -r
    if [[ ! $REPLY == "yes" ]]; then
        log_info "Uninstall cancelled"
        exit 0
    fi
    echo
}

stop_and_disable_service() {
    log_info "Stopping and disabling PostfixManager service..."
    
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        systemctl stop "$SERVICE_NAME"
        log_success "Service stopped"
    else
        log_info "Service was not running"
    fi
    
    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        systemctl disable "$SERVICE_NAME"
        log_success "Service disabled"
    else
        log_info "Service was not enabled"
    fi
}

remove_systemd_service() {
    log_info "Removing systemd service file..."
    
    local service_file="/etc/systemd/system/$SERVICE_NAME.service"
    if [[ -f "$service_file" ]]; then
        rm -f "$service_file"
        systemctl daemon-reload
        log_success "Systemd service file removed"
    else
        log_info "Systemd service file not found"
    fi
}

remove_sudo_permissions() {
    log_info "Removing sudo permissions..."
    
    local sudoers_file="/etc/sudoers.d/$SERVICE_USER"
    if [[ -f "$sudoers_file" ]]; then
        rm -f "$sudoers_file"
        log_success "Sudo permissions removed"
    else
        log_info "Sudo permissions file not found"
    fi
}

remove_installation_directory() {
    log_info "Removing installation directory..."
    
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        log_success "Installation directory removed"
    else
        log_info "Installation directory not found"
    fi
    
    # Remove data directory
    if [[ -d "/var/lib/postfixmanager" ]]; then
        rm -rf "/var/lib/postfixmanager"
        log_success "Data directory removed"
    else
        log_info "Data directory not found"
    fi
}

remove_service_user() {
    log_info "Removing service user..."
    
    if id "$SERVICE_USER" &>/dev/null; then
        # Remove user and home directory
        userdel --remove "$SERVICE_USER" 2>/dev/null || userdel "$SERVICE_USER" 2>/dev/null || true
        log_success "Service user removed"
    else
        log_info "Service user not found"
    fi
}

cleanup_config_permissions() {
    log_info "Configuration files preserved..."
    
    local config_files=(
        "blackhole_recipients.conf"
        "denied_senders.conf"
        "sender_restrictions.conf"
        "recipient_restrictions.conf"
        "relay_clients.cidr"
    )
    
    for config_file in "${config_files[@]}"; do
        local file_path="$CONFIG_DIR/$config_file"
        if [[ -f "$file_path" ]]; then
            # Note: Permissions on /etc/postfix files are preserved as requested
            log_info "Preserved $file_path"
        fi
    done
    
    log_success "Configuration files preserved with original permissions"
}

show_completion_message() {
    echo
    log_success "PostfixManager has been completely uninstalled!"
    echo
    echo -e "${BLUE}What was removed:${NC}"
    echo "  ✓ PostfixManager application"
    echo "  ✓ System service"
    echo "  ✓ Service user"
    echo "  ✓ Sudo permissions"
    echo
    echo -e "${BLUE}What was preserved:${NC}"
    echo "  ✓ Postfix configuration files"
    echo "  ✓ Postfix installation"
    echo
    echo -e "${YELLOW}Note:${NC} Your Postfix configuration files in $CONFIG_DIR remain intact"
    echo "      You may want to review and clean them up manually if needed"
}

# Main uninstall process
main() {
    confirm_uninstall
    
    stop_and_disable_service
    remove_systemd_service
    remove_sudo_permissions
    remove_installation_directory
    remove_service_user
    cleanup_config_permissions
    
    show_completion_message
}

# Handle script arguments
case "${1:-uninstall}" in
    "uninstall")
        check_root
        main
        ;;
    "help"|"-h"|"--help")
        echo "PostfixManager Uninstall Script"
        echo
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  uninstall  Remove PostfixManager (default)"
        echo "  help       Show this help message"
        echo
        echo "This script will remove:"
        echo "  - PostfixManager application"
        echo "  - System service and user"
        echo "  - Sudo permissions"
        echo
        echo "This script will preserve:"
        echo "  - Postfix configuration files"
        echo "  - Postfix installation"
        echo
        exit 0
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac