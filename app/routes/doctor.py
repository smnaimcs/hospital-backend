from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, UserRole, Doctor, Appointment, Diagnosis, Prescription, TestReport, Availability, Patient, MedicalRecord
from app.utils.auth import get_current_user, require_roles
from app.extensions import db
from datetime import datetime, time

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.route('/appointments', methods=['GET'])
@jwt_required()
@require_roles(UserRole.DOCTOR)
def get_doctor_appointments():
    try:
        user = get_current_user()
        status = request.args.get('status')
        date = request.args.get('date')
        
        query = Appointment.query.filter_by(doctor_id=user.doctor.id)
        
        if status:
            from app.models.appointment import AppointmentStatus
            query = query.filter_by(status=AppointmentStatus(status))
        
        if date:
            date_obj = datetime.fromisoformat(date).date()
            query = query.filter(db.func.date(Appointment.appointment_date) == date_obj)
        
        appointments = query.order_by(Appointment.appointment_date).all()
        
        return jsonify({
            'appointments': [appointment.to_dict() for appointment in appointments]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch appointments: {str(e)}'}), 500

@doctor_bp.route('/availability', methods=['POST'])
@jwt_required()
@require_roles(UserRole.DOCTOR)
def add_availability():
    try:
        user = get_current_user()
        data = request.get_json()
        
        required_fields = ['day_of_week', 'start_time', 'end_time']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        availability = Availability(
            doctor_id=user.doctor.id,
            day_of_week=data['day_of_week'],
            start_time=time.fromisoformat(data['start_time']),
            end_time=time.fromisoformat(data['end_time']),
            is_recurring=data.get('is_recurring', True),
            specific_date=datetime.fromisoformat(data['specific_date']).date() if data.get('specific_date') else None
        )
        
        db.session.add(availability)
        db.session.commit()
        
        return jsonify({
            'message': 'Availability added successfully',
            'availability': availability.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to add availability: {str(e)}'}), 500

@doctor_bp.route('/diagnosis', methods=['POST'])
@jwt_required()
@require_roles(UserRole.DOCTOR)
def add_diagnosis():
    try:
        user = get_current_user()
        data = request.get_json()
        
        required_fields = ['appointment_id', 'diagnosis', 'treatment_plan']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        # Check if appointment exists and belongs to this doctor
        appointment = Appointment.query.filter_by(
            id=data['appointment_id'],
            doctor_id=user.doctor.id
        ).first()
        
        if not appointment:
            return jsonify({'message': 'Appointment not found'}), 404
        
        diagnosis = Diagnosis(
            appointment_id=data['appointment_id'],
            doctor_id=user.doctor.id,
            diagnosis=data['diagnosis'],
            symptoms=data.get('symptoms'),
            treatment_plan=data['treatment_plan'],
            notes=data.get('notes'),
            follow_up_required=data.get('follow_up_required', False),
            follow_up_date=datetime.fromisoformat(data['follow_up_date']) if data.get('follow_up_date') else None
        )
        
        db.session.add(diagnosis)
        
        # Update appointment status to completed
        from app.models.appointment import AppointmentStatus
        appointment.status = AppointmentStatus.COMPLETED
        
        db.session.commit()
        
        return jsonify({
            'message': 'Diagnosis added successfully',
            'diagnosis': diagnosis.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to add diagnosis: {str(e)}'}), 500

@doctor_bp.route('/prescriptions', methods=['POST'])
@jwt_required()
@require_roles(UserRole.DOCTOR)
def prescribe_medicine():
    try:
        user = get_current_user()
        data = request.get_json()
        
        required_fields = ['appointment_id', 'medicine_name', 'dosage', 'duration']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        prescription = Prescription(
            appointment_id=data['appointment_id'],
            doctor_id=user.doctor.id,
            medicine_name=data['medicine_name'],
            dosage=data['dosage'],
            frequency=data.get('frequency'),
            duration=data['duration'],
            instructions=data.get('instructions')
        )
        
        db.session.add(prescription)
        db.session.commit()
        
        return jsonify({
            'message': 'Prescription added successfully',
            'prescription': prescription.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to add prescription: {str(e)}'}), 500

@doctor_bp.route('/patients/<int:patient_id>/medical-history')
@jwt_required()
@require_roles(UserRole.DOCTOR)
def get_patient_medical_history(patient_id):
    try:
        patient = Patient.query.get(patient_id)
        if not patient:
            return jsonify({'message': 'Patient not found'}), 404
        
        # Get medical records
        medical_records = MedicalRecord.query.filter_by(patient_id=patient_id).all()
        
        # Get previous diagnoses
        diagnoses = Diagnosis.query.join(Appointment).filter(
            Appointment.patient_id == patient_id
        ).all()
        
        # Get test reports
        test_reports = TestReport.query.join(Appointment).filter(
            Appointment.patient_id == patient_id
        ).all()
        #Get prescriptions
        prescriptions = Prescription.query.join(Appointment).filter(
            Appointment.patient_id == patient_id
        ).all()
        
        return jsonify({
            'patient': patient.to_dict(),
            'medical_records': [record.to_dict() for record in medical_records],
            'diagnoses': [diagnosis.to_dict() for diagnosis in diagnoses],
            'test_reports': [report.to_dict() for report in test_reports],
            'prescriptions': [prescription.to_dict() for prescription in prescriptions]

        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch medical history: {str(e)}'}), 500