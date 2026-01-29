"""
Repository layer for Admin table interactions.
"""
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key


from config.aws import get_admins_table
from utility.errors import ApiError
from utility.logger import get_logger


class AdminRepository:
    """
    Provides CRUD access for admins.
    """

    def __init__(self) -> None:
        self._table = get_admins_table()
        self._logger = get_logger(self.__class__.__name__)

    def put_item(self, item: Dict[str, Any]) -> None:
        """
        Persist a new admin.
        """

        try:
            self._table.put_item(
                Item=item,
            )
        except ClientError as exc:
            self._logger.error("Failed to create admin: %s", exc)
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ApiError("Admin already exists", 409, "admin_exists") from exc
            raise ApiError("Could not create admin", 500, "dynamodb_error") from exc

    def get_item(self, admin_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an admin by primary key.
        """

        try:
            #response = self._table.get_item(Key={"admin_id": admin_id})
            response = self._table.get_item(Key={"PK": f"ADMIN{admin_id}", "SK": "METADATA"})
            return response.get("Item")
        except ClientError as exc:
            self._logger.error("Failed to fetch admin: %s", exc)
            raise ApiError("Could not fetch admin", 500, "dynamodb_error") from exc

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an admin using the email GSI.
        """

        try:
            response = self._table.query(
                IndexName="GSI1",
                KeyConditionExpression=(Key("GSI1PK").eq("ADMIN") & Key("GSI1SK").eq(email)),
                Limit=1,
            )
            items = response.get("Items", [])
            return items[0] if items else None
        except ClientError as exc:
            self._logger.error("Failed to query admin by email: %s", exc)
            raise ApiError("Could not query admin", 500, "dynamodb_error") from exc

    def update_item(self, admin_id: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update mutable admin fields.
        """

        update_expression = "SET " + ", ".join(f"{key} = :{key}" for key in attributes)
        expression_values = {f":{key}": value for key, value in attributes.items()}

        try:
            response = self._table.update_item(
                Key={"PK": f"ADMIN{admin_id}", "SK": "METADATA"},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ConditionExpression="attribute_exists(PK)",
                ReturnValues="ALL_NEW",
            )
            return response["Attributes"]
        except ClientError as exc:
            self._logger.error("Failed to update admin: %s", exc)
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ApiError("Admin not found", 404, "admin_not_found") from exc
            raise ApiError("Could not update admin", 500, "dynamodb_error") from exc

    def delete_item(self, admin_id: str) -> None:
        """
        Delete an admin record.
        """

        try:
            self._table.delete_item(
                Key={"PK": f"ADMIN{admin_id}", "SK": "METADATA"},
                ConditionExpression="attribute_exists(admin_id)",
            )
        except ClientError as exc:
            self._logger.error("Failed to delete admin: %s", exc)
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ApiError("Admin not found", 404, "admin_not_found") from exc
            raise ApiError("Could not delete admin", 500, "dynamodb_error") from exc



