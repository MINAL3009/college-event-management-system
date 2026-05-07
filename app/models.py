"""
Complete Database Models - All 10 Tables
Normalized to 3NF with all constraints and validations
"""
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import Index, CheckConstraint, UniqueConstraint

# ==================== USER MODELS ====================

class Student(UserMixin, db.Model):
    """Student model with complete profile"""
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile
    name = db.Column(db.String(100), nullable=False)
    branch = db.Column(db.String(100), nullable=False)
    year = db.Column(db.String(20), nullable=False)
    division = db.Column(db.String(10), nullable=False)
    
    # Statistics
    events_participated = db.Column(db.Integer, default=0)
    events_won = db.Column(db.Integer, default=0)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    registrations = db.relationship('EventRegistration', backref='student', lazy='dynamic', 
                                   cascade='all, delete-orphan')
    team_memberships = db.relationship('TeamMember', backref='student', lazy='dynamic',
                                      cascade='all, delete-orphan')
    event_requests = db.relationship('EventRequest', backref='student', lazy='dynamic',
                                    cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='student', lazy='dynamic',
                                   cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        """Flask-Login requirement"""
        return f"student_{self.id}"
    
    def __repr__(self):
        return f'<Student {self.email}>'


class Club(UserMixin, db.Model):
    """Club model"""
    __tablename__ = 'clubs'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'))
    
    # Relationships
    events = db.relationship('Event', backref='club', lazy='dynamic',
                           cascade='all, delete-orphan')
    event_requests = db.relationship('EventRequest', backref='club', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        return f"club_{self.id}"
    
    def __repr__(self):
        return f'<Club {self.name}>'


class Admin(UserMixin, db.Model):
    """Admin model"""
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    clubs_created = db.relationship('Club', backref='created_by', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        return f"admin_{self.id}"
    
    def __repr__(self):
        return f'<Admin {self.username}>'


# ==================== EVENT MODELS ====================

class Event(db.Model):
    """Event model with venue-time conflict prevention"""
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False, index=True)
    
    # Basic info
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    
    # Location & Time
    venue = db.Column(db.String(200), nullable=False)
    event_date = db.Column(db.DateTime, nullable=False, index=True)
    registration_deadline = db.Column(db.DateTime, nullable=False)
    
    # Capacity
    max_participants = db.Column(db.Integer, nullable=False)
    current_participants = db.Column(db.Integer, default=0)
    
    # Team event
    is_team_event = db.Column(db.Boolean, default=False)
    team_size_min = db.Column(db.Integer, nullable=True)
    team_size_max = db.Column(db.Integer, nullable=True)
    
    # Additional
    rules = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='upcoming', index=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    registrations = db.relationship('EventRegistration', backref='event', lazy='dynamic',
                                   cascade='all, delete-orphan')
    teams = db.relationship('Team', backref='event', lazy='dynamic',
                          cascade='all, delete-orphan')
    results = db.relationship('EventResult', backref='event', lazy='dynamic',
                            cascade='all, delete-orphan')
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('venue', 'event_date', name='unique_venue_time'),
        CheckConstraint('registration_deadline < event_date', name='deadline_before_event'),
        CheckConstraint('max_participants > 0', name='positive_capacity'),
        CheckConstraint('current_participants <= max_participants', name='capacity_limit'),
        Index('idx_event_status_date', 'status', 'event_date'),
    )
    
    def __repr__(self):
        return f'<Event {self.title}>'


class EventRegistration(db.Model):
    """Individual event registration"""
    __tablename__ = 'event_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='registered')
    attendance_marked = db.Column(db.Boolean, default=False)
    
    __table_args__ = (
        UniqueConstraint('student_id', 'event_id', name='unique_student_event'),
        Index('idx_registration_status', 'status'),
    )
    
    def __repr__(self):
        return f'<Registration S:{self.student_id} E:{self.event_id}>'


# ==================== TEAM MODELS ====================

class Team(db.Model):
    """Team for team events"""
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    team_name = db.Column(db.String(100), nullable=False)
    leader_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    members = db.relationship('TeamMember', backref='team', lazy='dynamic',
                            cascade='all, delete-orphan')
    leader = db.relationship('Student', foreign_keys=[leader_id])
    
    __table_args__ = (
        UniqueConstraint('event_id', 'team_name', name='unique_team_per_event'),
    )
    
    def __repr__(self):
        return f'<Team {self.team_name}>'


class TeamMember(db.Model):
    """Team members"""
    __tablename__ = 'team_members'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('team_id', 'student_id', name='unique_member_per_team'),
    )
    
    def __repr__(self):
        return f'<TeamMember T:{self.team_id} S:{self.student_id}>'


# ==================== RESULTS ====================

class EventResult(db.Model):
    """Event results"""
    __tablename__ = 'event_results'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    position = db.Column(db.Integer, nullable=False)
    prize = db.Column(db.String(200))
    announced_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    winner_student = db.relationship('Student', foreign_keys=[student_id])
    winner_team = db.relationship('Team', foreign_keys=[team_id])
    
    __table_args__ = (
        UniqueConstraint('event_id', 'position', name='unique_position_per_event'),
        CheckConstraint('position IN (1, 2, 3)', name='valid_position'),
    )
    
    def __repr__(self):
        return f'<Result E:{self.event_id} P:{self.position}>'


# ==================== REQUESTS ====================

class EventRequest(db.Model):
    """Student requests for events"""
    __tablename__ = 'event_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False, index=True)
    
    event_title = db.Column(db.String(200), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    status = db.Column(db.String(20), default='pending')
    club_feedback = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)
    
    __table_args__ = (
        UniqueConstraint('student_id', 'club_id', 'event_title', name='unique_request'),
        Index('idx_request_status', 'status'),
    )
    
    def __repr__(self):
        return f'<EventRequest {self.event_title}>'


# ==================== NOTIFICATIONS ====================

class Notification(db.Model):
    """Notifications"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50))
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True)
    
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    related_event = db.relationship('Event', foreign_keys=[event_id])
    
    __table_args__ = (
        Index('idx_notification_read_status', 'student_id', 'is_read'),
    )
    
    def __repr__(self):
        return f'<Notification {self.title}>'