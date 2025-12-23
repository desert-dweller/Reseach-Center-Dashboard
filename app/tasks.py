from datetime import datetime, timedelta, time
from app.extensions import db
from app.models import Server, TimeSlot, user_server

def generate_time_slots(app, server_id, days_ahead=30):
    """
    Generates FULL DAY time slots for a specific server for X days ahead.
    Each slot runs from 00:00:00 to 23:59:59 of that day.
    """
    with app.app_context():
        server = Server.query.get(server_id)
        if not server:
            return

        # Start from today at midnight
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=days_ahead)
        
        # 1. Fetch existing slots to avoid duplicates
        existing_slots = db.session.query(TimeSlot.start_time).filter(
            TimeSlot.server_id == server.id,
            TimeSlot.start_time >= start_date,
            TimeSlot.start_time <= end_date
        ).all()
        
        existing_set = {slot[0] for slot in existing_slots}
        
        new_slots = []
        current_date = start_date
        
        # Loop through days
        while current_date < end_date:
            # We check if a slot starting at 00:00 of this day exists
            if current_date not in existing_set:
                # Create a slot that ends at 23:59:59 of the SAME day
                # We subtract one second from the next day to get 23:59:59
                next_day = current_date + timedelta(days=1)
                slot_end = next_day - timedelta(seconds=1)
                
                new_slot = TimeSlot(
                    start_time=current_date,
                    end_time=slot_end,
                    server_id=server.id
                )
                new_slots.append(new_slot)
            
            current_date += timedelta(days=1)
            
        # 2. Bulk Save
        if new_slots:
            try:
                db.session.add_all(new_slots)
                db.session.commit()
                print(f"Generated {len(new_slots)} daily slots for {server.name}")
            except Exception as e:
                db.session.rollback()
                print(f"Error generating slots: {e}")

def reset_user_quotas(app):
    """
    Resets the 'used_quota' column for all users to 0.
    """
    with app.app_context():
        try:
            stmt = user_server.update().values(used_quota=0)
            db.session.execute(stmt)
            db.session.commit()
            print("All user quotas have been reset.")
        except Exception as e:
            db.session.rollback()
            print(f"Error resetting quotas: {e}")