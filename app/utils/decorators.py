"""
Role-based access control decorators
"""
from functools import wraps
from flask import redirect, url_for, flash, abort
from flask_login import current_user

def student_required(f):
    """Require student role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('auth.login', role='student'))
        
        if current_user.__class__.__name__ != 'Student':
            flash('Access denied. Students only.', 'danger')
            abort(403)
        
        if not current_user.is_active:
            flash('Your account has been deactivated.', 'danger')
            return redirect(url_for('auth.logout'))
        
        return f(*args, **kwargs)
    return decorated_function

def club_required(f):
    """Require club role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('auth.login', role='club'))
        
        if current_user.__class__.__name__ != 'Club':
            flash('Access denied. Clubs only.', 'danger')
            abort(403)
        
        if not current_user.is_active:
            flash('Your account has been deactivated.', 'danger')
            return redirect(url_for('auth.logout'))
        
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('auth.login', role='admin'))
        
        if current_user.__class__.__name__ != 'Admin':
            flash('Access denied. Admins only.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function