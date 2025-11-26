from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, UserRole, Medicine, Inventory, StockAlert, MedicineCategory, StockStatus
from app.utils.auth import get_current_user, require_roles
from app.extensions import db
from datetime import datetime

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/medicines', methods=['POST'])
@jwt_required()
@require_roles(UserRole.PHARMACIST, UserRole.ADMIN)
def add_medicine():
    try:
        data = request.get_json()
        
        required_fields = ['name', 'category', 'expiry_date', 'unit_price']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        medicine = Medicine(
            name=data['name'],
            generic_name=data.get('generic_name'),
            category=MedicineCategory(data['category']),
            manufacturer=data.get('manufacturer'),
            batch_number=data.get('batch_number'),
            expiry_date=datetime.fromisoformat(data['expiry_date']).date(),
            unit_price=data['unit_price'],
            prescription_required=data.get('prescription_required', True),
            description=data.get('description'),
            side_effects=data.get('side_effects'),
            dosage_instructions=data.get('dosage_instructions')
        )
        
        db.session.add(medicine)
        db.session.flush()  # Get medicine ID without committing
        
        # Create inventory entry
        inventory = Inventory(
            medicine_id=medicine.id,
            current_stock=data.get('initial_stock', 0),
            minimum_stock=data.get('minimum_stock', 10),
            maximum_stock=data.get('maximum_stock', 100),
            shelf_location=data.get('shelf_location'),
            last_restocked=datetime.utcnow() if data.get('initial_stock', 0) > 0 else None
        )
        
        # Update stock status
        inventory.stock_status = get_stock_status(inventory.current_stock, inventory.minimum_stock)
        
        db.session.add(inventory)
        db.session.commit()
        
        return jsonify({
            'message': 'Medicine added successfully',
            'medicine': medicine.to_dict(),
            'inventory': inventory.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to add medicine: {str(e)}'}), 500

@inventory_bp.route('/medicines', methods=['GET'])
@jwt_required()
def get_medicines():
    try:
        search = request.args.get('search', '')
        category = request.args.get('category')
        low_stock = request.args.get('low_stock', 'false').lower() == 'true'
        
        query = Medicine.query.join(Inventory)
        
        if search:
            query = query.filter(
                db.or_(
                    Medicine.name.ilike(f'%{search}%'),
                    Medicine.generic_name.ilike(f'%{search}%')
                )
            )
        
        if category:
            query = query.filter(Medicine.category == MedicineCategory(category))
        
        if low_stock:
            query = query.filter(Inventory.current_stock <= Inventory.minimum_stock)
        
        medicines = query.all()
        
        result = []
        for medicine in medicines:
            medicine_data = medicine.to_dict()
            medicine_data['inventory'] = medicine.inventory.to_dict() if medicine.inventory else None
            result.append(medicine_data)
        
        return jsonify({'medicines': result}), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch medicines: {str(e)}'}), 500

@inventory_bp.route('/inventory/<int:medicine_id>/update-stock', methods=['PUT'])
@jwt_required()
@require_roles(UserRole.PHARMACIST, UserRole.ADMIN)
def update_stock(medicine_id):
    try:
        data = request.get_json()
        
        if 'quantity' not in data:
            return jsonify({'message': 'Quantity is required'}), 400
        
        inventory = Inventory.query.filter_by(medicine_id=medicine_id).first()
        if not inventory:
            return jsonify({'message': 'Inventory not found'}), 404
        
        operation = data.get('operation', 'add')  # add, remove, set
        quantity = int(data['quantity'])
        
        if operation == 'add':
            inventory.current_stock += quantity
        elif operation == 'remove':
            if inventory.current_stock < quantity:
                return jsonify({'message': 'Insufficient stock'}), 400
            inventory.current_stock -= quantity
        elif operation == 'set':
            inventory.current_stock = quantity
        
        # Update stock status
        inventory.stock_status = get_stock_status(inventory.current_stock, inventory.minimum_stock)
        inventory.last_restocked = datetime.utcnow()
        inventory.updated_at = datetime.utcnow()
        
        # Check for stock alerts
        check_stock_alerts(inventory)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Stock updated successfully',
            'inventory': inventory.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to update stock: {str(e)}'}), 500

@inventory_bp.route('/stock-alerts', methods=['GET'])
@jwt_required()
@require_roles(UserRole.PHARMACIST, UserRole.ADMIN, UserRole.FINANCIAL_MANAGER)
def get_stock_alerts():
    try:
        resolved = request.args.get('resolved', 'false').lower() == 'true'
        
        query = StockAlert.query
        
        if not resolved:
            query = query.filter_by(is_resolved=False)
        
        alerts = query.order_by(StockAlert.created_at.desc()).all()
        
        return jsonify({
            'alerts': [alert.to_dict() for alert in alerts]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch stock alerts: {str(e)}'}), 500

@inventory_bp.route('/stock-alerts/<int:alert_id>/resolve', methods=['PUT'])
@jwt_required()
@require_roles(UserRole.PHARMACIST, UserRole.ADMIN)
def resolve_stock_alert(alert_id):
    try:
        user = get_current_user()
        alert = StockAlert.query.get(alert_id)
        
        if not alert:
            return jsonify({'message': 'Alert not found'}), 404
        
        alert.is_resolved = True
        alert.resolved_by = user.id
        alert.resolved_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Stock alert resolved successfully',
            'alert': alert.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to resolve alert: {str(e)}'}), 500

@inventory_bp.route('/prescriptions/<int:prescription_id>/dispense', methods=['PUT'])
@jwt_required()
@require_roles(UserRole.PHARMACIST)
def dispense_prescription(prescription_id):
    try:
        from app.models import Prescription
        
        prescription = Prescription.query.get(prescription_id)
        if not prescription:
            return jsonify({'message': 'Prescription not found'}), 404
        
        # Check if medicine is in stock
        medicine = Medicine.query.filter_by(name=prescription.medicine_name).first()
        if not medicine or not medicine.inventory:
            return jsonify({'message': 'Medicine not found in inventory'}), 404
        
        if medicine.inventory.current_stock <= 0:
            return jsonify({'message': 'Medicine out of stock'}), 400
        
        # Update prescription status
        prescription.is_dispensed = True
        prescription.dispensed_at = datetime.utcnow()
        
        # Reduce stock
        medicine.inventory.current_stock -= 1
        medicine.inventory.stock_status = get_stock_status(
            medicine.inventory.current_stock, 
            medicine.inventory.minimum_stock
        )
        
        # Check for stock alerts
        check_stock_alerts(medicine.inventory)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Prescription dispensed successfully',
            'prescription': prescription.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to dispense prescription: {str(e)}'}), 500

def get_stock_status(current_stock, minimum_stock):
    """Determine stock status based on current stock level"""
    if current_stock == 0:
        return StockStatus.OUT_OF_STOCK
    elif current_stock <= minimum_stock:
        return StockStatus.LOW_STOCK
    else:
        return StockStatus.IN_STOCK

def check_stock_alerts(inventory):
    """Check and create stock alerts if necessary"""
    if inventory.stock_status == StockStatus.LOW_STOCK:
        # Check if there's already an unresolved alert
        existing_alert = StockAlert.query.filter_by(
            medicine_id=inventory.medicine_id,
            alert_type='low_stock',
            is_resolved=False
        ).first()
        
        if not existing_alert:
            alert = StockAlert(
                medicine_id=inventory.medicine_id,
                alert_type='low_stock',
                message=f'Low stock alert for {inventory.medicine.name}. Current stock: {inventory.current_stock}'
            )
            db.session.add(alert)
    
    elif inventory.stock_status == StockStatus.OUT_OF_STOCK:
        existing_alert = StockAlert.query.filter_by(
            medicine_id=inventory.medicine_id,
            alert_type='out_of_stock',
            is_resolved=False
        ).first()
        
        if not existing_alert:
            alert = StockAlert(
                medicine_id=inventory.medicine_id,
                alert_type='out_of_stock',
                message=f'Out of stock alert for {inventory.medicine.name}'
            )
            db.session.add(alert)
    
    # Check for expiry alerts (within 30 days)
    if inventory.medicine.expiry_date:
        days_until_expiry = (inventory.medicine.expiry_date - datetime.utcnow().date()).days
        if 0 <= days_until_expiry <= 30:
            existing_alert = StockAlert.query.filter_by(
                medicine_id=inventory.medicine_id,
                alert_type='near_expiry',
                is_resolved=False
            ).first()
            
            if not existing_alert:
                alert = StockAlert(
                    medicine_id=inventory.medicine_id,
                    alert_type='near_expiry',
                    message=f'Medicine {inventory.medicine.name} expires in {days_until_expiry} days'
                )
                db.session.add(alert)