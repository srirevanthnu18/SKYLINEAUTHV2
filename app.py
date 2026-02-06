from flask import Flask
from config import Config
from models import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.apps import apps_bp
    from routes.users import users_bp
    from routes.resellers import resellers_bp
    from routes.packages import packages_bp
    from routes.profile import profile_bp
    from routes.admins import admins_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(apps_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(resellers_bp)
    app.register_blueprint(packages_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(admins_bp)
    app.register_blueprint(api_bp)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
