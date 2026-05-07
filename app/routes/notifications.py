"""
Notifications Routes
- Get notifications (with pagination)
- Mark as read
- Get unread count
"""
from flask import Blueprint, jsonify, request
from flask_login import current_user
from app import db
from app.models import Notification
from app.utils.decorators import student_required

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/api/list')
@student_required
def get_notifications():
    """Get notifications for current student"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    notifications = Notification.query.filter_by(
        student_id=current_user.id
    ).order_by(Notification.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'notifications': [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.notification_type,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat(),
            'event_id': n.event_id
        } for n in notifications.items],
        'total': notifications.total,
        'pages': notifications.pages,
        'current_page': page
    })

@notifications_bp.route('/api/unread-count')
@student_required
def unread_count():
    """Get unread notification count"""
    count = Notification.query.filter_by(
        student_id=current_user.id,
        is_read=False
    ).count()
    
    return jsonify({'count': count})

@notifications_bp.route('/api/<int:notif_id>/read', methods=['POST'])
@student_required
def mark_read(notif_id):
    """Mark notification as read"""
    notification = Notification.query.get_or_404(notif_id)
    
    if notification.student_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})

@notifications_bp.route('/api/mark-all-read', methods=['POST'])
@student_required
def mark_all_read():
    """Mark all notifications as read"""
    Notification.query.filter_by(
        student_id=current_user.id,
        is_read=False
    ).update({'is_read': True})
    
    db.session.commit()
    
    return jsonify({'success': True})