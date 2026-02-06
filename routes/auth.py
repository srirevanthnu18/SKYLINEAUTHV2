from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db
from functools import wraps

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'admin_id' not in session:
                return redirect(url_for('auth.login'))
            admin = db.get_admin_by_id(session['admin_id'])
            if not admin or admin['role'] not in roles:
                flash('Access denied.', 'error')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated
    return decorator


def get_current_admin():
    if 'admin_id' in session:
        admin = db.get_admin_by_id(session['admin_id'])
        if admin:
            # Keep session credits fresh
            if admin['role'] == 'superadmin':
                session['credits'] = '∞'
            else:
                session['credits'] = admin.get('credits', 0)
        return admin
    return None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'admin_id' in session:
        return redirect(url_for('dashboard.index'))

    if db.count_admins() == 0:
        return redirect(url_for('auth.setup'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        admin = db.verify_admin(username, password)
        if admin:
            # Get client IP address
            login_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if login_ip:
                login_ip = login_ip.split(',')[0].strip()  # Get first IP if multiple
            
            # Update last login IP in database
            db.update_login_ip(str(admin['_id']), login_ip)
            
            session['admin_id'] = str(admin['_id'])
            session['username'] = admin['username']
            session['role'] = admin['role']
            session['credits'] = '∞' if admin['role'] == 'superadmin' else admin.get('credits', 0)
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')


@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    if db.count_admins() > 0:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip()

        if not username or not password:
            flash('Username and password are required.', 'error')
        else:
            admin_id = db.create_admin(username, password, email, 'superadmin')
            if admin_id:
                session['admin_id'] = str(admin_id)
                session['username'] = username
                session['role'] = 'superadmin'
                session['credits'] = '∞'
                flash('Super Admin account created!', 'success')
                return redirect(url_for('dashboard.index'))
            else:
                flash('Failed to create account.', 'error')

    return render_template('setup.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
