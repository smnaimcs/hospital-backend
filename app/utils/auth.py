from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, get_jwt_identity
from app.models import User, UserRole
from app.extensions import db
from functools import wraps

def hash_password(password):
    return generate_password_hash(password)

def verify_password(password_hash, password):
    return check_password_hash(password_hash, password)

def create_jwt_token(user_id):
    return create_access_token(identity=user_id)

def get_current_user():
    return User.query.get(get_jwt_identity())

def require_roles(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            current_user = get_current_user()
            if not current_user:
                return {'message': 'User not found'}, 404
            if current_user.role not in roles:
                return {'message': 'Unauthorized access'}, 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper