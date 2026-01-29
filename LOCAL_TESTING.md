# Local Testing Guide for ARKA Backend

Complete guide for setting up and running local testing for the AWS serverless backend with **zero risk** to production.

## 🔒 Safety First

**CRITICAL**: This setup is designed with hard safety guards:

- ✅ Production AWS resources remain **completely untouched**
- ✅ Local testing is **explicitly opt-in** via `APP_ENV=local`
- ✅ All table names have `-local` suffix
- ✅ Dummy credentials only (`local/local`)
- ✅ Scripts refuse to run without `APP_ENV=local`

## Prerequisites

1. **Docker Desktop** - For running DynamoDB Local and LocalStack
2. **Node.js** - For serverless offline
3. **Python 3.12** - For Lambda functions
4. **AWS CLI** (optional) - For manual DynamoDB inspection

## Quick Start (One Command)

```bash
# Install dependencies first
npm install

# Start everything (services + setup + serverless offline)
npm run local:all
```

This will:

1. Start Docker containers (DynamoDB Local + LocalStack)
2. Wait 5 seconds for services to initialize
3. Create all DynamoDB tables with GSIs
4. Create S3 bucket in LocalStack
5. Seed test data
6. Start serverless offline on http://localhost:3000

## Step-by-Step Setup

### 1. Install Dependencies

```bash
# Install Node dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Start Local Services

```bash
# Start DynamoDB Local and LocalStack
npm run local:services
```

This starts:

- **DynamoDB Local** on `http://localhost:8000`
- **LocalStack** (S3) on `http://localhost:4566`
- **DynamoDB Admin UI** on `http://localhost:8001` (optional web UI)

### 3. Create Tables and Seed Data

```bash
# Create all DynamoDB tables
npm run setup-tables

# Create S3 bucket in LocalStack
npm run setup-s3

# Seed test data
npm run seed-data

# Or run all setup at once
npm run local:setup
```

### 4. Verify Setup

```bash
# Run verification checks
npm run verify-local
```

This verifies:

- ✅ `APP_ENV=local` is set
- ✅ All endpoints point to localhost
- ✅ All table names end with `-local`
- ✅ Services are running
- ✅ No production AWS access

### 5. Start Serverless Offline

```bash
# Start the API server
npm run local:start
```

API will be available at: **http://localhost:3000**

### 6. Start with Uvicorn (Alternative)

For faster development cycles (hot reload) and Python-native debugging:

```bash
# Run uvicorn with local environment settings
uvicorn app:app --reload --env-file .env.local
```

API will be available at: **http://localhost:8000**

## Test Credentials

After seeding data, use these credentials:

### Admin

- **Email**: `admin@arka.local`
- **Password**: `admin123`

### Inspector

- **Email**: `inspector1@arka.local`
- **Password**: `inspector123`

### Crew

- **Email**: `crew1@arka.local`
- **Password**: `crew123`

## Testing the API

### Register a New Admin

```bash
curl -X POST http://localhost:3000/admins/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"newadmin@test.local\",\"password\":\"test123\",\"name\":\"New Admin\"}"
```

### Login

```bash
curl -X POST http://localhost:3000/admins/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"admin@arka.local\",\"password\":\"admin123\"}"
```

Save the returned `access_token` for authenticated requests.

### Get Admin Profile

```bash
curl http://localhost:3000/admin/profile \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create a Vessel

```bash
curl -X POST http://localhost:3000/vessels \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d "{\"ship_id\":\"SHIP-003\",\"name\":\"Test Vessel\",\"type\":\"Cargo\",\"imo_number\":\"IMO9999999\",\"flag\":\"USA\"}"
```

## Viewing Local Data

### DynamoDB Admin UI

Open http://localhost:8001 in your browser to view and edit tables visually.

### AWS CLI

```bash
# List all tables
aws dynamodb list-tables --endpoint-url http://localhost:8000 --region us-east-1

# Scan a table
aws dynamodb scan \
  --table-name arka-admins-local \
  --endpoint-url http://localhost:8000 \
  --region us-east-1

# Query by email (using GSI)
aws dynamodb query \
  --table-name arka-admins-local \
  --index-name email_index \
  --key-condition-expression "email = :email" \
  --expression-attribute-values '{":email":{"S":"admin@arka.local"}}' \
  --endpoint-url http://localhost:8000 \
  --region us-east-1
```

## NPM Scripts Reference

| Command                       | Description                                   |
| ----------------------------- | --------------------------------------------- |
| `npm run local:services`      | Start Docker services (DynamoDB + LocalStack) |
| `npm run local:services:stop` | Stop Docker services                          |
| `npm run setup-tables`        | Create DynamoDB tables                        |
| `npm run setup-s3`            | Create S3 bucket                              |
| `npm run seed-data`           | Populate test data                            |
| `npm run local:setup`         | Run all setup scripts                         |
| `npm run local:start`         | Start serverless offline                      |
| `npm run local:all`           | Complete bootstrap (services + setup + start) |
| `npm run verify-local`        | Verify local configuration                    |

## Safety Verification Checklist

Before running any local commands, verify:

- [ ] `APP_ENV=local` is set in `.env.local`
- [ ] All table names in `.env.local` end with `-local`
- [ ] S3 bucket name ends with `-local`
- [ ] AWS credentials are `local/local` (dummy values)
- [ ] `DYNAMODB_ENDPOINT=http://localhost:8000`
- [ ] `S3_ENDPOINT=http://localhost:4566`
- [ ] Running `npm run verify-local` passes all checks

## Troubleshooting

### Services won't start

```bash
# Check if ports are already in use
netstat -ano | findstr :8000
netstat -ano | findstr :4566

# Stop and restart services
npm run local:services:stop
npm run local:services
```

### Tables already exist error

```bash
# Stop services (this clears data)
npm run local:services:stop

# Start fresh
npm run local:all
```

### "SAFETY GUARD" error when running scripts

This is **intentional**. Scripts refuse to run without `APP_ENV=local` to protect production.

**Solution**: Use npm scripts which set `APP_ENV` automatically:

```bash
npm run setup-tables  # ✓ Sets APP_ENV automatically
python scripts/setup_local_tables.py  # ✗ Will fail
```

### Serverless offline won't start

```bash
# Check if .env.local exists
ls .env.local

# Verify APP_ENV is set
cross-env APP_ENV=local serverless offline start --stage local
```

### Can't connect to DynamoDB/LocalStack

```bash
# Verify services are running
docker ps

# Check logs
docker logs arka-dynamodb-local
docker logs arka-localstack
```

## Production Deployment

**IMPORTANT**: Local testing configuration does **NOT** affect production deployment.

When deploying to AWS:

1. `serverless.yml` remains unchanged
2. Production uses real AWS credentials (IAM roles)
3. Production table names have no `-local` suffix
4. `APP_ENV` defaults to `production` (or is not set)
5. No endpoint overrides are applied

Deploy normally:

```bash
# This uses production AWS, NOT local
serverless deploy --stage production
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Local Environment                     │
│                     (APP_ENV=local)                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Serverless Offline (Port 3000)                         │
│         │                                                │
│         ├─→ Lambda Functions (Python)                   │
│         │                                                │
│         ├─→ DynamoDB Local (Port 8000)                  │
│         │    └─ Tables: *-local                         │
│         │                                                │
│         └─→ LocalStack S3 (Port 4566)                   │
│              └─ Bucket: arka-media-local                │
│                                                          │
│  DynamoDB Admin UI (Port 8001) - Optional               │
│                                                          │
└─────────────────────────────────────────────────────────┘

                         vs

┌─────────────────────────────────────────────────────────┐
│                 Production Environment                   │
│                  (APP_ENV=production)                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  API Gateway                                             │
│         │                                                │
│         ├─→ Lambda Functions (AWS)                      │
│         │                                                │
│         ├─→ DynamoDB (AWS)                              │
│         │    └─ Tables: arka-*                          │
│         │                                                │
│         └─→ S3 (AWS)                                    │
│              └─ Bucket: arka-media                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Key Files

- **`.env.local`** - Local environment configuration (APP_ENV=local)
- **`docker-compose.yml`** - DynamoDB Local + LocalStack services
- **`config/aws.py`** - AWS client initialization with APP_ENV guards
- **`config/settings.py`** - Settings with APP_ENV field
- **`scripts/setup_local_tables.py`** - Table creation script
- **`scripts/setup_s3_bucket.py`** - S3 bucket creation script
- **`scripts/seed_test_data.py`** - Test data seeding script
- **`scripts/verify_local_setup.py`** - Safety verification script

## Support

If you encounter issues:

1. Run `npm run verify-local` to diagnose
2. Check Docker logs: `docker logs arka-dynamodb-local`
3. Ensure `.env.local` has `APP_ENV=local`
4. Verify all services are running: `docker ps`
