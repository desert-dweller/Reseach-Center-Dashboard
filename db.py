from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

# 1. Create the app instance
app = create_app()

# 2. Create the database tables
with app.app_context():
    db.create_all()
    
    # 3. Create a test user (if one doesn't exist)
    if not User.query.filter_by(username='testuser').first():
        user = User(
            username='testuser', 
            email='test@example.com', 
            password=generate_password_hash('password123'),
            is_admin=False,
            ratio=1.0
        )
        db.session.add(user)
        db.session.commit()
        print("User 'testuser' created!")
    else:
        print("User already exists.")