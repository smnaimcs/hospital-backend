import pytest
import json
from app import create_app
from app.extensions import db
from app.models import User, UserRole

@pytest.fixture
def client():
    app = create_app('testing')
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

def test_register_patient(client):
    response = client.post('/api/auth/register', json={
        'email': 'patient@test.com',
        'password': 'password123',
        'first_name': 'John',
        'last_name': 'Doe',
        'role': 'patient',
        'phone': '1234567890'
    })
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['message'] == 'User registered successfully'
    assert data['user']['email'] == 'patient@test.com'

def test_login(client):
    # First register
    client.post('/api/auth/register', json={
        'email': 'test@test.com',
        'password': 'password123',
        'first_name': 'Test',
        'last_name': 'User',
        'role': 'patient'
    })
    
    # Then login
    response = client.post('/api/auth/login', json={
        'email': 'test@test.com',
        'password': 'password123'
    })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Login successful'
    assert 'token' in data