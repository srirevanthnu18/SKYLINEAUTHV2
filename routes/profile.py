from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db
from routes.auth import login_required, get_current_admin

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/profile')
@login_required
def index():
    admin = get_current_admin()
    return render_template('profile.html', admin=admin)


@profile_bp.route('/profile/update', methods=['POST'])
@login_required
def update():
    admin = get_current_admin()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    confirm = request.form.get('confirm_password', '')

    if password and password != confirm:
        flash('Passwords do not match.', 'error')
    else:
        data = {'email': email}
        if password:
            data['password'] = password
        db.update_admin(str(admin['_id']), data)
        flash('Profile updated!', 'success')

    return redirect(url_for('profile.index'))
