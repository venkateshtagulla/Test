#!/usr/bin/env python3
"""
Script to create the S3 bucket in LocalStack.

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
    print("  Windows: set APP_ENV=local && python scripts/setup_s3_bucket.py")
    print("  Linux/Mac: APP_ENV=local python scripts/setup_s3_bucket.py")
    print("\nOr use: npm run setup-s3 (which sets APP_ENV automatically)")
    print("=" * 70)
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load local environment variables
load_dotenv('.env.local')

# Initialize S3 client for LocalStack
s3_client = boto3.client(
    's3',
    endpoint_url=os.getenv('S3_ENDPOINT', 'http://localhost:4566'),
    region_name=os.getenv('AWS_REGION', 'us-east-1'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'local'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'local'),
    use_ssl=False,
    config=boto3.session.Config(
        signature_version='s3v4',
        s3={'addressing_style': 'path'}
    )
)


def setup_s3_bucket():
    """Create S3 bucket in LocalStack if it doesn't exist."""
    bucket_name = os.getenv('S3_MEDIA_BUCKET', 'arka-media-local')
    
    try:
        # Check if bucket exists
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✓ Bucket '{bucket_name}' already exists")
        return False
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            # Bucket doesn't exist, create it
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"✓ Created bucket '{bucket_name}'")
            
            # Set CORS configuration for local testing
            cors_configuration = {
                'CORSRules': [{
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                    'AllowedOrigins': ['*'],
                    'ExposeHeaders': ['ETag']
                }]
            }
            s3_client.put_bucket_cors(
                Bucket=bucket_name,
                CORSConfiguration=cors_configuration
            )
            print(f"✓ Configured CORS for bucket '{bucket_name}'")
            return True
        else:
            raise


def main():
    """Main setup function."""
    print("=" * 60)
    print("Setting up LocalStack S3 bucket...")
    print("=" * 60)
    
    try:
        setup_s3_bucket()
        
        print("\n" + "=" * 60)
        print("✓ S3 bucket setup complete!")
        print("=" * 60)
        print(f"\nBucket endpoint: {os.getenv('S3_ENDPOINT')}")
        
    except Exception as e:
        print(f"\n✗ Error setting up S3 bucket: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
