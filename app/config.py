"""Application Configuration"""
import os
from datetime import timedelta

class Config:
    """Configuration class"""
    
    # Secret key
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-2024'
    
    # Database - CHANGE 'password' TO YOUR MYSQL PASSWORD
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://root:Minal@localhost:3306/campus_events'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File uploads
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    GALLERY_FOLDER = os.path.join(BASE_DIR, 'static', 'images', 'gallery')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Event types
    EVENT_TYPES = [
        'Cultural', 'Sports', 'Technical', 'Cybersecurity',
        'Robotics', 'Workshop', 'Seminar', 'Competition', 'Other'
    ]
    
    # Academic
    ACADEMIC_YEARS = ['FY', 'SY', 'TY', 'Final Year']
    BRANCHES = [
        'Computer Engineering', 'Information Technology',
        'Electronics', 'Mechanical', 'Civil', 'Electrical', 'Other'
    ]
    
    # Validation
    PASSWORD_MIN_LENGTH = 8
    MAX_PENDING_REQUESTS = 5
    EVENT_TIME_BUFFER_MINUTES = 30