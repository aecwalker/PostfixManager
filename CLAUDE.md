# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Flask-based web application** for managing Postfix email server multi-tier access control configuration files. The application provides a web interface to manage five types of email filtering and access control configurations without manually editing system files.

## Development Commands

### Installation
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
# Development/Production (uses Waitress WSGI server)
python app.py
```

The application runs on `0.0.0.0:8080` by default using Waitress for production deployment.

### Postfix Integration
```bash
# Reload Postfix configuration (available via web interface)
systemctl reload postfix
```

## Architecture

### Application Structure
- **`app.py`** - Main Flask application with all routes and business logic
- **`templates/`** - Jinja2 HTML templates
  - `base.html` - Bootstrap-based layout with navigation
  - `index.html` - Dashboard showing all configuration types
  - `config.html` - Individual configuration file management interface
- **`requirements.txt`** - Python dependencies (Flask 2.3.3, Waitress 2.1.2)

### Core Components

**Configuration Management (`app.py:10-16`)**:
- `CONFIG_FILES` dictionary maps config types to file paths in `/etc/postfix/`
- Five configuration types: blackhole_recipients, denied_senders, relay_clients, sender_restrictions, recipient_restrictions

**File Operations (`app.py:18-37`)**:
- `read_config_file()` - Safely reads configuration files
- `write_config_file()` - Writes configuration with directory creation

**Validation (`app.py:39-49`)**:
- `validate_ip_cidr()` - IP/CIDR notation validation using `ipaddress` module
- `validate_email()` - Basic email format validation

**REST API Routes**:
- `GET /` - Dashboard
- `GET /config/<type>` - View specific configuration
- `POST /config/<type>/add` - Add configuration entry
- `POST /config/<type>/delete` - Delete configuration entry  
- `POST /reload_postfix` - Reload Postfix via `systemctl`

### Frontend Architecture
- **Bootstrap 5** for responsive UI
- **Font Awesome 6** for icons
- **AJAX requests** for real-time updates without page refresh
- **Form validation** with helpful format examples for each config type

## Configuration File Types

The application manages these Postfix configuration files with specific validation rules:

1. **Blackhole Recipients** - Email addresses to silently discard
2. **Denied Senders** - Globally blocked sender addresses
3. **Relay Clients** - Trusted IPs with open relay (format: `IP/CIDR OK`)
4. **Sender Restrictions** - IP-based sender enforcement (format: `IP/CIDR email1 email2`)
5. **Recipient Restrictions** - IP-based recipient limits (format: `IP/CIDR recipient1 @domain.com`)

## Security Notes

- Application requires read/write access to `/etc/postfix/*.conf` files
- No built-in authentication - designed for internal/trusted network use
- Postfix reload requires appropriate sudo permissions for web server user
- Input validation prevents malformed IP/email configurations

## Dependencies

- **Flask 2.3.3** - Web framework
- **Waitress 2.1.2** - Production WSGI server
- Standard Python libraries: `os`, `ipaddress`
- Frontend: Bootstrap 5, Font Awesome 6 (CDN)

## Related Documentation

- `README.md` - Postfix system architecture and configuration details
- `POSTFIXMANAGER_README.md` - Comprehensive web application documentation
- `INSTALL.md` - Installation, update, and deployment guide
- `PROMPTS.md` - Development history and AI conversation log