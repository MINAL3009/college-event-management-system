"""
Authentication Routes
- Student Registration
- Universal Login (Student/Club/Admin)
- Logout
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from app import db
from app.models import Student, Club, Admin

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Student registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        branch = request.form.get('branch', '').strip()
        year = request.form.get('year', '').strip()
        division = request.form.get('division', '').strip()
        
        # Validation
        errors = []
        if not all([name, email, password, branch, year, division]):
            errors.append('All fields are required')
        
        if len(password) < 8:
            errors.append('Password must be at least 8 characters')
        
        # Check if email exists
        if Student.query.filter_by(email=email).first():
            errors.append('Email already registered')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/register.html')
        
        # Create student
        student = Student(
            name=name,
            email=email,
            branch=branch,
            year=year,
            division=division
        )
        student.set_password(password)
        
        db.session.add(student)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login', role='student'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Universal login page for Student/Club/Admin"""
    if current_user.is_authenticated:
        # Redirect to appropriate dashboard
        user_type = current_user.__class__.__name__.lower()
        return redirect(url_for(f'{user_type}s.dashboard'))
    
    role = request.args.get('role', 'student')  # student, club, or admin
    
    if request.method == 'POST':
        role = request.form.get('role', 'student')
        identifier = request.form.get('identifier', '').strip()  # email or username
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        user = None
        
        # Find user based on role
        if role == 'student':
            user = Student.query.filter_by(email=identifier).first()
        elif role == 'club':
            user = Club.query.filter_by(username=identifier).first()
        elif role == 'admin':
            user = Admin.query.filter_by(username=identifier).first()
        
        # Validate credentials
        if not user or not user.check_password(password):
            flash('Invalid credentials', 'danger')
            return render_template('auth/login.html', role=role)
        
        # Check if account is active (for students and clubs)
        if hasattr(user, 'is_active') and not user.is_active:
            flash('Your account has been deactivated. Contact admin.', 'danger')
            return render_template('auth/login.html', role=role)
        
        # Login user
        login_user(user, remember=remember)
        
        # Redirect to appropriate dashboard
        user_type = user.__class__.__name__.lower()
        flash(f'Welcome back, {user.name if hasattr(user, "name") else user.username}!', 'success')
        
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        
        return redirect(url_for(f'{user_type}s.dashboard'))
    
    return render_template('auth/login.html', role=role)

@auth_bp.route('/logout')
def logout():
    """Logout current user"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))