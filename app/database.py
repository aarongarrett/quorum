"""
Database module using Flask-SQLAlchemy.

Usage:
    from .database import db, init_db
    # In your app factory:
    init_db(app)
    # Use db.Model for models
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Initialize the Flask-SQLAlchemy extension with the Flask app."""
    db_uri = app.config.get("DATABASE_URL")
    if db_uri and db_uri.startswith("postgres://"):
        # Handle Heroku's postgres:// URL format
        app.config["SQLALCHEMY_DATABASE_URI"] = db_uri.replace(
            "postgres://", "postgresql://", 1
        )
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = db_uri or "sqlite:///quorum.db"

    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": {"check_same_thread": False}
        }

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
