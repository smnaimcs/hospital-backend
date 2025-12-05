from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, UserRole, TestReport, VitalSigns, MedicalRecord, Patient, Appointment
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

@medical_bp.route('/medical-records', methods=['GET'])
@jwt_required()
def get_medical_records():
    """
    Get medical records for a patient.
    Patients can view their own records.
    Doctors and nurses can view records of their patients.
    """
    try:
        user = get_current_user()
        patient_id = request.args.get('patient_id')
        
        # Build query based on user role
        if user.role == UserRole.PATIENT:
            # Patients can only view their own records
            query = MedicalRecord.query.filter_by(patient_id=user.patient.id)
            
        elif user.role in [UserRole.DOCTOR, UserRole.NURSE]:
            # Medical staff need patient_id parameter
            if not patient_id:
                return jsonify({'message': 'Patient ID is required for medical staff'}), 400
            
            # Optional: Verify patient belongs to doctor/nurse (for doctor's patients)
            if user.role == UserRole.DOCTOR:
                # Check if patient is assigned to this doctor
                patient = Patient.query.get(patient_id)
                if patient and patient.primary_doctor_id != user.doctor.id:
                    # Check through appointments
                    from app.models import Appointment
                    has_appointment = Appointment.query.filter_by(
                        patient_id=patient_id,
                        doctor_id=user.doctor.id
                    ).first()
                    if not has_appointment:
                        return jsonify({'message': 'Not authorized to view this patient\'s records'}), 403
            
            query = MedicalRecord.query.filter_by(patient_id=patient_id)
            
        elif user.role in [UserRole.LAB_TECHNICIAN, UserRole.STAFF]:
            # Other staff roles might need limited access
            if not patient_id:
                return jsonify({'message': 'Patient ID is required'}), 400
            query = MedicalRecord.query.filter_by(patient_id=patient_id)
            
        else:
            return jsonify({'message': 'Unauthorized access'}), 403
        
        # Optional filtering parameters
        record_type = request.args.get('record_type')
        if record_type:
            query = query.filter_by(record_type=record_type)
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date:
            query = query.filter(MedicalRecord.date_recorded >= datetime.fromisoformat(start_date))
        if end_date:
            query = query.filter(MedicalRecord.date_recorded <= datetime.fromisoformat(end_date))
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        paginated_records = query.order_by(MedicalRecord.date_recorded.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        records_data = [record.to_dict() for record in paginated_records.items]
        
        # Include doctor/nurse names if not in to_dict()
        for record in records_data:
            recorded_by_user = User.query.get(record['recorded_by'])
            if recorded_by_user:
                record['recorded_by_name'] = f"{recorded_by_user.first_name} {recorded_by_user.last_name}"
        
        return jsonify({
            'message': 'Medical records retrieved successfully',
            'medical_records': records_data,
            'pagination': {
                'total': paginated_records.total,
                'pages': paginated_records.pages,
                'current_page': paginated_records.page,
                'per_page': paginated_records.per_page,
                'has_next': paginated_records.has_next,
                'has_prev': paginated_records.has_prev
            }
        }), 200
        
    except ValueError as e:
        return jsonify({'message': f'Invalid date format: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to fetch medical records: {str(e)}'}), 500


@medical_bp.route('/medical-records/<int:record_id>', methods=['GET'])
@jwt_required()
def get_medical_record_by_id(record_id):
    """
    Get a specific medical record by ID.
    """
    try:
        user = get_current_user()
        
        # Get the medical record
        medical_record = MedicalRecord.query.get(record_id)
        if not medical_record:
            return jsonify({'message': 'Medical record not found'}), 404
        
        # Check authorization
        if user.role == UserRole.PATIENT:
            if medical_record.patient_id != user.patient.id:
                return jsonify({'message': 'Not authorized to view this record'}), 403
                
        elif user.role in [UserRole.DOCTOR, UserRole.NURSE]:
            # For doctors, check if they are the patient's doctor or have appointments with them
            if user.role == UserRole.DOCTOR:
                patient = Patient.query.get(medical_record.patient_id)
                if patient and patient.primary_doctor_id != user.doctor.id:
                    # Check through appointments
                    from app.models import Appointment
                    has_appointment = Appointment.query.filter_by(
                        patient_id=medical_record.patient_id,
                        doctor_id=user.doctor.id
                    ).first()
                    if not has_appointment:
                        return jsonify({'message': 'Not authorized to view this record'}), 403
        
        elif user.role in [UserRole.LAB_TECHNICIAN, UserRole.STAFF]:
            # Limited access for other staff - might need specific permissions
            return jsonify({'message': 'Not authorized to view medical records'}), 403
        else:
            return jsonify({'message': 'Unauthorized access'}), 403
        
        # Get record data
        record_data = medical_record.to_dict()
        
        # Add recorded by user name
        recorded_by_user = User.query.get(record_data['recorded_by'])
        if recorded_by_user:
            record_data['recorded_by_name'] = f"{recorded_by_user.first_name} {recorded_by_user.last_name}"
        
        # Add patient name for staff reference
        if user.role in [UserRole.DOCTOR, UserRole.NURSE]:
            patient = Patient.query.get(medical_record.patient_id)
            if patient and patient.user:
                record_data['patient_name'] = f"{patient.user.first_name} {patient.user.last_name}"
        
        return jsonify({
            'message': 'Medical record retrieved successfully',
            'medical_record': record_data
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch medical record: {str(e)}'}), 500

@medical_bp.route('/patient-arrival/<int:appointment_id>', methods=['PUT'])
@jwt_required()
@require_roles(UserRole.NURSE, UserRole.STAFF)
def update_patient_arrival(appointment_id):
    try:
        user = get_current_user()
        data = request.get_json()
        
        appointment = Appointment.query.get(appointment_id)
        if not appointment:
            return jsonify({'message': 'Appointment not found'}), 404
        
        if 'arrival_status' not in data:
            return jsonify({'message': 'Arrival status is required'}), 400
        
        # Update appointment with arrival status
        appointment.arrival_status = data['arrival_status']  # You'll need to add this field to Appointment model
        appointment.arrival_time = datetime.utcnow() if data['arrival_status'] == 'arrived' else None
        appointment.checked_in_by = user.id
        
        db.session.commit()
        
        # Notify doctor
        from app.utils.notifications import create_notification
        create_notification(
            title="Patient Arrival Update",
            message=f"Patient {appointment.patient.user.first_name} has {data['arrival_status']}",
            receiver_id=appointment.doctor.user.id,
            sender_id=user.id,
            notification_type="patient_arrival"
        )
        
        return jsonify({
            'message': 'Patient arrival status updated successfully',
            'appointment': appointment.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to update patient arrival: {str(e)}'}), 500

@medical_bp.route('/pass-tokens', methods=['POST'])
@jwt_required()
@require_roles(UserRole.STAFF)
def generate_pass_token():
    try:
        user = get_current_user()
        data = request.get_json()
        
        required_fields = ['patient_id', 'purpose', 'valid_until']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        # You'll need to create a PassToken model
        pass_token = PassToken(
            patient_id=data['patient_id'],
            generated_by=user.id,
            purpose=data['purpose'],
            token=f"PASS-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            valid_until=datetime.fromisoformat(data['valid_until']),
            status='active'
        )
        
        db.session.add(pass_token)
        db.session.commit()
        
        return jsonify({
            'message': 'Pass token generated successfully',
            'pass_token': pass_token.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to generate pass token: {str(e)}'}), 500
