from datetime import datetime
from flask_login import UserMixin
from app.extensions import db, login_manager

# --- Association Table ---
# This links Users to Servers with extra data
user_server = db.Table(
    "user_server",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("server_id", db.Integer, db.ForeignKey("server.id"), primary_key=True),
    db.Column("MAX_QUOTA", db.Integer, default=360),
    db.Column("used_quota", db.Integer, default=0),
    db.Column("Access_StartDate", db.DateTime, default=datetime.now),
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

    def __init__(
        self,
        username,
        email,
        password,
        position=None,
        resource_needed=None,
        ratio=None,
        is_admin=False,
    ):
        self.username = username
        self.email = email
        self.password = password
        self.position = position
        self.resource_needed = resource_needed
        self.ratio = ratio
        self.is_admin = is_admin

    def __repr__(self):
        return f"<User {self.username}>"


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
        "User", secondary=user_server, backref=db.backref("servers", lazy="dynamic")
    )

    def __init__(
        self,
        name,
        ip_address,
        location,
        hdd_size,
        ssd_size,
        ram_size,
        vram_size,
        cpu_model,
        gpu_model,
    ):
        self.name = name
        self.ip_address = ip_address
        self.location = location
        self.hdd_size = hdd_size
        self.ssd_size = ssd_size
        self.ram_size = ram_size
        self.vram_size = vram_size
        self.cpu_model = cpu_model
        self.gpu_model = gpu_model

    def __repr__(self):
        return f"<Server {self.name}>"


class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)

    # Link to Server
    server_id = db.Column(db.Integer, db.ForeignKey("server.id"), nullable=False)

    # Relationships
    # Note: We don't define 'server' or 'reserved_by_user' in __init__ because they are relationships,
    # but we accept the IDs or objects if needed. Usually, we just pass the IDs.

    server = db.relationship(
        "Server", backref=db.backref("time_slots", lazy=True, cascade="all, delete")
    )

    # Link to User (Reservation)
    reserved_by_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    reserved_by_user = db.relationship(
        "User", backref=db.backref("reservations", lazy=True)
    )

    def __init__(self, start_time, end_time, server_id, reserved_by_user_id=None):
        self.start_time = start_time
        self.end_time = end_time
        self.server_id = server_id
        self.reserved_by_user_id = reserved_by_user_id


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)

    # Who performed the action?
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user = db.relationship("User", backref="logs")

    # What happened?
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.String(255), nullable=True)

    def __init__(self, user_id, action, details):
        # We don't need to set timestamp in __init__ because it has a default=datetime.now
        self.user_id = user_id
        self.action = action
        self.details = details

    def __repr__(self):
        return f"Log('{self.action}', '{self.timestamp}')"


# --- User Loader Helper ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
