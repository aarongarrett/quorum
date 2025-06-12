import os
from typing import Optional

from flask import Flask
from flask_migrate import Migrate

from .blueprints.admin.routes import admin_bp
from .blueprints.api.routes import api_bp
from .blueprints.public.routes import public_bp
from .database import db, init_db
from .utils import strftime


def create_app(config_name: Optional[str] = None) -> Flask:
    if config_name is None:
        config_name = os.getenv("FLASK_CONFIG", os.getenv("FLASK_ENV", "default"))

    app = Flask(__name__, instance_relative_config=False)

    # Import config here so it sees any loaded env vars
    from .config import config as app_config

    # Load our configuration
    app.config.from_object(app_config[config_name])

    # Initialize Flask-SQLAlchemy
    init_db(app)

    # Set up Flask-Migrate with Flask-SQLAlchemy db
    Migrate(app, db, directory="migrations")

    app.add_template_filter(strftime, name="strftime")

    # Register blueprints
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(public_bp)

    if app.config.get("TESTING", False):
        from .blueprints.test_helpers import test_bp

        app.register_blueprint(test_bp)

    return app
