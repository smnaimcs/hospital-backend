from app.extensions import db
from datetime import datetime
import enum

class AppointmentStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    RESCHEDULED = "rescheduled"

class Appointment(db.Model):
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, default=30)  # in minutes
    status = db.Column(db.Enum(AppointmentStatus), default=AppointmentStatus.PENDING)
    reason = db.Column(db.Text)
    symptoms = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    diagnosis = db.relationship('Diagnosis', backref='appointment', uselist=False)
    prescriptions = db.relationship('Prescription', backref='appointment', lazy='dynamic')
    test_reports = db.relationship('TestReport', backref='appointment', lazy='dynamic')
    bill = db.relationship('MedicalBill', backref='appointment', uselist=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'patient': self.patient.to_dict(),
            'doctor': self.doctor.to_dict(),
            'appointment_date': self.appointment_date.isoformat(),
            'duration': self.duration,
            'status': self.status.value,
            'reason': self.reason,
            'symptoms': self.symptoms,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }