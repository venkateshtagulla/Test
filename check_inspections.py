"""
Simple script to check inspection assignments in the database.
"""
import boto3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get table name from environment
table_name = os.getenv('DYNAMODB_TABLE_INSPECTION_ASSIGNMENTS', 'InspectionAssignments-local')

print(f"Connecting to DynamoDB table: {table_name}")

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'ap-south-1'))
table = dynamodb.Table(table_name)

# Scan the table to get all inspection assignments
print("\nScanning inspection assignments table...")
response = table.scan(Limit=10)

items = response.get('Items', [])
print(f"Found {len(items)} inspection assignments\n")

if items:
    for idx, item in enumerate(items, 1):
        print(f"Assignment {idx}:")
        print(f"  - assignment_id: {item.get('assignment_id')}")
        print(f"  - inspection_name: {item.get('inspection_name', 'N/A')}")
        print(f"  - vessel_id: {item.get('vessel_id', 'N/A')}")
        print(f"  - form_id: {item.get('form_id')}")
        print(f"  - assignee_id: {item.get('assignee_id')}")
        print(f"  - status: {item.get('status')}")
        print()
else:
    print("No inspection assignments found in the table")
