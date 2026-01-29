"""
AWS clients and helpers.
"""
import os
import boto3
from botocore.config import Config
from dotenv import load_dotenv
from config.settings import get_settings

load_dotenv()
settings = get_settings()

aws_config = Config(
    region_name=settings.aws_region,
    connect_timeout=5,
    read_timeout=10,
    retries={"max_attempts": 2}
)

dynamodb_resource = boto3.resource(
    "dynamodb",
    region_name=settings.aws_region,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    config=aws_config,
)

s3_client = boto3.client(
    "s3",
    region_name=settings.aws_region,
    endpoint_url=f"https://s3.{settings.aws_region}.amazonaws.com",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    config=aws_config,
)

'''

# Initialize DynamoDB resource
dynamodb_resource = boto3.resource("dynamodb", region_name=settings.aws_region)

# Initialize S3 client
s3_client = boto3.client("s3", region_name=settings.aws_region)
'''


def get_inspectors_table():
    """
    Return the DynamoDB table resource for inspectors.
    """

    return dynamodb_resource.Table(settings.inspectors_table)


def get_admins_table():
    """
    Return the DynamoDB table resource for admins.
    """

    return dynamodb_resource.Table(settings.inspectors_table)


def get_inspection_forms_table():
    """
    Return the DynamoDB table resource for inspection forms.
    """

    return dynamodb_resource.Table(settings.inspectors_table)


def get_inspection_assignments_table():
    """
    Return the DynamoDB table resource for inspection assignments.
    """

    return dynamodb_resource.Table(settings.inspectors_table)


def get_crew_table():
    """
    Return the DynamoDB table resource for crew.
    """

    return dynamodb_resource.Table(settings.inspectors_table)


def get_defects_table():
    """
    Return the DynamoDB table resource for defects.
    """

    return dynamodb_resource.Table(settings.inspectors_table)


def get_vessel_assignments_table():
    """
    Return the DynamoDB table resource for vessel assignments.
    """

    return dynamodb_resource.Table(settings.inspectors_table)


def get_inspection_responses_table():
    """
    Return the DynamoDB table resource for inspection responses.
    """

    return dynamodb_resource.Table(settings.inspectors_table)


def get_s3_client():
    """
    Return the shared S3 client.
    """

    return s3_client
