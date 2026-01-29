"""
Repository layer for Inspection Assignment table interactions.
"""
from typing import Any, Dict, List, Optional, Tuple

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key,Attr
from config.aws import get_inspection_assignments_table
from utility.errors import ApiError
from utility.logger import get_logger


class InspectionAssignmentRepository:
    """
    Provides CRUD and query access for inspection assignments.
    """

    def __init__(self) -> None:
        self._table = get_inspection_assignments_table()
        self._logger = get_logger(self.__class__.__name__)

    def put_item(self, item: Dict[str, Any]) -> None:
        """
        Persist a new assignment.
        """

        try:
            self._table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(PK)",
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.exception(
                "Failed to create inspection assignment. Code: %s, Message: %s",
                error_code,
                error_message,
            )
            if error_code == "ConditionalCheckFailedException":
                raise ApiError("Inspection assignment already exists", 409, "assignment_exists") from exc
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not create inspection assignment: {error_message}", 500, "dynamodb_error") from exc

    def get_item(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an assignment by primary key.
        """

        try:
            response = self._table.get_item(Key={"PK": f"INSPECTION#{assignment_id}","SK": "METADATA",})
            return response.get("Item")
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to fetch inspection assignment %s: %s", assignment_id, error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not fetch inspection assignment: {error_message}", 500, "dynamodb_error") from exc

    def list_by_admin(
        self,
        admin_id: str,
        limit: int,
        cursor: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        List assignments created by a specific admin using admin_id_index.
        """

        try:
            query_kwargs: Dict[str, Any] = {
                "IndexName": "GSI1",
                "KeyConditionExpression": Key("GSI1PK").eq("INSPECTION"),
                "Limit": limit,
                "ScanIndexForward": True,  # A → Z by inspection_name
            }
            if cursor:
                query_kwargs["ExclusiveStartKey"] = cursor
            response = self._table.query(**query_kwargs)
            items = response.get("Items", [])
            last_evaluated_key = response.get("LastEvaluatedKey")
            return items, last_evaluated_key
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to query inspection assignments for admin %s: %s", admin_id, error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not query inspection assignments: {error_message}", 500, "dynamodb_error") from exc

    def list_by_form(
        self,
        form_id: str,
        limit: int,
        cursor: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        List assignments for a specific form using form_id_index.
        """

        try:
            query_kwargs: Dict[str, Any] = {
                "IndexName": "GSI4",
                "KeyConditionExpression": Key("GSI4PK").eq(f"FORM#{form_id}"),
                "Limit": limit
            }
            if cursor:
                query_kwargs["ExclusiveStartKey"] = cursor
            response = self._table.query(**query_kwargs)
            items = response.get("Items", [])
            last_evaluated_key = response.get("LastEvaluatedKey")
            return items, last_evaluated_key
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to query inspection assignments for form %s: %s", form_id, error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not query inspection assignments: {error_message}", 500, "dynamodb_error") from exc

    def list_by_assignee(
        self,
        assignee_id: str,
        limit: int,
        cursor: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        List assignments for a specific assignee (inspector or crew) using assignee_id_index.
        """

        try:
            query_kwargs: Dict[str, Any] = {
                "IndexName": "GSI2",
                "KeyConditionExpression": Key("GSI2PK").eq(assignee_id),
                "Limit": limit,
                "ScanIndexForward": True, 
            }
            if cursor:
                query_kwargs["ExclusiveStartKey"] = cursor
            response = self._table.query(**query_kwargs)
            items = response.get("Items", [])
            last_evaluated_key = response.get("LastEvaluatedKey")
            return items, last_evaluated_key
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to query inspection assignments for assignee %s: %s", assignee_id, error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not query inspection assignments: {error_message}", 500, "dynamodb_error") from exc
    

    def list_by_vessel(
        self,
        vessel_id: str,
        limit: int,
        cursor: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        List inspection assignments for a specific vessel using GSI3.
        Supports pagination via LastEvaluatedKey.
        """

        try:
            query_kwargs: Dict[str, Any] = {
                "IndexName": "GSI3",
                "KeyConditionExpression": Key("GSI3PK").eq(vessel_id),
                "Limit": limit,
                "ScanIndexForward": False,
            }

            # Pagination
            if cursor:
                query_kwargs["ExclusiveStartKey"] = cursor

            self._logger.info(
                "Querying inspection assignments for vessel_id=%s using GSI3",
                vessel_id,
            )

            response = self._table.query(**query_kwargs)

            items = response.get("Items", [])
            last_key = response.get("LastEvaluatedKey")

            self._logger.info(
                "Found %d items for vessel %s, next_page=%s",
                len(items),
                vessel_id,
                last_key is not None,
            )

            return items, last_key

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
                "Failed to query inspection assignments for vessel %s: %s",
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
                f"Could not query inspection assignments: {error_message}",
                500,
                "dynamodb_error",
            ) from exc

    def has_pending_assignments(self, assignee_id: str) -> bool:
        """
        Check if a crew member has any pending/incomplete assignments.
        Returns True if there are assignments with status 'assigned' or 'in_progress'.
        """

        try:
            query_kwargs: Dict[str, Any] = {
                "IndexName": "assignee_id_index",
                "KeyConditionExpression": "assignee_id = :assignee_id",
                "FilterExpression": "attribute_exists(#status) AND (#status = :assigned OR #status = :in_progress)",
                "ExpressionAttributeNames": {"#status": "status"},
                "ExpressionAttributeValues": {
                    ":assignee_id": assignee_id,
                    ":assigned": "assigned",
                    ":in_progress": "in_progress",
                },
                "Limit": 1,  # We only need to know if at least one exists
            }
            response = self._table.query(**query_kwargs)
            items = response.get("Items", [])
            return len(items) > 0
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to check pending assignments for assignee %s: %s", assignee_id, error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not check pending assignments: {error_message}", 500, "dynamodb_error") from exc

   
    def list_by_parent_assignment(
        self,
        parent_assignment_id: str,
        limit: int = 100  # optional, you can pass limit if needed
    ) -> List[Dict[str, Any]]:
        """
        List all assignments that belong to a parent assignment (including the parent itself).
        Uses GSI5 for efficient query instead of scanning the entire table.
        Handles pagination internally.
        """
        try:
            items = []

            # First, get the parent assignment itself
            parent = self.get_item(parent_assignment_id)
            if parent:
                items.append(parent)

            # Query child assignments using GSI5
            query_kwargs: Dict[str, Any] = {
                "IndexName": "GSI5",
                "KeyConditionExpression": Key("GSI5PK").eq(parent_assignment_id),
                "Limit": limit,
            }

            last_evaluated_key = None

            while True:
                if last_evaluated_key:
                    query_kwargs["ExclusiveStartKey"] = last_evaluated_key

                response = self._table.query(**query_kwargs)
                child_items = response.get("Items", [])
                items.extend(child_items)

                last_evaluated_key = response.get("LastEvaluatedKey")
                if not last_evaluated_key:
                    break

            return items

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to list assignments by parent %s: %s", parent_assignment_id, error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not list assignments by parent: {error_message}", 500, "dynamodb_error") from exc

    def delete_item(self, assignment_id: str) -> None:
        """
        Delete an inspection assignment by assignment_id.
        """

        try:
            pk = f"INSPECTION#{assignment_id}"
            self._table.delete_item(
                Key={"PK":pk,"SK":"METADATA"},
                ConditionExpression="attribute_exists(PK)",
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to delete inspection assignment %s: %s", assignment_id, error_message)
            if error_code == "ConditionalCheckFailedException":
                raise ApiError("Inspection assignment not found", 404, "assignment_not_found") from exc
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not delete inspection assignment: {error_message}", 500, "dynamodb_error") from exc

    def batch_put_items(self, items: List[Dict[str, Any]]) -> None:
        """
        Batch create multiple inspection assignments.
        DynamoDB batch_write_item can handle up to 25 items per request.
        """

        try:
            # DynamoDB batch_write_item handles up to 25 items at a time
            batch_size = 25
            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]
                request_items = {
                    self._table.name: [
                        {"PutRequest": {"Item": item}} for item in batch
                    ]
                }
                response = self._table.meta.client.batch_write_item(RequestItems=request_items)
                
                # Handle unprocessed items (retry once if needed)
                unprocessed = response.get("UnprocessedItems", {})
                if unprocessed:
                    self._logger.warning("Some items were unprocessed, retrying: %s", unprocessed)
                    retry_response = self._table.meta.client.batch_write_item(RequestItems=unprocessed)
                    still_unprocessed = retry_response.get("UnprocessedItems", {})
                    if still_unprocessed:
                        self._logger.error("Failed to process some items after retry: %s", still_unprocessed)
                        raise ApiError("Failed to create some assignments", 500, "batch_write_failed")
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to batch create inspection assignments: %s", error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not batch create inspection assignments: {error_message}", 500, "dynamodb_error") from exc

    def query_active_assignments_by_assignee(self, assignee_id: str) -> List[Dict[str, Any]]:
        """
        Query active inspection assignments for a specific assignee.
        Active assignments are those with status = 'assigned'.
        Used for deletion validation.
        """
        try:
            query_kwargs: Dict[str, Any] = {
                "IndexName": "GSI2",
                "KeyConditionExpression": Key("GSI2PK").eq(assignee_id),
                "FilterExpression": Attr("status").eq("assigned"),
                "ScanIndexForward": False,  # newest assignments first (optional)
            }

            items: List[Dict[str, Any]] = []
            response = self._table.query(**query_kwargs)
            items.extend(response.get("Items", []))
            
            # Handle pagination
            while "LastEvaluatedKey" in response:
                query_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = self._table.query(**query_kwargs)
                items.extend(response.get("Items", []))
            
            return items
        except ClientError as exc:
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to query active assignments for assignee %s: %s", assignee_id, error_message)
            raise ApiError(f"Could not query active assignments: {error_message}", 500, "dynamodb_error") from exc
