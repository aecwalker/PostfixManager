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

# User data file path - use a writable location
USER_DATA_FILE = '/var/lib/postfixmanager/users.json'

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
        print(f"[DEBUG] Attempting to save users to: {USER_DATA_FILE}")
        print(f"[DEBUG] Users data: {users}")
        
        # Check if directory exists
        dir_path = os.path.dirname(USER_DATA_FILE)
        print(f"[DEBUG] Directory path: {dir_path}")
        print(f"[DEBUG] Directory exists: {os.path.exists(dir_path)}")
        
        # Create directory
        os.makedirs(dir_path, exist_ok=True)
        print(f"[DEBUG] Directory created/exists")
        
        # Check permissions
        print(f"[DEBUG] Directory writable: {os.access(dir_path, os.W_OK)}")
        print(f"[DEBUG] Current working directory: {os.getcwd()}")
        print(f"[DEBUG] Process UID: {os.getuid()}")
        
        # Write file
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(users, f, indent=2)
        print(f"[DEBUG] File written successfully")
        
        # Verify file was created
        if os.path.exists(USER_DATA_FILE):
            print(f"[DEBUG] File exists after write: {USER_DATA_FILE}")
            file_size = os.path.getsize(USER_DATA_FILE)
            print(f"[DEBUG] File size: {file_size} bytes")
        else:
            print(f"[DEBUG] ERROR: File does not exist after write!")
            
        return True
    except Exception as e:
        print(f"[DEBUG] Exception in save_users: {type(e).__name__}: {e}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
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
            print(f"[DEBUG] About to save users for first-time password set")
            if save_users(users):
                print(f"[DEBUG] Password set successfully for {current_user.username}")
                flash('Password set successfully', 'success')
                return redirect(url_for('index'))
            else:
                print(f"[DEBUG] Failed to save password for {current_user.username}")
                flash('Failed to save password', 'error')
        else:
            # Verify current password for existing users
            if check_password_hash(user_data['password_hash'], current_password):
                users[current_user.username]['password_hash'] = generate_password_hash(new_password)
                users[current_user.username]['must_change_password'] = False
                print(f"[DEBUG] About to save users for password change")
                if save_users(users):
                    print(f"[DEBUG] Password changed successfully for {current_user.username}")
                    flash('Password changed successfully', 'success')
                    return redirect(url_for('index'))
                else:
                    print(f"[DEBUG] Failed to save password change for {current_user.username}")
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
        result = os.system('sudo systemctl reload postfix')
        if result == 0:
            return jsonify({'success': True, 'message': 'Postfix reloaded successfully'})
        else:
            return jsonify({'error': 'Failed to reload Postfix'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logs')
@login_required
def logs():
    """Display log viewer page"""
    # Check if user must change password
    if current_user.must_change_password:
        return redirect(url_for('change_password'))
    return render_template('logs.html')

@app.route('/api/logs')
@login_required
def get_logs():
    """Get mail.log file contents"""
    try:
        log_file = '/var/log/mail.log'
        lines = int(request.args.get('lines', '50'))
        
        # Read log file directly
        with open(log_file, 'r') as f:
            # Read all lines and get the last N lines
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            content = ''.join(last_lines)
        
        return jsonify({
            'success': True, 
            'content': content,
            'file': log_file
        })
            
    except FileNotFoundError:
        return jsonify({'error': 'Log file not found'}), 404
    except PermissionError:
        return jsonify({'error': 'Permission denied reading log file'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/follow')
@login_required
def follow_logs():
    """Get latest mail.log file contents (for following)"""
    try:
        log_file = '/var/log/mail.log'
        lines = int(request.args.get('lines', '20'))
        
        # Read log file directly (same as get_logs for simplicity)
        with open(log_file, 'r') as f:
            # Read all lines and get the last N lines
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            content = ''.join(last_lines)
        
        return jsonify({
            'success': True, 
            'content': content,
            'file': log_file
        })
            
    except FileNotFoundError:
        return jsonify({'error': 'Log file not found'}), 404
    except PermissionError:
        return jsonify({'error': 'Permission denied reading log file'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/search')
@login_required
def search_logs():
    """Search mail.log file for specific terms"""
    try:
        log_file = '/var/log/mail.log'
        search_term = request.args.get('q', '').strip()
        max_results = int(request.args.get('max_results', '100'))
        case_sensitive = request.args.get('case_sensitive', 'false').lower() == 'true'
        
        if not search_term:
            return jsonify({'error': 'Search term is required'}), 400
        
        matching_lines = []
        line_number = 0
        
        # Read log file and search for matching lines
        with open(log_file, 'r') as f:
            for line in f:
                line_number += 1
                
                # Perform search (case sensitive or insensitive)
                search_line = line if case_sensitive else line.lower()
                search_query = search_term if case_sensitive else search_term.lower()
                
                if search_query in search_line:
                    matching_lines.append({
                        'line_number': line_number,
                        'content': line.rstrip('\n')
                    })
                    
                    # Limit results to prevent huge responses
                    if len(matching_lines) >= max_results:
                        break
        
        return jsonify({
            'success': True,
            'search_term': search_term,
            'case_sensitive': case_sensitive,
            'total_matches': len(matching_lines),
            'max_results': max_results,
            'matches': matching_lines,
            'file': log_file
        })
            
    except FileNotFoundError:
        return jsonify({'error': 'Log file not found'}), 404
    except PermissionError:
        return jsonify({'error': 'Permission denied reading log file'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/trace')
@login_required
def trace_mail():
    """Trace mail flow through Postfix logs using message IDs and email addresses"""
    try:
        log_file = '/var/log/mail.log'
        source_email = request.args.get('source', '').strip()
        dest_email = request.args.get('destination', '').strip()
        message_id = request.args.get('message_id', '').strip()
        hours_back = int(request.args.get('hours_back', '24'))
        
        if not any([source_email, dest_email, message_id]):
            return jsonify({'error': 'At least one search criteria is required (source, destination, or message_id)'}), 400
        
        import re
        import datetime
        from collections import defaultdict
        
        # Message tracking
        message_traces = defaultdict(list)
        queue_ids = set()
        related_queue_ids = set()
        
        # Regex patterns for Postfix log parsing
        patterns = {
            'message_id': re.compile(r'message-id=<([^>]+)>'),
            'queue_id': re.compile(r'postfix/[^:]+\[[\d]+\]: ([A-F0-9]+):'),
            'from': re.compile(r'from=<([^>]*)>'),
            'to': re.compile(r'to=<([^>]*)>'),
            'status': re.compile(r'status=(\w+)'),
            'delay': re.compile(r'delay=([\d.]+)'),
            'dsn': re.compile(r'dsn=([\d.]+)'),
            'relay': re.compile(r'relay=([^,]+)'),
            'timestamp': re.compile(r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})'),
        }
        
        matching_entries = []
        line_number = 0
        
        # Read log file and find relevant entries
        with open(log_file, 'r') as f:
            for line in f:
                line_number += 1
                line = line.rstrip('\n')
                
                # Skip non-postfix lines
                if 'postfix/' not in line:
                    continue
                
                # Extract basic info
                timestamp_match = patterns['timestamp'].search(line)
                queue_id_match = patterns['queue_id'].search(line)
                
                if not queue_id_match:
                    continue
                
                current_queue_id = queue_id_match.group(1)
                
                # Check if this line matches our search criteria
                matches_criteria = False
                match_reasons = []
                
                # Check message ID
                if message_id:
                    msg_id_match = patterns['message_id'].search(line)
                    if msg_id_match and message_id.lower() in msg_id_match.group(1).lower():
                        matches_criteria = True
                        match_reasons.append(f"Message-ID: {msg_id_match.group(1)}")
                        queue_ids.add(current_queue_id)
                
                # Check source email
                if source_email:
                    from_match = patterns['from'].search(line)
                    if from_match and source_email.lower() in from_match.group(1).lower():
                        matches_criteria = True
                        match_reasons.append(f"From: {from_match.group(1)}")
                        queue_ids.add(current_queue_id)
                
                # Check destination email
                if dest_email:
                    to_match = patterns['to'].search(line)
                    if to_match and dest_email.lower() in to_match.group(1).lower():
                        matches_criteria = True
                        match_reasons.append(f"To: {to_match.group(1)}")
                        queue_ids.add(current_queue_id)
                
                # Check if this queue ID was already identified as relevant
                if current_queue_id in queue_ids or current_queue_id in related_queue_ids:
                    matches_criteria = True
                    if not match_reasons:
                        match_reasons.append(f"Related to Queue-ID: {current_queue_id}")
                
                if matches_criteria:
                    # Extract detailed information
                    entry_info = {
                        'line_number': line_number,
                        'content': line,
                        'timestamp': timestamp_match.group(1) if timestamp_match else '',
                        'queue_id': current_queue_id,
                        'match_reasons': match_reasons,
                        'details': {}
                    }
                    
                    # Extract additional details
                    for key, pattern in patterns.items():
                        if key not in ['timestamp', 'queue_id']:
                            match = pattern.search(line)
                            if match:
                                entry_info['details'][key] = match.group(1)
                    
                    # Determine entry type
                    if 'cleanup' in line:
                        entry_info['type'] = 'message_accepted'
                    elif 'qmgr' in line and 'from=' in line:
                        entry_info['type'] = 'queue_manager'
                    elif 'smtp' in line or 'lmtp' in line:
                        entry_info['type'] = 'delivery_attempt'
                    elif 'smtpd' in line:
                        entry_info['type'] = 'smtp_session'
                    elif 'bounce' in line:
                        entry_info['type'] = 'bounce'
                    elif 'error' in line.lower():
                        entry_info['type'] = 'error'
                    else:
                        entry_info['type'] = 'other'
                    
                    matching_entries.append(entry_info)
                    related_queue_ids.add(current_queue_id)
        
        # Group entries by queue ID for better organization
        grouped_traces = defaultdict(list)
        for entry in matching_entries:
            grouped_traces[entry['queue_id']].append(entry)
        
        # Sort entries within each group by line number
        for queue_id in grouped_traces:
            grouped_traces[queue_id].sort(key=lambda x: x['line_number'])
        
        return jsonify({
            'success': True,
            'source_email': source_email,
            'dest_email': dest_email,
            'message_id': message_id,
            'hours_back': hours_back,
            'total_entries': len(matching_entries),
            'queue_ids': list(queue_ids),
            'grouped_traces': dict(grouped_traces),
            'chronological_entries': sorted(matching_entries, key=lambda x: x['line_number']),
            'file': log_file
        })
            
    except FileNotFoundError:
        return jsonify({'error': 'Log file not found'}), 404
    except PermissionError:
        return jsonify({'error': 'Permission denied reading log file'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Use Waitress for production
    serve(app, host='0.0.0.0', port=8080)