from flask import Flask
from flask_migrate import Migrate, upgrade
from sqlalchemy import inspect

from .blueprints.admin.routes import admin_bp
from .blueprints.api.routes import api_bp
from .blueprints.public.routes import public_bp
from .config import config as app_config
from .database import db, init_db
from .utils import strftime


def create_app(config_name: str = "default") -> Flask:
    app = Flask(__name__, instance_relative_config=False)

    # Load our configuration
    app.config.from_object(app_config[config_name])

    # Initialize Flask-SQLAlchemy
    init_db(app)

    # Set up Flask-Migrate with Flask-SQLAlchemy db
    Migrate(app, db, directory="migrations")

    # Optional one-time schema bootstrap if DB is empty
    if not app.config.get("TESTING", False):
        with app.app_context():
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            if not tables:
                app.logger.info("No tables found — running flask db upgrade()")
                upgrade()

    app.add_template_filter(strftime, name="strftime")

    # Register blueprints
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(public_bp)  # home, checkin, vote, etc.

    if app.config.get("TESTING", False):
        from .blueprints.test_helpers import test_bp

        app.register_blueprint(test_bp)

    return app
