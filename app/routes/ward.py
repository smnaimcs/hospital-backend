from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, UserRole, Ward, Bed, Patient, Appointment
from app.utils.auth import get_current_user, require_roles
from app.extensions import db
from datetime import datetime

ward_bp = Blueprint('ward', __name__)

# ==================== WARD MANAGEMENT ====================

@ward_bp.route('/wards', methods=['GET'])
@jwt_required()
def get_wards():
    try:
        ward_type = request.args.get('type')
        available_only = request.args.get('available_only', 'false').lower() == 'true'
        
        query = Ward.query.filter_by(is_active=True)
        
        if ward_type:
            query = query.filter_by(type=ward_type)
        
        if available_only:
            query = query.filter(Ward.current_occupancy < Ward.capacity)
        
        wards = query.all()
        
        return jsonify({
            'wards': [ward.to_dict() for ward in wards]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch wards: {str(e)}'}), 500

@ward_bp.route('/wards/<int:ward_id>/beds', methods=['GET'])
@jwt_required()
def get_ward_beds(ward_id):
    try:
        status = request.args.get('status')
        
        ward = Ward.query.get(ward_id)
        if not ward:
            return jsonify({'message': 'Ward not found'}), 404
        
        query = Bed.query.filter_by(ward_id=ward_id)
        
        if status:
            query = query.filter_by(status=status)
        
        beds = query.all()
        
        return jsonify({
            'ward': ward.to_dict(),
            'beds': [bed.to_dict() for bed in beds]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch beds: {str(e)}'}), 500

@ward_bp.route('/beds/available', methods=['GET'])
@jwt_required()
def get_available_beds():
    try:
        ward_type = request.args.get('ward_type')
        
        query = Bed.query.filter_by(status='available').join(Ward)
        
        if ward_type:
            query = query.filter(Ward.type == ward_type)
        
        available_beds = query.all()
        
        return jsonify({
            'available_beds': [bed.to_dict() for bed in available_beds]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch available beds: {str(e)}'}), 500

@ward_bp.route('/beds/<int:bed_id>/assign', methods=['PUT'])
@jwt_required()
@require_roles(UserRole.WARD_MANAGER, UserRole.ADMIN, UserRole.DOCTOR)
def assign_bed_to_patient(bed_id):
    try:
        user = get_current_user()
        data = request.get_json()
        
        required_fields = ['patient_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        bed = Bed.query.get(bed_id)
        if not bed:
            return jsonify({'message': 'Bed not found'}), 404
        
        if bed.status != 'available':
            return jsonify({'message': 'Bed is not available'}), 400
        
        patient = Patient.query.get(data['patient_id'])
        if not patient:
            return jsonify({'message': 'Patient not found'}), 404
        
        # Update bed status
        bed.status = 'occupied'
        bed.patient_id = patient.id
        bed.admission_date = datetime.utcnow()
        bed.notes = data.get('notes', '')
        
        # Update ward occupancy
        bed.ward.current_occupancy += 1
        
        db.session.commit()
        
        # Create notification
        from app.utils.notifications import create_notification
        create_notification(
            title="Bed Assigned",
            message=f"Bed {bed.bed_number} in {bed.ward.name} has been assigned to you",
            receiver_id=patient.user.id,
            sender_id=user.id,
            notification_type="bed_assignment"
        )
        
        return jsonify({
            'message': 'Bed assigned successfully',
            'bed': bed.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to assign bed: {str(e)}'}), 500

@ward_bp.route('/beds/<int:bed_id>/discharge', methods=['PUT'])
@jwt_required()
@require_roles(UserRole.WARD_MANAGER, UserRole.ADMIN, UserRole.DOCTOR)
def discharge_patient_from_bed(bed_id):
    try:
        user = get_current_user()
        bed = Bed.query.get(bed_id)
        
        if not bed:
            return jsonify({'message': 'Bed not found'}), 404
        
        if bed.status != 'occupied':
            return jsonify({'message': 'Bed is not occupied'}), 400
        
        # Update bed status
        bed.status = 'available'
        patient_id = bed.patient_id
        bed.patient_id = None
        bed.discharge_date = datetime.utcnow()
        
        # Update ward occupancy
        bed.ward.current_occupancy -= 1
        
        db.session.commit()
        
        # Create notification
        from app.utils.notifications import create_notification
        create_notification(
            title="Patient Discharged",
            message=f"Patient has been discharged from bed {bed.bed_number}",
            receiver_id=user.id,  # Notify staff
            sender_id=user.id,
            notification_type="patient_discharge"
        )
        
        return jsonify({
            'message': 'Patient discharged successfully',
            'bed': bed.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to discharge patient: {str(e)}'}), 500

@ward_bp.route('/wards', methods=['POST'])
@jwt_required()
@require_roles(UserRole.WARD_MANAGER, UserRole.ADMIN)
def create_ward():
    try:
        data = request.get_json()
        
        required_fields = ['name', 'type', 'capacity']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        ward = Ward(
            name=data['name'],
            type=data['type'],
            capacity=data['capacity'],
            charge_per_day=data.get('charge_per_day', 0),
            description=data.get('description', '')
        )
        
        db.session.add(ward)
        db.session.commit()
        
        # Create beds for the ward
        for i in range(1, data['capacity'] + 1):
            bed = Bed(
                ward_id=ward.id,
                bed_number=f"{data['name']}-{i:02d}",
                status='available'
            )
            db.session.add(bed)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Ward created successfully',
            'ward': ward.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to create ward: {str(e)}'}), 500

@ward_bp.route('/wards/<int:ward_id>/beds', methods=['POST'])
@jwt_required()
@require_roles(UserRole.WARD_MANAGER, UserRole.ADMIN)
def add_bed_to_ward(ward_id):
    try:
        data = request.get_json()
        
        if 'bed_number' not in data:
            return jsonify({'message': 'Bed number is required'}), 400
        
        ward = Ward.query.get(ward_id)
        if not ward:
            return jsonify({'message': 'Ward not found'}), 404
        
        # Check if bed number already exists in this ward
        existing_bed = Bed.query.filter_by(
            ward_id=ward_id,
            bed_number=data['bed_number']
        ).first()
        
        if existing_bed:
            return jsonify({'message': 'Bed number already exists in this ward'}), 400
        
        bed = Bed(
            ward_id=ward_id,
            bed_number=data['bed_number'],
            status=data.get('status', 'available'),
            notes=data.get('notes', '')
        )
        
        db.session.add(bed)
        db.session.commit()
        
        return jsonify({
            'message': 'Bed added successfully',
            'bed': bed.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to add bed: {str(e)}'}), 500