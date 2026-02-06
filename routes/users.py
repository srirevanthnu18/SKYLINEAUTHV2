from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db
from routes.auth import login_required, get_current_admin

users_bp = Blueprint('users', __name__)


@users_bp.route('/users')
@login_required
def index():
    admin = get_current_admin()
    app_id = request.args.get('app_id')
    apps = db.get_apps()

    if admin['role'] == 'reseller':
        users = db.get_app_users(app_id=app_id, created_by=str(admin['_id']))
        licenses = db.get_licenses(app_id=app_id, created_by=str(admin['_id']))
    else:
        users = db.get_app_users(app_id=app_id)
        licenses = db.get_licenses(app_id=app_id)

    packages = db.get_packages(app_id=app_id)
    return render_template('users.html', admin=admin, users=users, apps=apps,
                           licenses=licenses, packages=packages, selected_app=app_id)


@users_bp.route('/users/create', methods=['POST'])
@login_required
def create():
    admin = get_current_admin()
    app_id = request.form.get('app_id')
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    license_key = request.form.get('license_key', '').strip()

    if not all([app_id, username, password, license_key]):
        flash('All fields are required.', 'error')
    else:
        user_id, error = db.create_app_user(app_id, username, password, license_key, None, str(admin['_id']))
        if error:
            flash(error, 'error')
        else:
            flash(f'User "{username}" created!', 'success')
    return redirect(url_for('users.index'))


@users_bp.route('/users/delete/<user_id>', methods=['POST'])
@login_required
def delete(user_id):
    db.delete_app_user(user_id)
    flash('User deleted.', 'success')
    return redirect(url_for('users.index'))


@users_bp.route('/users/toggle/<user_id>', methods=['POST'])
@login_required
def toggle(user_id):
    db.toggle_app_user(user_id)
    flash('User status updated.', 'success')
    return redirect(url_for('users.index'))


@users_bp.route('/licenses/generate', methods=['POST'])
@login_required
def generate_licenses():
    admin = get_current_admin()
    app_id = request.form.get('app_id')
    package_id = request.form.get('package_id')
    count = request.form.get('count', 1)

    if not app_id or not package_id:
        flash('Application and package are required.', 'error')
    else:
        keys = db.generate_license(app_id, package_id, str(admin['_id']), count)
        flash(f'Generated {len(keys)} license(s): {", ".join(keys)}', 'success')

    return redirect(url_for('users.index'))


@users_bp.route('/licenses/delete/<license_id>', methods=['POST'])
@login_required
def delete_license(license_id):
    db.delete_license(license_id)
    flash('License deleted.', 'success')
    return redirect(url_for('users.index'))
