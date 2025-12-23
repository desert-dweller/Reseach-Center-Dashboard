from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime
from sqlalchemy import text

from app import db
from app.models import User, Server, user_server, TimeSlot
from app.forms import AddUserForm, EditUserForm, ServerForm

from app.tasks import generate_time_slots
from app.utils import calculate_user_quota_stats, backup_database

from calendar import monthcalendar
from sqlalchemy import extract
from datetime import datetime, timedelta

admin_bp = Blueprint("admin", __name__)


# --- Middleware: Protect all admin routes ---
@admin_bp.before_request
def restrict_to_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash("Access restricted to admins only.", "danger")
        return redirect(url_for("main.index"))


# --- Dashboard ---
@admin_bp.route("/dashboard")
def dashboard():
    users_count = User.query.count()
    servers_count = Server.query.count()
    return render_template(
        "admin/dashboard.html", users_count=users_count, servers_count=servers_count
    )


# --- User Management ---


@admin_bp.route("/users")
def list_users():
    users = User.query.all()
    return render_template("admin/list_users.html", users=users)


@admin_bp.route("/users/add", methods=["GET", "POST"])
def add_user():
    form = AddUserForm()
    if form.validate_on_submit():

        # 1. Determine if this user is an Admin based on the dropdown
        is_admin_role = form.position.data == "Admin"

        # 2. Set Ratio map
        ratio_map = {"Professor": 2.0, "RA": 1.5, "TA": 1.0, "PG": 0.5, "UG": 0.25}

        # If Admin, ratio is 0 (unlimited). Otherwise, lookup the position.
        user_ratio = 0.0 if is_admin_role else ratio_map.get(form.position.data, 0.5)

        new_user = User(
            username=form.username.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data),
            position=form.position.data,
            resource_needed=form.resource_needed.data,
            ratio=user_ratio,
            is_admin=is_admin_role,  # <--- Set the DB flag based on dropdown
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            flash(
                f"User {new_user.username} created successfully as {form.position.data}.",
                "success",
            )
            return redirect(url_for("admin.list_users"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", "danger")

    return render_template("admin/add_user.html", form=form)


@admin_bp.route("/users/delete/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    # Safety Check: Prevent suicide (deleting your own account while logged in)
    if user.id == current_user.id:
        flash("You cannot delete your own account while logged in.", "danger")
    else:
        try:
            # Check if we are deleting an admin (optional warning in logs)
            if user.is_admin:
                print(
                    f"Warning: Admin user {user.username} is being deleted by {current_user.username}"
                )

            db.session.delete(user)
            db.session.commit()
            flash(f"User {user.username} has been permanently deleted.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting user: {str(e)}", "danger")

    return redirect(url_for("admin.list_users"))


# --- Edit User Route ---
@admin_bp.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    # Initialize form with the original username/email so validation doesn't fail on itself
    form = EditUserForm(original_username=user.username, original_email=user.email)

    if form.validate_on_submit():
        # 1. Update Basic Info
        user.username = form.username.data
        user.email = form.email.data
        user.position = form.position.data
        user.resource_needed = form.resource_needed.data

        # 2. Update Admin Status & Ratio
        is_admin_role = form.position.data == "Admin"
        user.is_admin = is_admin_role

        ratio_map = {"Professor": 2.0, "RA": 1.5, "TA": 1.0, "PG": 0.5, "UG": 0.25}
        user.ratio = 0.0 if is_admin_role else ratio_map.get(form.position.data, 0.5)

        # 3. Update Password (ONLY if the field was filled out)
        if form.password.data:
            user.password = generate_password_hash(form.password.data)
            flash(f"Password for {user.username} has been reset.", "info")

        try:
            db.session.commit()
            flash(f"User {user.username} updated successfully.", "success")
            return redirect(url_for("admin.list_users"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating user: {e}", "danger")

    # Pre-fill the form with existing data (GET request)
    elif request.method == "GET":
        form.username.data = user.username
        form.email.data = user.email
        # Handle the special "Admin" dropdown case
        form.position.data = "Admin" if user.is_admin else user.position
        form.resource_needed.data = user.resource_needed

    return render_template("admin/edit_user.html", form=form, user=user)


# --- Edit Server Route ---
@admin_bp.route("/servers/edit/<int:server_id>", methods=["GET", "POST"])
def edit_server(server_id):
    server = Server.query.get_or_404(server_id)
    form = ServerForm()

    if form.validate_on_submit():
        server.name = form.name.data
        server.ip_address = form.ip_address.data
        server.location = form.location.data
        server.hdd_size = form.hdd_size.data
        server.ssd_size = form.ssd_size.data
        server.ram_size = form.ram_size.data
        server.vram_size = form.vram_size.data
        server.cpu_model = form.cpu_model.data
        server.gpu_model = form.gpu_model.data

        try:
            db.session.commit()
            flash(f"Server {server.name} updated.", "success")
            return redirect(url_for("admin.list_servers"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating server: {e}", "danger")

    # Pre-fill (GET request)
    elif request.method == "GET":
        form.name.data = server.name
        form.ip_address.data = server.ip_address
        form.location.data = server.location
        form.hdd_size.data = server.hdd_size
        form.ssd_size.data = server.ssd_size
        form.ram_size.data = server.ram_size
        form.vram_size.data = server.vram_size
        form.cpu_model.data = server.cpu_model
        form.gpu_model.data = server.gpu_model

    return render_template("admin/edit_server.html", form=form, server=server)


# --- Server Management ---


@admin_bp.route("/servers")
def list_servers():
    servers = Server.query.all()
    return render_template("admin/list_servers.html", servers=servers)


@admin_bp.route("/servers/create", methods=["GET", "POST"])
def create_server():
    form = ServerForm()
    if form.validate_on_submit():
        new_server = Server(
            name=form.name.data,
            ip_address=form.ip_address.data,
            location=form.location.data,
            hdd_size=form.hdd_size.data,
            ssd_size=form.ssd_size.data,
            ram_size=form.ram_size.data,
            vram_size=form.vram_size.data,
            cpu_model=form.cpu_model.data,
            gpu_model=form.gpu_model.data,
        )

        db.session.add(new_server)
        db.session.commit()

        # Trigger Task: Generate slots immediately for this new server
        # (Pass 'current_app._get_current_object()' if using threaded tasks,
        # but for simple setup, just calling the function works)
        from flask import current_app

        generate_time_slots(current_app, new_server.id, days_ahead=30)

        flash(f"Server {new_server.name} initialized with time slots.", "success")
        return redirect(url_for("admin.list_servers"))

    return render_template("admin/create_server.html", form=form)


@admin_bp.route("/servers/delete/<int:server_id>", methods=["POST"])
def delete_server(server_id):
    server = Server.query.get_or_404(server_id)
    db.session.delete(server)  # Cascade will handle TimeSlots
    db.session.commit()
    flash(f"Server {server.name} deleted.", "success")
    return redirect(url_for("admin.list_servers"))


@admin_bp.route("/servers/<int:server_id>/assign", methods=["GET", "POST"])
def assign_users(server_id):
    server = Server.query.get_or_404(server_id)

    # Get users NOT already assigned to this server
    # We do this by checking if they are NOT in the server.users list
    available_users = [
        u for u in User.query.all() if u not in server.users and not u.is_admin
    ]

    if request.method == "POST":
        user_id = request.form.get("user_id")
        user = User.query.get(user_id)

        if user:
            # We use a raw SQL insert for the association table to include the extra data
            stmt = user_server.insert().values(
                user_id=user.id,
                server_id=server.id,
                Access_StartDate=datetime.now(),
                MAX_QUOTA=0,  # Will be calculated dynamically
                used_quota=0,
            )
            db.session.execute(stmt)
            db.session.commit()
            flash(f"User {user.username} assigned to {server.name}", "success")
        else:
            flash("User not found.", "danger")

        return redirect(url_for("admin.assign_users", server_id=server.id))

    # Show currently assigned users and their stats
    assigned_data = []
    for user in server.users:
        stats = calculate_user_quota_stats(user, server)
        assigned_data.append({"user": user, "stats": stats})

    return render_template(
        "admin/assign_users.html",
        server=server,
        available_users=available_users,
        assigned_data=assigned_data,
    )


@admin_bp.route("/servers/<int:server_id>/unassign/<int:user_id>", methods=["POST"])
def unassign_user(server_id, user_id):
    server = Server.query.get_or_404(server_id)
    user = User.query.get_or_404(user_id)

    if user in server.users:
        server.users.remove(user)
        db.session.commit()
        flash(f"Removed {user.username} from {server.name}", "warning")

    return redirect(url_for("admin.assign_users", server_id=server.id))


# --- Master Reservation List ---
# app/routes/admin.py

from calendar import monthcalendar
from sqlalchemy import extract
from datetime import datetime, timedelta


@admin_bp.route("/reservations", defaults={"year": None, "month": None})
@admin_bp.route("/reservations/<int:year>/<int:month>")
@login_required
def list_reservations(year, month):
    # Default to current month if no date provided
    now = datetime.now()
    if year is None or month is None:
        year = now.year
        month = now.month

    # Navigation Logic
    current_date = datetime(year, month, 1)
    prev_date = current_date - timedelta(days=1)
    next_date = current_date + timedelta(days=32)

    # Fetch ALL reserved slots for this specific month
    # We join with Server and User to make accessing their names easy
    slots = (
        TimeSlot.query.filter(
            extract("year", TimeSlot.start_time) == year,
            extract("month", TimeSlot.start_time) == month,
            TimeSlot.reserved_by_user_id.isnot(None),  # Only get booked slots
        )
        .join(Server)
        .join(User)
        .order_by(TimeSlot.start_time.asc())
        .all()
    )

    # Group slots by Day Number for the calendar template
    # Format: { 24: [SlotA, SlotB], 25: [SlotC] }
    reservations_by_day = {}
    for slot in slots:
        day = slot.start_time.day
        if day not in reservations_by_day:
            reservations_by_day[day] = []
        reservations_by_day[day].append(slot)

    # Get the matrix of weeks [ [0,0,1,2...], [3,4,5...] ]
    month_days = monthcalendar(year, month)

    return render_template(
        "admin/reservations.html",
        reservations_by_day=reservations_by_day,
        month_days=month_days,
        year=year,
        month=month,
        current_month_name=current_date.strftime("%B"),
        prev_month=prev_date.month,
        prev_year=prev_date.year,
        next_month=next_date.month,
        next_year=next_date.year,
    )


# --- Force Cancel Route ---
@admin_bp.route("/reservations/cancel/<int:slot_id>", methods=["POST"])
def force_cancel_reservation(slot_id):
    slot = TimeSlot.query.get_or_404(slot_id)

    if slot.reserved_by_user:
        user_name = slot.reserved_by_user.username
        date_str = slot.start_time.strftime("%Y-%m-%d")

        # Admin Override: Remove the user
        slot.reserved_by_user_id = None
        db.session.commit()

        flash(
            f"ADMIN OVERRIDE: Reservation for {user_name} on {date_str} has been cancelled.",
            "warning",
        )

    return redirect(url_for("admin.list_reservations"))


@admin_bp.route("/backup", methods=["POST"])
def create_backup():
    filename, error = backup_database()

    if filename:
        flash(f"Success! Database backed up to 'backups/{filename}'", "success")
    else:
        flash(f"Backup Failed: {error}", "danger")

    return redirect(url_for("admin.dashboard"))
