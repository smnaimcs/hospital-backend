from app.extensions import db
from datetime import datetime, time

class Doctor(db.Model):
    __tablename__ = 'doctors'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    years_of_experience = db.Column(db.Integer)
    qualification = db.Column(db.Text)
    consultation_fee = db.Column(db.Float, default=0.0)
    is_available = db.Column(db.Boolean, default=True)
    
    # Relationships
    availabilities = db.relationship('Availability', backref='doctor', lazy='dynamic', cascade='all, delete-orphan')
    appointments = db.relationship('Appointment', backref='doctor', lazy='dynamic')
    diagnoses = db.relationship('Diagnosis', backref='doctor', lazy='dynamic')
    prescriptions = db.relationship('Prescription', backref='doctor', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user': self.user.to_dict(),
            'license_number': self.license_number,
            'specialization': self.specialization,
            'years_of_experience': self.years_of_experience,
            'qualification': self.qualification,
            'consultation_fee': self.consultation_fee,
            'is_available': self.is_available
        }

class Availability(db.Model):
    __tablename__ = 'availabilities'
    
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0-6 (Monday-Sunday)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_recurring = db.Column(db.Boolean, default=True)
    specific_date = db.Column(db.Date)  # For one-time availability
    
    def to_dict(self):
        return {
            'id': self.id,
            'doctor_id': self.doctor_id,
            'day_of_week': self.day_of_week,
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M'),
            'is_recurring': self.is_recurring,
            'specific_date': self.specific_date.isoformat() if self.specific_date else None
        }

class DoctorSpecialization(db.Model):
    __tablename__ = 'doctor_specializations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }