from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

def create_admin_user():
    # Initialize the Flask application context
    app = create_app()
    
    with app.app_context():
        # Configuration
        ADMIN_USER = 'admin'
        ADMIN_PASS = 'bananaman35'
        ADMIN_EMAIL = 'admin@system.local'  # Email is required by your model

        # Check if admin already exists to prevent duplicates
        existing_user = User.query.filter_by(username=ADMIN_USER).first()
        
        if existing_user:
            print(f"User '{ADMIN_USER}' already exists.")
            # Optional: Update password if it exists
            existing_user.password = generate_password_hash(ADMIN_PASS)
            existing_user.is_admin = True
            db.session.commit()
            print(f"Updated password and permissions for '{ADMIN_USER}'.")
            
        else:
            # Create new admin user
            new_admin = User(
                username=ADMIN_USER,
                email=ADMIN_EMAIL,
                password=generate_password_hash(ADMIN_PASS),
                is_admin=True,
                ratio=0.0,  # Admins don't usually need quota limits
                position='System Admin',
                resource_needed='All'
            )
            
            db.session.add(new_admin)
            db.session.commit()
            print(f"Successfully created admin user: {ADMIN_USER}")

if __name__ == "__main__":
    create_admin_user()