from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db
from routes.auth import login_required, role_required, get_current_admin

apps_bp = Blueprint('apps', __name__)


@apps_bp.route('/apps')
@login_required
def index():
    admin = get_current_admin()
    if admin['role'] == 'superadmin':
        apps = db.get_apps()
    else:
        apps = db.get_apps()
    return render_template('apps.html', admin=admin, apps=apps)


@apps_bp.route('/apps/create', methods=['POST'])
@login_required
@role_required('superadmin', 'admin')
def create():
    admin = get_current_admin()
    name = request.form.get('name', '').strip()
    if not name:
        flash('App name is required.', 'error')
    else:
        app_id = db.create_app(name, str(admin['_id']))
        flash(f'Application "{name}" created!', 'success')
    return redirect(url_for('apps.index'))


@apps_bp.route('/apps/delete/<app_id>', methods=['POST'])
@login_required
@role_required('superadmin', 'admin')
def delete(app_id):
    db.delete_app(app_id)
    flash('Application deleted.', 'success')
    return redirect(url_for('apps.index'))


@apps_bp.route('/apps/toggle/<app_id>', methods=['POST'])
@login_required
@role_required('superadmin', 'admin')
def toggle(app_id):
    db.toggle_app(app_id)
    flash('Application status updated.', 'success')
    return redirect(url_for('apps.index'))
