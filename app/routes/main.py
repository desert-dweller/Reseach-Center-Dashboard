# app/routes/main.py
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models import Server, TimeSlot
from datetime import datetime
from sqlalchemy import desc
from app.utils import calculate_user_quota_stats

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # if current_user.is_authenticated:
    #     if current_user.is_admin:
    #         return redirect(url_for('admin.dashboard'))
    #     return redirect(url_for('main.dashboard'))
    return render_template('main/index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # 1. Get Servers assigned to this user
    assigned_servers = current_user.servers.all()
    
    server_stats = {}
    for server in assigned_servers:
        stats = calculate_user_quota_stats(current_user, server)
        server_stats[server.id] = stats

    # 2. Get Upcoming Reservations for this user
    upcoming_reservations = TimeSlot.query.filter(
        TimeSlot.reserved_by_user_id == current_user.id,
        TimeSlot.start_time >= datetime.now() # type: ignore
    ).order_by(TimeSlot.start_time.asc()).all() # type: ignore

    return render_template('main/dashboard.html', 
                          servers=assigned_servers, 
                          stats=server_stats,
                          reservations=upcoming_reservations)

@main_bp.route('/profile')
@login_required
def profile():
    # Reuse the same calculation logic for the profile page
    server_details = []
    for server in current_user.servers:
        stats = calculate_user_quota_stats(current_user, server)
        server_details.append({
            'name': server.name,
            'ip': server.ip_address,
            'stats': stats
        })
        
    return render_template('main/profile.html', server_details=server_details)