#!/usr/bin/env python3
"""
Verification script to ensure local setup is correct and isolated from production.

SAFETY: This script will ONLY run when APP_ENV=local is explicitly set.
"""
import os
import sys
import boto3
from botocore.exceptions import ClientError

# CRITICAL SAFETY CHECK
if os.getenv('APP_ENV', '').lower() != 'local':
    print("=" * 70)
    print("SAFETY GUARD: This script only runs when APP_ENV=local")
    print("=" * 70)
    print("\nUse: npm run verify-local")
    print("=" * 70)
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load local environment variables
load_dotenv('.env.local')


def check_environment():
    """Verify environment variables are set correctly."""
    print("\n" + "=" * 70)
    print("CHECKING ENVIRONMENT CONFIGURATION")
    print("=" * 70)
    
    checks = []
    
    # Check APP_ENV
    app_env = os.getenv('APP_ENV', '')
    if app_env.lower() == 'local':
        print("✓ APP_ENV is set to 'local'")
        checks.append(True)
    else:
        print(f"✗ APP_ENV is '{app_env}' (should be 'local')")
        checks.append(False)
    
    # Check endpoints
    dynamo_endpoint = os.getenv('DYNAMODB_ENDPOINT', '')
    if dynamo_endpoint == 'http://localhost:8000':
        print(f"✓ DYNAMODB_ENDPOINT: {dynamo_endpoint}")
        checks.append(True)
    else:
        print(f"✗ DYNAMODB_ENDPOINT: {dynamo_endpoint} (should be http://localhost:8000)")
        checks.append(False)
    
    s3_endpoint = os.getenv('S3_ENDPOINT', '')
    if s3_endpoint == 'http://localhost:4566':
        print(f"✓ S3_ENDPOINT: {s3_endpoint}")
        checks.append(True)
    else:
        print(f"✗ S3_ENDPOINT: {s3_endpoint} (should be http://localhost:4566)")
        checks.append(False)
    
    # Check table names have -local suffix
    tables = [
        'DYNAMODB_TABLE_INSPECTORS',
        'DYNAMODB_TABLE_ADMINS',
        'DYNAMODB_TABLE_VESSELS',
        'DYNAMODB_TABLE_INSPECTION_FORMS',
        'DYNAMODB_TABLE_INSPECTION_ASSIGNMENTS',
        'DYNAMODB_TABLE_CREW',
        'DYNAMODB_TABLE_DEFECTS',
        'DYNAMODB_TABLE_VESSEL_ASSIGNMENTS',
        'DYNAMODB_TABLE_INSPECTION_RESPONSES'
    ]
    
    print("\nTable names:")
    for table_env in tables:
        table_name = os.getenv(table_env, '')
        if table_name.endswith('-local'):
            print(f"  ✓ {table_env}: {table_name}")
            checks.append(True)
        else:
            print(f"  ✗ {table_env}: {table_name} (should end with -local)")
            checks.append(False)
    
    # Check S3 bucket
    bucket = os.getenv('S3_MEDIA_BUCKET', '')
    if bucket.endswith('-local'):
        print(f"✓ S3_MEDIA_BUCKET: {bucket}")
        checks.append(True)
    else:
        print(f"✗ S3_MEDIA_BUCKET: {bucket} (should end with -local)")
        checks.append(False)
    
    # Check credentials are dummy
    access_key = os.getenv('AWS_ACCESS_KEY_ID', '')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    
    if access_key == 'local' and secret_key == 'local':
        print("✓ Using dummy AWS credentials (local/local)")
        checks.append(True)
    else:
        print("⚠ WARNING: AWS credentials are not 'local/local'")
        print(f"  AWS_ACCESS_KEY_ID: {access_key[:4]}...")
        checks.append(False)
    
    return all(checks)


def check_services():
    """Check if local services are running."""
    print("\n" + "=" * 70)
    print("CHECKING LOCAL SERVICES")
    print("=" * 70)
    
    checks = []
    
    # Check DynamoDB Local
    try:
        dynamodb = boto3.client(
            'dynamodb',
            endpoint_url='http://localhost:8000',
            region_name='us-east-1',
            aws_access_key_id='local',
            aws_secret_access_key='local'
        )
        dynamodb.list_tables()
        print("✓ DynamoDB Local is running on port 8000")
        checks.append(True)
    except Exception as e:
        print(f"✗ DynamoDB Local is NOT running: {str(e)}")
        print("  Run: npm run local:services")
        checks.append(False)
    
    # Check LocalStack
    try:
        s3 = boto3.client(
            's3',
            endpoint_url='http://localhost:4566',
            region_name='us-east-1',
            aws_access_key_id='local',
            aws_secret_access_key='local',
            use_ssl=False
        )
        s3.list_buckets()
        print("✓ LocalStack is running on port 4566")
        checks.append(True)
    except Exception as e:
        print(f"✗ LocalStack is NOT running: {str(e)}")
        print("  Run: npm run local:services")
        checks.append(False)
    
    return all(checks)


def check_aws_isolation():
    """Verify we're not accidentally pointing to real AWS."""
    print("\n" + "=" * 70)
    print("VERIFYING AWS ISOLATION")
    print("=" * 70)
    
    # Import after environment is loaded
    from config.aws import IS_LOCAL, dynamodb_resource, s3_client
    
    if IS_LOCAL:
        print("✓ IS_LOCAL flag is True")
    else:
        print("✗ IS_LOCAL flag is False - DANGER!")
        return False
    
    # Check DynamoDB client endpoint
    dynamo_endpoint = dynamodb_resource.meta.client._endpoint.host
    if 'localhost' in dynamo_endpoint or '127.0.0.1' in dynamo_endpoint:
        print(f"✓ DynamoDB pointing to local: {dynamo_endpoint}")
    else:
        print(f"✗ DANGER: DynamoDB pointing to: {dynamo_endpoint}")
        return False
    
    # Check S3 client endpoint
    s3_endpoint = s3_client._endpoint.host
    if 'localhost' in s3_endpoint or '127.0.0.1' in s3_endpoint:
        print(f"✓ S3 pointing to local: {s3_endpoint}")
    else:
        print(f"✗ DANGER: S3 pointing to: {s3_endpoint}")
        return False
    
    return True


def main():
    """Main verification function."""
    print("=" * 70)
    print("LOCAL SETUP VERIFICATION")
    print("=" * 70)
    
    env_ok = check_environment()
    services_ok = check_services()
    isolation_ok = check_aws_isolation()
    
    print("\n" + "=" * 70)
    if env_ok and services_ok and isolation_ok:
        print("✓ ALL CHECKS PASSED - SAFE TO PROCEED")
        print("=" * 70)
        print("\nYour local environment is properly configured and isolated.")
        print("No production AWS resources will be accessed.")
        print("\nNext steps:")
        print("  1. npm run local:start  - Start serverless offline")
        print("  2. Test API at http://localhost:3000")
        sys.exit(0)
    else:
        print("✗ SOME CHECKS FAILED")
        print("=" * 70)
        print("\nPlease fix the issues above before proceeding.")
        if not services_ok:
            print("\nTo start services: npm run local:services")
        sys.exit(1)


if __name__ == "__main__":
    main()
