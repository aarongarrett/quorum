from flask import Flask
from flask_migrate import Migrate

from .blueprints.admin.routes import admin_bp
from .blueprints.api.routes import api_bp
from .blueprints.public.routes import public_bp
from .config import config as app_config
from .database import configure_database
from .models import Base
from .utils import strftime


def create_app(config_name: str = "default") -> Flask:
    app = Flask(__name__, instance_relative_config=False)

    # Load our configuration
    app.config.from_object(app_config[config_name])

    # Wire up the database (sets up engine & SessionLocal)
    configure_database(app.config["DATABASE_URL"])

    from .database import engine

    Migrate(app, engine, metadata=Base.metadata, directory="migrations")

    app.add_template_filter(strftime, name="strftime")

    # Register blueprints
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(public_bp)  # home, checkin, vote, etc.

    if app.config.get("TESTING", False):
        from .blueprints.test_helpers import test_bp

        app.register_blueprint(test_bp)

    return app
