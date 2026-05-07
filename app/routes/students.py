"""
Student Routes - ALL Features
- Dashboard with statistics
- Browse events with filters
- Register for events (individual & team)
- View registrations
- Request events from clubs
- Profile management
- Download certificates
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from app import db
from app.models import Event, Club, EventRegistration, Team, TeamMember, EventRequest, Notification, Student
from app.utils.decorators import student_required
from app.utils.validators import (
    validate_event_registration, 
    validate_team_registration, 
    validate_event_request,
    ValidationError
)
from app.utils.helpers import send_notification
from datetime import datetime

students_bp = Blueprint('students', __name__)

@students_bp.route('/dashboard')
@student_required
def dashboard():
    """Student dashboard with statistics"""
    # Get statistics
    total_registrations = EventRegistration.query.filter_by(
        student_id=current_user.id
    ).count()
    
    # Count team events
    team_events = db.session.query(Team).join(TeamMember).filter(
        TeamMember.student_id == current_user.id
    ).count()
    
    total_registrations += team_events
    
    # Upcoming events
    upcoming = db.session.query(Event).join(EventRegistration).filter(
        EventRegistration.student_id == current_user.id,
        Event.event_date > datetime.utcnow(),
        Event.status == 'upcoming'
    ).count()
    
    # Get upcoming events list
    upcoming_events = db.session.query(Event).join(EventRegistration).filter(
        EventRegistration.student_id == current_user.id,
        Event.event_date > datetime.utcnow(),
        Event.status == 'upcoming'
    ).order_by(Event.event_date).limit(5).all()
    
    # Unread notifications
    unread_notif = Notification.query.filter_by(
        student_id=current_user.id,
        is_read=False
    ).count()
    
    return render_template('dashboard/student.html',
        total_registrations=total_registrations,
        upcoming_events_count=upcoming,
        events_won=current_user.events_won,
        events_participated=current_user.events_participated,
        upcoming_events=upcoming_events,
        unread_notifications=unread_notif
    )

@students_bp.route('/events')
@student_required
def browse_events():
    """Browse events with filters"""
    # Get filter parameters
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
    
    # Get all clubs for filter dropdown
    clubs = Club.query.filter_by(is_active=True).all()
    
    # Get student's registered event IDs
    registered_event_ids = [reg.event_id for reg in 
                           EventRegistration.query.filter_by(student_id=current_user.id).all()]
    
    return render_template('student/browse_events.html',
        events=events,
        clubs=clubs,
        registered_event_ids=registered_event_ids,
        selected_club=club_id,
        selected_type=event_type,
        search_query=search
    )

@students_bp.route('/register/<int:event_id>', methods=['POST'])
@student_required
def register_event(event_id):
    """Register for individual event"""
    try:
        # Validate registration
        validate_event_registration(current_user.id, event_id)
        
        event = Event.query.get(event_id)
        
        # Create registration
        registration = EventRegistration(
            student_id=current_user.id,
            event_id=event_id
        )
        
        # Update participant count
        event.current_participants += 1
        
        db.session.add(registration)
        db.session.commit()
        
        # Send notification
        send_notification(
            current_user.id,
            'Registration Confirmed',
            f"You are registered for '{event.title}' on {event.event_date.strftime('%B %d, %Y at %I:%M %p')}",
            'event_registration',
            event_id
        )
        
        flash(f'Successfully registered for {event.title}!', 'success')
        
    except ValidationError as e:
        flash(str(e), 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Registration failed: {str(e)}', 'danger')
    
    return redirect(url_for('students.browse_events'))

@students_bp.route('/register-team/<int:event_id>', methods=['GET', 'POST'])
@student_required
def register_team(event_id):
    """Register team for team event"""
    event = Event.query.get_or_404(event_id)
    
    if not event.is_team_event:
        flash('This is not a team event', 'danger')
        return redirect(url_for('students.browse_events'))
    
    if request.method == 'POST':
        try:
            team_name = request.form.get('team_name', '').strip()
            member_emails = request.form.getlist('member_emails[]')
            
            # Get member IDs from emails
            member_ids = []
            for email in member_emails:
                email = email.strip()
                if email:
                    student = Student.query.filter_by(email=email, is_active=True).first()
                    if student:
                        member_ids.append(student.id)
                    else:
                        flash(f'Student with email {email} not found', 'danger')
                        return render_template('student/register_team.html', event=event)
            
            # Add current user as leader
            if current_user.id not in member_ids:
                member_ids.append(current_user.id)
            
            team_data = {
                'team_name': team_name,
                'member_ids': member_ids
            }
            
            # Validate
            validate_team_registration(event_id, team_data, current_user.id)
            
            # Create team
            team = Team(
                event_id=event_id,
                team_name=team_name,
                leader_id=current_user.id
            )
            db.session.add(team)
            db.session.flush()
            
            # Add members
            for member_id in member_ids:
                member = TeamMember(
                    team_id=team.id,
                    student_id=member_id
                )
                db.session.add(member)
                
                # Notify each member
                send_notification(
                    member_id,
                    'Team Registration',
                    f"You joined team '{team_name}' for '{event.title}'",
                    'event_registration',
                    event_id
                )
            
            # Update participant count
            event.current_participants += 1
            
            db.session.commit()
            
            flash(f'Team "{team_name}" registered successfully!', 'success')
            return redirect(url_for('students.my_registrations'))
            
        except ValidationError as e:
            flash(str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Team registration failed: {str(e)}', 'danger')
    
    # Get all active students for autocomplete
    students = Student.query.filter_by(is_active=True).all()
    
    return render_template('student/register_team.html', 
        event=event,
        students=students,
        min_size=event.team_size_min,
        max_size=event.team_size_max
    )

@students_bp.route('/registrations')
@student_required
def my_registrations():
    """View all registrations"""
    # Individual registrations
    individual_regs = db.session.query(EventRegistration, Event).join(Event).filter(
        EventRegistration.student_id == current_user.id
    ).order_by(Event.event_date.desc()).all()
    
    # Team registrations
    team_regs = db.session.query(Team, Event).join(Event).join(TeamMember).filter(
        TeamMember.student_id == current_user.id
    ).order_by(Event.event_date.desc()).all()
    
    return render_template('student/registrations.html',
        individual_registrations=individual_regs,
        team_registrations=team_regs
    )

@students_bp.route('/request-event', methods=['GET', 'POST'])
@student_required
def request_event():
    """Request event from club"""
    if request.method == 'POST':
        try:
            club_id = request.form.get('club_id', type=int)
            event_title = request.form.get('event_title', '').strip()
            event_type = request.form.get('event_type', '').strip()
            description = request.form.get('description', '').strip()
            
            request_data = {
                'event_title': event_title,
                'event_type': event_type,
                'description': description
            }
            
            # Validate
            validate_event_request(current_user.id, club_id, request_data)
            
            # Create request
            event_request = EventRequest(
                student_id=current_user.id,
                club_id=club_id,
                event_title=event_title,
                event_type=event_type,
                description=description
            )
            
            db.session.add(event_request)
            db.session.commit()
            
            flash(f'Event request submitted to {event_request.club.name}!', 'success')
            return redirect(url_for('students.my_requests'))
            
        except ValidationError as e:
            flash(str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Request failed: {str(e)}', 'danger')
    
    # Get all active clubs
    clubs = Club.query.filter_by(is_active=True).all()
    
    from app.config import Config
    return render_template('student/request_event.html', 
        clubs=clubs,
        event_types=Config.EVENT_TYPES
    )

@students_bp.route('/my-requests')
@student_required
def my_requests():
    """View all event requests"""
    requests = EventRequest.query.filter_by(
        student_id=current_user.id
    ).order_by(EventRequest.created_at.desc()).all()
    
    return render_template('student/my_requests.html', requests=requests)

@students_bp.route('/profile', methods=['GET', 'POST'])
@student_required
def profile():
    """View and edit profile"""
    if request.method == 'POST':
        current_user.name = request.form.get('name', current_user.name).strip()
        current_user.branch = request.form.get('branch', current_user.branch).strip()
        current_user.year = request.form.get('year', current_user.year).strip()
        current_user.division = request.form.get('division', current_user.division).strip()
        
        # Update password if provided
        new_password = request.form.get('new_password', '')
        if new_password:
            if len(new_password) < 8:
                flash('Password must be at least 8 characters', 'danger')
            else:
                current_user.set_password(new_password)
                flash('Password updated successfully', 'success')
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('students.profile'))
    
    return render_template('student/profile.html')

@students_bp.route('/notifications')
@student_required
def notifications():
    """View all notifications"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    notifications_query = Notification.query.filter_by(
        student_id=current_user.id
    ).order_by(Notification.created_at.desc())
    
    notifications_paginated = notifications_query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('student/notifications.html',
        notifications=notifications_paginated
    )

@students_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@student_required
def mark_notification_read(notif_id):
    """Mark notification as read"""
    notification = Notification.query.get_or_404(notif_id)
    
    if notification.student_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('students.notifications'))
    
    notification.is_read = True
    db.session.commit()
    
    return redirect(url_for('students.notifications'))