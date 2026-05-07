"""
Flask Application Factory
Initializes and configures the Flask app
"""
from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('app.config.Config')
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import Student, Club, Admin
        
        if '_' in user_id:
            user_type, uid = user_id.split('_')
            if user_type == 'student':
                return Student.query.get(int(uid))
            elif user_type == 'club':
                return Club.query.get(int(uid))
            elif user_type == 'admin':
                return Admin.query.get(int(uid))
        return None
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.students import students_bp
    from app.routes.clubs import clubs_bp
    from app.routes.admin import admin_bp
    from app.routes.events import events_bp
    from app.routes.notifications import notifications_bp
    from app.routes.certificates import certificates_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(students_bp, url_prefix='/student')
    app.register_blueprint(clubs_bp, url_prefix='/club')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(events_bp, url_prefix='/events')
    app.register_blueprint(notifications_bp, url_prefix='/notifications')
    app.register_blueprint(certificates_bp, url_prefix='/certificates')
    
    # Main routes
    @app.route('/')
    def index():
        """Homepage with dynamic gallery"""
        from app.models import Event, Club, Student
        
        # Get statistics
        total_events = Event.query.count()
        total_students = Student.query.filter_by(is_active=True).count()
        total_clubs = Club.query.filter_by(is_active=True).count()
        
        # Get upcoming events for gallery
        upcoming_events = Event.query.filter_by(status='upcoming')\
            .order_by(Event.event_date)\
            .limit(6)\
            .all()
        
        return render_template('index.html',
            total_events=total_events,
            total_students=total_students,
            total_clubs=total_clubs,
            gallery_events=upcoming_events
        )
    
    @app.route('/events')
    def events_page():
        """Public events listing"""
        from app.models import Event
        
        events = Event.query.filter_by(status='upcoming')\
            .order_by(Event.event_date)\
            .all()
        
        return render_template('events.html', events=events)
    
    @app.route('/clubs')
    def clubs_page():
        """Public clubs listing"""
        from app.models import Club
        
        clubs = Club.query.filter_by(is_active=True).all()
        return render_template('clubs.html', clubs=clubs)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500
    
    return app