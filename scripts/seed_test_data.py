#!/usr/bin/env python3
"""
Script to seed test data into local DynamoDB tables.

SAFETY: This script will ONLY run when APP_ENV=local is explicitly set.
"""
import os
import sys
import uuid
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

# CRITICAL SAFETY CHECK: Refuse to run unless APP_ENV is explicitly 'local'
if os.getenv('APP_ENV', '').lower() != 'local':
    print("=" * 70)
    print("SAFETY GUARD: This script only runs when APP_ENV=local")
    print("=" * 70)
    print("\nThis prevents accidental modification of production AWS resources.")
    print("\nTo run this script, set APP_ENV=local:")
    print("  Windows: set APP_ENV=local && python scripts/seed_test_data.py")
    print("  Linux/Mac: APP_ENV=local python scripts/seed_test_data.py")
    print("\nOr use: npm run seed-data (which sets APP_ENV automatically)")
    print("=" * 70)
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import bcrypt

# Load local environment variables
load_dotenv('.env.local')

# Initialize DynamoDB resource for local
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url=os.getenv('DYNAMODB_ENDPOINT', 'http://localhost:8000'),
    region_name=os.getenv('AWS_REGION', 'us-east-1'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'local'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'local')
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def seed_admins():
    """Seed test admin users."""
    table = dynamodb.Table(os.getenv('DYNAMODB_TABLE_ADMINS'))
    
    admins = [
        {
            'admin_id': str(uuid.uuid4()),
            'email': 'admin@arka.local',
            'password': hash_password('admin123'),
            'name': 'Test Admin',
            'created_at': datetime.utcnow().isoformat()
        }
    ]
    
    for admin in admins:
        try:
            table.put_item(Item=admin)
            print(f"✓ Created admin: {admin['email']}")
        except ClientError as e:
            print(f"✗ Error creating admin {admin['email']}: {str(e)}")
    
    return admins


def seed_inspectors():
    """Seed test inspectors."""
    table = dynamodb.Table(os.getenv('DYNAMODB_TABLE_INSPECTORS'))
    
    inspectors = [
        {
            'inspector_id': str(uuid.uuid4()),
            'email': 'inspector1@arka.local',
            'password': hash_password('inspector123'),
            'name': 'John Inspector',
            'phone': '+1234567890',
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'inspector_id': str(uuid.uuid4()),
            'email': 'inspector2@arka.local',
            'password': hash_password('inspector123'),
            'name': 'Jane Inspector',
            'phone': '+1234567891',
            'created_at': datetime.utcnow().isoformat()
        }
    ]
    
    for inspector in inspectors:
        try:
            table.put_item(Item=inspector)
            print(f"✓ Created inspector: {inspector['email']}")
        except ClientError as e:
            print(f"✗ Error creating inspector {inspector['email']}: {str(e)}")
    
    return inspectors


def seed_crew():
    """Seed test crew members."""
    table = dynamodb.Table(os.getenv('DYNAMODB_TABLE_CREW'))
    
    crew_members = [
        {
            'crew_id': str(uuid.uuid4()),
            'email': 'crew1@arka.local',
            'password': hash_password('crew123'),
            'name': 'Mike Crew',
            'role': 'Engineer',
            'created_at': datetime.utcnow().isoformat()
        }
    ]
    
    for crew in crew_members:
        try:
            table.put_item(Item=crew)
            print(f"✓ Created crew member: {crew['email']}")
        except ClientError as e:
            print(f"✗ Error creating crew {crew['email']}: {str(e)}")
    
    return crew_members


def seed_vessels(admin_id):
    """Seed test vessels."""
    table = dynamodb.Table(os.getenv('DYNAMODB_TABLE_VESSELS'))
    
    vessels = [
        {
            'vessel_id': str(uuid.uuid4()),
            'ship_id': 'SHIP-001',
            'admin_id': admin_id,
            'name': 'MV Test Vessel 1',
            'type': 'Cargo',
            'imo_number': 'IMO1234567',
            'flag': 'USA',
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'vessel_id': str(uuid.uuid4()),
            'ship_id': 'SHIP-002',
            'admin_id': admin_id,
            'name': 'MV Test Vessel 2',
            'type': 'Tanker',
            'imo_number': 'IMO7654321',
            'flag': 'UK',
            'created_at': datetime.utcnow().isoformat()
        }
    ]
    
    for vessel in vessels:
        try:
            table.put_item(Item=vessel)
            print(f"✓ Created vessel: {vessel['name']}")
        except ClientError as e:
            print(f"✗ Error creating vessel {vessel['name']}: {str(e)}")
    
    return vessels


def seed_inspection_forms(admin_id, vessel_id):
    """Seed test inspection forms."""
    table = dynamodb.Table(os.getenv('DYNAMODB_TABLE_INSPECTION_FORMS'))
    
    forms = [
        {
            'form_id': str(uuid.uuid4()),
            'vessel_id': vessel_id,
            'created_by_admin_id': admin_id,
            'form_name': 'Safety Inspection Form',
            'status': 'open',
            'questions': [
                {
                    'question_id': 'q1',
                    'question_text': 'Are all fire extinguishers in working condition?',
                    'question_type': 'yes_no'
                },
                {
                    'question_id': 'q2',
                    'question_text': 'Upload photo of emergency equipment',
                    'question_type': 'image'
                },
                {
                    'question_id': 'q3',
                    'question_text': 'Additional notes',
                    'question_type': 'text'
                }
            ],
            'created_at': datetime.utcnow().isoformat()
        }
    ]
    
    for form in forms:
        try:
            table.put_item(Item=form)
            print(f"✓ Created inspection form: {form['form_name']}")
        except ClientError as e:
            print(f"✗ Error creating form {form['form_name']}: {str(e)}")
    
    return forms


def main():
    """Main seeding function."""
    print("=" * 60)
    print("Seeding test data into local DynamoDB...")
    print("=" * 60)
    
    try:
        # Seed data in order
        admins = seed_admins()
        inspectors = seed_inspectors()
        crew = seed_crew()
        vessels = seed_vessels(admins[0]['admin_id'])
        forms = seed_inspection_forms(admins[0]['admin_id'], vessels[0]['vessel_id'])
        
        print("\n" + "=" * 60)
        print("✓ Test data seeded successfully!")
        print("=" * 60)
        print("\nTest Credentials:")
        print("-" * 60)
        print("Admin:")
        print("  Email: admin@arka.local")
        print("  Password: admin123")
        print("\nInspector:")
        print("  Email: inspector1@arka.local")
        print("  Password: inspector123")
        print("\nCrew:")
        print("  Email: crew1@arka.local")
        print("  Password: crew123")
        print("-" * 60)
        
    except Exception as e:
        print(f"\n✗ Error seeding data: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
