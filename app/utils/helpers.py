"""
Helper utility functions
"""
import os
import secrets
import string
from werkzeug.utils import secure_filename
from flask import current_app
from app import db

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_uploaded_file(file, subfolder='events'):
    """Save uploaded file and return URL"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        random_hex = secrets.token_hex(8)
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{random_hex}{ext}"
        
        folder = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(folder, exist_ok=True)
        
        filepath = os.path.join(folder, filename)
        file.save(filepath)
        
        return f"/static/uploads/{subfolder}/{filename}"
    return None

def generate_password(length=12):
    """Generate secure random password"""
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(chars) for _ in range(length))

def send_notification(student_id, title, message, notification_type, event_id=None):
    """Create notification for student"""
    from app.models import Notification
    
    notification = Notification(
        student_id=student_id,
        title=title,
        message=message,
        notification_type=notification_type,
        event_id=event_id
    )
    db.session.add(notification)
    db.session.commit()
    return notification

def send_bulk_notification(title, message, notification_type='announcement'):
    """Send notification to all active students"""
    from app.models import Student, Notification
    
    students = Student.query.filter_by(is_active=True).all()
    
    for student in students:
        notification = Notification(
            student_id=student.id,
            title=title,
            message=message,
            notification_type=notification_type
        )
        db.session.add(notification)
    
    db.session.commit()
    return len(students)