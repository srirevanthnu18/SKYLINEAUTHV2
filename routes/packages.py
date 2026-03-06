from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db
from routes.auth import login_required, role_required, get_current_admin

packages_bp = Blueprint('packages', __name__)


@packages_bp.route('/packages')
@login_required
@role_required('superadmin', 'admin')
def index():
    admin = get_current_admin()
    apps = db.get_apps()
    app_id = request.args.get('app_id')
    packages = db.get_packages(app_id=app_id)
    return render_template('packages.html', admin=admin, packages=packages, apps=apps, selected_app=app_id)


@packages_bp.route('/packages/create', methods=['POST'])
@login_required
@role_required('superadmin', 'admin')
def create():
    admin = get_current_admin()
    name = request.form.get('name', '').strip()
    duration = request.form.get('duration_days', '30')
    app_id = request.form.get('app_id')

    if not name or not app_id:
        flash('Package name and application are required.', 'error')
    else:
        pkg_id = db.create_package(name, duration, app_id, str(admin['_id']))
        flash(f'Package "{name}" created!', 'success')
    return redirect(url_for('packages.index'))


@packages_bp.route('/packages/delete/<package_id>', methods=['POST'])
@login_required
@role_required('superadmin', 'admin')
def delete(package_id):
    db.delete_package(package_id)
    flash('Package deleted.', 'success')
    return redirect(url_for('packages.index'))
