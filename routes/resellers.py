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
    packages = db.get_packages()
    # Attach assigned package details to each reseller
    for reseller in resellers:
        assigned_ids = reseller.get('assigned_packages', [])
        reseller['assigned_package_list'] = [
            db.get_package_by_id(pid) for pid in assigned_ids
            if db.get_package_by_id(pid)
        ]
    return render_template('resellers.html', admin=admin, resellers=resellers, packages=packages)


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


@resellers_bp.route('/resellers/<reseller_id>/assign-package', methods=['POST'])
@login_required
@role_required('superadmin', 'admin')
def assign_package(reseller_id):
    package_id = request.form.get('package_id')
    if not package_id:
        flash('Please select a package.', 'error')
    else:
        db.assign_package_to_reseller(reseller_id, package_id)
        flash('Package assigned to reseller.', 'success')
    return redirect(url_for('resellers.index'))


@resellers_bp.route('/resellers/<reseller_id>/remove-package/<package_id>', methods=['POST'])
@login_required
@role_required('superadmin', 'admin')
def remove_package(reseller_id, package_id):
    db.remove_package_from_reseller(reseller_id, package_id)
    flash('Package removed from reseller.', 'success')
    return redirect(url_for('resellers.index'))


@resellers_bp.route('/resellers/<reseller_id>/give-credits', methods=['POST'])
@login_required
@role_required('superadmin', 'admin')
def give_credits(reseller_id):
    admin = get_current_admin()
    amount = request.form.get('credits', 0)
    try:
        amount = int(amount)
    except ValueError:
        flash('Invalid credit amount.', 'error')
        return redirect(url_for('resellers.index'))

    if amount <= 0:
        flash('Credit amount must be positive.', 'error')
    else:
        success, error = db.transfer_credits(str(admin['_id']), reseller_id, amount)
        if success:
            flash(f'Gave {amount} credits to reseller.', 'success')
        else:
            flash(error, 'error')
    return redirect(url_for('resellers.index'))
