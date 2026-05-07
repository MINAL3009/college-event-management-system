"""
Complete validation functions for ALL business logic
Handles EVERY real-world scenario
"""
from datetime import datetime, timedelta
from flask import current_app
from app.models import Event, EventRegistration, Team, TeamMember, Student, EventRequest, EventResult
from app import db

class ValidationError(Exception):
    """Custom validation error"""
    pass

# ==================== EVENT VALIDATIONS ====================

def validate_event_creation(data, club_id):
    """
    Validate event creation with ALL constraints:
    - Venue-time conflict check (CRITICAL)
    - Date validations
    - Capacity checks
    - Team size consistency
    """
    errors = []
    
    # Required fields
    required = ['title', 'description', 'event_type', 'venue', 'event_date', 
                'registration_deadline', 'max_participants']
    for field in required:
        if field not in data or not str(data[field]).strip():
            errors.append(f"{field.replace('_', ' ').title()} is required")
    
    if errors:
        raise ValidationError("; ".join(errors))
    
    # Parse dates
    try:
        if isinstance(data['event_date'], str):
            event_date = datetime.fromisoformat(data['event_date'].replace('Z', '').replace('T', ' '))
        else:
            event_date = data['event_date']
            
        if isinstance(data['registration_deadline'], str):
            deadline = datetime.fromisoformat(data['registration_deadline'].replace('Z', '').replace('T', ' '))
        else:
            deadline = data['registration_deadline']
    except (ValueError, AttributeError) as e:
        raise ValidationError(f"Invalid date format: {str(e)}")
    
    now = datetime.utcnow()
    
    # Date validations
    if event_date <= now:
        raise ValidationError("Event date must be in the future")
    
    if deadline >= event_date:
        raise ValidationError("Registration deadline must be before event date")
    
    if deadline <= now:
        raise ValidationError("Registration deadline must be in the future")
    
    # Capacity validation
    try:
        max_participants = int(data['max_participants'])
        if max_participants < 1:
            raise ValidationError("Maximum participants must be at least 1")
    except ValueError:
        raise ValidationError("Invalid maximum participants value")
    
    # Team event validations
    is_team_event = data.get('is_team_event', False)
    if is_team_event:
        try:
            team_min = int(data.get('team_size_min', 0))
            team_max = int(data.get('team_size_max', 0))
            
            if team_min < 1:
                raise ValidationError("Minimum team size must be at least 1")
            
            if team_max < team_min:
                raise ValidationError("Maximum team size cannot be less than minimum")
            
            if max_participants < team_max:
                raise ValidationError("Max participants must be at least equal to max team size")
        except ValueError:
            raise ValidationError("Invalid team size values")
    
    # CRITICAL: Venue-Time Conflict Check
    conflict = Event.query.filter(
        Event.venue == data['venue'],
        Event.event_date == event_date,
        Event.status != 'cancelled',
        Event.club_id != club_id  # Different club
    ).first()
    
    if conflict:
        raise ValidationError(
            f"Venue '{data['venue']}' is already booked at "
            f"{event_date.strftime('%Y-%m-%d %H:%M')} by event '{conflict.title}' "
            f"(organized by {conflict.club.name})"
        )
    
    return True

def validate_event_registration(student_id, event_id):
    """
    Validate student event registration - PREVENTS:
    - Duplicate registration
    - Full capacity
    - Missed deadline
    - Time conflicts
    - Team event individual registration
    """
    event = Event.query.get(event_id)
    if not event:
        raise ValidationError("Event not found")
    
    # Event status check
    if event.status != 'upcoming':
        raise ValidationError(f"Cannot register for {event.status} event")
    
    # Capacity check
    if event.current_participants >= event.max_participants:
        raise ValidationError("Event is FULL. Registration closed.")
    
    # Deadline check
    if datetime.utcnow() > event.registration_deadline:
        raise ValidationError("Registration deadline has passed")
    
    # Team event check
    if event.is_team_event:
        raise ValidationError("This is a team event. Please register as a team.")
    
    # Duplicate registration check
    existing = EventRegistration.query.filter_by(
        student_id=student_id,
        event_id=event_id
    ).first()
    
    if existing:
        if existing.status == 'cancelled':
            raise ValidationError("You cancelled this registration. Contact organizers to re-register.")
        raise ValidationError("You are already registered for this event")
    
    # Time conflict check (30-minute buffer)
    buffer = timedelta(minutes=current_app.config.get('EVENT_TIME_BUFFER_MINUTES', 30))
    
    conflicts = db.session.query(EventRegistration).join(Event).filter(
        EventRegistration.student_id == student_id,
        EventRegistration.status == 'registered',
        Event.event_date >= event.event_date - buffer,
        Event.event_date <= event.event_date + buffer,
        Event.id != event_id
    ).all()
    
    if conflicts:
        conflict_event = conflicts[0].event
        raise ValidationError(
            f"Time conflict! You have '{conflict_event.title}' at "
            f"{conflict_event.event_date.strftime('%H:%M')}. "
            f"Events must be at least 30 minutes apart."
        )
    
    # Check student is active
    student = Student.query.get(student_id)
    if not student or not student.is_active:
        raise ValidationError("Student account is inactive")
    
    return True

def validate_team_registration(event_id, team_data, leader_id):
    """
    Validate team registration - PREVENTS:
    - Wrong event type
    - Invalid team size
    - Duplicate team name
    - Members already in teams
    - Duplicate members
    """
    event = Event.query.get(event_id)
    if not event:
        raise ValidationError("Event not found")
    
    # Event type check
    if not event.is_team_event:
        raise ValidationError("This is not a team event")
    
    # Event status
    if event.status != 'upcoming':
        raise ValidationError(f"Cannot register for {event.status} event")
    
    # Deadline check
    if datetime.utcnow() > event.registration_deadline:
        raise ValidationError("Registration deadline has passed")
    
    # Capacity check
    if event.current_participants >= event.max_participants:
        raise ValidationError("Event is FULL")
    
    # Team data validation
    team_name = team_data.get('team_name', '').strip()
    member_ids = team_data.get('member_ids', [])
    
    if not team_name:
        raise ValidationError("Team name is required")
    
    if not member_ids or not isinstance(member_ids, list):
        raise ValidationError("Team must have members")
    
    # Team size validation
    team_size = len(member_ids)
    if team_size < event.team_size_min:
        raise ValidationError(f"Team must have at least {event.team_size_min} members")
    
    if team_size > event.team_size_max:
        raise ValidationError(f"Team cannot have more than {event.team_size_max} members")
    
    # Leader must be in team
    if leader_id not in member_ids:
        raise ValidationError("Team leader must be part of the team")
    
    # Check for duplicate team name
    existing_team = Team.query.filter_by(
        event_id=event_id,
        team_name=team_name
    ).first()
    
    if existing_team:
        raise ValidationError(f"Team name '{team_name}' is already taken for this event")
    
    # Validate all members exist and are active
    members = Student.query.filter(Student.id.in_(member_ids)).all()
    
    if len(members) != team_size:
        raise ValidationError("One or more team members not found")
    
    for member in members:
        if not member.is_active:
            raise ValidationError(f"Student {member.name} is inactive")
    
    # Check if any member is already in a team for this event
    existing_membership = db.session.query(TeamMember).join(Team).filter(
        Team.event_id == event_id,
        TeamMember.student_id.in_(member_ids)
    ).first()
    
    if existing_membership:
        student = Student.query.get(existing_membership.student_id)
        raise ValidationError(f"{student.name} is already in a team for this event")
    
    # Check for duplicate members in request
    if len(member_ids) != len(set(member_ids)):
        raise ValidationError("Duplicate members in team")
    
    return True

def validate_result_announcement(event_id, results_data):
    """
    Validate result announcement - PREVENTS:
    - Results before event completion
    - Invalid positions
    - Duplicate positions
    - Winners not registered
    """
    event = Event.query.get(event_id)
    if not event:
        raise ValidationError("Event not found")
    
    # Event status check
    if event.status not in ['completed', 'ongoing']:
        raise ValidationError("Results can only be announced for completed or ongoing events")
    
    # Validate results data
    if not results_data or not isinstance(results_data, list):
        raise ValidationError("Invalid results data")
    
    positions_used = set()
    
    for result in results_data:
        position = result.get('position')
        student_id = result.get('student_id')
        team_id = result.get('team_id')
        
        # Position validation
        if not position or position not in [1, 2, 3]:
            raise ValidationError("Position must be 1, 2, or 3")
        
        # Duplicate position check
        if position in positions_used:
            raise ValidationError(f"Position {position} is specified multiple times")
        positions_used.add(position)
        
        # Winner validation
        if event.is_team_event:
            if not team_id:
                raise ValidationError(f"Team ID required for position {position}")
            
            team = Team.query.filter_by(id=team_id, event_id=event_id).first()
            if not team:
                raise ValidationError(f"Team not found for this event at position {position}")
        else:
            if not student_id:
                raise ValidationError(f"Student ID required for position {position}")
            
            registration = EventRegistration.query.filter_by(
                event_id=event_id,
                student_id=student_id
            ).first()
            
            if not registration:
                raise ValidationError(
                    f"Student (ID: {student_id}) is not registered for this event"
                )
    
    return True

def validate_event_request(student_id, club_id, request_data):
    """
    Validate event request - PREVENTS:
    - Duplicate requests
    - Too many pending requests
    - Missing fields
    """
    # Check for duplicate request
    existing = EventRequest.query.filter_by(
        student_id=student_id,
        club_id=club_id,
        event_title=request_data.get('event_title')
    ).first()
    
    if existing:
        if existing.status == 'pending':
            raise ValidationError("You already have a pending request for this event to this club")
        raise ValidationError("You have already requested this event from this club")
    
    # Check pending request limit
    max_pending = current_app.config.get('MAX_PENDING_REQUESTS', 5)
    pending_count = EventRequest.query.filter_by(
        student_id=student_id,
        status='pending'
    ).count()
    
    if pending_count >= max_pending:
        raise ValidationError(f"You have reached the maximum of {max_pending} pending requests")
    
    # Required fields
    required = ['event_title', 'event_type', 'description']
    for field in required:
        if field not in request_data or not str(request_data[field]).strip():
            raise ValidationError(f"{field.replace('_', ' ').title()} is required")
    
    return True

def validate_certificate_eligibility(student_id, event_id, certificate_type):
    """
    Validate certificate download - PREVENTS:
    - Certificates for incomplete events
    - Certificates for non-participants
    - Winner certificates for non-winners
    """
    event = Event.query.get(event_id)
    if not event:
        raise ValidationError("Event not found")
    
    if event.status != 'completed':
        raise ValidationError("Certificates are only available for completed events")
    
    # Check registration (individual or team)
    registration = EventRegistration.query.filter_by(
        event_id=event_id,
        student_id=student_id
    ).first()
    
    team_member = db.session.query(TeamMember).join(Team).filter(
        Team.event_id == event_id,
        TeamMember.student_id == student_id
    ).first()
    
    if not registration and not team_member:
        raise ValidationError("You are not registered for this event")
    
    if certificate_type == 'participation':
        # For participation certificate, attendance must be marked
        if registration and not registration.attendance_marked:
            raise ValidationError("Attendance not yet marked by organizers")
    
    elif certificate_type == 'winner':
        # For winner certificate, must be in results
        winner = EventResult.query.filter_by(
            event_id=event_id,
            student_id=student_id
        ).first()
        
        if not winner:
            # Check if student's team won
            if team_member:
                team_won = EventResult.query.filter_by(
                    event_id=event_id,
                    team_id=team_member.team_id
                ).first()
                
                if not team_won:
                    raise ValidationError("Your team did not win any position in this event")
            else:
                raise ValidationError("You did not win any position in this event")
    
    return True