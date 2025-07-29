from flask import Flask
from flask_sqlalchemy import SQLAlchemy

#This is the new heart of our application. It creates and configures the Flask app.
db = SQLAlchemy()

def create_app():
    """Application factory function."""
    # Create the Flask app instance
    app = Flask(__name__, instance_relative_config=False)

    #
    app.config.from_mapping(
        # Set a default secret key, change this in a real app
        SECRET_KEY='dev',
        # Set the database path, SQLite will create it in the instance folder
        SQLALCHEMY_DATABASE_URI='sqlite:///database.db',
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )

    # Initialize extensions with the app
    db.init_app(app)


    with app.app_context():
        # Import the Blueprint from our routes file
        from .routes import api
        # Register the Blueprint with the app
        app.register_blueprint(api, url_prefix='/api') # All routes in the blueprint will be prefixed with /api
        # Import parts of our application
        from . import routes  # Import our routes

        # Create database tables for our models
        db.create_all()

        return app