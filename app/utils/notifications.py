from app.models import Notification, User, UserRole
from app.extensions import db, mail
from flask_mail import Message

def create_notification(title, message, receiver_id, sender_id=None, notification_type=None):
    notification = Notification(
        title=title,
        message=message,
        sender_id=sender_id,
        receiver_id=receiver_id,
        notification_type=notification_type
    )
    db.session.add(notification)
    db.session.commit()
    return notification

def send_email_notification(recipient, subject, body):
    try:
        msg = Message(
            subject=subject,
            recipients=[recipient],
            body=body
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def notify_appointment_status(appointment, old_status=None):
    patient_user = appointment.patient.user
    doctor_user = appointment.doctor.user
    
    # Notify patient
    create_notification(
        title="Appointment Status Update",
        message=f"Your appointment with Dr. {doctor_user.last_name} has been {appointment.status.value}",
        receiver_id=patient_user.id,
        notification_type="appointment"
    )
    
    # Notify doctor if status changed by admin/patient
    if old_status and old_status != appointment.status:
        create_notification(
            title="Appointment Status Update",
            message=f"Appointment with {patient_user.first_name} {patient_user.last_name} has been {appointment.status.value}",
            receiver_id=doctor_user.id,
            notification_type="appointment"
        )