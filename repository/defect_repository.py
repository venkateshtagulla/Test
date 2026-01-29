"""
Repository layer for Defects table interactions.
"""
from typing import Any, Dict, List, Optional, Tuple

from botocore.exceptions import ClientError

from config.aws import get_defects_table
from utility.errors import ApiError
from utility.logger import get_logger
from boto3.dynamodb.conditions import Key,Attr


class DefectRepository:
    """
    Provides CRUD and query access for defects.
    """

    def __init__(self) -> None:
        self._table = get_defects_table()
        self._logger = get_logger(self.__class__.__name__)

    def put_item(self, item: Dict[str, Any]) -> None:
        """
        Persist a new defect.
        """

        try:
            self._table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)",
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.exception(
                "Failed to create defect. Code: %s, Message: %s",
                error_code,
                error_message,
            )
            if error_code == "ConditionalCheckFailedException":
                raise ApiError("Defect already exists", 409, "defect_exists") from exc
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not create defect: {error_message}", 500, "dynamodb_error") from exc

    def get_item(self, defect_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a defect by primary key.
        """

        try:
            response = self._table.get_item(Key={"PK": f"DEFECT#{defect_id}","SK": "METADATA",})
            return response.get("Item")
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to fetch defect %s: %s", defect_id, error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not fetch defect: {error_message}", 500, "dynamodb_error") from exc
        
    def update_item(self, defect_id: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a defect's attributes.
        """

        try:
            update_expression_parts: List[str] = []
            expression_attribute_names: Dict[str, str] = {}
            expression_attribute_values: Dict[str, Any] = {}

            for key, value in attributes.items():
                attr_name = f"#{key}"
                attr_value = f":{key}"
                update_expression_parts.append(f"{attr_name} = {attr_value}")
                expression_attribute_names[attr_name] = key
                expression_attribute_values[attr_value] = value

            # Always update updated_at timestamp
            update_expression_parts.append("#updated_at = :updated_at")
            expression_attribute_names["#updated_at"] = "updated_at"
            from datetime import datetime
            expression_attribute_values[":updated_at"] = datetime.utcnow().isoformat()

            update_expression = "SET " + ", ".join(update_expression_parts)

            response = self._table.update_item(
                Key={
                    "PK": f"DEFECT#{defect_id}",
                    "SK": "METADATA"
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes", {})

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)

            self._logger.error(
                "Failed to update defect %s: %s", defect_id, error_message
            )

            if error_code == "ResourceNotFoundException":
                raise ApiError(
                    f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}",
                    500,
                    "table_not_found"
                ) from exc

            raise ApiError(
                f"Could not update defect: {error_message}",
                500,
                "dynamodb_error"
            ) from exc


    '''def update_item(self, defect_id: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a defect's attributes.
        """

        try:
            update_expression_parts: List[str] = []
            expression_attribute_names: Dict[str, str] = {}
            expression_attribute_values: Dict[str, Any] = {}

            for key, value in attributes.items():
                attr_name = f"#{key}"
                attr_value = f":{key}"
                update_expression_parts.append(f"{attr_name} = {attr_value}")
                expression_attribute_names[attr_name] = key
                expression_attribute_values[attr_value] = value

            # Always update updated_at timestamp
            update_expression_parts.append("#updated_at = :updated_at")
            expression_attribute_names["#updated_at"] = "updated_at"
            from datetime import datetime
            expression_attribute_values[":updated_at"] = datetime.utcnow().isoformat()

            update_expression = "SET " + ", ".join(update_expression_parts)

            response = self._table.update_item(
                Key={"defect_id": defect_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes", {})
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to update defect %s: %s", defect_id, error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not update defect: {error_message}", 500, "dynamodb_error") from exc '''

    def list_items(
        self,
        status: Optional[str] = None,
        vessel_id: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        List defects with optional filtering by status and vessel_id.
        Uses scan with filter expression.
        """

        try:
            if vessel_id:
                query_kwargs = {
                    "IndexName": "GSI2",
                    "KeyConditionExpression": Key("GSI2PK").eq(vessel_id),
                    "Limit": limit,
                }
            else:
                query_kwargs = {
                    "IndexName": "GSI1",
                    "KeyConditionExpression": Key("GSI1PK").eq("DEFECT"),
                    "Limit": limit,
                }

            if status:
                query_kwargs["FilterExpression"] = Key("status").eq(status)

            if cursor:
                query_kwargs["ExclusiveStartKey"] = cursor

            self._logger.debug(
                "Querying defects vessel_id=%s status=%s limit=%d index=%s",
                vessel_id, status, limit, query_kwargs["IndexName"]
            )

            response = self._table.query(**query_kwargs)
            items = response.get("Items", [])
            last_evaluated_key = response.get("LastEvaluatedKey")

            self._logger.debug(
                "Query returned %d items has_more=%s",
                len(items), last_evaluated_key is not None
            )

            return items, last_evaluated_key

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to scan defects: %s", error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not list defects: {error_message}", 500, "dynamodb_error") from exc 
    
                



    ''' def list_by_raised_user(
        self,
        raised_field: str,
        user_id: str,
        status: Optional[str],
        vessel_id: Optional[str],
        limit: int,
        cursor: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        List defects raised by a specific inspector or crew member.

        This uses a scan with a filter expression on raised_by_inspector_id or
        raised_by_crew_id (depending on raised_field). For higher-scale usage,
        consider adding a GSI on these attributes.
        """

        if raised_field not in {"raised_by_inspector_id", "raised_by_crew_id"}:
            raise ApiError("Invalid raised_field for list_by_raised_user", 500, "invalid_raised_field")

        try:
            filter_expressions: List[str] = []
            expression_attribute_names: Dict[str, str] = {}
            expression_attribute_values: Dict[str, Any] = {}

            # Filter by who raised the defect
            filter_expressions.append("#raised = :user_id")
            expression_attribute_names["#raised"] = raised_field
            expression_attribute_values[":user_id"] = user_id

            if status:
                filter_expressions.append("#status = :status")
                expression_attribute_names["#status"] = "status"
                expression_attribute_values[":status"] = status

            if vessel_id:
                filter_expressions.append("vessel_id = :vessel_id")
                expression_attribute_values[":vessel_id"] = vessel_id

            scan_kwargs: Dict[str, Any] = {
                "Limit": limit,
                "FilterExpression": " AND ".join(filter_expressions),
                "ExpressionAttributeNames": expression_attribute_names,
                "ExpressionAttributeValues": expression_attribute_values,
            }

            if cursor:
                scan_kwargs["ExclusiveStartKey"] = cursor

            response = self._table.scan(**scan_kwargs)
            items = response.get("Items", [])
            last_evaluated_key = response.get("LastEvaluatedKey")
            return items, last_evaluated_key
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to list defects by raised user %s: %s", user_id, error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not list defects by raised user: {error_message}", 500, "dynamodb_error") from exc '''
    def list_by_raised_user(
        self,
        raised_field: str,
        user_id: str,
        status: Optional[str],
        vessel_id: Optional[str],
        limit: int,
        cursor: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        List defects raised by a specific inspector or crew member.
        Uses existing GSI1 (sorted by title) and filters in-memory.
        """

        if raised_field not in {"raised_by_inspector_id", "raised_by_crew_id"}:
            raise ApiError("Invalid raised_field for list_by_raised_user", 500, "invalid_raised_field")

        try:
            query_kwargs: Dict[str, Any] = {
                "IndexName": "GSI3",
                "KeyConditionExpression": Key("GSI3PK").eq(user_id),
                "Limit": limit,
                "ScanIndexForward": True,  # sorted by GSI1SK (title)
            }
            if status:
                query_kwargs["FilterExpression"] = Attr("status").eq(status)
            if vessel_id:
                if "FilterExpression" in query_kwargs:
                    query_kwargs["FilterExpression"] = query_kwargs["FilterExpression"] & Attr("vessel_id").eq(vessel_id)
                else:
                    query_kwargs["FilterExpression"] = Attr("vessel_id").eq(vessel_id)

            if cursor:
                query_kwargs["ExclusiveStartKey"] = cursor

            self._logger.debug(
                "Querying defects by raised user (in-memory filter) for %s, limit=%d, cursor_present=%s",
                user_id,
                limit,
                cursor is not None,
            )
            response = self._table.query(**query_kwargs)
            items = response.get("Items", [])
            last_evaluated_key = response.get("LastEvaluatedKey")
            self._logger.debug(
                "Query returned %d items after filtering, has_more=%s",
                len(items),
                last_evaluated_key is not None,
            )

            return items, last_evaluated_key

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error(
                "Failed to list defects by raised user %s. Code=%s Message=%s",
                user_id,
                error_code,
                error_message,
            )
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not list defects by raised user: {error_message}", 500, "dynamodb_error") from exc

    def query_open_defects_by_assigned_inspector(self, inspector_id: str) -> List[Dict[str, Any]]:
        """
        Query open defects assigned to a specific inspector.
        Open defects are those not in 'closed' or 'resolved' status.
        Used for deletion validation.
        """
        try:
            query_kwargs = {
            "IndexName": "GSI3",
            "KeyConditionExpression": Key("GSI3PK").eq(inspector_id),
            "FilterExpression": (Attr("status").ne("closed")& Attr("status").ne("resolved")),
            }
            
            items = []
            response = self._table.query(**query_kwargs)
            items.extend(response.get("Items", []))
            
            # Handle pagination
            while "LastEvaluatedKey" in response:
                query_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = self._table.scan(**query_kwargs)
                items.extend(response.get("Items", []))
            
            return items
        except ClientError as exc:
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to query open defects for inspector %s: %s", inspector_id, error_message)
            raise ApiError(f"Could not query open defects: {error_message}", 500, "dynamodb_error") from exc

    def query_open_defects_by_assigned_crew(self, crew_id: str) -> List[Dict[str, Any]]:
        """
        Query open defects assigned to a specific crew member.
        Open defects are those not in 'closed' or 'resolved' status.
        Used for deletion validation.
        """
        try:
            query_kwargs = {
            "IndexName": "GSI3",  # GSI for assigned_crew_id
            "KeyConditionExpression": Key("GSI3PK").eq(crew_id),
            "FilterExpression": (Attr("status").ne("closed")& Attr("status").ne("resolved")),
            }
            
            items = []
            response = self._table.query(**query_kwargs)
            items.extend(response.get("Items", []))
            
            # Handle pagination
            while "LastEvaluatedKey" in response:
                query_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = self._table.scan(**query_kwargs)
                items.extend(response.get("Items", []))
            
            return items
        except ClientError as exc:
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to query open defects for crew %s: %s", crew_id, error_message)
            raise ApiError(f"Could not query open defects: {error_message}", 500, "dynamodb_error") from exc
