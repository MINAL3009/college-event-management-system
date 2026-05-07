"""
Club Routes - ALL Features
- Dashboard with statistics
- Create events with image upload
- View club events
- Announce results
- Manage student requests
- View statistics
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from app import db
from app.models import Event, EventRegistration, EventRequest, EventResult, Student, Team, TeamMember
from app.utils.decorators import club_required
from app.utils.validators import validate_event_creation, validate_result_announcement, ValidationError
from app.utils.helpers import save_uploaded_file, send_notification, send_bulk_notification
from app.config import Config
from datetime import datetime

clubs_bp = Blueprint('clubs', __name__)


@clubs_bp.route('/dashboard')
@club_required
def dashboard():
    """Club dashboard with statistics"""
    events = Event.query.filter_by(club_id=current_user.id).all()

    total_events = len(events)
    upcoming = len([e for e in events if e.status == 'upcoming'])
    completed = len([e for e in events if e.status == 'completed'])

    total_participants = sum(e.current_participants for e in events)

    pending_requests = EventRequest.query.filter_by(
        club_id=current_user.id,
        status='pending'
    ).count()

    recent_events = Event.query.filter_by(
        club_id=current_user.id
    ).order_by(Event.created_at.desc()).limit(5).all()

    return render_template('dashboard/club.html',
        total_events=total_events,
        upcoming_events=upcoming,
        completed_events=completed,
        total_participants=total_participants,
        pending_requests=pending_requests,
        recent_events=recent_events
    )


@clubs_bp.route('/create-event', methods=['GET', 'POST'])
@club_required
def create_event():
    """Create new event with ALL validations"""
    if request.method == 'POST':
        try:
            data = {
                'title': request.form.get('title', '').strip(),
                'description': request.form.get('description', '').strip(),
                'event_type': request.form.get('event_type', '').strip(),
                'venue': request.form.get('venue', '').strip(),
                'event_date': request.form.get('event_date', ''),
                'registration_deadline': request.form.get('registration_deadline', ''),
                'max_participants': request.form.get('max_participants', ''),
                'is_team_event': request.form.get('is_team_event') == 'on',
                'team_size_min': request.form.get('team_size_min', ''),
                'team_size_max': request.form.get('team_size_max', ''),
                'rules': request.form.get('rules', '').strip()
            }

            validate_event_creation(data, current_user.id)

            event = Event(
                club_id=current_user.id,
                title=data['title'],
                description=data['description'],
                event_type=data['event_type'],
                venue=data['venue'],
                event_date=datetime.fromisoformat(data['event_date']),
                registration_deadline=datetime.fromisoformat(data['registration_deadline']),
                max_participants=int(data['max_participants']),
                is_team_event=data['is_team_event'],
                rules=data['rules']
            )

            if data['is_team_event']:
                event.team_size_min = int(data['team_size_min'])
                event.team_size_max = int(data['team_size_max'])

            if 'image' in request.files:
                image = request.files['image']
                if image and image.filename:
                    image_url = save_uploaded_file(image, 'events')
                    if image_url:
                        event.image_url = image_url

            db.session.add(event)
            db.session.commit()

            count = send_bulk_notification(
                'New Event Available',
                f"New event '{event.title}' by {current_user.name}. Register now!",
                'new_event'
            )

            flash(f'Event "{event.title}" created successfully! {count} students notified.', 'success')
            return redirect(url_for('clubs.my_events'))

        except ValidationError as e:
            flash(str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Event creation failed: {str(e)}', 'danger')

    return render_template('club/create_event.html',
        event_types=Config.EVENT_TYPES
    )


from datetime import datetime

@clubs_bp.route('/events')
@club_required
def my_events():
    events = Event.query.filter_by(
        club_id=current_user.id
    ).order_by(Event.event_date.desc()).all()

    current_time = datetime.now()

    for event in events:
        if event.status != 'cancelled':
            if current_time >= event.event_date:
                event.status = 'completed'
            else:
                event.status = 'upcoming'

    db.session.commit()

    return render_template('club/my_events.html', events=events)


@clubs_bp.route('/event/<int:event_id>')
@club_required
def view_event(event_id):
    """View event details with registrations"""
    event = Event.query.get_or_404(event_id)

    if event.club_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('clubs.my_events'))

    if event.is_team_event:
        teams = Team.query.filter_by(event_id=event_id).all()
        return render_template('club/view_event.html',
            event=event,
            teams=teams,
            is_team=True
        )
    else:
        registrations = db.session.query(EventRegistration, Student).join(Student).filter(
            EventRegistration.event_id == event_id
        ).all()
        return render_template('club/view_event.html',
            event=event,
            registrations=registrations,
            is_team=False
        )


@clubs_bp.route('/event/<int:event_id>/edit', methods=['GET', 'POST'])
@club_required
def edit_event(event_id):
    """Edit an upcoming event"""
    
    event = Event.query.get_or_404(event_id)

    if event.club_id != current_user.id:
        flash('You do not have permission to edit this event', 'danger')
        return redirect(url_for('clubs.my_events'))

    if event.status != 'upcoming':
        flash('You can only edit upcoming events', 'danger')
        return redirect(url_for('clubs.my_events'))

    if request.method == 'POST':
        event.title = request.form.get('title')
        event.description = request.form.get('description')
        event.event_type = request.form.get('event_type')
        event.venue = request.form.get('venue')
        event.max_participants = int(request.form.get('max_participants'))
        event.rules = request.form.get('rules')

        event_date_str = request.form.get('event_date')
        deadline_str = request.form.get('registration_deadline')
        event.event_date = datetime.strptime(event_date_str, '%Y-%m-%dT%H:%M')
        event.registration_deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')

        is_team = request.form.get('is_team_event') == 'on'
        event.is_team_event = is_team

        if is_team:
            event.team_size_min = int(request.form.get('team_size_min'))
            event.team_size_max = int(request.form.get('team_size_max'))

        try:
            validate_event_creation({
                'title': event.title,
                'description': event.description,
                'event_type': event.event_type,
                'venue': event.venue,
                'event_date': event.event_date,
                'registration_deadline': event.registration_deadline,
                'max_participants': event.max_participants,
                'is_team_event': event.is_team_event,
                'team_size_min': event.team_size_min,
                'team_size_max': event.team_size_max
            }, current_user.id)

            db.session.commit()
            flash('Event updated successfully!', 'success')
            return redirect(url_for('clubs.my_events'))

        except ValidationError as e:
            flash(str(e), 'danger')
            return redirect(url_for('clubs.edit_event', event_id=event_id))

    return render_template(
        'club/edit_event.html',
        event=event,
        event_types=Config.EVENT_TYPES
    )


@clubs_bp.route('/event/<int:event_id>/delete', methods=['POST'])
@club_required
def delete_event(event_id):
    """Delete an upcoming event with no registrations"""
    event = Event.query.get_or_404(event_id)

    if event.club_id != current_user.id:
        flash('You do not have permission to delete this event', 'danger')
        return redirect(url_for('clubs.my_events'))

    if event.current_participants > 0:
        flash('Cannot delete event with existing registrations', 'danger')
        return redirect(url_for('clubs.my_events'))

    db.session.delete(event)
    db.session.commit()

    flash('Event deleted successfully!', 'success')
    return redirect(url_for('clubs.my_events'))


@clubs_bp.route('/event/<int:event_id>/announce-result', methods=['GET', 'POST'])
@club_required
def announce_result(event_id):
    """Announce event results"""
    event = Event.query.get_or_404(event_id)

    if event.club_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('clubs.my_events'))

    if request.method == 'POST':
        try:
            results_data = []

            for position in [1, 2, 3]:
                if event.is_team_event:
                    team_id = request.form.get(f'team_position_{position}', type=int)
                    prize = request.form.get(f'prize_{position}', '').strip()
                    if team_id:
                        results_data.append({
                            'position': position,
                            'team_id': team_id,
                            'prize': prize
                        })
                else:
                    student_id = request.form.get(f'student_position_{position}', type=int)
                    prize = request.form.get(f'prize_{position}', '').strip()
                    if student_id:
                        results_data.append({
                            'position': position,
                            'student_id': student_id,
                            'prize': prize
                        })

            if not results_data:
                flash('Please select at least one winner', 'warning')
                return redirect(url_for('clubs.announce_result', event_id=event_id))

            validate_result_announcement(event_id, results_data)

            for result_data in results_data:
                result = EventResult(
                    event_id=event_id,
                    position=result_data['position'],
                    prize=result_data.get('prize')
                )

                if event.is_team_event:
                    result.team_id = result_data['team_id']

                    team = Team.query.get(result_data['team_id'])
                    members = TeamMember.query.filter_by(team_id=team.id).all()

                    for member in members:
                        student = Student.query.get(member.student_id)
                        student.events_won += 1
                        send_notification(
                            student.id,
                            'Congratulations! 🏆',
                            f"Your team '{team.team_name}' won position {result_data['position']} in '{event.title}'!",
                            'result',
                            event_id
                        )
                else:
                    result.student_id = result_data['student_id']

                    student = Student.query.get(result_data['student_id'])
                    student.events_won += 1
                    send_notification(
                        student.id,
                        'Congratulations! 🏆',
                        f"You won position {result_data['position']} in '{event.title}'!",
                        'result',
                        event_id
                    )

                db.session.add(result)

            event.status = 'completed'

            if event.is_team_event:
                teams = Team.query.filter_by(event_id=event_id).all()
                for team in teams:
                    members = TeamMember.query.filter_by(team_id=team.id).all()
                    for member in members:
                        student = Student.query.get(member.student_id)
                        student.events_participated += 1
            else:
                registrations = EventRegistration.query.filter_by(event_id=event_id).all()
                for reg in registrations:
                    student = Student.query.get(reg.student_id)
                    student.events_participated += 1

            db.session.commit()

            flash('Results announced successfully!', 'success')
            return redirect(url_for('clubs.view_event', event_id=event_id))

        except ValidationError as e:
            flash(str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to announce results: {str(e)}', 'danger')

    if event.is_team_event:
        teams = Team.query.filter_by(event_id=event_id).all()
        return render_template('club/announce_result.html',
            event=event,
            teams=teams,
            is_team=True
        )
    else:
        registrations = db.session.query(EventRegistration, Student).join(Student).filter(
            EventRegistration.event_id == event_id
        ).all()
        return render_template('club/announce_result.html',
            event=event,
            registrations=registrations,
            is_team=False
        )


@clubs_bp.route('/requests')
@club_required
def event_requests():
    """View all student event requests"""
    # Renamed local variable to avoid shadowing Flask's `request`
    all_requests = EventRequest.query.filter_by(
        club_id=current_user.id
    ).order_by(EventRequest.created_at.desc()).all()

    return render_template('club/requests.html', requests=all_requests)


@clubs_bp.route('/request/<int:request_id>/respond', methods=['POST'])
@club_required
def respond_request(request_id):
    """Accept or reject student request"""
    event_request = EventRequest.query.get_or_404(request_id)

    if event_request.club_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('clubs.event_requests'))

    status = request.form.get('status')
    feedback = request.form.get('feedback', '').strip()

    if status not in ['accepted', 'rejected']:
        flash('Invalid status', 'danger')
        return redirect(url_for('clubs.event_requests'))

    event_request.status = status
    event_request.club_feedback = feedback
    event_request.responded_at = datetime.utcnow()

    db.session.commit()

    send_notification(
        event_request.student_id,
        f"Event Request {status.title()}",
        f"Your request for '{event_request.event_title}' was {status}. {feedback}",
        'request_response'
    )

    flash(f'Request {status} successfully!', 'success')
    return redirect(url_for('clubs.event_requests'))


@clubs_bp.route('/statistics')
@club_required
def statistics():
    """View club statistics"""
    events = Event.query.filter_by(club_id=current_user.id).all()

    total_events = len(events)
    total_participants = sum(e.current_participants for e in events)
    avg_participants = total_participants / total_events if total_events > 0 else 0

    events_by_type = {}
    for event in events:
        events_by_type[event.event_type] = events_by_type.get(event.event_type, 0) + 1

    events_by_status = {
        'upcoming': len([e for e in events if e.status == 'upcoming']),
        'ongoing': len([e for e in events if e.status == 'ongoing']),
        'completed': len([e for e in events if e.status == 'completed']),
        'cancelled': len([e for e in events if e.status == 'cancelled'])
    }

    return render_template('club/statistics.html',
        total_events=total_events,
        total_participants=total_participants,
        avg_participants=round(avg_participants, 1),
        events_by_type=events_by_type,
        events_by_status=events_by_status
    )