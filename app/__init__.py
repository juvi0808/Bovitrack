from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os  # <-- Import the 'os' module

# This is the heart of our application.
db = SQLAlchemy()

def create_app():
    """Application factory function."""
    app = Flask(__name__, instance_relative_config=False)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # --- START OF THE FIX ---
    # Determine the correct, writable path for the database.
    
    # Get the standard folder for user-specific application data.
    # On Windows, this is typically C:\Users\YourUsername\AppData\Roaming
    app_data_path = os.environ.get('APPDATA') or os.path.expanduser("~")

    # For other OS's or if APPDATA is not set, use the user's home directory.
    if app_data_path:
        # Create a specific folder for our app's data within AppData
        bovitrack_data_folder = os.path.join(app_data_path, 'BoviTrack')
    else: # Fallback for other systems
        bovitrack_data_folder = os.path.join(os.path.expanduser("~"), '.BoviTrack')

    # Safely create this folder if it doesn't already exist
    os.makedirs(bovitrack_data_folder, exist_ok=True)

    # Define the full path to our database file
    db_path = os.path.join(bovitrack_data_folder, 'database.db')
    # --- END OF THE FIX ---

    app.config.from_mapping(
        SECRET_KEY='dev',
        # Set the database URI to the new, correct path
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{db_path}', # <-- USE THE NEW PATH
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )

    # Initialize extensions with the app
    db.init_app(app)

    with app.app_context():
        # Import and register the Blueprint
        from .routes import api
        app.register_blueprint(api, url_prefix='/api')

        # Create database tables for our models
        db.create_all()

        return app