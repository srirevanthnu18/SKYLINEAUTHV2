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
        self.db.app_users.create_index('key', unique=True)

    # ── Admin / Reseller account management ──────────────────────────

    def create_admin(self, username, password, email, role, created_by=None):
        if self.db.admins.find_one({'username': username}):
            return None
        doc = {
            'username': username,
            'password': generate_password_hash(password),
            'email': email,
            'role': role,
            'credits': 0,
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
        if 'username' in data and data['username']:
            # Check if username already exists for another user
            existing = self.db.admins.find_one({'username': data['username']})
            if existing and str(existing['_id']) != admin_id:
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
        if update:
            self.db.admins.update_one({'_id': ObjectId(admin_id)}, {'$set': update})
        return True, None

    def update_login_ip(self, admin_id, ip_address):
        """Update last login IP and time for an admin."""
        self.db.admins.update_one(
            {'_id': ObjectId(admin_id)},
            {'$set': {
                'last_login_ip': ip_address,
                'last_login_at': datetime.utcnow()
            }}
        )

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

    # ── Credit system ───────────────────────────────────────────────

    def get_credits(self, admin_id):
        admin = self.get_admin_by_id(admin_id)
        if not admin:
            return 0
        if admin['role'] == 'superadmin':
            return float('inf')
        return admin.get('credits', 0)

    def add_credits(self, admin_id, amount):
        self.db.admins.update_one(
            {'_id': ObjectId(admin_id)},
            {'$inc': {'credits': int(amount)}}
        )

    def deduct_credits(self, admin_id, amount=1):
        admin = self.get_admin_by_id(admin_id)
        if not admin:
            return False
        if admin['role'] == 'superadmin':
            return True
        current = admin.get('credits', 0)
        if current < amount:
            return False
        self.db.admins.update_one(
            {'_id': ObjectId(admin_id)},
            {'$inc': {'credits': -int(amount)}}
        )
        return True

    def transfer_credits(self, from_id, to_id, amount):
        """Transfer credits from one admin to another. Super admin has unlimited."""
        amount = int(amount)
        if amount <= 0:
            return False, 'Amount must be positive'
        from_admin = self.get_admin_by_id(from_id)
        if not from_admin:
            return False, 'Source not found'
        # Super admin doesn't lose credits
        if from_admin['role'] != 'superadmin':
            if from_admin.get('credits', 0) < amount:
                return False, 'Not enough credits'
            self.db.admins.update_one(
                {'_id': ObjectId(from_id)},
                {'$inc': {'credits': -amount}}
            )
        self.db.admins.update_one(
            {'_id': ObjectId(to_id)},
            {'$inc': {'credits': amount}}
        )
        return True, None

    # ── App Users (end-users) management ─────────────────────────────

    def create_user_direct(self, app_id, package_id, created_by, count=1, custom_days=None, hwid_lock=True, username=None, password=None):
        """Create user(s) directly with auto-generated or custom key + password.
        Costs 1 credit per user. Returns list of (key, password) tuples."""
        admin = self.get_admin_by_id(created_by)
        if not admin:
            return None, 'Invalid admin'

        count = int(count)

        # If custom username provided, force count to 1
        if username:
            count = 1

        # Check credits (superadmin = unlimited)
        if admin['role'] != 'superadmin':
            current_credits = admin.get('credits', 0)
            if current_credits < count:
                return None, f'Not enough credits. You have {current_credits}, need {count}'

        # Get package for expiry
        pkg = self.get_package_by_id(package_id)
        if not pkg:
            return None, 'Invalid package'

        if custom_days:
            expiry = datetime.utcnow() + timedelta(days=int(custom_days))
        else:
            expiry = datetime.utcnow() + timedelta(days=pkg['duration_days'])

        created_users = []
        for i in range(count):
            # Use custom username/password if provided (only for first user)
            if username and i == 0:
                key = username.strip()
                raw_password = password.strip() if password else secrets.token_urlsafe(8)
            else:
                key = f"NEUTRON-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
                raw_password = secrets.token_urlsafe(8)

            # Check if key already exists
            if self.db.app_users.find_one({'key': key}):
                return None, f'Username/Key "{key}" already exists'

            doc = {
                'app_id': ObjectId(app_id),
                'key': key,
                'password': generate_password_hash(raw_password),
                'hwid': '',
                'hwid_lock': hwid_lock,
                'expiry': expiry,
                'package_id': ObjectId(package_id),
                'created_by': ObjectId(created_by),
                'created_at': datetime.utcnow(),
                'is_active': True,
            }
            self.db.app_users.insert_one(doc)
            created_users.append({'key': key, 'password': raw_password})

        # Deduct credits
        if admin['role'] != 'superadmin':
            self.db.admins.update_one(
                {'_id': ObjectId(created_by)},
                {'$inc': {'credits': -count}}
            )

        return created_users, None

    def get_app_users(self, app_id=None, created_by=None):
        query = {}
        if app_id:
            query['app_id'] = ObjectId(app_id)
        if created_by:
            query['created_by'] = ObjectId(created_by)
        return list(self.db.app_users.find(query).sort('created_at', -1))

    def delete_app_user(self, user_id):
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


    # ── API auth (for external app integration) ──────────────────────

    def api_login(self, app_secret, key, password, hwid=''):
        """End-user login with key + password from their cheat/panel."""
        app = self.db.apps.find_one({'secret_key': app_secret, 'is_active': True})
        if not app:
            return None, 'Invalid application'

        user = self.db.app_users.find_one({
            'app_id': app['_id'],
            'key': key,
            'is_active': True,
        })
        if not user or not check_password_hash(user['password'], password):
            return None, 'Invalid credentials'

        if user.get('expiry') and user['expiry'] < datetime.utcnow():
            return None, 'Subscription expired'

        # Only check/set HWID if hwid_lock is enabled for this key
        if user.get('hwid_lock', True):
            if user.get('hwid') and user['hwid'] != hwid and hwid:
                return None, 'HWID mismatch'
            if not user.get('hwid') and hwid:
                self.db.app_users.update_one({'_id': user['_id']}, {'$set': {'hwid': hwid}})

        return user, None

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

    # ── Reseller package assignment ──────────────────────────────────

    def assign_package_to_reseller(self, reseller_id, package_id):
        self.db.admins.update_one(
            {'_id': ObjectId(reseller_id)},
            {'$addToSet': {'assigned_packages': ObjectId(package_id)}}
        )

    def remove_package_from_reseller(self, reseller_id, package_id):
        self.db.admins.update_one(
            {'_id': ObjectId(reseller_id)},
            {'$pull': {'assigned_packages': ObjectId(package_id)}}
        )

    def get_reseller_packages(self, reseller_id):
        reseller = self.get_admin_by_id(reseller_id)
        if not reseller or not reseller.get('assigned_packages'):
            return []
        return list(self.db.packages.find(
            {'_id': {'$in': reseller['assigned_packages']}}
        ))

    # ── Key operations (for resellers) ────────────────────────────────

    def reset_hwid(self, user_id):
        self.db.app_users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'hwid': ''}}
        )

    def extend_license(self, user_id, days):
        user = self.db.app_users.find_one({'_id': ObjectId(user_id)})
        if user:
            current_expiry = user.get('expiry') or datetime.utcnow()
            if current_expiry < datetime.utcnow():
                current_expiry = datetime.utcnow()
            new_expiry = current_expiry + timedelta(days=int(days))
            self.db.app_users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'expiry': new_expiry}}
            )

    def ban_license(self, user_id):
        self.db.app_users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'is_active': False}}
        )

    def unban_license(self, user_id):
        self.db.app_users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'is_active': True}}
        )

    def get_app_user_by_id(self, user_id):
        return self.db.app_users.find_one({'_id': ObjectId(user_id)})

    def get_license_by_id(self, license_id):
        return self.db.licenses.find_one({'_id': ObjectId(license_id)})

    # ── Dashboard stats ──────────────────────────────────────────────

    def get_stats(self, admin=None):
        if admin and admin['role'] == 'reseller':
            admin_id = str(admin['_id'])
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
