"""
Public Events Routes
- Browse events (accessible to all)
- Event details
"""
from flask import Blueprint, render_template, request
from app.models import Event, Club
from datetime import datetime

events_bp = Blueprint('events', __name__)

@events_bp.route('/')
def browse():
    """Public events browsing page"""
    # Get filters
    club_id = request.args.get('club_id', type=int)
    event_type = request.args.get('event_type', '')
    search = request.args.get('search', '')
    
    # Build query
    query = Event.query.filter_by(status='upcoming')
    
    if club_id:
        query = query.filter_by(club_id=club_id)
    
    if event_type:
        query = query.filter_by(event_type=event_type)
    
    if search:
        query = query.filter(Event.title.contains(search))
    
    events = query.order_by(Event.event_date).all()
    
    # Get all active clubs for filter
    clubs = Club.query.filter_by(is_active=True).order_by(Club.name).all()
    
    from app.config import Config
    event_types = Config.EVENT_TYPES
    
    return render_template('student/browse_events.html',
        events=events,
        clubs=clubs,
        event_types=event_types,
        selected_club=club_id,
        selected_type=event_type,
        search_query=search
    )

@events_bp.route('/<int:event_id>')
def view(event_id):
    """View event details (public)"""
    event = Event.query.get_or_404(event_id)
    
    # Calculate availability
    spots_left = event.max_participants - event.current_participants
    is_full = spots_left <= 0
    is_deadline_passed = datetime.utcnow() > event.registration_deadline
    
    return render_template('public/event_detail.html',
        event=event,
        spots_left=spots_left,
        is_full=is_full,
        is_deadline_passed=is_deadline_passed
    )