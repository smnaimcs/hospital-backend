from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, UserRole, Staff, Attendance, LeaveRequest, LeaveStatus, LeaveType
from app.utils.auth import get_current_user, require_roles
from app.extensions import db
from datetime import datetime, date

staff_bp = Blueprint('staff', __name__)

# ==================== ATTENDANCE MANAGEMENT ====================

@staff_bp.route('/attendance/check-in', methods=['POST'])
@jwt_required()
@require_roles(UserRole.NURSE, UserRole.LAB_TECHNICIAN, UserRole.STAFF, UserRole.PHARMACIST)
def check_in():
    try:
        user = get_current_user()
        today = date.today()
        
        # Check if already checked in today
        existing_attendance = Attendance.query.filter_by(
            staff_id=user.staff.id,
            date=today
        ).first()
        
        if existing_attendance:
            return jsonify({'message': 'Already checked in for today'}), 400
        
        attendance = Attendance(
            staff_id=user.staff.id,
            date=today,
            check_in=datetime.utcnow(),
            status='present'
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({
            'message': 'Checked in successfully',
            'attendance': attendance.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to check in: {str(e)}'}), 500

@staff_bp.route('/attendance/check-out', methods=['POST'])
@jwt_required()
@require_roles(UserRole.NURSE, UserRole.LAB_TECHNICIAN, UserRole.STAFF, UserRole.PHARMACIST)
def check_out():
    try:
        user = get_current_user()
        today = date.today()
        
        attendance = Attendance.query.filter_by(
            staff_id=user.staff.id,
            date=today
        ).first()
        
        if not attendance:
            return jsonify({'message': 'No check-in record found for today'}), 400
        
        if attendance.check_out:
            return jsonify({'message': 'Already checked out for today'}), 400
        
        attendance.check_out = datetime.utcnow()
        
        # Calculate total hours
        if attendance.check_in:
            time_diff = attendance.check_out - attendance.check_in
            attendance.total_hours = round(time_diff.total_seconds() / 3600, 2)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Checked out successfully',
            'attendance': attendance.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to check out: {str(e)}'}), 500

@staff_bp.route('/attendance/history', methods=['GET'])
@jwt_required()
@require_roles(UserRole.NURSE, UserRole.LAB_TECHNICIAN, UserRole.STAFF, UserRole.PHARMACIST)
def get_attendance_history():
    try:
        user = get_current_user()
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = Attendance.query.filter_by(staff_id=user.staff.id)
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date).date()
            query = query.filter(Attendance.date >= start_dt)
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date).date()
            query = query.filter(Attendance.date <= end_dt)
        
        attendance_records = query.order_by(Attendance.date.desc()).all()
        
        return jsonify({
            'attendance': [record.to_dict() for record in attendance_records]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch attendance history: {str(e)}'}), 500

@staff_bp.route('/attendance/today', methods=['GET'])
@jwt_required()
@require_roles(UserRole.NURSE, UserRole.LAB_TECHNICIAN, UserRole.STAFF, UserRole.PHARMACIST)
def get_today_attendance():
    try:
        user = get_current_user()
        today = date.today()
        
        attendance = Attendance.query.filter_by(
            staff_id=user.staff.id,
            date=today
        ).first()
        
        return jsonify({
            'attendance': attendance.to_dict() if attendance else None
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch today\'s attendance: {str(e)}'}), 500

# ==================== LEAVE MANAGEMENT ====================

@staff_bp.route('/leave-requests', methods=['POST'])
@jwt_required()
@require_roles(UserRole.NURSE, UserRole.LAB_TECHNICIAN, UserRole.STAFF, UserRole.PHARMACIST)
def request_leave():
    try:
        user = get_current_user()
        data = request.get_json()
        
        required_fields = ['leave_type', 'start_date', 'end_date', 'reason']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        # Validate dates
        start_date = datetime.fromisoformat(data['start_date']).date()
        end_date = datetime.fromisoformat(data['end_date']).date()
        
        if start_date >= end_date:
            return jsonify({'message': 'Start date must be before end date'}), 400
        
        if start_date < date.today():
            return jsonify({'message': 'Start date cannot be in the past'}), 400
        
        # Check for overlapping leave requests
        overlapping_leave = LeaveRequest.query.filter(
            LeaveRequest.staff_id == user.staff.id,
            LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED]),
            ((LeaveRequest.start_date <= end_date) & (LeaveRequest.end_date >= start_date))
        ).first()
        
        if overlapping_leave:
            return jsonify({'message': 'You already have a leave request for this period'}), 400
        
        leave_request = LeaveRequest(
            staff_id=user.staff.id,
            leave_type=LeaveType(data['leave_type']),
            start_date=start_date,
            end_date=end_date,
            reason=data['reason'],
            status=LeaveStatus.PENDING
        )
        
        db.session.add(leave_request)
        db.session.commit()
        
        # Notify admin for approval
        from app.utils.notifications import create_notification
        admins = User.query.filter_by(role=UserRole.ADMIN).all()
        
        for admin in admins:
            create_notification(
                title="New Leave Request",
                message=f"{user.first_name} {user.last_name} has requested leave from {start_date} to {end_date}",
                receiver_id=admin.id,
                sender_id=user.id,
                notification_type="leave_request"
            )
        
        return jsonify({
            'message': 'Leave request submitted successfully',
            'leave_request': leave_request.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to submit leave request: {str(e)}'}), 500

@staff_bp.route('/leave-requests', methods=['GET'])
@jwt_required()
@require_roles(UserRole.NURSE, UserRole.LAB_TECHNICIAN, UserRole.STAFF, UserRole.PHARMACIST)
def get_leave_requests():
    try:
        user = get_current_user()
        status = request.args.get('status')
        
        query = LeaveRequest.query.filter_by(staff_id=user.staff.id)
        
        if status:
            query = query.filter_by(status=LeaveStatus(status))
        
        leave_requests = query.order_by(LeaveRequest.created_at.desc()).all()
        
        return jsonify({
            'leave_requests': [request.to_dict() for request in leave_requests]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch leave requests: {str(e)}'}), 500

@staff_bp.route('/leave-requests/<int:request_id>/cancel', methods=['PUT'])
@jwt_required()
@require_roles(UserRole.NURSE, UserRole.LAB_TECHNICIAN, UserRole.STAFF, UserRole.PHARMACIST)
def cancel_leave_request(request_id):
    try:
        user = get_current_user()
        leave_request = LeaveRequest.query.filter_by(
            id=request_id,
            staff_id=user.staff.id
        ).first()
        
        if not leave_request:
            return jsonify({'message': 'Leave request not found'}), 404
        
        if leave_request.status != LeaveStatus.PENDING:
            return jsonify({'message': 'Only pending leave requests can be cancelled'}), 400
        
        leave_request.status = LeaveStatus.CANCELLED
        db.session.commit()
        
        return jsonify({
            'message': 'Leave request cancelled successfully',
            'leave_request': leave_request.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to cancel leave request: {str(e)}'}), 500

# ==================== ADMIN LEAVE MANAGEMENT ====================

@staff_bp.route('/admin/leave-requests', methods=['GET'])
@jwt_required()
@require_roles(UserRole.ADMIN)
def get_all_leave_requests():
    try:
        status = request.args.get('status')
        staff_type = request.args.get('staff_type')
        
        query = LeaveRequest.query.join(Staff).join(User)
        
        if status:
            query = query.filter(LeaveRequest.status == LeaveStatus(status))
        
        if staff_type:
            query = query.filter(Staff.staff_type == staff_type)
        
        leave_requests = query.order_by(LeaveRequest.created_at.desc()).all()
        
        return jsonify({
            'leave_requests': [request.to_dict() for request in leave_requests]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch leave requests: {str(e)}'}), 500

@staff_bp.route('/admin/leave-requests/<int:request_id>/approve', methods=['PUT'])
@jwt_required()
@require_roles(UserRole.ADMIN)
def approve_leave_request(request_id):
    try:
        admin_user = get_current_user()
        leave_request = LeaveRequest.query.get(request_id)
        
        if not leave_request:
            return jsonify({'message': 'Leave request not found'}), 404
        
        if leave_request.status != LeaveStatus.PENDING:
            return jsonify({'message': 'Only pending leave requests can be approved'}), 400
        
        leave_request.status = LeaveStatus.APPROVED
        leave_request.approved_by = admin_user.id
        leave_request.comments = request.get_json().get('comments', '')
        
        db.session.commit()
        
        # Notify staff member
        from app.utils.notifications import create_notification
        create_notification(
            title="Leave Request Approved",
            message=f"Your leave request from {leave_request.start_date} to {leave_request.end_date} has been approved",
            receiver_id=leave_request.staff.user.id,
            sender_id=admin_user.id,
            notification_type="leave_request"
        )
        
        return jsonify({
            'message': 'Leave request approved successfully',
            'leave_request': leave_request.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to approve leave request: {str(e)}'}), 500

@staff_bp.route('/admin/leave-requests/<int:request_id>/reject', methods=['PUT'])
@jwt_required()
@require_roles(UserRole.ADMIN)
def reject_leave_request(request_id):
    try:
        admin_user = get_current_user()
        leave_request = LeaveRequest.query.get(request_id)
        
        if not leave_request:
            return jsonify({'message': 'Leave request not found'}), 404
        
        if leave_request.status != LeaveStatus.PENDING:
            return jsonify({'message': 'Only pending leave requests can be rejected'}), 400
        
        leave_request.status = LeaveStatus.REJECTED
        leave_request.approved_by = admin_user.id
        leave_request.comments = request.get_json().get('comments', '')
        
        db.session.commit()
        
        # Notify staff member
        from app.utils.notifications import create_notification
        create_notification(
            title="Leave Request Rejected",
            message=f"Your leave request from {leave_request.start_date} to {leave_request.end_date} has been rejected",
            receiver_id=leave_request.staff.user.id,
            sender_id=admin_user.id,
            notification_type="leave_request"
        )
        
        return jsonify({
            'message': 'Leave request rejected successfully',
            'leave_request': leave_request.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to reject leave request: {str(e)}'}), 500