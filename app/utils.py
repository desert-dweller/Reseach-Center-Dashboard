from app.models import TimeSlot

def calculate_user_quota_stats(user, server):
    """
    Calculates the user's allowed vs used quota for a specific server.
    Returns a dictionary for easy use in templates.
    """
    total_slots_pool = 360  # Default monthly pool
    
    # 1. Calculate Total Ratio of all users on this server
    # (Avoid division by zero)
    total_ratio = sum([u.ratio for u in server.users if u.ratio is not None]) or 1
    
    # 2. Calculate User's Allowance
    user_ratio = user.ratio or 0
    max_quota = int((user_ratio / total_ratio) * total_slots_pool)
    
    # 3. Calculate Usage (Count reserved slots)
    used_quota = TimeSlot.query.filter_by(
        server_id=server.id, 
        reserved_by_user_id=user.id
    ).count()
    
    # 4. Calculate Percentage (for progress bars)
    usage_percent = 0
    if max_quota > 0:
        usage_percent = (used_quota / max_quota) * 100
        
    return {
        'max': max_quota,
        'used': used_quota,
        'remaining': max_quota - used_quota,
        'percent': round(usage_percent, 1),
        'status': 'danger' if usage_percent > 90 else 'success'
    }