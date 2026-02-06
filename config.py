import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'neutron-change-this-secret-key-in-production')
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://Adityashree12:srishtisingh0725@cluster0.82cjuzd.mongodb.net/?appName=Cluster0')  # Set MONGO_URI env var on Render
    DATABASE_NAME = os.environ.get('DATABASE_NAME', 'neutron')
    BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
