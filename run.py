"""
Campus Event Management System
Single entry point - runs entire application
"""
from app import create_app, db

# Create Flask application
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Create all database tables
        db.create_all()
        print("✅ Database tables created successfully!")
        print("=" * 60)
        print("🚀 Campus Event Management System")
        print("=" * 60)
        print("📍 Running on: http://localhost:5000")
        print("📝 Admin Login: http://localhost:5000/login?role=admin")
        print("🎓 Student Registration: http://localhost:5000/register")
        print("=" * 60)
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True
    )