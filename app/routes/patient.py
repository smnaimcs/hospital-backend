from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, UserRole, Patient, Doctor, Appointment, MedicalRecord, Bill, AppointmentHistory
from app.utils.auth import get_current_user, require_roles
from app.extensions import db
from datetime import datetime
from functools import wraps

patient_bp = Blueprint('patient', __name__)

@patient_bp.route('/doctors', methods=['GET'])
@jwt_required()
def get_doctors():
    try:
        # Get query parameters
        search = request.args.get('search', '')
        specialization = request.args.get('specialization', '')
        
        query = Doctor.query.join(User).filter(User.is_active == True)
        
        if search:
            query = query.filter(
                db.or_(
                    User.first_name.ilike(f'%{search}%'),
                    User.last_name.ilike(f'%{search}%'),
                    Doctor.specialization.ilike(f'%{search}%')
                )
            )
        
        if specialization:
            query = query.filter(Doctor.specialization.ilike(f'%{specialization}%'))
        
        doctors = query.all()
        
        return jsonify({
            'doctors': [doctor.to_dict() for doctor in doctors]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch doctors: {str(e)}'}), 500

@patient_bp.route('/appointments', methods=['POST'])
@jwt_required()
@require_roles(UserRole.PATIENT)
def request_appointment():
    try:
        user = get_current_user()
        data = request.get_json()
        
        required_fields = ['doctor_id', 'appointment_date', 'reason']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        # Check if doctor exists and is available
        doctor = Doctor.query.get(data['doctor_id'])
        if not doctor or not doctor.is_available:
            return jsonify({'message': 'Doctor not available'}), 400
        
        # Create appointment
        appointment = Appointment(
            patient_id=user.patient.id,
            doctor_id=data['doctor_id'],
            appointment_date=datetime.fromisoformat(data['appointment_date']),
            reason=data['reason'],
            symptoms=data.get('symptoms')
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        # Create notification for doctor
        from app.utils.notifications import create_notification
        create_notification(
            title="New Appointment Request",
            message=f"New appointment request from {user.first_name} {user.last_name}",
            receiver_id=doctor.user.id,
            notification_type="appointment"
        )
        
        return jsonify({
            'message': 'Appointment requested successfully',
            'appointment': appointment.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to request appointment: {str(e)}'}), 500

@patient_bp.route('/appointments', methods=['GET'])
@jwt_required()
@require_roles(UserRole.PATIENT)
def get_patient_appointments():
    try:
        user = get_current_user()
        status = request.args.get('status')
        
        query = Appointment.query.filter_by(patient_id=user.patient.id)
        
        if status:
            from app.models.appointment import AppointmentStatus
            query = query.filter_by(status=AppointmentStatus(status))
        
        appointments = query.order_by(Appointment.appointment_date.desc()).all()
        
        return jsonify({
            'appointments': [appointment.to_dict() for appointment in appointments]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch appointments: {str(e)}'}), 500

@patient_bp.route('/appointments/<int:appointment_id>/cancel', methods=['PUT'])
@jwt_required()
@require_roles(UserRole.PATIENT)
def cancel_appointment(appointment_id):
    try:
        user = get_current_user()
        appointment = Appointment.query.filter_by(
            id=appointment_id, 
            patient_id=user.patient.id
        ).first()
        
        if not appointment:
            return jsonify({'message': 'Appointment not found'}), 404
        
        from app.models.appointment import AppointmentStatus
        appointment.status = AppointmentStatus.CANCELLED
        db.session.commit()
        
        # Notify doctor
        from app.utils.notifications import create_notification
        create_notification(
            title="Appointment Cancelled",
            message=f"Appointment with {user.first_name} {user.last_name} has been cancelled",
            receiver_id=appointment.doctor.user.id,
            sender_id=user.id,
            notification_type="appointment"
        )
        
        return jsonify({
            'message': 'Appointment cancelled successfully',
            'appointment': appointment.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to cancel appointment: {str(e)}'}), 500

@patient_bp.route('/medical-records', methods=['GET'])
@jwt_required()
@require_roles(UserRole.PATIENT)
def get_medical_records():
    try:
        user = get_current_user()
        records = MedicalRecord.query.filter_by(patient_id=user.patient.id).all()
        
        return jsonify({
            'medical_records': [record.to_dict() for record in records]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch medical records: {str(e)}'}), 500

@patient_bp.route('/bills', methods=['GET'])
@jwt_required()
@require_roles(UserRole.PATIENT, UserRole.ADMIN)
def get_bills():
    try:
        user = get_current_user()
        status = request.args.get('status')

        # Admin sees ALL bills
        if user.role == UserRole.ADMIN:
            query = Bill.query
        else:
            # Patient sees only their own bills
            query = Bill.query.filter_by(patient_id=user.patient.id)

        # Optional filtering by status
        if status:
            query = query.filter_by(status=status)

        bills = query.order_by(Bill.created_at.desc()).all()

        return jsonify({
            'bills': [bill.to_dict() for bill in bills]
        }), 200

    except Exception as e:
        return jsonify({'message': f'Failed to fetch bills: {str(e)}'}), 500
