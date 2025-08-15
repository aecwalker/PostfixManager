# PostfixManager - Web Interface

A Flask-based web application for managing Postfix multi-tier email access control configuration files through an intuitive web interface.

## Overview

This web application provides a user-friendly interface to manage the five-tier Postfix email access control system described in the main README.md. Instead of manually editing configuration files, administrators can use this web interface to add, remove, and manage email access rules.

## Features

- **Dashboard Overview**: Visual representation of all configuration file types
- **Real-time Management**: Add and delete configuration entries without server restart
- **Input Validation**: Automatic validation of email addresses and IP/CIDR formats
- **Postfix Integration**: One-click Postfix configuration reload
- **Responsive Design**: Bootstrap-based UI that works on desktop and mobile
- **Production Ready**: Uses Waitress WSGI server for production deployment

## Configuration File Management

The web interface manages these Postfix configuration files:

### 1. Blackhole Recipients (`/etc/postfix/blackhole_recipients.conf`)
- **Purpose**: Email addresses to silently discard
- **Format**: One email address per line
- **Example**: `spam@company.com`

### 2. Denied Senders (`/etc/postfix/denied_senders.conf`)
- **Purpose**: Sender addresses blocked globally
- **Format**: One email address per line
- **Example**: `ceo@company.com`

### 3. Open Relay Clients (`/etc/postfix/relay_clients.cidr`)
- **Purpose**: Trusted IPs with unrestricted sending
- **Format**: IP/CIDR followed by "OK"
- **Example**: `192.168.40.215/32 OK`

### 4. Sender Restrictions (`/etc/postfix/sender_restrictions.conf`)
- **Purpose**: Force specific sender addresses by IP
- **Format**: IP/CIDR followed by allowed email addresses
- **Example**: `192.168.40.0/24 app1@company.com service@company.com`

### 5. Recipient Restrictions (`/etc/postfix/recipient_restrictions.conf`)
- **Purpose**: Limit destinations by IP
- **Format**: IP/CIDR followed by allowed recipients/domains
- **Example**: `10.10.10.10/32 admin@company.com @internal.company.com`

## Installation

### Prerequisites

- Python 3.6 or higher
- Postfix mail server (for production use)
- Root/sudo access for Postfix configuration management

### Setup

1. **Clone/Download the application files**
   ```bash
   # Ensure you have the following files:
   # app.py, requirements.txt, templates/
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure file permissions (Linux/Unix)**
   ```bash
   # Ensure the web application can read/write config files
   sudo chown www-data:www-data /etc/postfix/*.conf
   sudo chmod 644 /etc/postfix/*.conf
   ```

4. **Update configuration paths (if needed)**
   Edit `app.py` and modify the `CONFIG_FILES` dictionary if your Postfix configuration files are in different locations.

## Running the Application

### Development Mode
```bash
python app.py
```

### Production Mode
The application uses Waitress WSGI server by default for production deployment:

```bash
# Run on all interfaces, port 8080
python app.py

# Or customize host/port by editing app.py
```

### As a System Service (Linux)

Create a systemd service file `/etc/systemd/system/postfix-webui.service`:

```ini
[Unit]
Description=Postfix Web UI
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/webapp
ExecStart=/usr/bin/python3 /path/to/webapp/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl enable postfix-webui
sudo systemctl start postfix-webui
```

## Usage

### Accessing the Interface

1. Open your web browser and navigate to `http://your-server:8080`
2. You'll see the dashboard with all configuration file types

### Managing Configuration Files

1. **View/Edit Configuration**: Click "Manage" on any configuration type
2. **Add New Entry**: Use the form on the right side of the configuration page
3. **Delete Entry**: Click the trash icon next to any configuration line
4. **Reload Postfix**: Click "Reload Postfix" in the navigation bar to apply changes

### Input Validation

The application validates input based on configuration type:

- **Email addresses**: Must contain '@' and a valid domain format
- **IP/CIDR notation**: Validated using Python's `ipaddress` module
- **Combined formats**: Ensures proper syntax for restriction files

## Security Considerations

### File Permissions
- Ensure configuration files are readable/writable by the web application user
- Use appropriate file permissions (644 or 640) to protect sensitive configuration

### Network Access
- Consider running behind a reverse proxy (nginx/Apache)
- Use HTTPS in production environments
- Restrict access to authorized administrators only

### Authentication
The current version does not include built-in authentication. For production use, consider:
- Adding Flask-Login for session management
- Implementing LDAP/Active Directory integration
- Using a reverse proxy with authentication

## API Endpoints

The application provides these REST endpoints:

- `GET /` - Main dashboard
- `GET /config/<config_type>` - View specific configuration
- `POST /config/<config_type>/add` - Add new configuration line
- `POST /config/<config_type>/delete` - Delete configuration line
- `POST /reload_postfix` - Reload Postfix configuration

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**
   ```bash
   # Check file permissions
   ls -la /etc/postfix/*.conf
   
   # Fix permissions if needed
   sudo chown www-data:www-data /etc/postfix/*.conf
   ```

2. **Postfix Reload Fails**
   ```bash
   # Check if user has sudo privileges for systemctl
   sudo visudo
   # Add: www-data ALL=(ALL) NOPASSWD: /bin/systemctl reload postfix
   ```

3. **Configuration Files Not Found**
   - Verify file paths in `CONFIG_FILES` dictionary in `app.py`
   - Ensure directories exist: `sudo mkdir -p /etc/postfix`

### Logging

Enable Flask debug mode for development:
```python
# In app.py, add before the serve() call:
app.debug = True
```

For production logging, configure Python logging or use system logs.

## Customization

### Changing Default Paths
Edit the `CONFIG_FILES` dictionary in `app.py`:
```python
CONFIG_FILES = {
    'blackhole_recipients': '/custom/path/blackhole_recipients.conf',
    # ... other files
}
```

### Styling
The application uses Bootstrap 5. Customize by:
- Modifying `templates/base.html` for global changes
- Adding custom CSS classes
- Updating the Bootstrap theme

### Adding Features
The Flask application structure supports easy extension:
- Add new routes in `app.py`
- Create additional templates
- Implement backup/restore functionality
- Add configuration validation rules

## License

This software is provided as-is for managing Postfix email server configurations. Use at your own risk in production environments.