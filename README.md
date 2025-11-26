# Healthcare Management System - Backend Documentation

## 📋 Table of Contents
1. [System Architecture](#system-architecture)
2. [Database Models](#database-models)
3. [API Endpoints](#api-endpoints)
4. [Authentication Flow](#authentication-flow)
5. [Frontend Integration Guide](#frontend-integration-guide)
6. [Error Handling](#error-handling)
7. [Testing Guide](#testing-guide)
8. [Deployment Guide](#deployment-guide)

---

## 🏗️ System Architecture

### Tech Stack
- **Backend Framework**: Flask (Python)
- **Database**: SQLite (Development) / PostgreSQL (Production)
- **Authentication**: JWT (JSON Web Tokens)
- **ORM**: SQLAlchemy
- **Migrations**: Flask-Migrate (Alembic)
- **File Structure**: Modular Blueprint-based architecture

### Architecture Overview
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask API      │    │   Database      │
│   (React/Vue)   │◄──►│   Backend        │◄──►│   (SQLite/PSQL) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌────────┴────────┐              │
         │              │   External      │              │
         └──────────────│   Services      │──────────────┘
                        └─────────────────┘
                         │    │    │    │
                         ▼    ▼    ▼    ▼
                      Email Stripe  File Cloud
                             Storage
```

### User Roles & Permissions
| Role | Permissions |
|------|-------------|
| **Patient** | View doctors, book appointments, view medical records, pay bills |
| **Doctor** | Manage appointments, add diagnoses, prescribe medicine, view patient history |
| **Admin** | Manage users, handle appointments, system configuration |
| **Lab Technician** | Upload test reports, manage lab tests |
| **Nurse** | Record vital signs, update patient information |
| **Pharmacist** | Manage medicine inventory, dispense prescriptions |
| **Ward Manager** | Manage beds, patient admissions/discharges |
| **Financial Manager** | Handle billing, payments, financial reports |

---

## 🗃️ Database Models

### Core Models Overview

#### 1. User Model
```python
# Base user with common attributes
User(id, email, password_hash, first_name, last_name, phone, role, is_active)
```

#### 2. Role-Specific Models
- **Patient**: `Patient(user_id, blood_group, emergency_contact, insurance_info)`
- **Doctor**: `Doctor(user_id, license_number, specialization, consultation_fee)`
- **Staff**: `Staff(user_id, staff_type, department, employee_id)`

#### 3. Medical Models
- **Appointment**: Links patients and doctors with status tracking
- **Diagnosis**: Medical diagnoses with treatment plans
- **Prescription**: Medicine prescriptions
- **MedicalRecord**: Patient medical history
- **TestReport**: Laboratory test results
- **VitalSigns**: Patient vital measurements

#### 4. Operational Models
- **Bill & Payment**: Financial transactions
- **Medicine & Inventory**: Pharmacy management
- **Ward & Bed**: Hospital bed management
- **Attendance & Leave**: Staff management

### Complete ER Diagram
```
Users ─┬─ Patients ─┬─ Appointments ─┬─ Diagnoses
       │            │                ├─ Prescriptions
       │            │                └─ TestReports
       │            ├─ MedicalRecords
       │            ├─ VitalSigns
       │            └─ Bills ─── Payments
       │
       ├─ Doctors ──┬─ Availabilities
       │            └─ Specializations
       │
       └─ Staff ────┬─ Attendance
                    └─ LeaveRequests
                    
Medicine ── Inventory ── StockAlerts
Ward ────── Beds
```

---

## 🌐 API Endpoints

### Base URL
```
http://localhost:5000/api
```

### Authentication Endpoints

#### Register User
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "first_name": "John",
  "last_name": "Doe",
  "role": "patient", // patient, doctor, admin, etc.
  "phone": "1234567890",
  "address": "123 Main St",
  "date_of_birth": "1990-01-01",
  "gender": "male"
}
```

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

#### Get Profile
```http
GET /auth/profile
Authorization: Bearer <jwt_token>
```

#### Update Profile
```http
PUT /auth/profile
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Smith",
  "phone": "0987654321"
}
```

### Patient Endpoints

#### Get Available Doctors
```http
GET /patient/doctors?search=cardiology&specialization=Cardiology
Authorization: Bearer <patient_token>
```

#### Request Appointment
```http
POST /patient/appointments
Authorization: Bearer <patient_token>
Content-Type: application/json

{
  "doctor_id": 1,
  "appointment_date": "2025-11-27T10:00:00",
  "reason": "Regular checkup",
  "symptoms": "Headache and fever"
}
```

#### Get Patient Appointments
```http
GET /patient/appointments?status=pending
Authorization: Bearer <patient_token>
```

#### Cancel Appointment
```http
PUT /patient/appointments/{id}/cancel
Authorization: Bearer <patient_token>
```

#### Get Medical Records
```http
GET /patient/medical-records
Authorization: Bearer <patient_token>
```

#### Get Bills
```http
GET /patient/bills?status=pending
Authorization: Bearer <patient_token>
```

### Doctor Endpoints

#### Get Doctor Appointments
```http
GET /doctor/appointments?status=confirmed&date=2025-11-27
Authorization: Bearer <doctor_token>
```

#### Add Availability
```http
POST /doctor/availability
Authorization: Bearer <doctor_token>
Content-Type: application/json

{
  "day_of_week": 1, // Monday
  "start_time": "09:00",
  "end_time": "17:00",
  "is_recurring": true
}
```

#### Add Diagnosis
```http
POST /doctor/diagnosis
Authorization: Bearer <doctor_token>
Content-Type: application/json

{
  "appointment_id": 1,
  "diagnosis": "Common cold",
  "symptoms": "Fever, cough, headache",
  "treatment_plan": "Rest and hydration",
  "follow_up_required": true,
  "follow_up_date": "2025-12-04"
}
```

#### Prescribe Medicine
```http
POST /doctor/prescriptions
Authorization: Bearer <doctor_token>
Content-Type: application/json

{
  "appointment_id": 1,
  "medicine_name": "Paracetamol",
  "dosage": "500mg",
  "frequency": "3 times a day",
  "duration": "7 days",
  "instructions": "Take after meals"
}
```

#### Get Patient Medical History
```http
GET /doctor/patients/{patient_id}/medical-history
Authorization: Bearer <doctor_token>
```

### Admin Endpoints

#### Dashboard Statistics
```http
GET /admin/dashboard/stats
Authorization: Bearer <admin_token>
```

#### Manage Users
```http
GET /admin/users?role=doctor&page=1
POST /admin/users
PUT /admin/users/{id}
DELETE /admin/users/{id}
Authorization: Bearer <admin_token>
```

#### Manage Appointments
```http
GET /admin/appointments?status=pending
PUT /admin/appointments/{id}
Authorization: Bearer <admin_token>
```

#### Send Notifications
```http
POST /admin/notifications
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "title": "System Maintenance",
  "message": "System will be down for maintenance",
  "receiver_id": 1 // or null for broadcast
}
```

### Medical Endpoints

#### Upload Test Report
```http
POST /medical/test-reports
Authorization: Bearer <lab_tech_token>
Content-Type: application/json

{
  "appointment_id": 1,
  "patient_id": 1,
  "test_name": "Blood Test",
  "test_type": "blood",
  "result": "Normal",
  "normal_range": "120-129",
  "units": "mg/dL"
}
```

#### Record Vital Signs
```http
POST /medical/vital-signs
Authorization: Bearer <nurse_token>
Content-Type: application/json

{
  "patient_id": 1,
  "blood_pressure_systolic": 120,
  "blood_pressure_diastolic": 80,
  "heart_rate": 72,
  "temperature": 36.6,
  "oxygen_saturation": 98.5
}
```

### Billing Endpoints

#### Create Bill
```http
POST /billing/bills
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "patient_id": 1,
  "appointment_id": 1,
  "total_amount": 150.0,
  "due_date": "2025-12-01",
  "items": [
    {
      "description": "Consultation Fee",
      "quantity": 1,
      "unit_price": 150.0,
      "type": "consultation"
    }
  ]
}
```

#### Process Payment
```http
POST /billing/bills/{bill_id}/pay
Authorization: Bearer <patient_token>
Content-Type: application/json

{
  "payment_method": "online", // cash, card, insurance, online
  "amount": 150.0
}
```

### Inventory Endpoints

#### Add Medicine
```http
POST /inventory/medicines
Authorization: Bearer <pharmacist_token>
Content-Type: application/json

{
  "name": "Paracetamol",
  "generic_name": "Acetaminophen",
  "category": "tablet",
  "manufacturer": "Pharma Inc",
  "expiry_date": "2025-12-31",
  "unit_price": 5.0,
  "prescription_required": false,
  "initial_stock": 100
}
```

#### Update Stock
```http
PUT /inventory/inventory/{medicine_id}/update-stock
Authorization: Bearer <pharmacist_token>
Content-Type: application/json

{
  "quantity": 50,
  "operation": "add" // add, remove, set
}
```

#### Dispense Prescription
```http
PUT /inventory/prescriptions/{prescription_id}/dispense
Authorization: Bearer <pharmacist_token>
```

---

## 🔐 Authentication Flow

### JWT Token System
- **Token Lifetime**: 24 hours
- **Automatic Refresh**: Manual re-login required
- **Storage**: Frontend should store in secure storage (httpOnly cookies recommended)

### Frontend Authentication Implementation

```javascript
// Authentication service example
class AuthService {
  static async login(email, password) {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('token', data.token);
      localStorage.setItem('user', JSON.stringify(data.user));
      return data;
    }
    throw new Error('Login failed');
  }

  static getToken() {
    return localStorage.getItem('token');
  }

  static getUser() {
    return JSON.parse(localStorage.getItem('user') || 'null');
  }

  static isAuthenticated() {
    return !!this.getToken();
  }

  static logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }
}

// API service with auth headers
class ApiService {
  static async request(endpoint, options = {}) {
    const token = AuthService.getToken();
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers,
      },
      ...options,
    };

    const response = await fetch(`/api${endpoint}`, config);
    
    if (response.status === 401) {
      AuthService.logout();
      window.location.href = '/login';
      return;
    }

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    return response.json();
  }
}
```

### Role-Based Route Protection (Frontend)

```javascript
// React example
const ProtectedRoute = ({ children, roles = [] }) => {
  const user = AuthService.getUser();
  
  if (!AuthService.isAuthenticated()) {
    return <Navigate to="/login" />;
  }

  if (roles.length > 0 && !roles.includes(user.role)) {
    return <Navigate to="/unauthorized" />;
  }

  return children;
};

// Usage
<Route 
  path="/doctor/*" 
  element={
    <ProtectedRoute roles={['doctor', 'admin']}>
      <DoctorLayout />
    </ProtectedRoute>
  } 
/>
```

---

## 🎯 Frontend Integration Guide

### 1. Setup and Configuration

#### Environment Variables
```javascript
// src/config.js
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';
export const ROLES = {
  PATIENT: 'patient',
  DOCTOR: 'doctor',
  ADMIN: 'admin',
  NURSE: 'nurse',
  LAB_TECHNICIAN: 'lab_technician',
  PHARMACIST: 'pharmacist'
};
```

#### API Service Layer
```javascript
// src/services/api.js
export class HealthcareAPI {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  async request(endpoint, options = {}) {
    const token = localStorage.getItem('token');
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers,
      },
      ...options,
    };

    const response = await fetch(`${this.baseURL}${endpoint}`, config);
    
    if (response.status === 401) {
      this.handleUnauthorized();
      throw new Error('Unauthorized');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Unknown error' }));
      throw new Error(error.message || 'Request failed');
    }

    return response.json();
  }

  handleUnauthorized() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
  }

  // Authentication methods
  async login(email, password) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
  }

  async register(userData) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData)
    });
  }

  async getProfile() {
    return this.request('/auth/profile');
  }

  // Patient methods
  async getDoctors(filters = {}) {
    const params = new URLSearchParams(filters);
    return this.request(`/patient/doctors?${params}`);
  }

  async bookAppointment(appointmentData) {
    return this.request('/patient/appointments', {
      method: 'POST',
      body: JSON.stringify(appointmentData)
    });
  }

  // Add similar methods for other endpoints...
}

export const api = new HealthcareAPI();
```

### 2. State Management

#### React Context Example
```javascript
// src/context/AuthContext.js
import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { api } from '../services/api';

const AuthContext = createContext();

const authReducer = (state, action) => {
  switch (action.type) {
    case 'LOGIN_SUCCESS':
      return {
        ...state,
        isAuthenticated: true,
        user: action.payload.user,
        token: action.payload.token
      };
    case 'LOGOUT':
      return {
        ...state,
        isAuthenticated: false,
        user: null,
        token: null
      };
    case 'UPDATE_USER':
      return {
        ...state,
        user: { ...state.user, ...action.payload }
      };
    default:
      return state;
  }
};

export const AuthProvider = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, {
    isAuthenticated: false,
    user: null,
    token: null
  });

  useEffect(() => {
    const token = localStorage.getItem('token');
    const user = JSON.parse(localStorage.getItem('user') || 'null');
    
    if (token && user) {
      dispatch({
        type: 'LOGIN_SUCCESS',
        payload: { user, token }
      });
    }
  }, []);

  const login = async (email, password) => {
    try {
      const data = await api.login(email, password);
      localStorage.setItem('token', data.token);
      localStorage.setItem('user', JSON.stringify(data.user));
      dispatch({ type: 'LOGIN_SUCCESS', payload: data });
      return data;
    } catch (error) {
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    dispatch({ type: 'LOGOUT' });
  };

  const updateProfile = async (profileData) => {
    const data = await api.updateProfile(profileData);
    dispatch({ type: 'UPDATE_USER', payload: data.user });
    return data;
  };

  return (
    <AuthContext.Provider value={{
      ...state,
      login,
      logout,
      updateProfile
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

### 3. Component Examples

#### Login Component
```javascript
// src/components/Login.js
import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

const Login = () => {
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      await login(formData.email, formData.password);
      // Redirect handled in context
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="Email"
          value={formData.email}
          onChange={(e) => setFormData({...formData, email: e.target.value})}
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={formData.password}
          onChange={(e) => setFormData({...formData, password: e.target.value})}
          required
        />
        {error && <div className="error">{error}</div>}
        <button type="submit" disabled={loading}>
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>
    </div>
  );
};
```

#### Doctor List Component
```javascript
// src/components/DoctorList.js
import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

const DoctorList = () => {
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    search: '',
    specialization: ''
  });

  const loadDoctors = async () => {
    try {
      setLoading(true);
      const data = await api.getDoctors(filters);
      setDoctors(data.doctors);
    } catch (error) {
      console.error('Failed to load doctors:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDoctors();
  }, [filters]);

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  if (loading) return <div>Loading doctors...</div>;

  return (
    <div>
      <div className="filters">
        <input
          type="text"
          placeholder="Search doctors..."
          value={filters.search}
          onChange={(e) => handleFilterChange('search', e.target.value)}
        />
        <select
          value={filters.specialization}
          onChange={(e) => handleFilterChange('specialization', e.target.value)}
        >
          <option value="">All Specializations</option>
          <option value="Cardiology">Cardiology</option>
          <option value="Pediatrics">Pediatrics</option>
          {/* Add more options */}
        </select>
      </div>

      <div className="doctors-grid">
        {doctors.map(doctor => (
          <div key={doctor.id} className="doctor-card">
            <h3>Dr. {doctor.user.first_name} {doctor.user.last_name}</h3>
            <p>Specialization: {doctor.specialization}</p>
            <p>Experience: {doctor.years_of_experience} years</p>
            <p>Fee: ${doctor.consultation_fee}</p>
            <button onClick={() => /* Navigate to booking */}>
              Book Appointment
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
```

### 4. Dashboard Examples

#### Patient Dashboard
```javascript
// src/components/patient/Dashboard.js
import React, { useState, useEffect } from 'react';
import { api } from '../../services/api';

const PatientDashboard = () => {
  const [stats, setStats] = useState({
    upcomingAppointments: 0,
    pendingBills: 0,
    medicalRecords: 0
  });
  const [recentAppointments, setRecentAppointments] = useState([]);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [appointmentsRes, billsRes] = await Promise.all([
        api.request('/patient/appointments?status=confirmed'),
        api.request('/patient/bills?status=pending')
      ]);

      setStats({
        upcomingAppointments: appointmentsRes.appointments.length,
        pendingBills: billsRes.bills.length,
        medicalRecords: 0 // You might need a separate endpoint for this
      });

      setRecentAppointments(appointmentsRes.appointments.slice(0, 5));
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    }
  };

  return (
    <div className="dashboard">
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Upcoming Appointments</h3>
          <div className="stat-number">{stats.upcomingAppointments}</div>
        </div>
        <div className="stat-card">
          <h3>Pending Bills</h3>
          <div className="stat-number">{stats.pendingBills}</div>
        </div>
        <div className="stat-card">
          <h3>Medical Records</h3>
          <div className="stat-number">{stats.medicalRecords}</div>
        </div>
      </div>

      <div className="recent-appointments">
        <h3>Recent Appointments</h3>
        {recentAppointments.map(appointment => (
          <div key={appointment.id} className="appointment-item">
            <span>Dr. {appointment.doctor.user.last_name}</span>
            <span>{new Date(appointment.appointment_date).toLocaleDateString()}</span>
            <span className={`status ${appointment.status}`}>{appointment.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## ⚠️ Error Handling

### Common HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `500` - Internal Server Error

### Error Response Format
```json
{
  "message": "Error description",
  "errors": {
    "field_name": ["Error message"]
  }
}
```

### Frontend Error Handling
```javascript
// src/utils/errorHandler.js
export class HealthcareError extends Error {
  constructor(message, code, details = {}) {
    super(message);
    this.name = 'HealthcareError';
    this.code = code;
    this.details = details;
  }
}

export const handleAPIError = (error) => {
  if (error instanceof HealthcareError) {
    return error;
  }

  if (error.message.includes('Network Error')) {
    return new HealthcareError('Network connection failed', 'NETWORK_ERROR');
  }

  return new HealthcareError(
    'An unexpected error occurred', 
    'UNKNOWN_ERROR',
    { originalError: error.message }
  );
};
```

---

## 🧪 Testing Guide

### API Testing with Postman

#### Collection Structure
```
Healthcare API/
├── Authentication/
│   ├── Register User
│   ├── Login User
│   └── Get Profile
├── Patient/
│   ├── Get Doctors
│   ├── Book Appointment
│   └── Get Appointments
├── Doctor/
│   ├── Get Appointments
│   ├── Add Diagnosis
│   └── Prescribe Medicine
└── Admin/
    ├── Dashboard Stats
    └── Manage Users
```

#### Environment Variables
```javascript
// Postman Environment
{
  "base_url": "http://localhost:5000/api",
  "patient_token": "{{patient_jwt}}",
  "doctor_token": "{{doctor_jwt}}", 
  "admin_token": "{{admin_jwt}}"
}
```

### Frontend Testing

#### Component Testing Example
```javascript
// src/components/__tests__/Login.test.js
import { render, screen, fireEvent } from '@testing-library/react';
import { AuthProvider } from '../../context/AuthContext';
import Login from '../Login';

const MockLogin = () => (
  <AuthProvider>
    <Login />
  </AuthProvider>
);

test('login form submits correctly', async () => {
  render(<MockLogin />);
  
  fireEvent.change(screen.getByPlaceholderText('Email'), {
    target: { value: 'test@example.com' }
  });
  
  fireEvent.change(screen.getByPlaceholderText('Password'), {
    target: { value: 'password123' }
  });
  
  fireEvent.click(screen.getByRole('button', { name: 'Login' }));
  
  // Add your assertions here
});
```

---

## 🚀 Deployment Guide

### Production Environment Variables
```env
FLASK_CONFIG=production
SECRET_KEY=your-production-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
DATABASE_URL=postgresql://user:pass@localhost/healthcare
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### Frontend Build Configuration
```javascript
// package.json scripts
{
  "build": "react-scripts build",
  "build:prod": "REACT_APP_API_URL=https://api.yourdomain.com npm run build"
}
```

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        root /var/www/frontend/build;
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📞 Support & Resources

### Useful Links
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [JWT Introduction](https://jwt.io/introduction)
- [React Documentation](https://reactjs.org/docs)

### Common Issues & Solutions
1. **CORS Issues**: Ensure CORS is configured in Flask
2. **JWT Expiry**: Implement token refresh logic
3. **File Uploads**: Use FormData for file uploads
4. **Real-time Updates**: Consider WebSocket implementation

### Getting Help
- Check API responses in browser Network tab
- Use Postman for API testing
- Review server logs for errors
- Validate request/response formats
