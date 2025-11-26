from app.extensions import db
from datetime import datetime

class Diagnosis(db.Model):
    __tablename__ = 'diagnoses'
    
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)  # Added foreign key
    diagnosis = db.Column(db.Text, nullable=False)
    symptoms = db.Column(db.Text)
    treatment_plan = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text)
    follow_up_required = db.Column(db.Boolean, default=False)
    follow_up_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'appointment_id': self.appointment_id,
            'doctor_id': self.doctor_id,
            'diagnosis': self.diagnosis,
            'symptoms': self.symptoms,
            'treatment_plan': self.treatment_plan,
            'notes': self.notes,
            'follow_up_required': self.follow_up_required,
            'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None,
            'created_at': self.created_at.isoformat()
        }

class Prescription(db.Model):
    __tablename__ = 'prescriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    medicine_name = db.Column(db.String(200), nullable=False)
    dosage = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.String(100))  # e.g., "3 times a day"
    duration = db.Column(db.String(100), nullable=False)  # e.g., "7 days"
    instructions = db.Column(db.Text)
    is_dispensed = db.Column(db.Boolean, default=False)
    dispensed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'appointment_id': self.appointment_id,
            'doctor_id': self.doctor_id,
            'medicine_name': self.medicine_name,
            'dosage': self.dosage,
            'frequency': self.frequency,
            'duration': self.duration,
            'instructions': self.instructions,
            'is_dispensed': self.is_dispensed,
            'dispensed_at': self.dispensed_at.isoformat() if self.dispensed_at else None,
            'created_at': self.created_at.isoformat()
        }

class TestReport(db.Model):
    __tablename__ = 'test_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    test_name = db.Column(db.String(200), nullable=False)
    test_type = db.Column(db.String(100), nullable=False)  # e.g., 'blood', 'urine', 'xray'
    result = db.Column(db.Text)
    normal_range = db.Column(db.String(200))
    units = db.Column(db.String(50))
    comments = db.Column(db.Text)
    performed_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # lab technician
    report_file_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending')  # pending, completed, cancelled
    requested_date = db.Column(db.DateTime, default=datetime.utcnow)
    completed_date = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'appointment_id': self.appointment_id,
            'patient_id': self.patient_id,
            'test_name': self.test_name,
            'test_type': self.test_type,
            'result': self.result,
            'normal_range': self.normal_range,
            'units': self.units,
            'comments': self.comments,
            'performed_by': self.performed_by,
            'report_file_url': self.report_file_url,
            'status': self.status,
            'requested_date': self.requested_date.isoformat(),
            'completed_date': self.completed_date.isoformat() if self.completed_date else None
        }

class VitalSigns(db.Model):
    __tablename__ = 'vital_signs'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # nurse/doctor
    blood_pressure_systolic = db.Column(db.Integer)  # mmHg
    blood_pressure_diastolic = db.Column(db.Integer)  # mmHg
    heart_rate = db.Column(db.Integer)  # bpm
    respiratory_rate = db.Column(db.Integer)  # breaths per minute
    temperature = db.Column(db.Float)  # Celsius
    oxygen_saturation = db.Column(db.Float)  # percentage
    weight = db.Column(db.Float)  # kg
    height = db.Column(db.Float)  # cm
    blood_sugar = db.Column(db.Float)  # mg/dL
    notes = db.Column(db.Text)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'recorded_by': self.recorded_by,
            'blood_pressure': f"{self.blood_pressure_systolic}/{self.blood_pressure_diastolic}" if self.blood_pressure_systolic and self.blood_pressure_diastolic else None,
            'blood_pressure_systolic': self.blood_pressure_systolic,
            'blood_pressure_diastolic': self.blood_pressure_diastolic,
            'heart_rate': self.heart_rate,
            'respiratory_rate': self.respiratory_rate,
            'temperature': self.temperature,
            'oxygen_saturation': self.oxygen_saturation,
            'weight': self.weight,
            'height': self.height,
            'blood_sugar': self.blood_sugar,
            'notes': self.notes,
            'recorded_at': self.recorded_at.isoformat()
        }