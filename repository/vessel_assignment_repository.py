"""
Repository layer for Vessel Assignment table interactions.
"""
from typing import Any, Dict, List, Optional, Tuple

from botocore.exceptions import ClientError

from config.aws import get_vessel_assignments_table
from config.settings import get_settings
from utility.errors import ApiError
from utility.logger import get_logger


settings = get_settings()


class VesselAssignmentRepository:
    """
    Provides CRUD and query access for vessel assignments.
    """

    def __init__(self) -> None:
        self._table = get_vessel_assignments_table()
        self._logger = get_logger(self.__class__.__name__)

    def put_item(self, item: Dict[str, Any]) -> None:
        """
        Persist a new vessel assignment.
        """

        try:
            self._table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(PK)",
            )
        except ClientError as exc:
            self._logger.error("Failed to create vessel assignment: %s", exc)
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ApiError(
                    "Vessel assignment already exists", 409, "assignment_exists"
                ) from exc
            raise ApiError(
                "Could not create vessel assignment", 500, "dynamodb_error"
            ) from exc

    def get_item(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a vessel assignment by assignment_id (via GSI lookup for vessel_id).
        """

        try:
            response = self._table.get_item(
            Key={
                "PK": f"USER_ASSIGNMENT#{assignment_id}",
                "SK": "METADATA",
            }
            )
            return response.get("Item")
        except ClientError as exc:
            self._logger.error("Failed to fetch vessel assignment %s: %s", assignment_id, exc)
            raise ApiError(
                "Could not fetch vessel assignment", 500, "dynamodb_error"
            ) from exc

    def list_by_vessel(
        self,
        vessel_id: str,
        limit: int,
        cursor: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        List vessel assignments for a specific vessel using vessel_id (PK).
        """

        try:
            query_kwargs: Dict[str, Any] = {
                "IndexName": "GSI1",
                "KeyConditionExpression": "GSI1PK = :vessel_id",
                "ExpressionAttributeValues": {":vessel_id": vessel_id},
                "Limit": limit,
            }
            if cursor:
                query_kwargs["ExclusiveStartKey"] = cursor
            response = self._table.query(**query_kwargs)
            items = response.get("Items", [])
            last_evaluated_key = response.get("LastEvaluatedKey")
            return items, last_evaluated_key
        except ClientError as exc:
            error_code = (
                exc.response.get("Error", {}).get("Code", "Unknown")
                if hasattr(exc, "response")
                else "Unknown"
            )
            error_message = (
                exc.response.get("Error", {}).get("Message", str(exc))
                if hasattr(exc, "response")
                else str(exc)
            )
            self._logger.error(
                "Failed to query vessel assignments for vessel %s: %s",
                vessel_id,
                error_message,
            )
            if error_code == "ResourceNotFoundException":
                raise ApiError(
                    f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}",
                    500,
                    "table_not_found",
                ) from exc
            raise ApiError(
                f"Could not query vessel assignments: {error_message}",
                500,
                "dynamodb_error",
            ) from exc

    def delete_item(self, assignment_id: str) -> None:
        """
        Delete a vessel assignment by assignment_id.
        """

        try:
            self._table.delete_item(
            Key={
                "PK": f"USER_ASSIGNMENT#{assignment_id}",
                "SK": "METADATA",
            },
            ConditionExpression="attribute_exists(PK)",
            )
        except ClientError as exc:
            self._logger.error("Failed to delete vessel assignment %s: %s", assignment_id, exc)
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ApiError(
                    "Vessel assignment not found", 404, "assignment_not_found"
                ) from exc
            raise ApiError(
                "Could not delete vessel assignment", 500, "dynamodb_error"
            ) from exc

