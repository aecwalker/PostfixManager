from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import ipaddress
from waitress import serve

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Configuration file paths
CONFIG_FILES = {
    'blackhole_recipients': '/etc/postfix/blackhole_recipients.conf',
    'denied_senders': '/etc/postfix/denied_senders.conf', 
    'sender_restrictions': '/etc/postfix/sender_restrictions.conf',
    'recipient_restrictions': '/etc/postfix/recipient_restrictions.conf',
    'relay_clients': '/etc/postfix/relay_clients.cidr'
}

def read_config_file(file_path):
    """Read configuration file and return lines"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return [line.strip() for line in f.readlines() if line.strip()]
        return []
    except Exception as e:
        return []

def write_config_file(file_path, lines):
    """Write lines to configuration file"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            for line in lines:
                f.write(line + '\n')
        return True
    except Exception as e:
        return False

def validate_ip_cidr(ip_string):
    """Validate IP/CIDR notation"""
    try:
        ipaddress.ip_network(ip_string, strict=False)
        return True
    except:
        return False

def validate_email(email):
    """Basic email validation"""
    return '@' in email and '.' in email.split('@')[1]

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/config/<config_type>')
def view_config(config_type):
    """View specific configuration file"""
    if config_type not in CONFIG_FILES:
        flash('Invalid configuration type', 'error')
        return redirect(url_for('index'))
    
    file_path = CONFIG_FILES[config_type]
    lines = read_config_file(file_path)
    
    return render_template('config.html', 
                         config_type=config_type, 
                         lines=lines,
                         file_path=file_path)

@app.route('/config/<config_type>/add', methods=['POST'])
def add_config_line(config_type):
    """Add new line to configuration"""
    if config_type not in CONFIG_FILES:
        return jsonify({'error': 'Invalid configuration type'}), 400
    
    new_line = request.form.get('line', '').strip()
    if not new_line:
        return jsonify({'error': 'Line cannot be empty'}), 400
    
    # Validate based on config type
    if config_type in ['blackhole_recipients', 'denied_senders']:
        if not validate_email(new_line):
            return jsonify({'error': 'Invalid email format'}), 400
    elif config_type == 'relay_clients':
        ip_part = new_line.split()[0]
        if not validate_ip_cidr(ip_part):
            return jsonify({'error': 'Invalid IP/CIDR format'}), 400
    elif config_type in ['sender_restrictions', 'recipient_restrictions']:
        parts = new_line.split()
        if len(parts) < 2:
            return jsonify({'error': 'Format: IP/CIDR email1 email2...'}), 400
        if not validate_ip_cidr(parts[0]):
            return jsonify({'error': 'Invalid IP/CIDR format'}), 400
    
    file_path = CONFIG_FILES[config_type]
    lines = read_config_file(file_path)
    lines.append(new_line)
    
    if write_config_file(file_path, lines):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to write file'}), 500

@app.route('/config/<config_type>/delete', methods=['POST'])
def delete_config_line(config_type):
    """Delete line from configuration"""
    if config_type not in CONFIG_FILES:
        return jsonify({'error': 'Invalid configuration type'}), 400
    
    line_index = int(request.form.get('index', -1))
    file_path = CONFIG_FILES[config_type]
    lines = read_config_file(file_path)
    
    if 0 <= line_index < len(lines):
        lines.pop(line_index)
        if write_config_file(file_path, lines):
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to write file'}), 500
    else:
        return jsonify({'error': 'Invalid line index'}), 400

@app.route('/reload_postfix', methods=['POST'])
def reload_postfix():
    """Reload Postfix configuration"""
    try:
        result = os.system('systemctl reload postfix')
        if result == 0:
            return jsonify({'success': True, 'message': 'Postfix reloaded successfully'})
        else:
            return jsonify({'error': 'Failed to reload Postfix'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Use Waitress for production
    serve(app, host='0.0.0.0', port=8080)