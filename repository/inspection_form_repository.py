"""
Repository layer for Inspection Forms table interactions.
"""
from typing import Any, Dict, List, Optional, Tuple

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key,Attr
from config.aws import get_inspection_forms_table
from utility.errors import ApiError
from utility.logger import get_logger


class InspectionFormRepository:
    """
    Provides CRUD access for inspection forms.
    """

    def __init__(self) -> None:
        self._table = get_inspection_forms_table()
        self._logger = get_logger(self.__class__.__name__)

    def put_item(self, item: Dict[str, Any]) -> None:
        """
        Persist a new inspection form.
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
                "Failed to create inspection form in DynamoDB. Code: %s, Message: %s",
                error_code,
                error_message,
            )
            # Fallback stdout print to ensure visibility in CloudWatch logs
            print(f"[ERROR] DynamoDB put_item failed. Code: {error_code}, Message: {error_message}")
            if hasattr(exc, "response"):
                print("[ERROR] DynamoDB error response:", exc.response)
            print("[ERROR] Table name used:", getattr(self._table, "name", "unknown"))
            if error_code == "ConditionalCheckFailedException":
                raise ApiError("Inspection form already exists", 409, "inspection_form_exists") from exc
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not create inspection form: {error_message}", 500, "dynamodb_error") from exc

    def get_item(self, form_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an inspection form by primary key.
        """

        try:
            #response = self._table.get_item(Key={"form_id": form_id})
            pk = f"FORM#{form_id}"
            response = self._table.get_item(
                Key={
                    "PK": pk,
                    "SK": "METADATA"
                }
            )
            item = response.get("Item")

            return item
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to fetch inspection form %s: %s", form_id, error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not fetch inspection form: {error_message}", 500, "dynamodb_error") from exc

    def list_by_vessel(
        self,
        vessel_id: str,
        limit: int,
        cursor: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        List inspection forms for a specific vessel using vessel_id_index.
        """

        try:
            query_kwargs: Dict[str, Any] = {
                "IndexName": "vessel_id_index",
                "KeyConditionExpression": "vessel_id = :vessel_id",
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
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to query inspection forms for vessel %s: %s", vessel_id, error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not query inspection forms: {error_message}", 500, "dynamodb_error") from exc

    def list_by_admin(
        self,
        admin_id: str,
        limit: int,
        cursor: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        List inspection forms created by a specific admin using admin_id_index.
        """

        try:
            query_kwargs: Dict[str, Any] = {
                "IndexName": "GSI1",
                "KeyConditionExpression": Key("GSI1PK").eq("FORM"),
                "Limit": limit,
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
            self._logger.error("Failed to query inspection forms for admin %s: %s", admin_id, error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not query inspection forms: {error_message}", 500, "dynamodb_error") from exc

    def list_by_inspector(
        self,
        inspector_id: str,
        limit: int,
        cursor: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        List inspection forms assigned to a specific inspector using inspector_id_index.
        """

        try:
            query_kwargs: Dict[str, Any] = {
                "IndexName": "inspector_id_index",
                "KeyConditionExpression": "assigned_inspector_id = :inspector_id",
                "ExpressionAttributeValues": {":inspector_id": inspector_id},
                "Limit": limit,
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
            self._logger.error("Failed to query inspection forms for inspector %s: %s", inspector_id, error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not query inspection forms: {error_message}", 500, "dynamodb_error") from exc

    def update_item(self, form_id: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update mutable inspection form fields.
        """

        update_expression_parts = []
        expression_values: Dict[str, Any] = {}
        expression_names: Dict[str, str] = {}

        for key, value in attributes.items():
            # Use expression attribute names to avoid DynamoDB reserved keywords (e.g. status)
            placeholder_name = f"#attr_{key}"
            placeholder_value = f":{key}"
            expression_names[placeholder_name] = key
            update_expression_parts.append(f"{placeholder_name} = {placeholder_value}")
            expression_values[placeholder_value] = value

        update_expression = "SET " + ", ".join(update_expression_parts)

        try:
            response = self._table.update_item(
                Key={"PK": f"FORM#{form_id}","SK": "METADATA"},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
                ConditionExpression="attribute_exists(PK)",
                ReturnValues="ALL_NEW",
            )
            return response["Attributes"]
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to update inspection form %s: %s", form_id, error_message)
            if error_code == "ConditionalCheckFailedException":
                raise ApiError("Inspection form not found", 404, "form_not_found") from exc
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not update inspection form: {error_message}", 500, "dynamodb_error") from exc

    def list_items(
        self,
        limit: int = 1000,
        cursor: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        List all inspection forms using scan (for dashboard aggregation).
        """

        try:
            scan_kwargs: Dict[str, Any] = {"Limit": limit}
            if cursor:
                scan_kwargs["ExclusiveStartKey"] = cursor

            response = self._table.scan(**scan_kwargs)
            items = response.get("Items", [])
            last_evaluated_key = response.get("LastEvaluatedKey")
            return items, last_evaluated_key
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to scan inspection forms: %s", error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not list inspection forms: {error_message}", 500, "dynamodb_error") from exc

    def find_active_form_by_title(self, title: str, exclude_form_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find an active or assigned form with the given title.
        Active/assigned means status is not 'completed'.
        Optionally exclude a specific form_id (useful for update operations).
        
        Note: This uses scan which can be expensive. Consider adding a GSI on title+status in the future.
        """
        try:
            # Scan with filter to find forms with matching title and active status
            # Active means status is 'Unassigned' or 'In Progress' (not 'Closed')
            '''scan_kwargs: Dict[str, Any] = {
                "FilterExpression": "title = :title AND (attribute_not_exists(#status) OR (#status <> :closed))",
                "ExpressionAttributeNames": {"#status": "status"},
                "ExpressionAttributeValues": {
                    ":title": title,
                    ":closed": "Closed",
                },
            }
            
            response = self._table.scan(**scan_kwargs)'''
            response = self._table.query(
                IndexName="GSI1",
                KeyConditionExpression=Key("GSI1PK").eq("FORM")&Key("GSI1SK").eq(title)
            )
            items = response.get("Items", [])
            
            # Handle pagination if needed (though unlikely for title uniqueness check)
            '''while "LastEvaluatedKey" in response:
                scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = self._table.scan(**scan_kwargs)
                items.extend(response.get("Items", []))'''
            
            # Filter out excluded form_id if provided
            if exclude_form_id:
                items = [item for item in items if item.get("form_id") != exclude_form_id]
            items = [i for i in items if i.get("status") != "Closed"]
            # Return first match (should only be one for uniqueness)
            return items[0] if items else None
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown") if hasattr(exc, "response") else "Unknown"
            error_message = exc.response.get("Error", {}).get("Message", str(exc)) if hasattr(exc, "response") else str(exc)
            self._logger.error("Failed to find form by title %s: %s", title, error_message)
            if error_code == "ResourceNotFoundException":
                raise ApiError(f"DynamoDB table not found: {getattr(self._table, 'name', 'unknown')}", 500, "table_not_found") from exc
            raise ApiError(f"Could not check form title uniqueness: {error_message}", 500, "dynamodb_error") from exc

    def query_active_forms_by_assigned_inspector(self, inspector_id: str) -> List[Dict[str, Any]]:
        """
        Query active inspection forms assigned to a specific inspector.
        Active forms are those not in 'closed' or 'submitted' status.
        Used for deletion validation.
        """
        try:
            # query_kwargs: Dict[str, Any] = {
            #     "IndexName": "inspector_id_index",
            #     "KeyConditionExpression": "assigned_inspector_id = :inspector_id",
            #     "FilterExpression": "attribute_not_exists(#status) OR (#status NOT IN (:closed, :submitted))",
            #     "ExpressionAttributeNames": {"#status": "status"},
            #     "ExpressionAttributeValues": {
            #         ":inspector_id": inspector_id,
            #         ":closed": "closed",
            #         ":submitted": "submitted",
            #     },
            # }
            query_kwargs: Dict[str, Any] = {
                "IndexName": "GSI3", 
                "KeyConditionExpression": Key("GSI3PK").eq(inspector_id),
                "FilterExpression": (
                    Attr("status").not_exists()
                    | (
                    Attr("status").ne("closed")
                    & Attr("status").ne("submitted")
                )
                ),
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
            self._logger.error("Failed to query active forms for inspector %s: %s", inspector_id, error_message)
            raise ApiError(f"Could not query active forms: {error_message}", 500, "dynamodb_error") from exc

    def query_active_forms_by_assigned_crew(self, crew_id: str) -> List[Dict[str, Any]]:
        """
        Query active inspection forms assigned to a specific crew member.
        Active forms are those not in 'closed' or 'submitted' status.
        Used for deletion validation.
        
        Note: This uses scan since there's no GSI on assigned_crew_id.
        """
        try:
            query_kwargs: Dict[str, Any] = {
                "IndexName": "GSI3", 
                "KeyConditionExpression": Key("GSI3PK").eq(crew_id),
                "FilterExpression": (
                    Attr("status").not_exists()
                    | (
                    Attr("status").ne("closed")
                    & Attr("status").ne("submitted")
                )
                ),
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
            self._logger.error("Failed to query active forms for crew %s: %s", crew_id, error_message)
            raise ApiError(f"Could not query active forms: {error_message}", 500, "dynamodb_error") from exc
