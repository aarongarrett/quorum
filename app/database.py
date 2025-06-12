"""
Database module using Flask-SQLAlchemy.

Usage:
    from .database import db, init_db
    # In your app factory:
    init_db(app)
    # Use db.Model for models
"""

import os

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Initialize the Flask-SQLAlchemy extension with the Flask app."""
    # If the env variable is set, we should use that because the config
    # variable is stale at this point.
    db_uri = os.getenv("DATABASE_URL") or app.config.get("DATABASE_URL")
    app.config["DATABASE_URL"] = db_uri
    if db_uri and db_uri.startswith("postgres://"):
        # Handle Heroku's postgres:// URL format
        app.config["SQLALCHEMY_DATABASE_URI"] = db_uri.replace(
            "postgres://", "postgresql://", 1
        )
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = db_uri

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
