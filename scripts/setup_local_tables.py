#!/usr/bin/env python3
"""
Setup script for creating DynamoDB Local tables.
This script creates all required tables with their schemas and GSIs.

SAFETY: This script will ONLY run when APP_ENV=local is explicitly set.
"""
import os
import sys
import boto3
from botocore.exceptions import ClientError

# CRITICAL SAFETY CHECK: Refuse to run unless APP_ENV is explicitly 'local'
if os.getenv('APP_ENV', '').lower() != 'local':
    print("=" * 70)
    print("SAFETY GUARD: This script only runs when APP_ENV=local")
    print("=" * 70)
    print("\nThis prevents accidental modification of production AWS resources.")
    print("\nTo run this script, set APP_ENV=local:")
    print("  Windows: set APP_ENV=local && python scripts/setup_local_tables.py")
    print("  Linux/Mac: APP_ENV=local python scripts/setup_local_tables.py")
    print("\nOr use: npm run setup-tables (which sets APP_ENV automatically)")
    print("=" * 70)
    sys.exit(1)

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load local environment variables
load_dotenv('.env.local')

# Initialize DynamoDB client for local
dynamodb = boto3.client(
    'dynamodb',
    endpoint_url=os.getenv('DYNAMODB_ENDPOINT', 'http://localhost:8000'),
    region_name=os.getenv('AWS_REGION', 'us-east-1'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'local'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'local')
)


def create_table_if_not_exists(table_name, key_schema, attribute_definitions, global_secondary_indexes=None):
    """Create a DynamoDB table if it doesn't already exist."""
    try:
        # Check if table exists
        dynamodb.describe_table(TableName=table_name)
        print(f"✓ Table '{table_name}' already exists")
        return False
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            # Table doesn't exist, create it
            params = {
                'TableName': table_name,
                'KeySchema': key_schema,
                'AttributeDefinitions': attribute_definitions,
                'BillingMode': 'PAY_PER_REQUEST'
            }
            
            if global_secondary_indexes:
                params['GlobalSecondaryIndexes'] = global_secondary_indexes
            
            dynamodb.create_table(**params)
            print(f"✓ Created table '{table_name}'")
            return True
        else:
            raise


def setup_inspection_responses_table():
    """Create InspectionResponses table."""
    table_name = os.getenv('DYNAMODB_TABLE_INSPECTION_RESPONSES')
    create_table_if_not_exists(
        table_name=table_name,
        key_schema=[
            {'AttributeName': 'inspection_id', 'KeyType': 'HASH'},
            {'AttributeName': 'question_id', 'KeyType': 'RANGE'}
        ],
        attribute_definitions=[
            {'AttributeName': 'inspection_id', 'AttributeType': 'S'},
            {'AttributeName': 'question_id', 'AttributeType': 'S'}
        ]
    )


def setup_vessels_table():
    """Create Vessels table."""
    table_name = os.getenv('DYNAMODB_TABLE_VESSELS')
    create_table_if_not_exists(
        table_name=table_name,
        key_schema=[
            {'AttributeName': 'vessel_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'vessel_id', 'AttributeType': 'S'},
            {'AttributeName': 'ship_id', 'AttributeType': 'S'},
            {'AttributeName': 'admin_id', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'ship_id_index',
                'KeySchema': [{'AttributeName': 'ship_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'admin_id_index',
                'KeySchema': [{'AttributeName': 'admin_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    )


def setup_inspection_forms_table():
    """Create InspectionForms table."""
    table_name = os.getenv('DYNAMODB_TABLE_INSPECTION_FORMS')
    create_table_if_not_exists(
        table_name=table_name,
        key_schema=[
            {'AttributeName': 'form_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'form_id', 'AttributeType': 'S'},
            {'AttributeName': 'vessel_id', 'AttributeType': 'S'},
            {'AttributeName': 'assigned_inspector_id', 'AttributeType': 'S'},
            {'AttributeName': 'created_by_admin_id', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'vessel_id_index',
                'KeySchema': [{'AttributeName': 'vessel_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'inspector_id_index',
                'KeySchema': [{'AttributeName': 'assigned_inspector_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'admin_id_index',
                'KeySchema': [{'AttributeName': 'created_by_admin_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    )


def setup_inspection_assignments_table():
    """Create InspectionAssignments table."""
    table_name = os.getenv('DYNAMODB_TABLE_INSPECTION_ASSIGNMENTS')
    create_table_if_not_exists(
        table_name=table_name,
        key_schema=[
            {'AttributeName': 'assignment_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'assignment_id', 'AttributeType': 'S'},
            {'AttributeName': 'created_by_admin_id', 'AttributeType': 'S'},
            {'AttributeName': 'form_id', 'AttributeType': 'S'},
            {'AttributeName': 'assignee_id', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'admin_id_index',
                'KeySchema': [{'AttributeName': 'created_by_admin_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'form_id_index',
                'KeySchema': [{'AttributeName': 'form_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'assignee_id_index',
                'KeySchema': [{'AttributeName': 'assignee_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    )


def setup_admins_table():
    """Create Admins table."""
    table_name = os.getenv('DYNAMODB_TABLE_ADMINS')
    create_table_if_not_exists(
        table_name=table_name,
        key_schema=[
            {'AttributeName': 'admin_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'admin_id', 'AttributeType': 'S'},
            {'AttributeName': 'email', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'email_index',
                'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    )


def setup_inspectors_table():
    """Create Inspectors table."""
    table_name = os.getenv('DYNAMODB_TABLE_INSPECTORS')
    # Note: Inspectors table schema not defined in serverless.yml
    # Using similar structure to Admins table
    create_table_if_not_exists(
        table_name=table_name,
        key_schema=[
            {'AttributeName': 'inspector_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'inspector_id', 'AttributeType': 'S'},
            {'AttributeName': 'email', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'email_index',
                'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    )


def setup_crew_table():
    """Create Crew table."""
    table_name = os.getenv('DYNAMODB_TABLE_CREW')
    create_table_if_not_exists(
        table_name=table_name,
        key_schema=[
            {'AttributeName': 'crew_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'crew_id', 'AttributeType': 'S'},
            {'AttributeName': 'email', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'email_index',
                'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    )


def setup_defects_table():
    """Create Defects table."""
    table_name = os.getenv('DYNAMODB_TABLE_DEFECTS')
    create_table_if_not_exists(
        table_name=table_name,
        key_schema=[
            {'AttributeName': 'defect_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'defect_id', 'AttributeType': 'S'}
        ]
    )


def setup_vessel_assignments_table():
    """Create VesselAssignments table."""
    table_name = os.getenv('DYNAMODB_TABLE_VESSEL_ASSIGNMENTS')
    create_table_if_not_exists(
        table_name=table_name,
        key_schema=[
            {'AttributeName': 'vessel_id', 'KeyType': 'HASH'},
            {'AttributeName': 'assignment_id', 'KeyType': 'RANGE'}
        ],
        attribute_definitions=[
            {'AttributeName': 'vessel_id', 'AttributeType': 'S'},
            {'AttributeName': 'assignment_id', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'assignment_id_index',
                'KeySchema': [{'AttributeName': 'assignment_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'KEYS_ONLY'}
            }
        ]
    )


def main():
    """Main setup function."""
    print("=" * 60)
    print("Setting up DynamoDB Local tables...")
    print("=" * 60)
    
    try:
        # Create all tables
        setup_inspection_responses_table()
        setup_vessels_table()
        setup_inspection_forms_table()
        setup_inspection_assignments_table()
        setup_admins_table()
        setup_inspectors_table()
        setup_crew_table()
        setup_defects_table()
        setup_vessel_assignments_table()
        
        print("\n" + "=" * 60)
        print("✓ All tables created successfully!")
        print("=" * 60)
        print("\nYou can view tables at: http://localhost:8001 (DynamoDB Admin UI)")
        
    except Exception as e:
        print(f"\n✗ Error setting up tables: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
