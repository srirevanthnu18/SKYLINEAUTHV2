from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db
from routes.auth import login_required, role_required, get_current_admin

resellers_bp = Blueprint('resellers', __name__)


@resellers_bp.route('/resellers')
@login_required
@role_required('superadmin', 'admin')
def index():
    admin = get_current_admin()
    resellers = db.get_admins(role='reseller')
    return render_template('resellers.html', admin=admin, resellers=resellers)


@resellers_bp.route('/resellers/create', methods=['POST'])
@login_required
@role_required('superadmin', 'admin')
def create():
    admin = get_current_admin()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    email = request.form.get('email', '').strip()

    if not username or not password:
        flash('Username and password are required.', 'error')
    else:
        reseller_id = db.create_admin(username, password, email, 'reseller', str(admin['_id']))
        if reseller_id:
            flash(f'Reseller "{username}" created!', 'success')
        else:
            flash('Username already exists.', 'error')
    return redirect(url_for('resellers.index'))


@resellers_bp.route('/resellers/delete/<reseller_id>', methods=['POST'])
@login_required
@role_required('superadmin', 'admin')
def delete(reseller_id):
    db.delete_admin(reseller_id)
    flash('Reseller deleted.', 'success')
    return redirect(url_for('resellers.index'))


@resellers_bp.route('/resellers/toggle/<reseller_id>', methods=['POST'])
@login_required
@role_required('superadmin', 'admin')
def toggle(reseller_id):
    reseller = db.get_admin_by_id(reseller_id)
    if reseller:
        db.update_admin(reseller_id, {'is_active': not reseller.get('is_active', True)})
        flash('Reseller status updated.', 'success')
    return redirect(url_for('resellers.index'))
