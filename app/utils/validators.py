import re
from datetime import datetime, date
from flask import request, jsonify
from functools import wraps

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Validate phone number format"""
    # Basic phone validation - adjust based on your requirements
    pattern = r'^\+?1?\d{9,15}$'
    return re.match(pattern, phone) is not None

def validate_date(date_string, date_format='%Y-%m-%d'):
    """Validate date string format"""
    try:
        datetime.strptime(date_string, date_format)
        return True
    except ValueError:
        return False

def validate_time(time_string, time_format='%H:%M'):
    """Validate time string format"""
    try:
        datetime.strptime(time_string, time_format)
        return True
    except ValueError:
        return False

def validate_required_fields(required_fields):
    """Decorator to validate required fields in request JSON"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            if not data:
                return jsonify({'message': 'No JSON data provided'}), 400
            
            missing_fields = []
            for field in required_fields:
                if field not in data or data[field] in [None, '']:
                    missing_fields.append(field)
            
            if missing_fields:
                return jsonify({
                    'message': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_positive_number(value, field_name):
    """Validate that a value is a positive number"""
    try:
        num = float(value)
        if num < 0:
            return False, f'{field_name} must be positive'
        return True, None
    except (ValueError, TypeError):
        return False, f'{field_name} must be a valid number'

def validate_appointment_date(appointment_date):
    """Validate appointment date is not in the past"""
    try:
        appointment_dt = datetime.fromisoformat(appointment_date.replace('Z', '+00:00'))
        if appointment_dt < datetime.utcnow():
            return False, 'Appointment date cannot be in the past'
        return True, None
    except ValueError:
        return False, 'Invalid appointment date format'

def validate_blood_pressure(systolic, diastolic):
    """Validate blood pressure values"""
    if systolic and diastolic:
        if not (60 <= systolic <= 250):
            return False, 'Systolic blood pressure must be between 60 and 250 mmHg'
        if not (40 <= diastolic <= 150):
            return False, 'Diastolic blood pressure must be between 40 and 150 mmHg'
        if systolic <= diastolic:
            return False, 'Systolic pressure must be greater than diastolic pressure'
    return True, None

def validate_heart_rate(heart_rate):
    """Validate heart rate value"""
    if heart_rate and not (30 <= heart_rate <= 250):
        return False, 'Heart rate must be between 30 and 250 bpm'
    return True, None

def validate_temperature(temperature):
    """Validate body temperature value"""
    if temperature and not (35.0 <= temperature <= 42.0):
        return False, 'Body temperature must be between 35.0 and 42.0 °C'
    return True, None

def validate_oxygen_saturation(spo2):
    """Validate oxygen saturation value"""
    if spo2 and not (70 <= spo2 <= 100):
        return False, 'Oxygen saturation must be between 70% and 100%'
    return True, None

def validate_medicine_dosage(dosage):
    """Validate medicine dosage format"""
    # Basic validation - can be enhanced based on specific requirements
    if not dosage or len(dosage) > 100:
        return False, 'Invalid dosage format'
    return True, None

def validate_prescription_data(data):
    """Validate prescription data"""
    required_fields = ['medicine_name', 'dosage', 'duration']
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f'Missing required field: {field}'
    
    # Validate dosage
    is_valid, error = validate_medicine_dosage(data['dosage'])
    if not is_valid:
        return False, error
    
    return True, None

def validate_user_registration(data):
    """Validate user registration data"""
    required_fields = ['email', 'password', 'first_name', 'last_name', 'role']
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f'Missing required field: {field}'
    
    # Validate email
    if not validate_email(data['email']):
        return False, 'Invalid email format'
    
    # Validate password strength
    if len(data['password']) < 6:
        return False, 'Password must be at least 6 characters long'
    
    # Validate role
    from app.models import UserRole
    try:
        UserRole(data['role'])
    except ValueError:
        return False, 'Invalid user role'
    
    # Validate phone if provided
    if 'phone' in data and data['phone'] and not validate_phone(data['phone']):
        return False, 'Invalid phone number format'
    
    # Validate date of birth if provided
    if 'date_of_birth' in data and data['date_of_birth']:
        if not validate_date(data['date_of_birth']):
            return False, 'Invalid date of birth format'
        
        # Check if date of birth is in the past
        dob = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        if dob >= date.today():
            return False, 'Date of birth must be in the past'
    
    return True, None

def validate_bill_data(data):
    """Validate bill data"""
    required_fields = ['patient_id', 'total_amount', 'due_date']
    for field in required_fields:
        if field not in data:
            return False, f'Missing required field: {field}'
    
    # Validate amount
    is_valid, error = validate_positive_number(data['total_amount'], 'Total amount')
    if not is_valid:
        return False, error
    
    # Validate due date
    if not validate_date(data['due_date']):
        return False, 'Invalid due date format'
    
    due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
    if due_date < date.today():
        return False, 'Due date cannot be in the past'
    
    return True, None