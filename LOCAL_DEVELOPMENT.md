# Local Development Guide for ARKA Backend

Complete guide for running the ARKA FastAPI backend locally.

## 🚀 Quick Start

The ARKA backend uses **FastAPI** with **uvicorn** for local development.

### Prerequisites

1. **Python 3.9+** - For running the FastAPI application
2. **AWS Credentials** - Configured for DynamoDB and S3 access
3. **DynamoDB Tables** - Created in your AWS account
4. **S3 Bucket** - Created for media storage

### Start the Server

```bash
# 1. Activate virtual environment
venv\Scripts\activate  # On Windows
source venv/bin/activate  # On macOS/Linux

# 2. Start the FastAPI server
uvicorn app:app --reload --port 8000
```

The API will be available at: **http://localhost:8000**

- **API Documentation (Swagger)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc

## 📋 Step-by-Step Setup

### 1. Install Dependencies

```bash
# Create virtual environment (if not exists)
python -m venv venv

# Activate virtual environment
venv\Scripts\activate  # On Windows
source venv/bin/activate  # On macOS/Linux

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the `backend-development` directory:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# DynamoDB Tables
DYNAMODB_TABLE_INSPECTORS=arka-inspectors
DYNAMODB_TABLE_ADMINS=arka-admins
DYNAMODB_TABLE_VESSELS=arka-vessels
DYNAMODB_TABLE_INSPECTION_FORMS=arka-inspection-forms
DYNAMODB_TABLE_INSPECTION_ASSIGNMENTS=arka-inspection-assignments
DYNAMODB_TABLE_INSPECTION_RESPONSES=arka-inspection-responses
DYNAMODB_TABLE_CREW=arka-crew
DYNAMODB_TABLE_DEFECTS=arka-defects

# S3
S3_MEDIA_BUCKET=arka-media-bucket

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_MINUTES=43200

# App Settings
APP_NAME=ARKA Backend
APP_VERSION=1.0.0
DEBUG=True
```

### 3. Start the Development Server

```bash
# Make sure virtual environment is activated
uvicorn app:app --reload --port 8000
```

You should see output like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345]
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 4. Verify the Server is Running

Open your browser or use curl:

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
{"status":"healthy","message":"API is running properly"}

# Root endpoint
curl http://localhost:8000/

# Expected response:
{"message":"Welcome","status":"running"}
```

## 🧪 Testing the API

### Using Swagger UI (Recommended)

1. Open http://localhost:8000/docs in your browser
2. You'll see interactive API documentation
3. Click on any endpoint to expand it
4. Click "Try it out" to test the endpoint
5. Fill in parameters and click "Execute"

### Using curl

#### Register a New Admin

```bash
curl -X POST http://localhost:8000/admin/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@test.com",
    "password": "admin123",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

#### Login

```bash
curl -X POST http://localhost:8000/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@test.com",
    "password": "admin123"
  }'
```

Save the returned `access_token` for authenticated requests.

#### Create an Inspection Assignment (with inspection_name)

```bash
curl -X POST http://localhost:8000/inspection-assignments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "inspection_name": "Monthly Safety Inspection - January 2026",
    "form_id": "your-form-id",
    "vessel_id": "your-vessel-id",
    "assignee_id": "your-inspector-id",
    "assignee_type": "inspector",
    "role": "Lead Inspector",
    "priority": "High",
    "due_date": "2026-01-31T00:00:00Z"
  }'
```

#### Get Admin Profile

```bash
curl http://localhost:8000/admin/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 🔧 Development Tips

### Auto-Reload

The `--reload` flag enables auto-reload. Any changes to Python files will automatically restart the server.

### Custom Port

To run on a different port:

```bash
uvicorn app:app --reload --port 3001
```

### Debug Mode

Set `DEBUG=True` in your `.env` file to enable detailed error messages.

### CORS Configuration

The app is configured to allow requests from `http://localhost:3000` (frontend). To add more origins, edit `app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",  # Add more as needed
    ],
    # ...
)
```

## 📁 Project Structure

```
backend-development/
├── app.py                 # FastAPI application entry point
├── config/                # Configuration and settings
├── models/                # Pydantic models (DB, Request, Response)
├── routers/               # API route handlers
├── services/              # Business logic layer
├── repository/            # Data access layer (DynamoDB)
├── utility/               # Helper functions
├── requirements.txt       # Python dependencies
└── .env                   # Environment variables (create this)
```

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Windows: Find and kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <process-id> /F

# macOS/Linux: Find and kill process
lsof -ti:8000 | xargs kill -9
```

### Module Not Found Errors

```bash
# Ensure virtual environment is activated
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Reinstall dependencies
pip install -r requirements.txt
```

### AWS Credentials Error

Make sure your `.env` file has valid AWS credentials, or configure AWS CLI:

```bash
aws configure
```

### DynamoDB Table Not Found

Verify your table names in `.env` match the actual table names in your AWS account.

## 🚀 Production Deployment

For production deployment to AWS Lambda, use:

```bash
serverless deploy --stage production
```

This uses the `serverless.yml` configuration and deploys to AWS Lambda + API Gateway.

## 📚 Additional Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Uvicorn Documentation**: https://www.uvicorn.org/
- **Swagger UI**: http://localhost:8000/docs (when server is running)
- **ReDoc**: http://localhost:8000/redoc (when server is running)

## ✅ Verification Checklist

Before starting development, verify:

- [ ] Virtual environment is activated
- [ ] `.env` file exists with all required variables
- [ ] AWS credentials are valid
- [ ] DynamoDB tables exist in AWS
- [ ] S3 bucket exists in AWS
- [ ] Dependencies are installed (`pip install -r requirements.txt`)
- [ ] Server starts without errors (`uvicorn app:app --reload --port 8000`)
- [ ] Health check responds (`curl http://localhost:8000/health`)
- [ ] Swagger UI loads (`http://localhost:8000/docs`)

## 🆕 Recent Changes

### Inspection Name Field (2026-01-10)

Added support for custom inspection names:

- New `inspection_name` field in inspection assignments
- Optional field - backward compatible with existing assignments
- Can be provided during assignment creation
- Displayed in API responses

**Example**:

```json
{
  "inspection_name": "Monthly Safety Check - January 2026",
  "form_id": "...",
  "vessel_id": "...",
  ...
}
```
