"""Create first admin user"""
from app import create_app, db
from app.models import Admin

app = create_app()

with app.app_context():
    # Check if admin exists
    existing = Admin.query.filter_by(username='admin').first()
    
    if existing:
        print("❌ Admin already exists!")
        print(f"Username: {existing.username}")
    else:
        # Create admin
        admin = Admin(
            username='admin',
            email='admin@campus.edu'
        )
        admin.set_password('admin123')
        
        db.session.add(admin)
        db.session.commit()
        
        print("✅ Admin created successfully!")
        print("=" * 40)
        print(f"Username: admin")
        print(f"Password: admin123")
        print("=" * 40)
        print("⚠️  Change password after first login!")