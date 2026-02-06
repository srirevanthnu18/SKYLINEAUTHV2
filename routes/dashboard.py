from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from models import db
from routes.auth import login_required, get_current_admin
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    admin = get_current_admin()
    stats = db.get_stats(admin)
    last_backup = db.get_last_backup_time(current_app.config['BACKUP_DIR'])
    now = datetime.utcnow()

    if last_backup:
        diff = now - last_backup
        minutes = int(diff.total_seconds() / 60)
        if minutes < 1:
            backup_text = 'Just now'
        elif minutes < 60:
            backup_text = f'{minutes} minutes ago'
        else:
            hours = minutes // 60
            backup_text = f'{hours} hours ago'
    else:
        backup_text = 'Never'

    return render_template('dashboard.html',
                           admin=admin,
                           stats=stats,
                           last_backup=backup_text,
                           now=now)


@dashboard_bp.route('/backup', methods=['POST'])
@login_required
def backup():
    admin = get_current_admin()
    if admin['role'] not in ('superadmin', 'admin'):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard.index'))

    try:
        path = db.backup(current_app.config['BACKUP_DIR'])
        flash(f'Backup created successfully!', 'success')
    except Exception as e:
        flash(f'Backup failed: {str(e)}', 'error')

    return redirect(url_for('dashboard.index'))
