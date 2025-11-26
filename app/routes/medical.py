from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, UserRole, TestReport, VitalSigns, MedicalRecord, Patient
from app.utils.auth import get_current_user, require_roles
from app.extensions import db
from datetime import datetime

medical_bp = Blueprint('medical', __name__)

@medical_bp.route('/test-reports', methods=['POST'])
@jwt_required()
@require_roles(UserRole.LAB_TECHNICIAN, UserRole.DOCTOR)
def upload_test_report():
    try:
        user = get_current_user()
        data = request.get_json()
        
        required_fields = ['appointment_id', 'patient_id', 'test_name', 'test_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        test_report = TestReport(
            appointment_id=data['appointment_id'],
            patient_id=data['patient_id'],
            test_name=data['test_name'],
            test_type=data['test_type'],
            result=data.get('result'),
            normal_range=data.get('normal_range'),
            units=data.get('units'),
            comments=data.get('comments'),
            performed_by=user.id,
            status='completed',
            completed_date=datetime.utcnow()
        )
        
        db.session.add(test_report)
        db.session.commit()
        
        # Notify patient and doctor
        from app.utils.notifications import create_notification
        
        # Get appointment details for notification
        from app.models import Appointment
        appointment = Appointment.query.get(data['appointment_id'])
        
        if appointment:
            create_notification(
                title="Test Report Available",
                message=f"Your {data['test_name']} test results are available",
                receiver_id=appointment.patient.user.id,
                sender_id=user.id,
                notification_type="test_report"
            )
            
            create_notification(
                title="Test Report Available",
                message=f"Test results for {appointment.patient.user.first_name} are available",
                receiver_id=appointment.doctor.user.id,
                sender_id=user.id,
                notification_type="test_report"
            )
        
        return jsonify({
            'message': 'Test report uploaded successfully',
            'test_report': test_report.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to upload test report: {str(e)}'}), 500

@medical_bp.route('/test-reports', methods=['GET'])
@jwt_required()
def get_test_reports():
    try:
        user = get_current_user()
        patient_id = request.args.get('patient_id')
        
        if user.role == UserRole.PATIENT:
            query = TestReport.query.filter_by(patient_id=user.patient.id)
        elif user.role == UserRole.DOCTOR:
            if patient_id:
                query = TestReport.query.filter_by(patient_id=patient_id)
            else:
                # Get reports for doctor's patients
                from app.models import Appointment
                doctor_appointments = [app.id for app in user.doctor.appointments]
                query = TestReport.query.filter(TestReport.appointment_id.in_(doctor_appointments))
        elif user.role == UserRole.LAB_TECHNICIAN:
            query = TestReport.query.filter_by(performed_by=user.id)
        else:
            query = TestReport.query
        
        test_reports = query.order_by(TestReport.completed_date.desc()).all()
        
        return jsonify({
            'test_reports': [report.to_dict() for report in test_reports]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch test reports: {str(e)}'}), 500

@medical_bp.route('/vital-signs', methods=['POST'])
@jwt_required()
@require_roles(UserRole.NURSE, UserRole.DOCTOR)
def record_vital_signs():
    try:
        user = get_current_user()
        data = request.get_json()
        
        required_fields = ['patient_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        vital_signs = VitalSigns(
            patient_id=data['patient_id'],
            recorded_by=user.id,
            blood_pressure_systolic=data.get('blood_pressure_systolic'),
            blood_pressure_diastolic=data.get('blood_pressure_diastolic'),
            heart_rate=data.get('heart_rate'),
            respiratory_rate=data.get('respiratory_rate'),
            temperature=data.get('temperature'),
            oxygen_saturation=data.get('oxygen_saturation'),
            weight=data.get('weight'),
            height=data.get('height'),
            blood_sugar=data.get('blood_sugar'),
            notes=data.get('notes')
        )
        
        db.session.add(vital_signs)
        db.session.commit()
        
        return jsonify({
            'message': 'Vital signs recorded successfully',
            'vital_signs': vital_signs.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to record vital signs: {str(e)}'}), 500

@medical_bp.route('/vital-signs', methods=['GET'])
@jwt_required()
def get_vital_signs():
    try:
        user = get_current_user()
        patient_id = request.args.get('patient_id')
        
        if user.role == UserRole.PATIENT:
            query = VitalSigns.query.filter_by(patient_id=user.patient.id)
        elif user.role in [UserRole.DOCTOR, UserRole.NURSE]:
            if not patient_id:
                return jsonify({'message': 'Patient ID is required'}), 400
            query = VitalSigns.query.filter_by(patient_id=patient_id)
        else:
            return jsonify({'message': 'Unauthorized access'}), 403
        
        vital_signs = query.order_by(VitalSigns.recorded_at.desc()).all()
        
        return jsonify({
            'vital_signs': [vs.to_dict() for vs in vital_signs]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch vital signs: {str(e)}'}), 500

@medical_bp.route('/medical-records', methods=['POST'])
@jwt_required()
@require_roles(UserRole.DOCTOR, UserRole.NURSE)
def add_medical_record():
    try:
        user = get_current_user()
        data = request.get_json()
        
        required_fields = ['patient_id', 'record_type', 'description']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        medical_record = MedicalRecord(
            patient_id=data['patient_id'],
            record_type=data['record_type'],
            description=data['description'],
            date_recorded=datetime.fromisoformat(data.get('date_recorded', datetime.utcnow().isoformat())),
            recorded_by=user.id
        )
        
        db.session.add(medical_record)
        db.session.commit()
        
        return jsonify({
            'message': 'Medical record added successfully',
            'medical_record': medical_record.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to add medical record: {str(e)}'}), 500