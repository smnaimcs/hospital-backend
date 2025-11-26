from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, UserRole, Bill, Payment, PaymentStatus, PaymentMethod, Expense
from app.utils.auth import get_current_user, require_roles
from app.extensions import db
from datetime import datetime
import stripe

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/bills', methods=['POST'])
@jwt_required()
@require_roles(UserRole.ADMIN, UserRole.FINANCIAL_MANAGER)
def create_bill():
    try:
        data = request.get_json()
        
        required_fields = ['patient_id', 'total_amount', 'due_date']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        # Generate bill number
        from datetime import datetime
        bill_number = f"BILL-{datetime.now().strftime('%Y%m%d')}-{Bill.query.count() + 1:04d}"
        
        bill = Bill(
            patient_id=data['patient_id'],
            appointment_id=data.get('appointment_id'),
            bill_number=bill_number,
            total_amount=data['total_amount'],
            tax_amount=data.get('tax_amount', 0),
            discount_amount=data.get('discount_amount', 0),
            final_amount=data['total_amount'] - data.get('discount_amount', 0) + data.get('tax_amount', 0),
            due_date=datetime.fromisoformat(data['due_date']),
            status='pending'
        )
        
        db.session.add(bill)
        db.session.commit()
        
        # Add bill items if provided
        if 'items' in data:
            for item_data in data['items']:
                bill_item = BillItem(
                    bill_id=bill.id,
                    item_description=item_data['description'],
                    quantity=item_data.get('quantity', 1),
                    unit_price=item_data['unit_price'],
                    total_price=item_data['unit_price'] * item_data.get('quantity', 1),
                    item_type=item_data.get('type', 'service')
                )
                db.session.add(bill_item)
        
        db.session.commit()
        
        # Notify patient
        from app.utils.notifications import create_notification
        create_notification(
            title="New Bill Generated",
            message=f"A new bill (${bill.final_amount}) has been generated for you",
            receiver_id=bill.patient.user.id,
            notification_type="billing"
        )
        
        return jsonify({
            'message': 'Bill created successfully',
            'bill': bill.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to create bill: {str(e)}'}), 500

@billing_bp.route('/bills/<int:bill_id>/pay', methods=['POST'])
@jwt_required()
def process_payment(bill_id):
    try:
        user = get_current_user()
        data = request.get_json()
        
        bill = Bill.query.get(bill_id)
        if not bill:
            return jsonify({'message': 'Bill not found'}), 404
        
        # Authorization check
        if user.role == UserRole.PATIENT and bill.patient_id != user.patient.id:
            return jsonify({'message': 'Unauthorized access'}), 403
        
        required_fields = ['payment_method', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        payment_method = PaymentMethod(data['payment_method'])
        amount = float(data['amount'])
        
        if amount != bill.final_amount:
            return jsonify({'message': 'Payment amount must match bill amount'}), 400
        
        # Process payment based on method
        if payment_method == PaymentMethod.ONLINE:
            # Integrate with Stripe
            try:
                stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
                
                # Create Stripe payment intent
                intent = stripe.PaymentIntent.create(
                    amount=int(amount * 100),  # Convert to cents
                    currency='usd',
                    metadata={'bill_id': bill_id}
                )
                
                transaction_id = intent.id
                
            except Exception as stripe_error:
                return jsonify({'message': f'Stripe error: {str(stripe_error)}'}), 400
        
        else:
            transaction_id = f"MANUAL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create payment record
        payment = Payment(
            bill_id=bill_id,
            patient_id=bill.patient_id,
            amount=amount,
            payment_method=payment_method,
            payment_status=PaymentStatus.COMPLETED,
            transaction_id=transaction_id,
            processed_by=user.id if user.role != UserRole.PATIENT else None
        )
        
        # Update bill status
        bill.status = 'paid'
        
        db.session.add(payment)
        db.session.commit()
        
        # Send notification
        from app.utils.notifications import create_notification
        create_notification(
            title="Payment Received",
            message=f"Payment of ${amount} received for bill {bill.bill_number}",
            receiver_id=bill.patient.user.id,
            notification_type="payment"
        )
        
        # Notify financial manager
        financial_managers = User.query.filter_by(role=UserRole.FINANCIAL_MANAGER).all()
        for fm in financial_managers:
            create_notification(
                title="Payment Processed",
                message=f"Payment received for bill {bill.bill_number}",
                receiver_id=fm.id,
                notification_type="payment"
            )
        
        return jsonify({
            'message': 'Payment processed successfully',
            'payment': payment.to_dict(),
            'client_secret': intent.client_secret if payment_method == PaymentMethod.ONLINE else None
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to process payment: {str(e)}'}), 500

@billing_bp.route('/expenses', methods=['POST'])
@jwt_required()
@require_roles(UserRole.FINANCIAL_MANAGER, UserRole.ADMIN)
def add_expense():
    try:
        user = get_current_user()
        data = request.get_json()
        
        required_fields = ['category', 'description', 'amount', 'expense_date']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        expense = Expense(
            category=data['category'],
            description=data['description'],
            amount=data['amount'],
            expense_date=datetime.fromisoformat(data['expense_date']),
            recorded_by=user.id,
            department=data.get('department'),
            receipt_url=data.get('receipt_url')
        )
        
        db.session.add(expense)
        db.session.commit()
        
        return jsonify({
            'message': 'Expense recorded successfully',
            'expense': expense.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to record expense: {str(e)}'}), 500

@billing_bp.route('/financial-reports', methods=['GET'])
@jwt_required()
@require_roles(UserRole.FINANCIAL_MANAGER, UserRole.ADMIN)
def get_financial_reports():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Calculate revenue from payments
        revenue_query = db.session.query(
            db.func.sum(Payment.amount)
        ).filter(Payment.payment_status == PaymentStatus.COMPLETED)
        
        # Calculate expenses
        expense_query = db.session.query(db.func.sum(Expense.amount))
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            revenue_query = revenue_query.filter(Payment.payment_date >= start_dt)
            expense_query = expense_query.filter(Expense.expense_date >= start_dt)
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            revenue_query = revenue_query.filter(Payment.payment_date <= end_dt)
            expense_query = expense_query.filter(Expense.expense_date <= end_dt)
        
        total_revenue = revenue_query.scalar() or 0
        total_expenses = expense_query.scalar() or 0
        net_profit = total_revenue - total_expenses
        
        # Get department-wise expenses
        dept_expenses = db.session.query(
            Expense.department,
            db.func.sum(Expense.amount).label('total')
        ).group_by(Expense.department).all()
        
        return jsonify({
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'department_expenses': [
                {'department': dept, 'total': total} 
                for dept, total in dept_expenses
            ],
            'report_period': {
                'start_date': start_date,
                'end_date': end_date
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to generate financial report: {str(e)}'}), 500