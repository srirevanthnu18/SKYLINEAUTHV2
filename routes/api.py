from flask import Blueprint, request, jsonify
from models import db

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


@api_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    secret = data.get('secret', '')
    username = data.get('username', '')
    password = data.get('password', '')
    hwid = data.get('hwid', '')

    user, error = db.api_login(secret, username, password, hwid)
    if error:
        return jsonify({'success': False, 'error': error}), 401

    return jsonify({
        'success': True,
        'user': {
            'username': user['username'],
            'expiry': user['expiry'].isoformat() if user.get('expiry') else None,
            'hwid': user.get('hwid', ''),
        }
    })


@api_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    secret = data.get('secret', '')
    username = data.get('username', '')
    password = data.get('password', '')
    license_key = data.get('license', '')
    hwid = data.get('hwid', '')

    user, error = db.api_register(secret, username, password, license_key, hwid)
    if error:
        return jsonify({'success': False, 'error': error}), 400

    return jsonify({
        'success': True,
        'message': 'Registration successful',
    })


@api_bp.route('/check', methods=['POST'])
def check():
    data = request.get_json() or {}
    secret = data.get('secret', '')
    license_key = data.get('license', '')

    app = db.db.apps.find_one({'secret_key': secret, 'is_active': True})
    if not app:
        return jsonify({'success': False, 'error': 'Invalid application'}), 401

    lic = db.db.app_users.find_one({'key': license_key, 'app_id': app['_id']})
    if not lic:
        return jsonify({'success': False, 'error': 'Invalid license'}), 404

    return jsonify({
        'success': True,
        'license': {
            'key': lic['key'],
            'is_used': lic.get('is_active', True),
            'created_at': lic['created_at'].isoformat() if lic.get('created_at') else None,
        }
    })
