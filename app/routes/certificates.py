from flask import Blueprint, send_file
from flask_login import login_required, current_user
from app.utils.decorators import student_required
from app.models import Event, EventRegistration, EventResult
from io import BytesIO
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime

certificates_bp = Blueprint('certificates', __name__, url_prefix='/certificates')

@certificates_bp.route('/participation/<int:event_id>')
@student_required
def participation(event_id):
    """Generate participation certificate"""
    event = Event.query.get_or_404(event_id)
    
    # Check if student participated
    registration = EventRegistration.query.filter_by(
        student_id=current_user.id,
        event_id=event_id,
        attendance_marked=True
    ).first()
    
    if not registration:
        from flask import flash, redirect, url_for
        flash('You did not participate in this event', 'danger')
        return redirect(url_for('students.my_registrations'))
    
    # Generate PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)
    
    # Border
    c.setStrokeColor(colors.HexColor('#2563eb'))
    c.setLineWidth(3)
    c.rect(0.5*inch, 0.5*inch, width-inch, height-inch)
    
    # Title
    c.setFont("Helvetica-Oblique", 12)
    c.setFillColor(colors.HexColor('#2563eb'))
    c.drawCentredString(width/2, height-2*inch, "CERTIFICATE OF PARTICIPATION")
    
    # Subtitle
    c.setFont("Helvetica", 16)
    c.setFillColor(colors.black)
    c.drawCentredString(width/2, height-2.7*inch, "This is to certify that")
    
    # Student name
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(colors.HexColor('#8b5cf6'))
    c.drawCentredString(width/2, height-3.5*inch, current_user.name)
    
    # Event details
    c.setFont("Helvetica", 16)
    c.setFillColor(colors.black)
    c.drawCentredString(width/2, height-4.2*inch, f'has successfully participated in')
    
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(colors.HexColor('#2563eb'))
    c.drawCentredString(width/2, height-4.8*inch, event.title)
    
    # Organized by
    c.setFont("Helvetica", 14)
    c.setFillColor(colors.black)
    c.drawCentredString(width/2, height-5.4*inch, f'Organized by {event.club.name}')
    c.drawCentredString(width/2, height-5.8*inch, 
                       f'on {event.event_date.strftime("%B %d, %Y")}')
    
    # Date of issue
    # Date of issue
    c.setFont("Helvetica-Oblique", 12)
    c.setFillColor(colors.black)
    c.drawCentredString(width/2, 1.5*inch, 
                    f'Issued on: {datetime.now().strftime("%B %d, %Y")}')
    
    c.save()
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'participation_{event.title.replace(" ", "_")}.pdf',
        mimetype='application/pdf'
    )


@certificates_bp.route('/winner/<int:result_id>')
@student_required
def winner(result_id):
    """Generate winner certificate"""
    result = EventResult.query.get_or_404(result_id)
    
    # Check if this is the current user's result
    if result.student_id != current_user.id:
        from flask import flash, redirect, url_for
        flash('Invalid certificate request', 'danger')
        return redirect(url_for('students.my_registrations'))
    
    event = result.event
    
    # Position colors
    position_colors = {
        1: '#ffd700',  # Gold
        2: '#c0c0c0',  # Silver
        3: '#cd7f32'   # Bronze
    }
    
    position_names = {
        1: 'FIRST POSITION',
        2: 'SECOND POSITION',
        3: 'THIRD POSITION'
    }
    
    # Generate PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)
    
    # Border with position color
    c.setStrokeColor(colors.HexColor(position_colors.get(result.position, '#2563eb')))
    c.setLineWidth(4)
    c.rect(0.5*inch, 0.5*inch, width-inch, height-inch)
    
    # Medal emoji equivalent (using text)
    medals = {1: '🥇', 2: '🥈', 3: '🥉'}
    c.setFont("Helvetica-Bold", 48)
    c.setFillColor(colors.HexColor(position_colors.get(result.position, '#2563eb')))
    c.drawCentredString(width/2, height-1.5*inch, medals.get(result.position, '🏆'))
    
    # Title
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(width/2, height-2.2*inch, "CERTIFICATE OF ACHIEVEMENT")
    
    # Position
    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(colors.HexColor(position_colors.get(result.position, '#2563eb')))
    c.drawCentredString(width/2, height-2.8*inch, position_names.get(result.position, 'WINNER'))
    
    # Student name
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(colors.black)
    c.drawCentredString(width/2, height-3.6*inch, current_user.name)
    
    # Event details
    c.setFont("Helvetica", 16)
    c.drawCentredString(width/2, height-4.2*inch, 
                       f'secured {position_names.get(result.position, "a position")} in')
    
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(colors.HexColor('#2563eb'))
    c.drawCentredString(width/2, height-4.8*inch, event.title)
    
    # Organized by
    c.setFont("Helvetica", 14)
    c.setFillColor(colors.black)
    c.drawCentredString(width/2, height-5.4*inch, f'Organized by {event.club.name}')
    c.drawCentredString(width/2, height-5.8*inch, 
                       f'on {event.event_date.strftime("%B %d, %Y")}')
    
    # Prize (if any)
    if result.prize:
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.HexColor('#10b981'))
        c.drawCentredString(width/2, height-6.3*inch, f'Prize: {result.prize}')
    
    # Date of issue
    c.setFont("Helvetica-Oblique", 12)
    c.setFillColor(colors.black)
    c.drawCentredString(width/2, 1.5*inch, 
                       f'Issued on: {datetime.now().strftime("%B %d, %Y")}')
    
    c.save()
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'winner_{event.title.replace(" ", "_")}_position_{result.position}.pdf',
        mimetype='application/pdf'
    )