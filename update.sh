#!/bin/bash

# PostfixManager Update Script
# This script updates PostfixManager to the latest version

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
BACKUP_DIR="/opt/postfixmanager-backup-$(date +%Y%m%d-%H%M%S)"

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

check_installation() {
    if [[ ! -d "$INSTALL_DIR" ]]; then
        log_error "PostfixManager is not installed at $INSTALL_DIR"
        log_info "Please run the installation script first"
        exit 1
    fi
    
    if [[ ! -d "$INSTALL_DIR/.git" ]]; then
        log_error "Installation directory is not a git repository"
        log_info "This might be a manual installation. Please reinstall using the install script."
        exit 1
    fi
}

backup_current_installation() {
    log_info "Creating backup of current installation..."
    
    cp -r "$INSTALL_DIR" "$BACKUP_DIR"
    log_success "Backup created at $BACKUP_DIR"
}

stop_service() {
    log_info "Stopping PostfixManager service..."
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        systemctl stop "$SERVICE_NAME"
        log_success "Service stopped"
    else
        log_warning "Service was not running"
    fi
}

update_repository() {
    log_info "Updating PostfixManager..."
    
    cd "$INSTALL_DIR"
    
    # Check for local changes
    if ! git diff --quiet || ! git diff --cached --quiet; then
        log_warning "Local changes detected. Stashing them..."
        sudo -u "$SERVICE_USER" git stash push -m "Auto-stash before update $(date)"
    fi
    
    # Fetch and pull latest changes
    sudo -u "$SERVICE_USER" git fetch origin
    local current_commit=$(git rev-parse HEAD)
    sudo -u "$SERVICE_USER" git pull origin main
    local new_commit=$(git rev-parse HEAD)
    
    if [[ "$current_commit" == "$new_commit" ]]; then
        log_info "Already up to date"
        return 0
    else
        log_success "Updated from $current_commit to $new_commit"
        return 1
    fi
}

update_dependencies() {
    log_info "Updating Python dependencies..."
    
    cd "$INSTALL_DIR"
    sudo -u "$SERVICE_USER" pip3 install --user --upgrade -r requirements.txt
    
    log_success "Dependencies updated"
}

restart_service() {
    log_info "Starting PostfixManager service..."
    
    systemctl start "$SERVICE_NAME"
    
    # Wait a moment and check status
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "Service started successfully"
    else
        log_error "Failed to start service"
        log_info "Attempting to restore from backup..."
        restore_from_backup
        exit 1
    fi
}

restore_from_backup() {
    log_warning "Restoring from backup..."
    
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    rm -rf "$INSTALL_DIR"
    mv "$BACKUP_DIR" "$INSTALL_DIR"
    systemctl start "$SERVICE_NAME"
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "Restored from backup successfully"
    else
        log_error "Failed to restore from backup"
    fi
}

cleanup_backup() {
    if [[ -d "$BACKUP_DIR" ]]; then
        log_info "Cleaning up backup..."
        rm -rf "$BACKUP_DIR"
        log_success "Backup cleaned up"
    fi
}

show_completion_message() {
    echo
    log_success "PostfixManager update completed!"
    echo
    echo -e "${BLUE}Service Status:${NC}"
    systemctl status "$SERVICE_NAME" --no-pager -l
    echo
    echo -e "${BLUE}Useful Commands:${NC}"
    echo "  View logs:       sudo journalctl -u $SERVICE_NAME -f"
    echo "  Restart service: sudo systemctl restart $SERVICE_NAME"
    echo "  Check status:    sudo systemctl status $SERVICE_NAME"
}

rollback() {
    log_info "Rolling back to previous version..."
    
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_error "No backup found for rollback"
        exit 1
    fi
    
    stop_service
    restore_from_backup
    
    log_success "Rollback completed"
}

# Main update process
main() {
    echo "=================================================="
    echo "        PostfixManager Update Script"
    echo "=================================================="
    echo
    
    check_root
    check_installation
    backup_current_installation
    
    stop_service
    
    # Attempt update
    if update_repository; then
        # No changes, just restart
        restart_service
        cleanup_backup
        log_info "No updates available"
    else
        # Updates applied, update dependencies and restart
        update_dependencies
        restart_service
        cleanup_backup
        show_completion_message
    fi
}

# Handle script arguments
case "${1:-update}" in
    "update")
        main
        ;;
    "rollback")
        rollback
        ;;
    "help"|"-h"|"--help")
        echo "PostfixManager Update Script"
        echo
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  update     Update to latest version (default)"
        echo "  rollback   Rollback to previous version"
        echo "  help       Show this help message"
        echo
        exit 0
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac