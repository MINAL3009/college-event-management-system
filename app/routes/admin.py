"""
Admin Routes - ALL Features
- Dashboard with system statistics
- Create clubs with auto-generated credentials
- Manage clubs (view, deactivate)
- Manage students (view, deactivate)
- Send announcements to all students
- View system-wide statistics
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from app import db
from app.models import Club, Student, Event, Admin, EventRegistration
from app.utils.decorators import admin_required
from app.utils.helpers import generate_password, send_bulk_notification

admin_bp = Blueprint('admins', __name__)

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard with system statistics"""
    # Get counts
    total_students = Student.query.filter_by(is_active=True).count()
    total_clubs = Club.query.filter_by(is_active=True).count()
    total_events = Event.query.count()
    
    # Inactive counts
    inactive_students = Student.query.filter_by(is_active=False).count()
    inactive_clubs = Club.query.filter_by(is_active=False).count()
    
    # Recent activity
    recent_students = Student.query.order_by(Student.created_at.desc()).limit(5).all()
    recent_clubs = Club.query.order_by(Club.created_at.desc()).limit(5).all()
    recent_events = Event.query.order_by(Event.created_at.desc()).limit(5).all()
    
    # Events by status
    upcoming_events = Event.query.filter_by(status='upcoming').count()
    completed_events = Event.query.filter_by(status='completed').count()
    
    return render_template('dashboard/admin.html',
        total_students=total_students,
        total_clubs=total_clubs,
        total_events=total_events,
        inactive_students=inactive_students,
        inactive_clubs=inactive_clubs,
        upcoming_events=upcoming_events,
        completed_events=completed_events,
        recent_students=recent_students,
        recent_clubs=recent_clubs,
        recent_events=recent_events
    )

@admin_bp.route('/create-club', methods=['GET', 'POST'])
@admin_required
def create_club():
    """Create new club with auto-generated credentials"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        description = request.form.get('description', '').strip()
        
        # Validation
        errors = []
        if not all([name, username, email]):
            errors.append('Name, username, and email are required')
        
        if Club.query.filter_by(username=username).first():
            errors.append('Username already exists')
        
        if Club.query.filter_by(email=email).first():
            errors.append('Email already exists')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('admin/create_club.html')
        
        # Generate secure password
        password = generate_password(12)
        
        # Create club
        club = Club(
            name=name,
            username=username,
            email=email,
            description=description,
            created_by_admin_id=current_user.id
        )
        club.set_password(password)
        
        db.session.add(club)
        db.session.commit()
        
        # Show credentials (ONE TIME ONLY)
        flash('Club created successfully! Save these credentials:', 'success')
        return render_template('admin/club_credentials.html',
            club=club,
            password=password
        )
    
    return render_template('admin/create_club.html')

@admin_bp.route('/clubs')
@admin_required
def manage_clubs():
    """View and manage all clubs"""
    # Get filter
    status_filter = request.args.get('status', 'all')
    search = request.args.get('search', '')
    
    # Build query
    query = Club.query
    
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
    
    if search:
        query = query.filter(
            db.or_(
                Club.name.contains(search),
                Club.username.contains(search),
                Club.email.contains(search)
            )
        )
    
    clubs = query.order_by(Club.created_at.desc()).all()
    
    # Get event counts for each club
    club_stats = {}
    for club in clubs:
        event_count = Event.query.filter_by(club_id=club.id).count()
        club_stats[club.id] = event_count
    
    return render_template('admin/manage_clubs.html',
        clubs=clubs,
        club_stats=club_stats,
        status_filter=status_filter,
        search_query=search
    )

@admin_bp.route('/club/<int:club_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_club_status(club_id):
    """Activate or deactivate club"""
    club = Club.query.get_or_404(club_id)
    
    club.is_active = not club.is_active
    db.session.commit()
    
    status = 'activated' if club.is_active else 'deactivated'
    flash(f'Club "{club.name}" has been {status}.', 'success')
    
    return redirect(url_for('admins.manage_clubs'))

@admin_bp.route('/students')
@admin_required
def manage_students():
    """View and manage all students"""
    # Get filters
    status_filter = request.args.get('status', 'all')
    branch_filter = request.args.get('branch', '')
    year_filter = request.args.get('year', '')
    search = request.args.get('search', '')
    
    # Build query
    query = Student.query
    
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
    
    if branch_filter:
        query = query.filter_by(branch=branch_filter)
    
    if year_filter:
        query = query.filter_by(year=year_filter)
    
    if search:
        query = query.filter(
            db.or_(
                Student.name.contains(search),
                Student.email.contains(search)
            )
        )
    
    students = query.order_by(Student.created_at.desc()).all()
    
    # Get unique branches and years for filters
    branches = db.session.query(Student.branch).distinct().all()
    branches = [b[0] for b in branches]
    
    years = db.session.query(Student.year).distinct().all()
    years = [y[0] for y in years]
    
    return render_template('admin/manage_students.html',
        students=students,
        branches=branches,
        years=years,
        status_filter=status_filter,
        branch_filter=branch_filter,
        year_filter=year_filter,
        search_query=search
    )

@admin_bp.route('/student/<int:student_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_student_status(student_id):
    """Activate or deactivate student"""
    student = Student.query.get_or_404(student_id)
    
    student.is_active = not student.is_active
    db.session.commit()
    
    status = 'activated' if student.is_active else 'deactivated'
    flash(f'Student "{student.name}" has been {status}.', 'success')
    
    return redirect(url_for('admins.manage_students'))

@admin_bp.route('/announcement', methods=['GET', 'POST'])
@admin_required
def send_announcement():
    """Send announcement to all active students"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        
        if not title or not message:
            flash('Title and message are required', 'danger')
            return render_template('admin/announcement.html')
        
        # Send to all active students
        count = send_bulk_notification(title, message, 'announcement')
        
        flash(f'Announcement sent to {count} students successfully!', 'success')
        return redirect(url_for('admins.dashboard'))
    
    return render_template('admin/announcement.html')

@admin_bp.route('/statistics')
@admin_required
def statistics():
    """View system-wide statistics"""
    # Student statistics
    total_students = Student.query.count()
    active_students = Student.query.filter_by(is_active=True).count()
    
    students_by_year = {}
    years = db.session.query(Student.year, db.func.count(Student.id)).group_by(Student.year).all()
    for year, count in years:
        students_by_year[year] = count
    
    students_by_branch = {}
    branches = db.session.query(Student.branch, db.func.count(Student.id)).group_by(Student.branch).all()
    for branch, count in branches:
        students_by_branch[branch] = count
    
    # Club statistics
    total_clubs = Club.query.count()
    active_clubs = Club.query.filter_by(is_active=True).count()
    
    # Event statistics
    total_events = Event.query.count()
    events_by_status = {
        'upcoming': Event.query.filter_by(status='upcoming').count(),
        'ongoing': Event.query.filter_by(status='ongoing').count(),
        'completed': Event.query.filter_by(status='completed').count(),
        'cancelled': Event.query.filter_by(status='cancelled').count()
    }
    
    events_by_type = {}
    types = db.session.query(Event.event_type, db.func.count(Event.id)).group_by(Event.event_type).all()
    for event_type, count in types:
        events_by_type[event_type] = count
    
    # Registration statistics
    total_registrations = EventRegistration.query.count()
    
    # Top performing students
    top_students = Student.query.filter(
        Student.events_won > 0
    ).order_by(Student.events_won.desc()).limit(10).all()
    
    # Most active clubs
    club_event_counts = db.session.query(
        Club.name, 
        db.func.count(Event.id).label('event_count')
    ).join(Event).group_by(Club.id).order_by(db.desc('event_count')).limit(10).all()
    
    return render_template('admin/statistics.html',
        total_students=total_students,
        active_students=active_students,
        students_by_year=students_by_year,
        students_by_branch=students_by_branch,
        total_clubs=total_clubs,
        active_clubs=active_clubs,
        total_events=total_events,
        events_by_status=events_by_status,
        events_by_type=events_by_type,
        total_registrations=total_registrations,
        top_students=top_students,
        club_event_counts=club_event_counts
    )

@admin_bp.route('/events')
@admin_required
def view_all_events():
    """View all events in the system"""
    status_filter = request.args.get('status', 'all')
    
    query = Event.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    events = query.order_by(Event.event_date.desc()).all()
    
    return render_template('admin/all_events.html',
        events=events,
        status_filter=status_filter
    )