# PostfixManager Installation Guide

This guide provides step-by-step instructions for installing, updating, and managing PostfixManager on Linux systems.

## Quick Installation

For a quick automated installation, run:

```bash
# Download and run the installation script
curl -sSL https://raw.githubusercontent.com/aecwalker/PostfixManager/main/install.sh | sudo bash

# Or if you have the repository cloned locally:
git clone https://github.com/aecwalker/PostfixManager.git
cd PostfixManager
sudo ./install.sh
```

## Prerequisites

- **Operating System**: Linux (Ubuntu 18.04+, CentOS 7+, Debian 9+, or compatible)
- **Python**: 3.6 or higher
- **Git**: For repository management
- **Postfix**: Mail server (for production use)
- **Root Access**: Required for system installation

### Installing Prerequisites

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y git python3 python3-pip postfix
```

**CentOS/RHEL:**
```bash
sudo yum install -y git python3 python3-pip postfix
# or on newer versions:
sudo dnf install -y git python3 python3-pip postfix
```

## Manual Installation

If you prefer to install manually or need to customize the installation:

### 1. Clone the Repository

```bash
# Clone to a temporary location
git clone https://github.com/aecwalker/PostfixManager.git /tmp/postfixmanager
cd /tmp/postfixmanager
```

### 2. Run Installation Script

```bash
# Make script executable and run
chmod +x install.sh
sudo ./install.sh
```

### 3. Verify Installation

```bash
# Check service status
sudo systemctl status postfixmanager

# Check if web interface is accessible
curl -I http://localhost:8080
```

## Installation Details

The installation script performs the following actions:

### System Changes
- Creates a dedicated system user: `postfixmanager`
- Installs PostfixManager to: `/opt/postfixmanager`
- Creates systemd service: `postfixmanager.service`
- Sets up configuration directory: `/etc/postfix/`

### Security Configuration
- Runs with minimal privileges (non-root user)
- Limited file system access
- Sudo permissions only for Postfix reload
- Systemd security hardening

### File Permissions
```
/opt/postfixmanager/          - owned by postfixmanager:postfixmanager
/etc/postfix/*.conf           - owned by postfixmanager:postfix (640)
/etc/sudoers.d/postfixmanager - sudo permissions for Postfix reload
```

## Post-Installation

### 1. Access the Web Interface

Open your web browser and navigate to:
- **Local access**: http://localhost:8080
- **Network access**: http://your-server-ip:8080

### 2. Configure Firewall (if needed)

```bash
# UFW (Ubuntu)
sudo ufw allow 8080

# FirewallD (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload

# iptables
sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
```

### 3. Test Postfix Integration

1. Add a test configuration entry through the web interface
2. Click "Reload Postfix" in the navigation bar
3. Verify no errors are displayed

## Updates

### Automatic Updates

```bash
# Update to latest version
sudo /opt/postfixmanager/update.sh

# Check for updates (dry run)
sudo /opt/postfixmanager/update.sh --check
```

### Manual Updates

```bash
cd /opt/postfixmanager
sudo systemctl stop postfixmanager
sudo -u postfixmanager git pull origin main
sudo -u postfixmanager pip3 install --user -r requirements.txt
sudo systemctl start postfixmanager
```

## Service Management

### Basic Commands

```bash
# Start service
sudo systemctl start postfixmanager

# Stop service
sudo systemctl stop postfixmanager

# Restart service
sudo systemctl restart postfixmanager

# Check status
sudo systemctl status postfixmanager

# Enable auto-start on boot
sudo systemctl enable postfixmanager

# Disable auto-start on boot
sudo systemctl disable postfixmanager
```

### Viewing Logs

```bash
# Real-time logs
sudo journalctl -u postfixmanager -f

# Recent logs
sudo journalctl -u postfixmanager -n 50

# Logs for specific date
sudo journalctl -u postfixmanager --since "2024-01-01" --until "2024-01-02"
```

## Configuration

### Application Settings

The main configuration is in `/opt/postfixmanager/app.py`. Key settings:

```python
# Server configuration
HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 8080       # Default port

# Configuration file paths
CONFIG_FILES = {
    'blackhole_recipients': '/etc/postfix/blackhole_recipients.conf',
    'denied_senders': '/etc/postfix/denied_senders.conf',
    'relay_clients': '/etc/postfix/relay_clients.cidr',
    'sender_restrictions': '/etc/postfix/sender_restrictions.conf',
    'recipient_restrictions': '/etc/postfix/recipient_restrictions.conf'
}
```

### Changing Default Port

1. Edit the service file:
   ```bash
   sudo systemctl edit postfixmanager
   ```

2. Add environment variable:
   ```ini
   [Service]
   Environment=POSTFIXMANAGER_PORT=8081
   ```

3. Update the application to read this environment variable, or modify `app.py` directly.

4. Restart service:
   ```bash
   sudo systemctl restart postfixmanager
   ```

## Troubleshooting

### Common Issues

**1. Service fails to start**
```bash
# Check logs for errors
sudo journalctl -u postfixmanager -n 20

# Common causes:
# - Port already in use
# - Permission denied on config files
# - Missing Python dependencies
```

**2. Permission denied errors**
```bash
# Fix config file permissions
sudo chown postfixmanager:postfix /etc/postfix/*.conf
sudo chmod 640 /etc/postfix/*.conf
```

**3. Postfix reload fails**
```bash
# Check sudo permissions
sudo -u postfixmanager sudo -l

# Should show: (ALL) NOPASSWD: /bin/systemctl reload postfix
```

**4. Web interface not accessible**
```bash
# Check if service is listening
sudo netstat -tlnp | grep :8080

# Check firewall settings
sudo ufw status
sudo firewall-cmd --list-ports
```

### Debug Mode

Enable debug mode for detailed error messages:

```bash
# Edit the service
sudo systemctl edit postfixmanager

# Add debug environment
[Service]
Environment=FLASK_DEBUG=1
Environment=FLASK_ENV=development

# Restart service
sudo systemctl restart postfixmanager
```

## Uninstallation

To completely remove PostfixManager:

```bash
# Run the uninstall script
sudo /opt/postfixmanager/uninstall.sh

# Or manually:
sudo systemctl stop postfixmanager
sudo systemctl disable postfixmanager
sudo rm -f /etc/systemd/system/postfixmanager.service
sudo rm -f /etc/sudoers.d/postfixmanager
sudo userdel -r postfixmanager
sudo rm -rf /opt/postfixmanager
sudo systemctl daemon-reload
```

**Note**: Configuration files in `/etc/postfix/` are preserved during uninstallation.

## Security Considerations

### Network Security
- Run behind a reverse proxy (nginx/Apache) with HTTPS
- Use firewall rules to restrict access
- Consider VPN access for remote administration

### Authentication
The current version doesn't include built-in authentication. For production:

1. **Reverse Proxy Authentication**:
   ```nginx
   # nginx example
   location / {
       auth_basic "PostfixManager";
       auth_basic_user_file /etc/nginx/.htpasswd;
       proxy_pass http://localhost:8080;
   }
   ```

2. **Network Restrictions**:
   ```bash
   # Allow only specific IP ranges
   sudo iptables -A INPUT -p tcp --dport 8080 -s 192.168.1.0/24 -j ACCEPT
   sudo iptables -A INPUT -p tcp --dport 8080 -j DROP
   ```

### File System Security
- Configuration files are owned by the service user
- Service runs with minimal privileges
- Systemd security features are enabled

## Advanced Configuration

### Custom Installation Directory

```bash
# Set custom directory before installation
export POSTFIXMANAGER_INSTALL_DIR="/usr/local/postfixmanager"
sudo ./install.sh
```

### Multiple Instances

To run multiple instances (different ports/configs):

1. Create separate installation directories
2. Use different service names and users
3. Configure different ports
4. Use different configuration file paths

### Integration with Configuration Management

For Ansible, Puppet, or Chef integration:

1. Use the installation script as a starting point
2. Customize configuration file paths
3. Integrate with existing user management
4. Use configuration management for updates

## Support

### Getting Help

1. **Check logs**: `sudo journalctl -u postfixmanager`
2. **Review documentation**: README.md and POSTFIXMANAGER_README.md
3. **Verify prerequisites**: Ensure all requirements are met
4. **Test manually**: Try running `python3 /opt/postfixmanager/app.py` directly

### Reporting Issues

When reporting issues, include:
- Operating system and version
- Python version
- Service logs (`journalctl` output)
- Configuration file contents (sanitized)
- Steps to reproduce the issue