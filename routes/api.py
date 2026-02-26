import hmac
import hashlib
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, make_response
from models import db

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

def sign_response(data_json, key):
    """Sign the JSON response body using HMAC-SHA256."""
    if isinstance(key, str):
        key = key.encode()
    signature = hmac.new(key, data_json.encode(), hashlib.sha256).hexdigest()
    return signature

@api_bp.route('/init', methods=['POST'])
def init():
    # KeyAuth SDK uses form data (UploadValues)
    data = request.form
    name = data.get('name')
    ownerid = data.get('ownerid')
    secret = data.get('secret') # Standard KeyAuth doesn't send secret in init, but user's project might
    version = data.get('ver') # SDK sends 'ver'
    sent_key = data.get('enckey')
    
    # In standard KeyAuth, 'secret' is not sent. 
    # We'll try to find the app by name and ownerid first.
    # If the user's project DOES send secret, we use it.
    app = None
    if secret:
        app = db.get_app_by_details(name, secret, ownerid)
    else:
        # Fallback for standard KeyAuth behavior (secret is pre-shared but not sent)
        app = db.db.apps.find_one({'name': name, 'owner_id': db._to_id(ownerid)})

    if not app:
        return "KeyAuth_Invalid" # SDK checks for this exact string
    
    if app.get('version') != version:
        # Standard KeyAuth returns success:false but message:invalid version
        resp_data = {
            "success": False,
            "message": "Invalid application version."
        }
        json_resp = json.dumps(resp_data, separators=(',', ':'))
        signature = sign_response(json_resp, app['secret_key'])
        response = make_response(json_resp)
        response.headers['signature'] = signature
        return response
    
    # Create session
    session_id = db.create_session(app['_id'], sent_key)
    stats = db.get_app_stats(app['_id'])
    
    resp_data = {
        'success': True,
        'message': 'Initialized',
        'sessionid': session_id,
        'appinfo': {
            'numUsers': str(stats['numUsers']),
            'numOnlineUsers': str(stats['numOnlineUsers']),
            'numKeys': str(stats['numKeys']),
            'version': app['version'],
            'customerPanelLink': 'https://keyauth.cc/'
        },
        'newSession': True
    }
    
    json_resp = json.dumps(resp_data, separators=(',', ':'))
    # Init response is signed with the app secret
    signature = sign_response(json_resp, app['secret_key'])
    
    response = make_response(json_resp)
    response.headers['signature'] = signature
    return response


@api_bp.route('/login', methods=['POST'])
def login():
    data = request.form
    session_id = data.get('sessionid')
    username = data.get('username', '')
    password = data.get('pass', '') # SDK sends 'pass'
    hwid = data.get('hwid', '')

    session = db.get_session(session_id)
    if not session:
        return jsonify({'success': False, 'message': 'Invalid session'}), 401
    
    app = db.get_app_by_id(session['app_id'])
    user, error = db.api_login(app['secret_key'], username, password, hwid)
    
    if error:
        resp_data = {'success': False, 'message': error}
    else:
        resp_data = {
            'success': True,
            'message': 'Logged in',
            'info': {
                'username': user['username'],
                'ip': request.remote_addr,
                'hwid': user.get('hwid', ''),
                'createdate': str(user['created_at'].timestamp()) if user.get('created_at') else "0",
                'lastlogin': str(datetime.utcnow().timestamp()),
                'subscriptions': [{'subscription': 'default', 'expiry': str(user['expiry'].timestamp())}] if user.get('expiry') else []
            }
        }

    json_resp = json.dumps(resp_data, separators=(',', ':'))
    signing_key = session['sent_key'] + "-" + app['secret_key']
    signature = sign_response(json_resp, signing_key)
    
    response = make_response(json_resp)
    response.headers['signature'] = signature
    return response


@api_bp.route('/register', methods=['POST'])
def register():
    data = request.form
    session_id = data.get('sessionid')
    username = data.get('username', '')
    password = data.get('pass', '') # SDK sends 'pass'
    license_key = data.get('key', '') # SDK sends 'key'
    hwid = data.get('hwid', '')

    session = db.get_session(session_id)
    if not session:
        return jsonify({'success': False, 'message': 'Invalid session'}), 401
    
    app = db.get_app_by_id(session['app_id'])
    user, error = db.api_register(app['secret_key'], username, password, license_key, hwid)
    
    if error:
        resp_data = {'success': False, 'message': error}
    else:
        resp_data = {'success': True, 'message': 'Registration successful'}

    json_resp = json.dumps(resp_data, separators=(',', ':'))
    signing_key = session['sent_key'] + "-" + app['secret_key']
    signature = sign_response(json_resp, signing_key)
    
    response = make_response(json_resp)
    response.headers['signature'] = signature
    return response


@api_bp.route('/check', methods=['POST'])
def check():
    data = request.form
    session_id = data.get('sessionid')

    session = db.get_session(session_id)
    if not session:
        return jsonify({'success': False, 'message': 'Invalid session'}), 401
    
    app = db.get_app_by_id(session['app_id'])
    resp_data = {'success': True, 'message': 'Session is valid'}

    json_resp = json.dumps(resp_data)
    signing_key = session['sent_key'] + "-" + app['secret_key']
    signature = sign_response(json_resp, signing_key)
    
    response = make_response(json_resp)
    response.headers['signature'] = signature
    return response


@api_bp.route('/var', methods=['POST'])
def get_var():
    data = request.form
    session_id = data.get('sessionid')
    varid = data.get('varid')
    
    session = db.get_session(session_id)
    if not session:
        return jsonify({'success': False, 'message': 'Invalid session'}), 401
    
    app = db.get_app_by_id(session['app_id'])
    vardata = db.get_app_var(app['_id'], varid)
    
    if vardata:
        resp_data = {'success': True, 'message': vardata} # SDK 'var' expects message for the value
    else:
        resp_data = {'success': False, 'message': 'Variable not found'}

    json_resp = json.dumps(resp_data)
    signing_key = session['sent_key'] + "-" + app['secret_key']
    signature = sign_response(json_resp, signing_key)
    
    response = make_response(json_resp)
    response.headers['signature'] = signature
    return response


@api_bp.route('/setvar', methods=['POST'])
def set_var():
    data = request.form
    session_id = data.get('sessionid')
    varid = data.get('var')
    vardata = data.get('data')
    
    session = db.get_session(session_id)
    if not session:
        return jsonify({'success': False, 'message': 'Invalid session'}), 401
    
    app = db.get_app_by_id(session['app_id'])
    db.set_app_var(app['_id'], varid, vardata)
    
    resp_data = {'success': True, 'message': 'Variable updated'}
    json_resp = json.dumps(resp_data)
    signing_key = session['sent_key'] + "-" + app['secret_key']
    signature = sign_response(json_resp, signing_key)
    
    response = make_response(json_resp)
    response.headers['signature'] = signature
    return response
