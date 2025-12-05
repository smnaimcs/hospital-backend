from app.extensions import db
from datetime import datetime

class PassToken(db.Model):
    __tablename__ = 'pass_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    generated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    purpose = db.Column(db.String(200), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    valid_until = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, used, expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'generated_by': self.generated_by,
            'purpose': self.purpose,
            'token': self.token,
            'valid_until': self.valid_until.isoformat(),
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }