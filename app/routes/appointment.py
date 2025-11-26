from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Appointment, AppointmentStatus, User, UserRole
from app.utils.auth import get_current_user
from app.extensions import db
from datetime import datetime

appointment_bp = Blueprint('appointment', __name__)

@appointment_bp.route('/', methods=['GET'])
@jwt_required()
def get_appointments():
    try:
        user = get_current_user()
        status = request.args.get('status')
        date = request.args.get('date')
        
        if user.role == UserRole.PATIENT:
            query = Appointment.query.filter_by(patient_id=user.patient.id)
        elif user.role == UserRole.DOCTOR:
            query = Appointment.query.filter_by(doctor_id=user.doctor.id)
        elif user.role == UserRole.ADMIN:
            query = Appointment.query
        else:
            return jsonify({'message': 'Unauthorized access'}), 403
        
        if status:
            query = query.filter_by(status=AppointmentStatus(status))
        
        if date:
            date_obj = datetime.fromisoformat(date).date()
            query = query.filter(db.func.date(Appointment.appointment_date) == date_obj)
        
        appointments = query.order_by(Appointment.appointment_date.desc()).all()
        
        return jsonify({
            'appointments': [appointment.to_dict() for appointment in appointments]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch appointments: {str(e)}'}), 500

@appointment_bp.route('/<int:appointment_id>', methods=['GET'])
@jwt_required()
def get_appointment(appointment_id):
    try:
        user = get_current_user()
        appointment = Appointment.query.get(appointment_id)
        
        if not appointment:
            return jsonify({'message': 'Appointment not found'}), 404
        
        # Check authorization
        if user.role == UserRole.PATIENT and appointment.patient_id != user.patient.id:
            return jsonify({'message': 'Unauthorized access'}), 403
        elif user.role == UserRole.DOCTOR and appointment.doctor_id != user.doctor.id:
            return jsonify({'message': 'Unauthorized access'}), 403
        
        appointment_data = appointment.to_dict()
        
        # Add related data
        if appointment.diagnosis:
            appointment_data['diagnosis'] = appointment.diagnosis.to_dict()
        
        if appointment.prescriptions:
            appointment_data['prescriptions'] = [presc.to_dict() for presc in appointment.prescriptions]
        
        if appointment.test_reports:
            appointment_data['test_reports'] = [report.to_dict() for report in appointment.test_reports]
        
        return jsonify({'appointment': appointment_data}), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch appointment: {str(e)}'}), 500

@appointment_bp.route('/<int:appointment_id>/status', methods=['PUT'])
@jwt_required()
def update_appointment_status(appointment_id):
    try:
        user = get_current_user()
        appointment = Appointment.query.get(appointment_id)
        
        if not appointment:
            return jsonify({'message': 'Appointment not found'}), 404
        
        data = request.get_json()
        if 'status' not in data:
            return jsonify({'message': 'Status is required'}), 400
        
        new_status = AppointmentStatus(data['status'])
        old_status = appointment.status
        
        # Authorization checks
        if user.role == UserRole.PATIENT:
            if appointment.patient_id != user.patient.id:
                return jsonify({'message': 'Unauthorized access'}), 403
            # Patients can only cancel their own appointments
            if new_status != AppointmentStatus.CANCELLED:
                return jsonify({'message': 'Patients can only cancel appointments'}), 403
        
        elif user.role == UserRole.DOCTOR:
            if appointment.doctor_id != user.doctor.id:
                return jsonify({'message': 'Unauthorized access'}), 403
            # Doctors can confirm or complete appointments
            if new_status not in [AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED]:
                return jsonify({'message': 'Doctors can only confirm or complete appointments'}), 403
        
        elif user.role != UserRole.ADMIN:
            return jsonify({'message': 'Unauthorized access'}), 403
        
        appointment.status = new_status
        db.session.commit()
        
        # Send notifications
        from app.utils.notifications import notify_appointment_status
        notify_appointment_status(appointment, old_status)
        
        return jsonify({
            'message': 'Appointment status updated successfully',
            'appointment': appointment.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to update appointment status: {str(e)}'}), 500

@appointment_bp.route('/<int:appointment_id>/reschedule', methods=['PUT'])
@jwt_required()
def reschedule_appointment(appointment_id):
    try:
        user = get_current_user()
        appointment = Appointment.query.get(appointment_id)
        
        if not appointment:
            return jsonify({'message': 'Appointment not found'}), 404
        
        data = request.get_json()
        if 'appointment_date' not in data:
            return jsonify({'message': 'New appointment date is required'}), 400
        
        # Authorization checks
        if user.role == UserRole.PATIENT:
            if appointment.patient_id != user.patient.id:
                return jsonify({'message': 'Unauthorized access'}), 403
        elif user.role == UserRole.DOCTOR:
            if appointment.doctor_id != user.doctor.id:
                return jsonify({'message': 'Unauthorized access'}), 403
        elif user.role != UserRole.ADMIN:
            return jsonify({'message': 'Unauthorized access'}), 403
        
        old_date = appointment.appointment_date
        appointment.appointment_date = datetime.fromisoformat(data['appointment_date'])
        appointment.status = AppointmentStatus.RESCHEDULED
        
        db.session.commit()
        
        # Notify both parties
        from app.utils.notifications import create_notification
        
        # Notify patient
        create_notification(
            title="Appointment Rescheduled",
            message=f"Your appointment with Dr. {appointment.doctor.user.last_name} has been rescheduled",
            receiver_id=appointment.patient.user.id,
            sender_id=user.id,
            notification_type="appointment"
        )
        
        # Notify doctor
        create_notification(
            title="Appointment Rescheduled",
            message=f"Appointment with {appointment.patient.user.first_name} has been rescheduled",
            receiver_id=appointment.doctor.user.id,
            sender_id=user.id,
            notification_type="appointment"
        )
        
        return jsonify({
            'message': 'Appointment rescheduled successfully',
            'appointment': appointment.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to reschedule appointment: {str(e)}'}), 500