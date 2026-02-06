from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import secrets
import json
import os


class Database:
    def __init__(self):
        self.client = None
        self.db = None

    def init_app(self, app):
        self.client = MongoClient(app.config['MONGO_URI'])
        self.db = self.client[app.config['DATABASE_NAME']]
        self._create_indexes()

    def _create_indexes(self):
        self.db.admins.create_index('username', unique=True)
        self.db.apps.create_index('secret_key', unique=True)
        self.db.app_users.create_index([('username', 1), ('app_id', 1)])
        self.db.licenses.create_index('key', unique=True)

    # ── Admin / Reseller account management ──────────────────────────

    def create_admin(self, username, password, email, role, created_by=None):
        if self.db.admins.find_one({'username': username}):
            return None
        doc = {
            'username': username,
            'password': generate_password_hash(password),
            'email': email,
            'role': role,
            'created_by': ObjectId(created_by) if created_by else None,
            'created_at': datetime.utcnow(),
            'is_active': True,
        }
        result = self.db.admins.insert_one(doc)
        return result.inserted_id

    def verify_admin(self, username, password):
        admin = self.db.admins.find_one({'username': username, 'is_active': True})
        if admin and check_password_hash(admin['password'], password):
            return admin
        return None

    def get_admin_by_id(self, admin_id):
        return self.db.admins.find_one({'_id': ObjectId(admin_id)})

    def get_admins(self, role=None):
        query = {}
        if role:
            query['role'] = role
        return list(self.db.admins.find(query).sort('created_at', -1))

    def update_admin(self, admin_id, data):
        update = {}
        if 'email' in data:
            update['email'] = data['email']
        if 'password' in data and data['password']:
            update['password'] = generate_password_hash(data['password'])
        if 'is_active' in data:
            update['is_active'] = data['is_active']
        if update:
            self.db.admins.update_one({'_id': ObjectId(admin_id)}, {'$set': update})

    def delete_admin(self, admin_id):
        self.db.admins.delete_one({'_id': ObjectId(admin_id)})

    def count_admins(self, role=None):
        query = {}
        if role:
            query['role'] = role
        return self.db.admins.count_documents(query)

    # ── Application management ───────────────────────────────────────

    def create_app(self, name, owner_id):
        doc = {
            'name': name,
            'secret_key': secrets.token_hex(32),
            'owner_id': ObjectId(owner_id),
            'created_at': datetime.utcnow(),
            'is_active': True,
        }
        result = self.db.apps.insert_one(doc)
        return result.inserted_id

    def get_apps(self, owner_id=None):
        query = {}
        if owner_id:
            query['owner_id'] = ObjectId(owner_id)
        return list(self.db.apps.find(query).sort('created_at', -1))

    def get_app_by_id(self, app_id):
        return self.db.apps.find_one({'_id': ObjectId(app_id)})

    def delete_app(self, app_id):
        self.db.apps.delete_one({'_id': ObjectId(app_id)})
        self.db.app_users.delete_many({'app_id': ObjectId(app_id)})
        self.db.licenses.delete_many({'app_id': ObjectId(app_id)})
        self.db.packages.delete_many({'app_id': ObjectId(app_id)})

    def toggle_app(self, app_id):
        app = self.get_app_by_id(app_id)
        if app:
            self.db.apps.update_one(
                {'_id': ObjectId(app_id)},
                {'$set': {'is_active': not app['is_active']}}
            )

    def count_apps(self, owner_id=None):
        query = {}
        if owner_id:
            query['owner_id'] = ObjectId(owner_id)
        return self.db.apps.count_documents(query)

    # ── App Users (end-users) management ─────────────────────────────

    def create_app_user(self, app_id, username, password, license_key, package_id, created_by):
        license_doc = self.db.licenses.find_one({'key': license_key, 'is_used': False})
        if not license_doc:
            return None, 'Invalid or already used license key'

        pkg = self.db.packages.find_one({'_id': license_doc['package_id']})
        expiry = datetime.utcnow() + timedelta(days=pkg['duration_days']) if pkg else None

        doc = {
            'app_id': ObjectId(app_id),
            'username': username,
            'password': generate_password_hash(password),
            'license_key': license_key,
            'hwid': '',
            'expiry': expiry,
            'package_id': license_doc['package_id'],
            'created_by': ObjectId(created_by),
            'created_at': datetime.utcnow(),
            'is_active': True,
        }
        result = self.db.app_users.insert_one(doc)
        self.db.licenses.update_one({'_id': license_doc['_id']}, {'$set': {'is_used': True, 'used_by': result.inserted_id}})
        return result.inserted_id, None

    def get_app_users(self, app_id=None, created_by=None):
        query = {}
        if app_id:
            query['app_id'] = ObjectId(app_id)
        if created_by:
            query['created_by'] = ObjectId(created_by)
        return list(self.db.app_users.find(query).sort('created_at', -1))

    def delete_app_user(self, user_id):
        user = self.db.app_users.find_one({'_id': ObjectId(user_id)})
        if user:
            self.db.licenses.update_one(
                {'key': user.get('license_key')},
                {'$set': {'is_used': False, 'used_by': None}}
            )
        self.db.app_users.delete_one({'_id': ObjectId(user_id)})

    def count_app_users(self, app_id=None, created_by=None):
        query = {}
        if app_id:
            query['app_id'] = ObjectId(app_id)
        if created_by:
            query['created_by'] = ObjectId(created_by)
        return self.db.app_users.count_documents(query)

    def toggle_app_user(self, user_id):
        user = self.db.app_users.find_one({'_id': ObjectId(user_id)})
        if user:
            self.db.app_users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'is_active': not user['is_active']}}
            )

    # ── Package management ───────────────────────────────────────────

    def create_package(self, name, duration_days, app_id, created_by):
        doc = {
            'name': name,
            'duration_days': int(duration_days),
            'app_id': ObjectId(app_id),
            'created_by': ObjectId(created_by),
            'created_at': datetime.utcnow(),
        }
        result = self.db.packages.insert_one(doc)
        return result.inserted_id

    def get_packages(self, app_id=None):
        query = {}
        if app_id:
            query['app_id'] = ObjectId(app_id)
        return list(self.db.packages.find(query).sort('created_at', -1))

    def get_package_by_id(self, package_id):
        return self.db.packages.find_one({'_id': ObjectId(package_id)})

    def delete_package(self, package_id):
        self.db.packages.delete_one({'_id': ObjectId(package_id)})

    def count_packages(self, app_id=None):
        query = {}
        if app_id:
            query['app_id'] = ObjectId(app_id)
        return self.db.packages.count_documents(query)

    # ── License management ───────────────────────────────────────────

    def generate_license(self, app_id, package_id, created_by, count=1):
        keys = []
        for _ in range(int(count)):
            key = f"NEUTRON-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
            doc = {
                'key': key,
                'app_id': ObjectId(app_id),
                'package_id': ObjectId(package_id),
                'is_used': False,
                'used_by': None,
                'created_by': ObjectId(created_by),
                'created_at': datetime.utcnow(),
            }
            self.db.licenses.insert_one(doc)
            keys.append(key)
        return keys

    def get_licenses(self, app_id=None, created_by=None):
        query = {}
        if app_id:
            query['app_id'] = ObjectId(app_id)
        if created_by:
            query['created_by'] = ObjectId(created_by)
        return list(self.db.licenses.find(query).sort('created_at', -1))

    def delete_license(self, license_id):
        self.db.licenses.delete_one({'_id': ObjectId(license_id)})

    def count_licenses(self, app_id=None, used=None):
        query = {}
        if app_id:
            query['app_id'] = ObjectId(app_id)
        if used is not None:
            query['is_used'] = used
        return self.db.licenses.count_documents(query)

    # ── API auth (for external app integration) ──────────────────────

    def api_login(self, app_secret, username, password, hwid=''):
        app = self.db.apps.find_one({'secret_key': app_secret, 'is_active': True})
        if not app:
            return None, 'Invalid application'

        user = self.db.app_users.find_one({
            'app_id': app['_id'],
            'username': username,
            'is_active': True,
        })
        if not user or not check_password_hash(user['password'], password):
            return None, 'Invalid credentials'

        if user.get('expiry') and user['expiry'] < datetime.utcnow():
            return None, 'Subscription expired'

        if user.get('hwid') and user['hwid'] != hwid and hwid:
            return None, 'HWID mismatch'

        if not user.get('hwid') and hwid:
            self.db.app_users.update_one({'_id': user['_id']}, {'$set': {'hwid': hwid}})

        return user, None

    def api_register(self, app_secret, username, password, license_key, hwid=''):
        app = self.db.apps.find_one({'secret_key': app_secret, 'is_active': True})
        if not app:
            return None, 'Invalid application'

        if self.db.app_users.find_one({'app_id': app['_id'], 'username': username}):
            return None, 'Username already exists'

        license_doc = self.db.licenses.find_one({
            'key': license_key,
            'app_id': app['_id'],
            'is_used': False,
        })
        if not license_doc:
            return None, 'Invalid or used license key'

        pkg = self.db.packages.find_one({'_id': license_doc['package_id']})
        expiry = datetime.utcnow() + timedelta(days=pkg['duration_days']) if pkg else None

        doc = {
            'app_id': app['_id'],
            'username': username,
            'password': generate_password_hash(password),
            'license_key': license_key,
            'hwid': hwid,
            'expiry': expiry,
            'package_id': license_doc['package_id'],
            'created_by': None,
            'created_at': datetime.utcnow(),
            'is_active': True,
        }
        result = self.db.app_users.insert_one(doc)
        self.db.licenses.update_one(
            {'_id': license_doc['_id']},
            {'$set': {'is_used': True, 'used_by': result.inserted_id}}
        )
        return doc, None

    # ── Backup ───────────────────────────────────────────────────────

    def backup(self, backup_dir):
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'backup_{timestamp}.json')

        data = {}
        for coll_name in self.db.list_collection_names():
            docs = list(self.db[coll_name].find())
            for doc in docs:
                for key, val in doc.items():
                    if isinstance(val, ObjectId):
                        doc[key] = str(val)
                    elif isinstance(val, datetime):
                        doc[key] = val.isoformat()
            data[coll_name] = docs

        with open(backup_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        return backup_path

    def get_last_backup_time(self, backup_dir):
        os.makedirs(backup_dir, exist_ok=True)
        files = [f for f in os.listdir(backup_dir) if f.endswith('.json')]
        if not files:
            return None
        files.sort(reverse=True)
        latest = os.path.getmtime(os.path.join(backup_dir, files[0]))
        return datetime.fromtimestamp(latest)

    # ── Dashboard stats ──────────────────────────────────────────────

    def get_stats(self, admin=None):
        if admin and admin['role'] == 'reseller':
            return {
                'apps': self.count_apps(),
                'users': self.count_app_users(created_by=str(admin['_id'])),
                'packages': self.count_packages(),
                'licenses': self.count_licenses(),
                'licenses_used': self.count_licenses(used=True),
                'licenses_unused': self.count_licenses(used=False),
                'admins': 0,
                'resellers': 0,
            }
        return {
            'apps': self.count_apps(),
            'users': self.count_app_users(),
            'packages': self.count_packages(),
            'licenses': self.count_licenses(),
            'licenses_used': self.count_licenses(used=True),
            'licenses_unused': self.count_licenses(used=False),
            'admins': self.count_admins(role='admin'),
            'resellers': self.count_admins(role='reseller'),
        }


db = Database()
