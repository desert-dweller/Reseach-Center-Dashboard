from datetime import datetime
from flask_login import UserMixin
from app.extensions import db, login_manager

# --- Association Table ---
# This links Users to Servers with extra data (Quota, Access Date)
user_server = db.Table('user_server',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('server_id', db.Integer, db.ForeignKey('server.id'), primary_key=True),
    db.Column('MAX_QUOTA', db.Integer, default=360),
    db.Column('used_quota', db.Integer, default=0),
    db.Column('Access_StartDate', db.DateTime, default=datetime.now) 
)

# --- Models ---

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    
    # User Details
    ratio = db.Column(db.Float, nullable=True)
    resource_needed = db.Column(db.String(50), nullable=True)
    position = db.Column(db.String(50), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    # 'reservations' backref is defined in TimeSlot below
    
    def __repr__(self):
        return f'<User {self.username}>'


class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100))
    
    # Hardware Specs
    hdd_size = db.Column(db.Integer)
    ssd_size = db.Column(db.Integer)
    ram_size = db.Column(db.Integer)
    vram_size = db.Column(db.Integer)
    cpu_model = db.Column(db.String(100))
    gpu_model = db.Column(db.String(100))
    
    # Relationship to User (Many-to-Many)
    users = db.relationship(
        'User', 
        secondary=user_server, 
        backref=db.backref('servers', lazy='dynamic')
    )

    def __repr__(self):
        return f'<Server {self.name}>'


class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    
    # Link to Server
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    server = db.relationship('Server', backref=db.backref('time_slots', lazy=True, cascade="all, delete"))

    # Link to User (Reservation)
    reserved_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reserved_by_user = db.relationship('User', backref=db.backref('reservations', lazy=True))


# --- User Loader Helper ---
# Flask-Login calls this to get the User object from the session ID
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))