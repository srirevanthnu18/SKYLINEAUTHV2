from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import json
import os
import pymongo
from bson.objectid import ObjectId


class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.mode = 'mongo'
    
    def init_app(self, app):
        mongo_uri = app.config.get('MONGO_URI')
        if not mongo_uri:
            raise RuntimeError('MONGO_URI is required for MongoDB')
        self.client = pymongo.MongoClient(mongo_uri)
        db_name = app.config.get('DATABASE_NAME', 'neutron')
        self.db = self.client[db_name]
        self.db.admins.create_index('username', unique=True)
        self.db.apps.create_index('secret_key', unique=True)
        self.db.app_users.create_index('key', unique=True)

    def _to_id(self, val):
        if isinstance(val, ObjectId):
            return val
        if val is None:
            return None
        try:
            return ObjectId(str(val))
        except Exception:
            return None

    def _now(self):
        return datetime.utcnow()
    
    # ── Admin / Reseller account management ──────────────────────────

    def create_admin(self, username, password, email, role, created_by=None):
        if self.mode == 'mongo':
            if self.db.admins.find_one({'username': username}):
                return None
            doc = {
                'username': username,
                'password': generate_password_hash(password),
                'email': email,
                'role': role,
                'credits': 0,
                'created_by': self._to_id(created_by) if created_by else None,
                'created_at': self._now(),
                'is_active': True,
                'last_login_ip': None,
                'last_login_at': None,
                'profile_pic': None,
                'assigned_packages': []
            }
            res = self.db.admins.insert_one(doc)
            return str(res.inserted_id)

    def verify_admin(self, username, password):
        if self.mode == 'mongo':
            admin = self.db.admins.find_one({'username': username, 'is_active': True})
            if admin and check_password_hash(admin.get('password', ''), password):
                admin['_id'] = admin['_id']
                return admin
            return None

    def verify_app_user(self, key, password):
        if self.mode == 'mongo':
            user = self.db.app_users.find_one({'key': key})
            if user and check_password_hash(user.get('password', ''), password):
                return user
            return None

    def get_admin_by_id(self, admin_id):
        if self.mode == 'mongo':
            oid = self._to_id(admin_id)
            admin = self.db.admins.find_one({'_id': oid})
            return admin if admin else None

    def get_admins(self, role=None):
        if self.mode == 'mongo':
            q = {}
            if role:
                q['role'] = role
            admins = list(self.db.admins.find(q).sort('created_at', -1))
            return admins

    def update_admin(self, admin_id, data):
        if self.mode == 'mongo':
            oid = self._to_id(admin_id)
            update = {}
            if 'username' in data and data['username']:
                existing = self.db.admins.find_one({'username': data['username']})
                if existing and existing['_id'] != oid:
                    return False, 'Username already exists'
                update['username'] = data['username']
            if 'email' in data:
                update['email'] = data['email']
            if 'password' in data and data['password']:
                update['password'] = generate_password_hash(data['password'])
            if 'is_active' in data:
                update['is_active'] = data['is_active']
            if 'profile_pic' in data:
                update['profile_pic'] = data['profile_pic']
            res = self.db.admins.update_one({'_id': oid}, {'$set': update})
            return (res.modified_count > 0), None

    def update_login_ip(self, admin_id, ip_address):
        if self.mode == 'mongo':
            oid = self._to_id(admin_id)
            self.db.admins.update_one({'_id': oid}, {'$set': {'last_login_ip': ip_address, 'last_login_at': self._now()}})
            return

    def delete_admin(self, admin_id):
        if self.mode == 'mongo':
            oid = self._to_id(admin_id)
            self.db.admins.delete_one({'_id': oid})
            return

    def count_admins(self, role=None):
        if self.mode == 'mongo':
            q = {}
            if role:
                q['role'] = role
            return self.db.admins.count_documents(q)

    # ── Application management ───────────────────────────────────────

    def create_app(self, name, owner_id):
        if self.mode == 'mongo':
            doc = {
                'name': name,
                'secret_key': secrets.token_hex(32),
                'owner_id': self._to_id(owner_id),
                'created_at': self._now(),
                'is_active': True
            }
            res = self.db.apps.insert_one(doc)
            return str(res.inserted_id)

    def get_apps(self, owner_id=None):
        if self.mode == 'mongo':
            q = {}
            if owner_id:
                q['owner_id'] = self._to_id(owner_id)
            return list(self.db.apps.find(q).sort('created_at', -1))

    def get_app_by_id(self, app_id):
        if self.mode == 'mongo':
            oid = self._to_id(app_id)
            app = self.db.apps.find_one({'_id': oid})
            return app if app else None

    def delete_app(self, app_id):
        if self.mode == 'mongo':
            oid = self._to_id(app_id)
            self.db.app_users.delete_many({'app_id': oid})
            self.db.packages.delete_many({'app_id': oid})
            self.db.apps.delete_one({'_id': oid})
            return

    def toggle_app(self, app_id):
        if self.mode == 'mongo':
            oid = self._to_id(app_id)
            app = self.db.apps.find_one({'_id': oid})
            if app:
                self.db.apps.update_one({'_id': oid}, {'$set': {'is_active': not app.get('is_active', True)}})
            return

    def count_apps(self, owner_id=None):
        if self.mode == 'mongo':
            q = {}
            if owner_id:
                q['owner_id'] = self._to_id(owner_id)
            return self.db.apps.count_documents(q)

    # ── Credit system ───────────────────────────────────────────────

    def get_credits(self, admin_id):
        admin = self.get_admin_by_id(admin_id)
        if not admin:
            return 0
        if admin['role'] == 'superadmin':
            return float('inf')
        return admin.get('credits', 0)

    def add_credits(self, admin_id, amount):
        if self.mode == 'mongo':
            oid = self._to_id(admin_id)
            self.db.admins.update_one({'_id': oid}, {'$inc': {'credits': int(amount)}})
            return

    def deduct_credits(self, admin_id, amount=1):
        if self.mode == 'mongo':
            oid = self._to_id(admin_id)
            admin = self.db.admins.find_one({'_id': oid})
            if not admin:
                return False
            if admin.get('role') == 'superadmin':
                return True
            current = int(admin.get('credits', 0))
            if current < int(amount):
                return False
            self.db.admins.update_one({'_id': oid}, {'$inc': {'credits': -int(amount)}})
            return True

    def transfer_credits(self, from_id, to_id, amount):
        if self.mode == 'mongo':
            amount = int(amount)
            if amount <= 0:
                return False, 'Amount must be positive'
            from_oid = self._to_id(from_id)
            to_oid = self._to_id(to_id)
            from_admin = self.db.admins.find_one({'_id': from_oid})
            if not from_admin:
                return False, 'Source not found'
            to_admin = self.db.admins.find_one({'_id': to_oid})
            if not to_admin:
                return False, 'Destination not found'
            if from_admin.get('role') != 'superadmin':
                if int(from_admin.get('credits', 0)) < amount:
                    return False, 'Not enough credits'
                self.db.admins.update_one({'_id': from_oid}, {'$inc': {'credits': -amount}})
            self.db.admins.update_one({'_id': to_oid}, {'$inc': {'credits': amount}})
            return True, None

    # ── App Users (end-users) management ─────────────────────────────

    def create_user_direct(self, app_id, package_id, created_by, count=1, custom_days=None, hwid_lock=True, username=None, password=None):
        if self.mode == 'mongo':
            admin = self.db.admins.find_one({'_id': self._to_id(created_by)})
            if not admin:
                return None, 'Invalid admin'
            count = int(count)
            if username:
                count = 1
            if admin.get('role') != 'superadmin':
                current_credits = int(admin.get('credits', 0))
                if current_credits < count:
                    return None, f'Not enough credits. You have {current_credits}, need {count}'
            pkg = self.db.packages.find_one({'_id': self._to_id(package_id)})
            if not pkg:
                return None, 'Invalid package'
            if custom_days:
                expiry_base = self._now() + timedelta(days=int(custom_days))
            else:
                expiry_base = self._now() + timedelta(days=int(pkg.get('duration_days', 30)))
            created_users = []
            for i in range(count):
                if username and i == 0:
                    key = username.strip()
                    raw_password = password.strip() if password else secrets.token_urlsafe(8)
                else:
                    key = f"NEUTRON-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
                    raw_password = secrets.token_urlsafe(8)
                if self.db.app_users.find_one({'key': key}):
                    return None, f'Username/Key "{key}" already exists'
                self.db.app_users.insert_one({
                    'app_id': self._to_id(app_id),
                    'key': key,
                    'password': generate_password_hash(raw_password),
                    'hwid': '',
                    'hwid_lock': bool(hwid_lock),
                    'expiry': expiry_base,
                    'package_id': self._to_id(package_id),
                    'created_by': self._to_id(created_by),
                    'created_at': self._now(),
                    'is_active': True,
                })
                created_users.append({'key': key, 'password': raw_password})
            if admin.get('role') != 'superadmin':
                self.db.admins.update_one({'_id': admin['_id']}, {'$inc': {'credits': -count}})
            return created_users, None

    def get_app_users(self, app_id=None, created_by=None):
        if self.mode == 'mongo':
            q = {}
            if app_id:
                q['app_id'] = self._to_id(app_id)
            if created_by:
                q['created_by'] = self._to_id(created_by)
            return list(self.db.app_users.find(q).sort('created_at', -1))

    def delete_app_user(self, user_id):
        if self.mode == 'mongo':
            self.db.app_users.delete_one({'_id': self._to_id(user_id)})
            return

    def count_app_users(self, app_id=None, created_by=None):
        if self.mode == 'mongo':
            q = {}
            if app_id:
                q['app_id'] = self._to_id(app_id)
            if created_by:
                q['created_by'] = self._to_id(created_by)
            return self.db.app_users.count_documents(q)

    def toggle_app_user(self, user_id):
        if self.mode == 'mongo':
            user = self.db.app_users.find_one({'_id': self._to_id(user_id)})
            if user:
                self.db.app_users.update_one({'_id': user['_id']}, {'$set': {'is_active': not user.get('is_active', True)}})
            return

    # ── Package management ───────────────────────────────────────────

    def create_package(self, name, duration_days, app_id, created_by):
        if self.mode == 'mongo':
            doc = {
                'name': name,
                'duration_days': int(duration_days),
                'app_id': self._to_id(app_id),
                'created_by': self._to_id(created_by),
                'created_at': self._now(),
            }
            res = self.db.packages.insert_one(doc)
            return str(res.inserted_id)

    def get_packages(self, app_id=None):
        if self.mode == 'mongo':
            q = {}
            if app_id:
                q['app_id'] = self._to_id(app_id)
            return list(self.db.packages.find(q).sort('created_at', -1))

    def get_package_by_id(self, package_id):
        if self.mode == 'mongo':
            return self.db.packages.find_one({'_id': self._to_id(package_id)})

    def delete_package(self, package_id):
        if self.mode == 'mongo':
            self.db.packages.delete_one({'_id': self._to_id(package_id)})
            return

    def count_packages(self, app_id=None):
        if self.mode == 'mongo':
            q = {}
            if app_id:
                q['app_id'] = self._to_id(app_id)
            return self.db.packages.count_documents(q)

    # ── API auth (for external app integration) ──────────────────────

    def api_login(self, app_secret, key, password, hwid=''):
        if self.mode == 'mongo':
            app = self.db.apps.find_one({'secret_key': app_secret, 'is_active': True})
            if not app:
                return None, 'Invalid application'
            user = self.db.app_users.find_one({'app_id': app['_id'], 'key': key, 'is_active': True})
            if not user or not check_password_hash(user.get('password', ''), password):
                return None, 'Invalid credentials'
            if user.get('expiry') and user['expiry'] < self._now():
                return None, 'Subscription expired'
            if user.get('hwid_lock', True):
                if user.get('hwid') and user['hwid'] != hwid and hwid:
                    return None, 'HWID mismatch'
                if not user.get('hwid') and hwid:
                    self.db.app_users.update_one({'_id': user['_id']}, {'$set': {'hwid': hwid}})
                    user['hwid'] = hwid
            return user, None





    # ── Backup ───────────────────────────────────────────────────────

    def backup(self, backup_dir):
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'backup_{timestamp}.json')
        if self.mode == 'mongo':
            def serialize(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                if isinstance(obj, ObjectId):
                    return str(obj)
                return obj
            data = {
                'admins': list(self.db.admins.find()),
                'apps': list(self.db.apps.find()),
                'packages': list(self.db.packages.find()),
                'app_users': list(self.db.app_users.find()),
            }
            with open(backup_path, 'w') as f:
                json.dump(data, f, indent=2, default=serialize)
            return backup_path

    def get_last_backup_time(self, backup_dir):
        os.makedirs(backup_dir, exist_ok=True)
        files = [f for f in os.listdir(backup_dir) if f.endswith('.json')]
        if not files:
            return None
        files.sort(reverse=True)
        latest = os.path.getmtime(os.path.join(backup_dir, files[0]))
        return datetime.fromtimestamp(latest)

    # ── Reseller package assignment ──────────────────────────────────

    def assign_package_to_reseller(self, reseller_id, package_id):
        if self.mode == 'mongo':
            oid = self._to_id(reseller_id)
            pkg_oid = self._to_id(package_id)
            self.db.admins.update_one({'_id': oid}, {'$addToSet': {'assigned_packages': pkg_oid}})
            return

    def remove_package_from_reseller(self, reseller_id, package_id):
        if self.mode == 'mongo':
            oid = self._to_id(reseller_id)
            pkg_oid = self._to_id(package_id)
            self.db.admins.update_one({'_id': oid}, {'$pull': {'assigned_packages': pkg_oid}})
            return

    def get_reseller_packages(self, reseller_id):
        if self.mode == 'mongo':
            admin = self.db.admins.find_one({'_id': self._to_id(reseller_id)})
            if not admin or not admin.get('assigned_packages'):
                return []
            return list(self.db.packages.find({'_id': {'$in': admin['assigned_packages']}}))

    # ── Key operations (for resellers) ────────────────────────────────

    def reset_hwid(self, user_id):
        if self.mode == 'mongo':
            self.db.app_users.update_one({'_id': self._to_id(user_id)}, {'$set': {'hwid': ''}})
            return

    def extend_license(self, user_id, days):
        if self.mode == 'mongo':
            user = self.db.app_users.find_one({'_id': self._to_id(user_id)})
            if user:
                current_expiry = user.get('expiry') or self._now()
                if current_expiry < self._now():
                    current_expiry = self._now()
                new_expiry = current_expiry + timedelta(days=int(days))
                self.db.app_users.update_one({'_id': user['_id']}, {'$set': {'expiry': new_expiry}})
            return

    def ban_license(self, user_id):
        if self.mode == 'mongo':
            self.db.app_users.update_one({'_id': self._to_id(user_id)}, {'$set': {'is_active': False}})
            return

    def unban_license(self, user_id):
        if self.mode == 'mongo':
            self.db.app_users.update_one({'_id': self._to_id(user_id)}, {'$set': {'is_active': True}})
            return

    def get_app_user_by_id(self, user_id):
        if self.mode == 'mongo':
            return self.db.app_users.find_one({'_id': self._to_id(user_id)})

    def get_license_by_id(self, license_id):
        # This was referencing a 'licenses' collection that doesn't exist in the schema
        # Mapping to app_users for compatibility
        return self.get_app_user_by_id(license_id)

    # ── Dashboard stats ──────────────────────────────────────────────

    def get_stats(self, admin=None):
        if admin and admin['role'] == 'reseller':
            admin_id = admin['_id']
            return {
                'users': self.count_app_users(created_by=admin_id),
                'credits': admin.get('credits', 0),
                'assigned_packages': len(admin.get('assigned_packages', [])),
            }
        if admin and admin['role'] == 'admin':
            return {
                'apps': self.count_apps(),
                'users': self.count_app_users(),
                'packages': self.count_packages(),
                'credits': admin.get('credits', 0),
                'admins': self.count_admins(role='admin'),
                'resellers': self.count_admins(role='reseller'),
            }
        return {
            'apps': self.count_apps(),
            'users': self.count_app_users(),
            'packages': self.count_packages(),
            'credits': '∞',
            'admins': self.count_admins(role='admin'),
            'resellers': self.count_admins(role='reseller'),
        }


db = Database()
