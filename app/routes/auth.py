from flask import Blueprint, request, jsonify
from app.models import User, UserRole, Patient, Doctor, Staff
from app.utils.auth import hash_password, verify_password, create_jwt_token
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

auth_bp = Blueprint("auth", __name__)


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------
def parse_date(date_str):
    """Parse a YYYY-MM-DD string into a Python date object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD.")


def error(message, code=400):
    return jsonify({"message": message, "success": False}), code


def success(message, data=None, code=200):
    payload = {"message": message, "success": True}
    if data:
        payload.update(data)
    return jsonify(payload), code


# -------------------------------------------------------
# REGISTER
# -------------------------------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json() or {}

        # Required fields
        required = ["email", "password", "first_name", "last_name", "role"]
        missing = [f for f in required if f not in data]
        if missing:
            return error(f"Missing required fields: {', '.join(missing)}")

        # Email already exists?
        if User.query.filter_by(email=data["email"]).first():
            return error("User already exists")

        # Parse date
        dob = parse_date(data.get("date_of_birth"))

        # Validate role
        try:
            role = UserRole(data["role"])
        except ValueError:
            return error("Invalid role.")

        # Create User
        user = User(
            email=data["email"],
            password_hash=hash_password(data["password"]),
            first_name=data["first_name"],
            last_name=data["last_name"],
            phone=data.get("phone"),
            address=data.get("address"),
            date_of_birth=dob,
            gender=data.get("gender"),
            role=role
        )

        db.session.add(user)
        db.session.flush()  # Get user.id

        # ROLE-SPECIFIC PROFILES
        if role == UserRole.PATIENT:
            patient = Patient(
                user_id=user.id,
                blood_group=data.get("blood_group"),
                emergency_contact=data.get("emergency_contact"),
                insurance_info=data.get("insurance_info")
            )
            db.session.add(patient)

        elif role == UserRole.DOCTOR:
            doctor = Doctor(
                user_id=user.id,
                license_number=data.get("license_number"),
                specialization=data.get("specialization"),
                years_of_experience=data.get("years_of_experience"),
                qualification=data.get("qualification"),
                consultation_fee=data.get("consultation_fee", 0.0)
            )
            db.session.add(doctor)

        elif role in [
            UserRole.STAFF, UserRole.NURSE, UserRole.LAB_TECHNICIAN,
            UserRole.PHARMACIST, UserRole.WARD_MANAGER, UserRole.FINANCIAL_MANAGER
        ]:
            staff = Staff(
                user_id=user.id,
                staff_type=role.value,
                department=data.get("department")
            )
            db.session.add(staff)

        db.session.commit()

        token = create_jwt_token(user.id)

        return success(
            "User registered successfully",
            {"token": token, "user": user.to_dict()},
            code=201
        )

    except ValueError as ve:
        db.session.rollback()
        return error(str(ve))

    except Exception as e:
        db.session.rollback()
        return error(f"Registration failed: {str(e)}", code=500)


# -------------------------------------------------------
# LOGIN
# -------------------------------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json() or {}

        if not data.get("email") or not data.get("password"):
            return error("Email and password required")

        user = User.query.filter_by(email=data["email"]).first()

        if not user or not verify_password(user.password_hash, data["password"]):
            return error("Invalid credentials", code=401)

        if not user.is_active:
            return error("Account is deactivated", code=403)

        token = create_jwt_token(user.id)

        return success("Login successful", {"token": token, "user": user.to_dict()})

    except Exception as e:
        return error(f"Login failed: {str(e)}", 500)


# -------------------------------------------------------
# GET PROFILE
# -------------------------------------------------------
@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return error("User not found", 404)

        profile = user.to_dict()

        # ROLE DETAILS
        if user.role == UserRole.PATIENT and user.patient:
            profile["patient_info"] = user.patient.to_dict()

        elif user.role == UserRole.DOCTOR and user.doctor:
            profile["doctor_info"] = user.doctor.to_dict()

        elif user.staff:
            profile["staff_info"] = user.staff.to_dict()

        return success("Profile fetched successfully", profile)

    except Exception as e:
        return error(f"Failed to get profile: {str(e)}", 500)


# -------------------------------------------------------
# UPDATE PROFILE
# -------------------------------------------------------
@auth_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return error("User not found", 404)

        data = request.get_json() or {}

        # BASIC FIELDS
        basic_fields = ["first_name", "last_name", "phone", "address", "gender"]
        for field in basic_fields:
            if field in data:
                setattr(user, field, data[field])

        # DATE OF BIRTH
        if "date_of_birth" in data:
            try:
                user.date_of_birth = parse_date(data["date_of_birth"])
            except ValueError as ve:
                return error(str(ve))

        # PATIENT FIELDS
        if user.role == UserRole.PATIENT and user.patient:
            patient_fields = ["blood_group", "emergency_contact", "insurance_info"]
            for field in patient_fields:
                if field in data:
                    setattr(user.patient, field, data[field])

        # DOCTOR FIELDS
        elif user.role == UserRole.DOCTOR and user.doctor:
            doctor_fields = [
                "specialization", "years_of_experience",
                "qualification", "consultation_fee"
            ]
            for field in doctor_fields:
                if field in data:
                    setattr(user.doctor, field, data[field])

        db.session.commit()

        return success("Profile updated successfully", {"user": user.to_dict()})

    except Exception as e:
        db.session.rollback()
        return error(f"Failed to update profile: {str(e)}", 500)
