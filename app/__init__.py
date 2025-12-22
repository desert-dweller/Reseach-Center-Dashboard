from flask import Flask
from config import config
from app.extensions import db, login_manager, migrate, scheduler

def create_app(config_name='default'):
    """
    Application Factory: Creates and configures the Flask app.
    """
    app = Flask(__name__)
    
    # 1. Load Configuration
    app.config.from_object(config[config_name])

    # 2. Initialize Extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize Scheduler (Modern Flask-APScheduler pattern)
    scheduler.init_app(app)
    scheduler.start()

    # 3. Register Blueprints (Routes)
    # We import these inside the function to avoid circular imports
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.reservations import reservations_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')   # e.g., /auth/login
    app.register_blueprint(admin_bp, url_prefix='/admin') # e.g., /admin/dashboard
    app.register_blueprint(reservations_bp)               # e.g., /daily_slots/

    # 4. Import Models
    # This ensures SQLAlchemy "knows" about your tables before migration runs
    from app import models

    return app