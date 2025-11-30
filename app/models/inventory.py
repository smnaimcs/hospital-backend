from app.extensions import db
from datetime import datetime
import enum

class MedicineCategory(enum.Enum):
    TABLET = "tablet"
    CAPSULE = "capsule"
    SYRUP = "syrup"
    INJECTION = "injection"
    OINTMENT = "ointment"
    DROPS = "drops"
    INHALER = "inhaler"

class StockStatus(enum.Enum):
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"

class Medicine(db.Model):
    __tablename__ = 'medicines'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    generic_name = db.Column(db.String(200))
    category = db.Column(db.Enum(MedicineCategory), nullable=False)
    manufacturer = db.Column(db.String(200))
    batch_number = db.Column(db.String(100))
    expiry_date = db.Column(db.Date, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    prescription_required = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
    side_effects = db.Column(db.Text)
    dosage_instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    inventory = db.relationship('Inventory', backref='medicine', uselist=False, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'generic_name': self.generic_name,
            'category': self.category.value,
            'manufacturer': self.manufacturer,
            'batch_number': self.batch_number,
            'expiry_date': self.expiry_date.isoformat(),
            'unit_price': self.unit_price,
            'prescription_required': self.prescription_required,
            'description': self.description,
            'side_effects': self.side_effects,
            'dosage_instructions': self.dosage_instructions,
            'created_at': self.created_at.isoformat()
        }

class Inventory(db.Model):
    __tablename__ = 'inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    current_stock = db.Column(db.Integer, default=0)
    minimum_stock = db.Column(db.Integer, default=10)
    maximum_stock = db.Column(db.Integer, default=100)
    stock_status = db.Column(db.Enum(StockStatus), default=StockStatus.IN_STOCK)
    last_restocked = db.Column(db.DateTime)
    shelf_location = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'medicine_id': self.medicine_id,
            'current_stock': self.current_stock,
            'minimum_stock': self.minimum_stock,
            'maximum_stock': self.maximum_stock,
            'stock_status': self.stock_status.value,
            'last_restocked': self.last_restocked.isoformat() if self.last_restocked else None,
            'shelf_location': self.shelf_location,
            'updated_at': self.updated_at.isoformat()
        }

class StockAlert(db.Model):
    __tablename__ = 'stock_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)  # low_stock, expired, near_expiry
    message = db.Column(db.Text, nullable=False)
    is_resolved = db.Column(db.Boolean, default=False)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'medicine_id': self.medicine_id,
            'alert_type': self.alert_type,
            'message': self.message,
            'is_resolved': self.is_resolved,
            'resolved_by': self.resolved_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'created_at': self.created_at.isoformat()
        }