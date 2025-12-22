from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Server, TimeSlot
# We will create utils.py next, but we reference it here
from app.utils import calculate_user_quota_stats

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('main.dashboard'))
    return render_template('main/index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Only show servers assigned to this user
    assigned_servers = current_user.servers.all()
    
    server_stats = {}
    
    for server in assigned_servers:
        # Calculate usage stats for the progress bars
        stats = calculate_user_quota_stats(current_user, server)
        server_stats[server.id] = stats

    return render_template('main/dashboard.html', 
                         servers=assigned_servers, 
                         stats=server_stats)

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