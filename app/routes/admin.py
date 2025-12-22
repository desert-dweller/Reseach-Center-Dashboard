from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app import db
from app.models import User, Server, user_server
from app.forms import AddUserForm, EditUserForm, ServerForm
from app.tasks import generate_time_slots # We will use this when creating a server

admin_bp = Blueprint('admin', __name__)

# --- Middleware: Protect all admin routes ---
@admin_bp.before_request
def restrict_to_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash("Access restricted to admins only.", 'danger')
        return redirect(url_for('main.index'))

# --- Dashboard ---
@admin_bp.route('/dashboard')
def dashboard():
    users_count = User.query.count()
    servers_count = Server.query.count()
    return render_template('admin/dashboard.html', 
                         users_count=users_count, 
                         servers_count=servers_count)

# --- User Management ---

@admin_bp.route('/users')
def list_users():
    users = User.query.all()
    return render_template('admin/list_users.html', users=users)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
def add_user():
    form = AddUserForm()
    if form.validate_on_submit():
        # Map Position to Ratio automatically
        ratio_map = {'RA': 1.5, 'TA': 1.0, 'PG': 0.5}
        
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data),
            position=form.position.data,
            resource_needed=form.resource_needed.data,
            ratio=ratio_map.get(form.position.data, 0.5),
            is_admin=False
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash(f"User {new_user.username} created successfully.", 'success')
            return redirect(url_for('admin.list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", 'danger')

    return render_template('admin/add_user.html', form=form)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash("Cannot delete admin accounts.", 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f"User {user.username} deleted.", 'success')
    return redirect(url_for('admin.list_users'))

# --- Server Management ---

@admin_bp.route('/servers')
def list_servers():
    servers = Server.query.all()
    return render_template('admin/list_servers.html', servers=servers)

@admin_bp.route('/servers/create', methods=['GET', 'POST'])
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
            gpu_model=form.gpu_model.data
        )
        
        db.session.add(new_server)
        db.session.commit()
        
        # Trigger Task: Generate slots immediately for this new server
        # (Pass 'current_app._get_current_object()' if using threaded tasks, 
        # but for simple setup, just calling the function works)
        from flask import current_app
        generate_time_slots(current_app, new_server.id, days_ahead=30)
        
        flash(f"Server {new_server.name} initialized with time slots.", 'success')
        return redirect(url_for('admin.list_servers'))

    return render_template('admin/create_server.html', form=form)

@admin_bp.route('/servers/delete/<int:server_id>', methods=['POST'])
def delete_server(server_id):
    server = Server.query.get_or_404(server_id)
    db.session.delete(server) # Cascade will handle TimeSlots
    db.session.commit()
    flash(f"Server {server.name} deleted.", 'success')
    return redirect(url_for('admin.list_servers'))