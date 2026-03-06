"""
Internal management API used by the Discord bot.
Routes are protected by a shared MGMT_SECRET token in the Authorization header.
Only callable from localhost / the bot — not exposed publicly.
"""

import os
from flask import Blueprint, request, jsonify
from models import db
from bson import ObjectId

discord_mgmt_bp = Blueprint('discord_mgmt', __name__, url_prefix='/mgmt')


def _check_token():
    """Validate the management secret token."""
    token = request.headers.get('Authorization', '')
    expected = os.environ.get('MGMT_SECRET', '')
    if not expected:
        return False, 'MGMT_SECRET not configured on server'
    if token != f'Bearer {expected}':
        return False, 'Unauthorized'
    return True, None


@discord_mgmt_bp.route('/users/create', methods=['POST'])
def create_user():
    ok, err = _check_token()
    if not ok:
        return jsonify({'success': False, 'message': err}), 401

    data = request.json or {}
    app_id = data.get('app_id') or os.environ.get('DISCORD_APP_ID')
    package_id = data.get('package_id') or os.environ.get('DISCORD_PACKAGE_ID')
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    days = int(data.get('days', 30))

    # We need a creator admin — use superadmin (first one found)
    admin = db.db.admins.find_one({'role': 'superadmin'})
    if not admin:
        return jsonify({'success': False, 'message': 'No superadmin found'}), 500

    users, error = db.create_user_direct(
        app_id=app_id,
        package_id=package_id,
        created_by=str(admin['_id']),
        count=1,
        custom_days=days,
        username=username if username else None,
        password=password if password else None,
    )

    if error:
        return jsonify({'success': False, 'message': error})
    return jsonify({'success': True, 'users': users})


@discord_mgmt_bp.route('/users/delete', methods=['DELETE'])
def delete_user():
    ok, err = _check_token()
    if not ok:
        return jsonify({'success': False, 'message': err}), 401

    data = request.json or {}
    key = data.get('key', '').strip()
    if not key:
        return jsonify({'success': False, 'message': 'key is required'})

    user = db.db.app_users.find_one({'key': key})
    if not user:
        return jsonify({'success': False, 'message': f'User "{key}" not found'})

    db.delete_app_user(str(user['_id']))
    return jsonify({'success': True, 'message': f'User "{key}" deleted'})


@discord_mgmt_bp.route('/users/reset-hwid', methods=['POST'])
def reset_hwid():
    ok, err = _check_token()
    if not ok:
        return jsonify({'success': False, 'message': err}), 401

    data = request.json or {}
    key = data.get('key', '').strip()
    if not key:
        return jsonify({'success': False, 'message': 'key is required'})

    user = db.db.app_users.find_one({'key': key})
    if not user:
        return jsonify({'success': False, 'message': f'User "{key}" not found'})

    db.reset_hwid(str(user['_id']))
    return jsonify({'success': True, 'message': f'HWID reset for "{key}"'})


@discord_mgmt_bp.route('/users/list', methods=['GET'])
def list_users():
    ok, err = _check_token()
    if not ok:
        return jsonify({'success': False, 'message': err}), 401

    app_id = request.args.get('app_id') or os.environ.get('DISCORD_APP_ID')
    users = db.get_app_users(app_id=app_id)
    result = []
    for u in users[:25]:  # cap at 25 for Discord
        result.append({
            'key': u.get('key', ''),
            'is_active': u.get('is_active', True),
            'expiry': u['expiry'].strftime('%Y-%m-%d') if u.get('expiry') else 'N/A',
            'hwid_locked': bool(u.get('hwid')),
        })
    return jsonify({'success': True, 'users': result, 'total': len(users)})
