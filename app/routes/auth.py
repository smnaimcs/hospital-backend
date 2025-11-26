from flask import Blueprint, request, jsonify
from app.models import User, UserRole, Patient, Doctor, Staff
from app.utils.auth import hash_password, verify_password, create_jwt_token
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'first_name', 'last_name', 'role']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        # Check if user already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'message': 'User already exists'}), 400
        
        # Create user
        user = User(
            email=data['email'],
            password_hash=hash_password(data['password']),
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data.get('phone'),
            address=data.get('address'),
            date_of_birth=data.get('date_of_birth'),
            gender=data.get('gender'),
            role=UserRole(data['role'])
        )
        
        db.session.add(user)
        db.session.flush()  # Get user ID without committing
        
        # Create role-specific profile
        if user.role == UserRole.PATIENT:
            patient = Patient(
                user_id=user.id,
                blood_group=data.get('blood_group'),
                emergency_contact=data.get('emergency_contact'),
                insurance_info=data.get('insurance_info')
            )
            db.session.add(patient)
        
        elif user.role == UserRole.DOCTOR:
            doctor = Doctor(
                user_id=user.id,
                license_number=data.get('license_number'),
                specialization=data.get('specialization'),
                years_of_experience=data.get('years_of_experience'),
                qualification=data.get('qualification'),
                consultation_fee=data.get('consultation_fee', 0.0)
            )
            db.session.add(doctor)
        
        elif user.role in [UserRole.STAFF, UserRole.NURSE, UserRole.LAB_TECHNICIAN, 
                          UserRole.PHARMACIST, UserRole.WARD_MANAGER, UserRole.FINANCIAL_MANAGER]:
            staff = Staff(
                user_id=user.id,
                staff_type=user.role.value,
                department=data.get('department')
            )
            db.session.add(staff)
        
        db.session.commit()
        
        # Generate token
        token = create_jwt_token(user.id)
        
        return jsonify({
            'message': 'User registered successfully',
            'token': token,
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Registration failed: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'message': 'Email and password required'}), 400
        
        user = User.query.filter_by(email=data['email']).first()
        
        if not user or not verify_password(user.password_hash, data['password']):
            return jsonify({'message': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'message': 'Account is deactivated'}), 403
        
        token = create_jwt_token(user.id)
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Login failed: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        profile_data = user.to_dict()
        
        # Add role-specific data
        if user.role == UserRole.PATIENT and user.patient:
            profile_data['patient_info'] = user.patient.to_dict()
        elif user.role == UserRole.DOCTOR and user.doctor:
            profile_data['doctor_info'] = user.doctor.to_dict()
        elif user.staff:
            profile_data['staff_info'] = user.staff.to_dict()
        
        return jsonify(profile_data), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get profile: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update basic user info
        updatable_fields = ['first_name', 'last_name', 'phone', 'address', 'date_of_birth', 'gender']
        for field in updatable_fields:
            if field in data:
                setattr(user, field, data[field])
        
        # Update role-specific info
        if user.role == UserRole.PATIENT and user.patient:
            patient_fields = ['blood_group', 'emergency_contact', 'insurance_info']
            for field in patient_fields:
                if field in data:
                    setattr(user.patient, field, data[field])
        
        elif user.role == UserRole.DOCTOR and user.doctor:
            doctor_fields = ['specialization', 'years_of_experience', 'qualification', 'consultation_fee']
            for field in doctor_fields:
                if field in data:
                    setattr(user.doctor, field, data[field])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to update profile: {str(e)}'}), 500