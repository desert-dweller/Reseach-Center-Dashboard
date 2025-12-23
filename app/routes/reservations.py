from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date
from sqlalchemy import extract
from app import db
from app.models import Server, TimeSlot
from app.utils import calculate_user_quota_stats, log_action
from calendar import monthcalendar

reservations_bp = Blueprint("reservations", __name__)
MONTHLY_LIMIT = 8


@reservations_bp.route("/reserve", methods=["GET"])
@login_required
def list_servers():
    """
    Step 1: User selects which server they want to book.
    """
    # Only show servers assigned to this user
    servers = current_user.servers.all()
    return render_template("reservations/select_server.html", servers=servers)


@reservations_bp.route("/reserve/<int:server_id>", methods=["GET"])
@login_required
def calendar(server_id):
    server = Server.query.get_or_404(server_id)

    if server not in current_user.servers:
        flash("You do not have access to this server.", "danger")
        return redirect(url_for("main.dashboard"))

    today = datetime.now()
    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)

    # Navigation logic
    current_date = datetime(year, month, 1)
    prev_date = current_date - timedelta(days=1)
    # Getting next month is tricky, easiest way is adding 32 days to the 1st
    next_date = current_date + timedelta(days=32)

    # Fetch slots
    slots = TimeSlot.query.filter(
        TimeSlot.server_id == server.id,  # type: ignore
        extract("year", TimeSlot.start_time) == year,  # type: ignore
        extract("month", TimeSlot.start_time) == month,  # type: ignore
    ).all()

    # Create dictionary for lookup
    days_data = {slot.start_time.day: slot for slot in slots}

    # NEW: Get the matrix of weeks [ [0,0,1,2,3,4,5], [6,7,8...] ]
    # 0 represents days from the previous/next month
    month_days = monthcalendar(year, month)

    return render_template(
        "reservations/calendar.html",
        server=server,
        days_data=days_data,
        month_days=month_days,  # <--- Passing this new data
        year=year,
        month=month,
        current_month_name=current_date.strftime("%B"),
        prev_month=prev_date.month,
        prev_year=prev_date.year,
        next_month=next_date.month,
        next_year=next_date.year,
    )


@reservations_bp.route("/reserve/book/<int:slot_id>", methods=["POST"])
@login_required
def book_slot(slot_id):
    slot = TimeSlot.query.get_or_404(slot_id)
    target_date = slot.start_time

    slot = TimeSlot.query.get_or_404(slot_id)
    target_date = slot.start_time

    # 1. Check Access
    if slot.server not in current_user.servers:
        flash("Access Denied.", "danger")
        return redirect(url_for("main.dashboard"))

    # 2. Check if already taken (and handle cancellation)
    if slot.reserved_by_user_id:
        if slot.reserved_by_user_id == current_user.id:

            # --- NEW PROTECTION: Prevent cancelling past/current reservations ---
            # We compare the slot's date to today's date.
            # We assume you cannot cancel "Today" because the resource is already "used" for the day.
            today = datetime.now().date()
            slot_date = slot.start_time.date()

            if slot_date < today:
                flash(
                    "You cannot cancel a reservation that has already passed.", "danger"
                )
            elif slot_date == today:
                flash("You cannot cancel a reservation for the current day.", "warning")
            else:
                # Only allow if the date is strictly in the future (Tomorrow onwards)
                slot.reserved_by_user_id = None
                log_action(
                    current_user.id,
                    "CANCEL_SLOT",
                    f"Cancelled reservation for {slot.server.name} on {target_date.strftime('%Y-%m-%d')}",
                )
                db.session.commit()
                flash("Reservation Cancelled. Quota restored.", "info")

            # --- END PROTECTION ---

        else:
            flash("This day is already reserved.", "danger")

        return redirect(
            url_for(
                "reservations.calendar",
                server_id=slot.server_id,
                year=target_date.year,
                month=target_date.month,
            )
        )

    # 3. Monthly Limit Check (Hard limit: 8 days per month)
    monthly_count = TimeSlot.query.filter(
        TimeSlot.server_id == slot.server_id,  # type: ignore
        TimeSlot.reserved_by_user_id == current_user.id,
        extract("year", TimeSlot.start_time) == target_date.year,  # type: ignore
        extract("month", TimeSlot.start_time) == target_date.month,  # type: ignore
    ).count()

    if monthly_count >= MONTHLY_LIMIT:
        flash(
            f"Monthly Quota Reached: You cannot book more than {MONTHLY_LIMIT} days per month. (Used: {monthly_count}/8)",
            "danger",
        )
        return redirect(
            url_for(
                "reservations.calendar",
                server_id=slot.server_id,
                year=target_date.year,
                month=target_date.month,
            )
        )

    # 4. Weekly Limit Check (Hard limit: 2 days per week, starting Sunday)
    # Algorithm: Find the Sunday that started this week
    # Python weekday(): Mon=0 ... Sun=6
    # If today is Sun(6), subtract 0. If Mon(0), subtract 1.
    days_to_subtract = (target_date.weekday() + 1) % 7
    start_of_week = target_date - timedelta(days=days_to_subtract)
    end_of_week = start_of_week + timedelta(days=6)

    # Ensure we look at the whole day boundaries
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0)
    end_of_week = end_of_week.replace(hour=23, minute=59, second=59)

    weekly_count = TimeSlot.query.filter(
        TimeSlot.server_id == slot.server_id,  # type: ignore
        TimeSlot.reserved_by_user_id == current_user.id,
        TimeSlot.start_time >= start_of_week,  # type: ignore
        TimeSlot.start_time <= end_of_week,  # type: ignore
    ).count()

    if weekly_count >= 2:
        flash(
            f"Weekly Limit Reached: You can only book 2 days per week (Sun-Sat).",
            "warning",
        )
        return redirect(
            url_for(
                "reservations.calendar",
                server_id=slot.server_id,
                year=target_date.year,
                month=target_date.month,
            )
        )

    # --- END NEW LIMITS ---

    # 5. Book the slot
    slot.reserved_by_user_id = current_user.id
    log_action(
        current_user.id,
        "BOOK_SLOT",
        f"Reserved {slot.server.name} for {target_date.strftime('%Y-%m-%d')}",
    )
    db.session.commit()
    flash(f"Successfully reserved {target_date.strftime('%Y-%m-%d')}", "success")

    return redirect(
        url_for(    
            "reservations.calendar",
            server_id=slot.server_id,
            year=target_date.year,
            month=target_date.month,
        )
    )
