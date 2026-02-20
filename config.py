import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DATABASE_NAME = os.environ.get('DATABASE_NAME', 'neutron')
    MONGO_URI = os.environ.get('MONGO_URI')
    DB_DRIVER = os.environ.get('DB_DRIVER', 'mongo')
    BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB max file size
