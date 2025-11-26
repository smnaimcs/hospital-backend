from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, UserRole, Patient, Doctor, Staff, Appointment, Notification
from app.utils.auth import get_current_user, require_roles
from app.extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required()
@require_roles(UserRole.ADMIN)
def get_dashboard_stats():
    try:
        # Total counts
        total_patients = Patient.query.count()
        total_doctors = Doctor.query.count()
        total_staff = Staff.query.count()
        
        # Today's appointments
        today = datetime.now().date()
        today_appointments = Appointment.query.filter(
            func.date(Appointment.appointment_date) == today
        ).count()
        
        # Pending appointments
        from app.models.appointment import AppointmentStatus
        pending_appointments = Appointment.query.filter_by(
            status=AppointmentStatus.PENDING
        ).count()
        
        # Recent appointments (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recent_appointments = Appointment.query.filter(
            Appointment.created_at >= week_ago
        ).count()
        
        # Revenue stats (you would integrate with your billing system)
        total_revenue = 0  # Placeholder - implement based on your billing
        
        return jsonify({
            'total_patients': total_patients,
            'total_doctors': total_doctors,
            'total_staff': total_staff,
            'today_appointments': today_appointments,
            'pending_appointments': pending_appointments,
            'recent_appointments': recent_appointments,
            'total_revenue': total_revenue
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch dashboard stats: {str(e)}'}), 500

@admin_bp.route('/users', methods=['GET'])
@jwt_required()
@require_roles(UserRole.ADMIN)
def get_all_users():
    try:
        role = request.args.get('role')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = User.query
        
        if role:
            query = query.filter_by(role=UserRole(role))
        
        users = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch users: {str(e)}'}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
@require_roles(UserRole.ADMIN)
def update_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update user fields
        updatable_fields = ['first_name', 'last_name', 'phone', 'address', 'date_of_birth', 'gender', 'is_active']
        for field in updatable_fields:
            if field in data:
                setattr(user, field, data[field])
        
        # Update role-specific fields
        if user.role == UserRole.DOCTOR and user.doctor:
            doctor_fields = ['specialization', 'years_of_experience', 'qualification', 'consultation_fee', 'is_available']
            for field in doctor_fields:
                if field in data:
                    setattr(user.doctor, field, data[field])
        
        elif user.role == UserRole.PATIENT and user.patient:
            patient_fields = ['blood_group', 'emergency_contact', 'insurance_info']
            for field in patient_fields:
                if field in data:
                    setattr(user.patient, field, data[field])
        
        elif user.staff:
            staff_fields = ['department', 'salary', 'shift', 'is_active']
            for field in staff_fields:
                if field in data:
                    setattr(user.staff, field, data[field])
        
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to update user: {str(e)}'}), 500

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@require_roles(UserRole.ADMIN)
def delete_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        # Soft delete by deactivating
        user.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'User deactivated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to deactivate user: {str(e)}'}), 500

@admin_bp.route('/appointments', methods=['GET'])
@jwt_required()
@require_roles(UserRole.ADMIN)
def get_all_appointments():
    try:
        status = request.args.get('status')
        date = request.args.get('date')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = Appointment.query
        
        if status:
            from app.models.appointment import AppointmentStatus
            query = query.filter_by(status=AppointmentStatus(status))
        
        if date:
            date_obj = datetime.fromisoformat(date).date()
            query = query.filter(func.date(Appointment.appointment_date) == date_obj)
        
        appointments = query.order_by(Appointment.appointment_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'appointments': [appointment.to_dict() for appointment in appointments.items],
            'total': appointments.total,
            'pages': appointments.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch appointments: {str(e)}'}), 500

@admin_bp.route('/appointments/<int:appointment_id>', methods=['PUT'])
@jwt_required()
@require_roles(UserRole.ADMIN)
def update_appointment(appointment_id):
    try:
        appointment = Appointment.query.get(appointment_id)
        if not appointment:
            return jsonify({'message': 'Appointment not found'}), 404
        
        data = request.get_json()
        
        from app.models.appointment import AppointmentStatus
        old_status = appointment.status
        
        # Update appointment fields
        if 'status' in data:
            appointment.status = AppointmentStatus(data['status'])
        
        if 'appointment_date' in data:
            appointment.appointment_date = datetime.fromisoformat(data['appointment_date'])
        
        if 'duration' in data:
            appointment.duration = data['duration']
        
        db.session.commit()
        
        # Send notifications if status changed
        if 'status' in data and old_status != appointment.status:
            from app.utils.notifications import notify_appointment_status
            notify_appointment_status(appointment, old_status)
        
        return jsonify({
            'message': 'Appointment updated successfully',
            'appointment': appointment.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to update appointment: {str(e)}'}), 500

@admin_bp.route('/doctor-availability', methods=['GET'])
@jwt_required()
@require_roles(UserRole.ADMIN)
def get_doctor_availability():
    try:
        doctor_id = request.args.get('doctor_id')
        date = request.args.get('date')
        
        query = Doctor.query.filter_by(is_available=True)
        
        if doctor_id:
            query = query.filter_by(id=doctor_id)
        
        doctors = query.all()
        
        availability_data = []
        for doctor in doctors:
            doctor_avail = doctor.to_dict()
            doctor_avail['availabilities'] = [avail.to_dict() for avail in doctor.availabilities]
            availability_data.append(doctor_avail)
        
        return jsonify({
            'doctors': availability_data
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch doctor availability: {str(e)}'}), 500

@admin_bp.route('/notifications', methods=['GET'])
@jwt_required()
@require_roles(UserRole.ADMIN)
def get_all_notifications():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        notifications = Notification.query.order_by(Notification.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'notifications': [notification.to_dict() for notification in notifications.items],
            'total': notifications.total,
            'pages': notifications.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch notifications: {str(e)}'}), 500

@admin_bp.route('/notifications', methods=['POST'])
@jwt_required()
@require_roles(UserRole.ADMIN)
def send_notification():
    try:
        data = request.get_json()
        
        required_fields = ['title', 'message', 'receiver_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        from app.utils.notifications import create_notification
        notification = create_notification(
            title=data['title'],
            message=data['message'],
            receiver_id=data['receiver_id'],
            sender_id=get_jwt_identity(),
            notification_type=data.get('notification_type', 'admin')
        )
        
        return jsonify({
            'message': 'Notification sent successfully',
            'notification': notification.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'message': f'Failed to send notification: {str(e)}'}), 500