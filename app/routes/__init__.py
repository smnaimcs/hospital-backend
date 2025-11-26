# This file makes the routes directory a Python package
# It can also be used to organize and export route blueprints

from .auth import auth_bp
from .patient import patient_bp
from .doctor import doctor_bp
from .admin import admin_bp
from .appointment import appointment_bp
from .medical import medical_bp
from .billing import billing_bp
from .inventory import inventory_bp

# Optional: You can also import staff routes if you create them later
# from .staff import staff_bp

__all__ = [
    'auth_bp',
    'patient_bp',
    'doctor_bp', 
    'admin_bp',
    'appointment_bp',
    'medical_bp',
    'billing_bp',
    'inventory_bp',
    # 'staff_bp'
]