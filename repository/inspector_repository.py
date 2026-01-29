"""
Repository layer for Inspector table interactions.
"""
from typing import Any, Dict, List, Optional, Tuple
from boto3.dynamodb.conditions import Key

from botocore.exceptions import ClientError

from config.aws import get_inspectors_table
from utility.errors import ApiError
from utility.logger import get_logger


class InspectorRepository:
    """
    Provides CRUD access for inspectors.
    """

    def __init__(self) -> None:
        self._table = get_inspectors_table()
        self._logger = get_logger(self.__class__.__name__)

    def put_item(self, item: Dict[str, Any]) -> None:
        """
        Persist a new inspector.
        """

        try:
            self._table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(PK)",
            )
        except ClientError as exc:
            self._logger.error("Failed to create inspector: %s", exc)
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ApiError("Inspector already exists", 409, "inspector_exists") from exc
            raise ApiError("Could not create inspector", 500, "dynamodb_error") from exc

    def get_item(self, inspector_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an inspector by primary key.
        """

        try:
            pk = f"INSPECTOR#{inspector_id}"
            response = self._table.get_item(Key={"PK": pk,"SK":"METADATA"})
            return response.get("Item")
        except ClientError as exc:
            self._logger.error("Failed to fetch inspector: %s", exc)
            raise ApiError("Could not fetch inspector", 500, "dynamodb_error") from exc

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an inspector using the email GSI.
        """

        try:
            response = self._table.query(
                IndexName="GSI1",
                KeyConditionExpression=Key("GSI1PK").eq("INSPECTOR") & Key("GSI1SK").eq(email),
                Limit=1,
            )
            items = response.get("Items", [])
            return items[0] if items else None
        except ClientError as exc:
            self._logger.error("Failed to query inspector by email: %s", exc)
            raise ApiError("Could not query inspector", 500, "dynamodb_error") from exc

    def update_item(self, inspector_id: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update mutable inspector fields.
        """

        
        update_expression = "SET " + ", ".join(f"#{k} = :{k}" for k in attributes)
        expression_values = {f":{k}": v for k, v in attributes.items()}
        expression_names = {f"#{k}": k for k in attributes}

        try:
            response = self._table.update_item(
                Key={"PK": f"INSPECTOR#{inspector_id}","SK": "METADATA",},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
                ConditionExpression="attribute_exists(PK)",
                ReturnValues="ALL_NEW",
            )
            return response["Attributes"]
        except ClientError as exc:
            self._logger.error("Failed to update inspector: %s", exc)
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ApiError("Inspector not found", 404, "inspector_not_found") from exc
            raise ApiError("Could not update inspector", 500, "dynamodb_error") from exc

    def delete_item(self, inspector_id: str) -> None:
        """
        Delete an inspector record.
        """

        try:
            self._table.delete_item(
                Key={"PK": f"INSPECTOR#{inspector_id}","SK": "METADATA",},
                ConditionExpression="attribute_exists(PK)",
            )
        except ClientError as exc:
            self._logger.error("Failed to delete inspector: %s", exc)
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ApiError("Inspector not found", 404, "inspector_not_found") from exc
            raise ApiError("Could not delete inspector", 500, "dynamodb_error") from exc

    def list_items(
        self, limit: int, exclusive_start_key: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        List inspectors with pagination support.

        Uses DynamoDB scan with a Limit and optional ExclusiveStartKey.
        Returns a tuple of (items, last_evaluated_key).
        """

        query_kwargs: Dict[str, Any] = {
        "IndexName": "GSI1",
        "KeyConditionExpression": Key("GSI1PK").eq("INSPECTOR"),
        "Limit": limit,
       }

        if exclusive_start_key:
            query_kwargs["ExclusiveStartKey"] = exclusive_start_key

        try:
            response = self._table.query(**query_kwargs)
            return (
                response.get("Items", []),
                response.get("LastEvaluatedKey"),
            )
        except ClientError as exc:
            self._logger.error("Failed to list inspectors: %s", exc)
            raise ApiError("Could not list inspectors", 500, "dynamodb_error") from exc

