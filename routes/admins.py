from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db
from routes.auth import login_required, role_required, get_current_admin

admins_bp = Blueprint('admins', __name__)


@admins_bp.route('/admins')
@login_required
@role_required('superadmin')
def index():
    admin = get_current_admin()
    admins = db.get_admins(role='admin')
    return render_template('admins.html', admin=admin, admins=admins)


@admins_bp.route('/admins/create', methods=['POST'])
@login_required
@role_required('superadmin')
def create():
    admin = get_current_admin()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    email = request.form.get('email', '').strip()

    if not username or not password:
        flash('Username and password are required.', 'error')
    else:
        admin_id = db.create_admin(username, password, email, 'admin', str(admin['_id']))
        if admin_id:
            flash(f'Admin "{username}" created!', 'success')
        else:
            flash('Username already exists.', 'error')
    return redirect(url_for('admins.index'))


@admins_bp.route('/admins/delete/<admin_id>', methods=['POST'])
@login_required
@role_required('superadmin')
def delete(admin_id):
    target = db.get_admin_by_id(admin_id)
    if target and target['role'] == 'superadmin':
        flash('Cannot delete super admin.', 'error')
    else:
        db.delete_admin(admin_id)
        flash('Admin deleted.', 'success')
    return redirect(url_for('admins.index'))


@admins_bp.route('/admins/toggle/<admin_id>', methods=['POST'])
@login_required
@role_required('superadmin')
def toggle(admin_id):
    target = db.get_admin_by_id(admin_id)
    if target:
        db.update_admin(admin_id, {'is_active': not target.get('is_active', True)})
        flash('Admin status updated.', 'success')
    return redirect(url_for('admins.index'))


@admins_bp.route('/admins/give-credits/<admin_id>', methods=['POST'])
@login_required
@role_required('superadmin')
def give_credits(admin_id):
    admin = get_current_admin()
    amount = request.form.get('credits', 0)
    try:
        amount = int(amount)
    except ValueError:
        flash('Invalid credit amount.', 'error')
        return redirect(url_for('admins.index'))

    if amount <= 0:
        flash('Credit amount must be positive.', 'error')
    else:
        success, error = db.transfer_credits(str(admin['_id']), admin_id, amount)
        if success:
            flash(f'Gave {amount} credits to admin.', 'success')
        else:
            flash(error, 'error')
    return redirect(url_for('admins.index'))
