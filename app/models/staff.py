from app.extensions import db
from datetime import datetime
import enum

class LeaveStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class LeaveType(enum.Enum):
    SICK = "sick"
    VACATION = "vacation"
    PERSONAL = "personal"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    EMERGENCY = "emergency"

class Staff(db.Model):
    __tablename__ = 'staff'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    staff_type = db.Column(db.String(50), nullable=False)  # nurse, lab_technician, etc.
    department = db.Column(db.String(100))
    employee_id = db.Column(db.String(50), unique=True)
    hire_date = db.Column(db.Date)
    salary = db.Column(db.Float)
    shift = db.Column(db.String(50))  # morning, evening, night
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    attendances = db.relationship('Attendance', backref='staff', lazy='dynamic', cascade='all, delete-orphan')
    leave_requests = db.relationship('LeaveRequest', backref='staff', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user': self.user.to_dict(),
            'staff_type': self.staff_type,
            'department': self.department,
            'employee_id': self.employee_id,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'salary': self.salary,
            'shift': self.shift,
            'is_active': self.is_active
        }

class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.DateTime)
    check_out = db.Column(db.DateTime)
    total_hours = db.Column(db.Float)
    status = db.Column(db.String(20), default='present')  # present, absent, late, half-day
    notes = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'staff_id': self.staff_id,
            'date': self.date.isoformat(),
            'check_in': self.check_in.isoformat() if self.check_in else None,
            'check_out': self.check_out.isoformat() if self.check_out else None,
            'total_hours': self.total_hours,
            'status': self.status,
            'notes': self.notes
        }

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    leave_type = db.Column(db.Enum(LeaveType), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(LeaveStatus), default=LeaveStatus.PENDING)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'staff_id': self.staff_id,
            'leave_type': self.leave_type.value,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'reason': self.reason,
            'status': self.status.value,
            'approved_by': self.approved_by,
            'comments': self.comments,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Ward(db.Model):
    __tablename__ = 'wards'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # general, icu, emergency, maternity
    capacity = db.Column(db.Integer, nullable=False)
    current_occupancy = db.Column(db.Integer, default=0)
    charge_per_day = db.Column(db.Float)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    beds = db.relationship('Bed', backref='ward', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'capacity': self.capacity,
            'current_occupancy': self.current_occupancy,
            'availability': self.capacity - self.current_occupancy,
            'charge_per_day': self.charge_per_day,
            'description': self.description,
            'is_active': self.is_active
        }

class Bed(db.Model):
    __tablename__ = 'beds'
    
    id = db.Column(db.Integer, primary_key=True)
    ward_id = db.Column(db.Integer, db.ForeignKey('wards.id'), nullable=False)
    bed_number = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='available')  # available, occupied, maintenance
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'))
    admission_date = db.Column(db.DateTime)
    discharge_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'ward_id': self.ward_id,
            'bed_number': self.bed_number,
            'status': self.status,
            'patient_id': self.patient_id,
            'admission_date': self.admission_date.isoformat() if self.admission_date else None,
            'discharge_date': self.discharge_date.isoformat() if self.discharge_date else None,
            'notes': self.notes
        }