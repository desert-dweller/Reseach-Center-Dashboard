from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_apscheduler import APScheduler

# Initialize extensions (unbound)
db = SQLAlchemy()
migrate = Migrate()
scheduler = APScheduler()

# Setup Login Manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # type: ignore
login_manager.login_message_category = 'info'