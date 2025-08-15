from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import ipaddress
import json
from waitress import serve

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access PostfixManager.'

# User data file path
USER_DATA_FILE = '/opt/postfixmanager/users.json'

# Configuration file paths
CONFIG_FILES = {
    'blackhole_recipients': '/etc/postfix/blackhole_recipients.conf',
    'denied_senders': '/etc/postfix/denied_senders.conf', 
    'sender_restrictions': '/etc/postfix/sender_restrictions.conf',
    'recipient_restrictions': '/etc/postfix/recipient_restrictions.conf',
    'relay_clients': '/etc/postfix/relay_clients.cidr'
}

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, username, password_hash=None, must_change_password=False):
        self.id = username
        self.username = username
        self.password_hash = password_hash
        self.must_change_password = must_change_password

@login_manager.user_loader
def load_user(username):
    users = load_users()
    if username in users:
        user_data = users[username]
        return User(username, user_data.get('password_hash'), user_data.get('must_change_password', False))
    return None

def load_users():
    """Load users from JSON file"""
    try:
        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, 'r') as f:
                return json.load(f)
        else:
            # Create initial root user with no password (must change on first login)
            initial_users = {
                'root': {
                    'password_hash': None,
                    'must_change_password': True
                }
            }
            save_users(initial_users)
            return initial_users
    except Exception as e:
        return {}

def save_users(users):
    """Save users to JSON file"""
    try:
        os.makedirs(os.path.dirname(USER_DATA_FILE), exist_ok=True)
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(users, f, indent=2)
        return True
    except Exception as e:
        return False

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        users = load_users()
        if username in users:
            user_data = users[username]
            
            # Check if user has no password set (first login)
            if user_data['password_hash'] is None:
                if username == 'root' and password == '':
                    # Allow login with empty password for initial setup
                    user = User(username, None, True)
                    login_user(user)
                    flash('Welcome! You must set a password before continuing.', 'warning')
                    return redirect(url_for('change_password'))
                else:
                    flash('Invalid username or password', 'error')
                    return render_template('login.html')
            
            # Check password for existing users
            if check_password_hash(user_data['password_hash'], password):
                user = User(username, user_data['password_hash'], user_data.get('must_change_password', False))
                login_user(user)
                
                # Redirect to password change if required
                if user.must_change_password:
                    flash('You must change your password', 'warning')
                    return redirect(url_for('change_password'))
                
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                flash('Invalid username or password', 'error')
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password page"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return render_template('change_password.html')
        
        if len(new_password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return render_template('change_password.html')
        
        users = load_users()
        user_data = users[current_user.username]
        
        # For first-time setup (no current password)
        if user_data['password_hash'] is None:
            # Set new password
            users[current_user.username] = {
                'password_hash': generate_password_hash(new_password),
                'must_change_password': False
            }
            if save_users(users):
                flash('Password set successfully', 'success')
                return redirect(url_for('index'))
            else:
                flash('Failed to save password', 'error')
        else:
            # Verify current password for existing users
            if check_password_hash(user_data['password_hash'], current_password):
                users[current_user.username]['password_hash'] = generate_password_hash(new_password)
                users[current_user.username]['must_change_password'] = False
                if save_users(users):
                    flash('Password changed successfully', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('Failed to save password', 'error')
            else:
                flash('Current password is incorrect', 'error')
    
    return render_template('change_password.html')

@app.route('/')
@login_required
def index():
    """Main dashboard"""
    # Check if user must change password
    if current_user.must_change_password:
        return redirect(url_for('change_password'))
    return render_template('index.html')

@app.route('/config/<config_type>')
@login_required
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
@login_required
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
@login_required
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
@login_required
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