# KHM Backend Development

A **serverless maritime inspection management system** built with **Python** for **AWS Lambda** with **API Gateway**. The system manages vessel inspections, inspectors, crew members, and inspection workflows.

---

##Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│                      (localhost:3000)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AWS API Gateway                             │
│              (Routes requests to Lambda handlers)                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Lambda Handlers (Routers)                     │
│   auth.py │ admin_auth.py │ vessel.py │ crew.py │ etc.          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Service Layer                              │
│  inspector_service │ admin_service │ vessel_service │ etc.      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Repository Layer                             │
│  inspector_repository │ admin_repository │ vessel_repository    │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│     AWS DynamoDB        │     │        AWS S3           │
│   (6 Tables - NoSQL)    │     │   (Document Storage)    │
└─────────────────────────┘     └─────────────────────────┘
```

---

##Project Structure

| Directory | Purpose |
|-----------|---------|
| `app.py` | FastAPI app entry point (for local development) |
| `config/` | Settings, AWS clients, JWT configuration |
| `models/` | Pydantic data models for DB, requests, and responses |
| `routers/` | Lambda handler functions (API endpoints) |
| `services/` | Business logic layer |
| `repository/` | Data access layer (DynamoDB operations) |
| `utility/` | Shared utilities (CORS, S3, error handling, etc.) |

---

##Database Schema (DynamoDB)

The system uses **6 DynamoDB tables**:

### 1. Inspectors Table (`DYNAMODB_TABLE_INSPECTORS`)

| Field | Type | Description |
|-------|------|-------------|
| `inspector_id` | String (PK) | UUID primary key |
| `email` | String (GSI) | Login credential |
| `first_name` | String | Inspector's first name |
| `last_name` | String | Inspector's last name |
| `phone_number` | String | Contact number |
| `password_hash` | String | Bcrypt hashed password |
| `role` | String | Inspector role |
| `company_code` | String | Company identifier |
| `id_proof_url` | String | S3 URL for ID document |
| `address_proof_url` | String | S3 URL for address proof |
| `additional_docs` | List | Additional document URLs |
| `created_at` / `updated_at` | String | ISO8601 timestamps |

### 2. Admins Table (`DYNAMODB_TABLE_ADMINS`)

| Field | Type | Description |
|-------|------|-------------|
| `admin_id` | String (PK) | UUID primary key |
| `email` | EmailStr (GSI) | Login credential |
| `password_hash` | String | Bcrypt hashed password |
| `first_name` | String | Admin's first name |
| `last_name` | String | Admin's last name |
| `created_at` / `updated_at` | String | ISO8601 timestamps |

### 3. Vessels Table (`DYNAMODB_TABLE_VESSELS`)

| Field | Type | Description |
|-------|------|-------------|
| `vessel_id` | String (PK) | UUID primary key |
| `admin_id` | String (GSI) | Owner/manager admin |
| `name` | String | Vessel name |
| `vessel_type` | String | Type (Bulk Carrier, Tanker, etc.) |
| `other_vessel_type` | String | Custom type when "Other" |
| `imo_number` | String | International Maritime Organization number |
| `status` | String | Status (active, inactive) |
| `created_at` / `updated_at` | String | ISO8601 timestamps |

### 4. Crew Table (`DYNAMODB_TABLE_CREW`)

| Field | Type | Description |
|-------|------|-------------|
| `crew_id` | String (PK) | UUID primary key |
| `first_name` | String | Crew member's first name |
| `last_name` | String | Crew member's last name |
| `email` | String | Login credential |
| `phone_number` | String | Contact number |
| `password_hash` | String | Bcrypt hashed password |
| `role` | String | Crew role |
| `company_code` | String | Company identifier |
| `id_proof_url` | String | S3 URL for ID document |
| `address_proof_url` | String | S3 URL for address proof |
| `additional_docs` | List | Additional document URLs |
| `created_at` / `updated_at` | String | ISO8601 timestamps |

### 5. Inspection Forms Table (`DYNAMODB_TABLE_INSPECTION_FORMS`)

| Field | Type | Description |
|-------|------|-------------|
| `form_id` | String (PK) | UUID primary key |
| `vessel_id` | String | Vessel this form belongs to |
| `created_by_admin_id` | String | Admin who created the form |
| `ship_id` | String | Optional ship reference |
| `title` | String | Form title |
| `description` | String | Form description |
| `status` | String | Form status (pending, in_progress, completed) |
| `assigned_inspector_id` | String | Assigned inspector |
| `assigned_crew_id` | String | Assigned crew member |
| `due_date` | String | ISO8601 due date |
| `last_synced_at` | String | Last sync timestamp |
| `questions` | List[Dict] | Ordered list of questions |
| `created_at` / `updated_at` | String | ISO8601 timestamps |

### 6. Inspection Assignments Table (`DYNAMODB_TABLE_INSPECTION_ASSIGNMENTS`)

| Field | Type | Description |
|-------|------|-------------|
| `assignment_id` | String (PK) | UUID primary key |
| `form_id` | String | Reference to inspection form |
| `vessel_id` | String | Optional vessel reference |
| `created_by_admin_id` | String | Admin who created assignment |
| `assignee_id` | String | Crew or inspector ID |
| `assignee_type` | String | Either "crew" or "inspector" |
| `role` | String | Role for the inspection |
| `priority` | String | Priority (low, medium, high) |
| `due_date` | String | ISO8601 due date |
| `status` | String | Status (assigned, in_progress, completed) |
| `created_at` / `updated_at` | String | ISO8601 timestamps |

---

## Authentication & Security

### JWT Token System

- Uses **HS256 algorithm** for signing tokens
- **Access Token**: 15 minutes expiry (configurable)
- **Refresh Token**: 30 days expiry (configurable)
- Token payload includes: `sub` (user ID), `type`, `email`, `role`, `iat`, `exp`

### Authentication Flow

```
1. User registers/logs in → Server validates credentials
2. Server generates access + refresh token pair
3. Client sends "Authorization: Bearer <token>" header
4. Server validates token and extracts user identity
```

### Password Security

- Uses **bcrypt** for password hashing

---

## API Endpoints

### Inspector Authentication (`routers/auth.py`)

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| POST | `/inspector/register` | `register_handler` | Register new inspector |
| POST | `/inspector/login` | `login_handler` | Inspector login |
| GET | `/inspector/profile/{id}` | `profile_handler` | Get inspector profile |

### Admin Authentication (`routers/admin_auth.py`)

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| POST | `/admin/register` | `admin_register_handler` | Register new admin |
| POST | `/admin/login` | `admin_login_handler` | Admin login |
| GET | `/admin/profile/{id}` | `admin_profile_handler` | Get admin profile |
| GET | `/admin/me` | `admin_me_handler` | Get current admin (from token) |

### Vessel Management (`routers/vessel.py`)

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| POST | `/vessels` | `create_vessel_handler` | Create vessel (admin auth) |
| GET | `/vessels` | `list_vessels_handler` | List admin's vessels with pagination |
| GET | `/vessels/{id}` | `get_vessel_handler` | Get specific vessel |

### Crew Management (`routers/crew.py`)

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| POST | `/crew` | `create_crew_handler` | Create crew member (supports file uploads) |
| GET | `/crew/{id}` | `get_crew_handler` | Get crew member |
| GET | `/crew` | `list_crew_handler` | List crew with pagination |
| POST | `/crew/register` | `register_crew_handler` | Self-registration for crew |
| POST | `/crew/login` | `login_crew_handler` | Crew login |

### Admin Inspector Management (`routers/admin_inspector.py`)

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| POST | `/admin/inspectors` | `admin_create_inspector_handler` | Admin creates inspector (with docs) |
| GET | `/admin/inspectors/{id}` | `admin_get_inspector_handler` | Get inspector by ID |
| GET | `/admin/inspectors` | `admin_list_inspectors_handler` | List all inspectors |

### Inspection Forms (`routers/inspection_form.py`)

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| POST | `/inspection-forms` | `create_inspection_form_handler` | Create inspection form |
| GET | `/inspection-forms/{id}` | `get_inspection_form_handler` | Get form by ID |
| GET | `/inspection-forms` | `list_inspection_forms_handler` | List forms (by vessel or admin) |
| GET | `/inspector/forms` | `list_inspector_forms_handler` | List forms for inspector |
| POST | `/inspection-forms/{form_id}/submit` | `submit_inspection_form_handler` | Submit form answers |

### Inspection Assignments (`routers/inspection_assignment.py`)

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| POST | `/inspection-assignments` | `create_inspection_assignment_handler` | Create assignment |
| GET | `/inspection-assignments/{id}` | `get_inspection_assignment_handler` | Get assignment |
| GET | `/inspection-assignments` | `list_inspection_assignments_handler` | List assignments |
| GET | `/inspector/assignments` | `list_inspector_assignments_handler` | List inspector's assignments |
| POST | `/inspection-assignments/bulk` | `bulk_create_inspection_assignment_handler` | Bulk create assignments |
| POST | `/crew/{crew_id}/assignments` | `create_crew_inspection_assignment_handler` | Assign to crew |
| GET | `/crew/assignments` | `list_crew_assignments_handler` | List crew's assignments |

### File Upload (`routers/upload.py`)

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| POST | `/upload/presign` | `presign_upload_handler` | Get pre-signed S3 upload URL |

---

## AWS Integrations

### AWS DynamoDB

- NoSQL database for all data storage
- Uses `boto3.resource("dynamodb")` for table operations
- Supports scan with pagination for list operations

### AWS S3

- Stores documents (ID proofs, address proofs, inspection images)
- Supports both:
  - **Pre-signed URLs** for client-side uploads
  - **Direct uploads** from Lambda for inline file handling
- Bucket configured via `S3_MEDIA_BUCKET` environment variable

### File Upload Flow

```
Option 1 (Pre-signed):
Client → Request presigned URL → Upload directly to S3

Option 2 (Direct via Lambda):
Client → Multipart form data → Lambda → S3
```

---

## Utility Functions

| Utility | File | Purpose |
|---------|------|---------|
| `cors_middleware` | `utility/cors.py` | Adds CORS headers to Lambda responses |
| `parse_json_body` | `utility/body_parser.py` | Parses API Gateway event body |
| `parse_multipart_form_data` | `utility/multipart_parser.py` | Handles file uploads |
| `handle_error` | `utility/error_handler.py` | Standardized error responses |
| `format_response` | `utility/response.py` | Standard API response format |
| `upload_file_to_s3` | `utility/s3_utils.py` | Direct S3 file upload |
| `generate_presigned_put_url` | `utility/s3_utils.py` | Generate upload URLs |
| `sign_s3_url_if_possible` | `utility/s3_utils.py` | Sign S3 URLs for secure access |

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Runtime | Python 3.x |
| Framework | FastAPI (local) / AWS Lambda (production) |
| Database | AWS DynamoDB |
| File Storage | AWS S3 |
| Auth | JWT (PyJWT) + bcrypt |
| Validation | Pydantic |
| AWS SDK | boto3 / botocore |
| Testing | pytest |

---

## Environment Variables

Create a `.env` file with the following variables:

```bash
AWS_REGION=<aws-region>
AWS_ACCESS_KEY_ID=<optional-for-local-dev>
AWS_SECRET_ACCESS_KEY=<optional-for-local-dev>

# DynamoDB Tables
DYNAMODB_TABLE_INSPECTORS=<table-name>
DYNAMODB_TABLE_ADMINS=<table-name>
DYNAMODB_TABLE_VESSELS=<table-name>
DYNAMODB_TABLE_INSPECTION_FORMS=<table-name>
DYNAMODB_TABLE_INSPECTION_ASSIGNMENTS=<table-name>
DYNAMODB_TABLE_CREW=<table-name>

# S3
S3_MEDIA_BUCKET=<bucket-name>

# JWT
JWT_SECRET_KEY=<secret-key>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_MINUTES=43200
```

---

## Getting Started

### Prerequisites

- Python 3.9+
- AWS CLI configured with appropriate credentials
- DynamoDB tables created
- S3 bucket created

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd backend-development

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with required variables
cp .env.example .env
# Edit .env with your values

# Run locally with FastAPI
uvicorn app:app --reload --port 8000
```

### Running Tests

```bash
pytest
```

---

## Typical Workflow

1. **Admin Registration/Login** → Gets JWT tokens
2. **Admin Creates Vessels** → Registers ships they manage
3. **Admin Creates Inspectors/Crew** → With documents (uploaded to S3)
4. **Admin Creates Inspection Forms** → With ordered questions
5. **Admin Creates Assignments** → Links forms to inspectors/crew
6. **Inspectors/Crew Login** → Get their assignments
7. **Inspectors/Crew Submit Forms** → Answers (including images) saved

---

## 📄 License

This project is proprietary and confidential.
