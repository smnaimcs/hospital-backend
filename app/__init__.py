from flask import Flask
from app.config import config
from app.extensions import db, jwt, mail, migrate, cors

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.patient import patient_bp
    from app.routes.doctor import doctor_bp
    from app.routes.admin import admin_bp
    from app.routes.appointment import appointment_bp
    from app.routes.medical import medical_bp
    from app.routes.billing import billing_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(patient_bp, url_prefix='/api/patient')
    app.register_blueprint(doctor_bp, url_prefix='/api/doctor')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(appointment_bp, url_prefix='/api/appointments')
    app.register_blueprint(medical_bp, url_prefix='/api/medical')
    app.register_blueprint(billing_bp, url_prefix='/api/billing')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'message': 'Resource not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'message': 'Internal server error'}, 500
    
    return app