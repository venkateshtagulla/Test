"""
Repository layer for Crew table interactions.
"""
from typing import Any, Dict, List, Optional, Tuple

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from config.aws import get_crew_table
from utility.errors import ApiError
from utility.logger import get_logger


class CrewRepository:
    """
    Provides CRUD access for crew members.
    """

    def __init__(self) -> None:
        self._table = get_crew_table()
        self._logger = get_logger(self.__class__.__name__)

    def put_item(self, item: Dict[str, Any]) -> None:
        """
        Persist a new crew member.
        """

        try:
            self._table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(PK)",
            )
        except ClientError as exc:
            self._logger.error("Failed to create crew: %s", exc)
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ApiError("Crew member already exists", 409, "crew_exists") from exc
            raise ApiError("Could not create crew", 500, "dynamodb_error") from exc

    def get_item(self, crew_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a crew member by primary key.
        """

        try:
            pk = f"CREW#{crew_id}"
            response = self._table.get_item(Key={"PK": pk,"SK":"METADATA"})
            return response.get("Item")
        except ClientError as exc:
            self._logger.error("Failed to fetch crew: %s", exc)
            raise ApiError("Could not fetch crew", 500, "dynamodb_error") from exc

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a crew member using the email GSI.
        """

        try:
            response = self._table.query(
                # IndexName="email_index",
                # KeyConditionExpression="email = :email",
                # ExpressionAttributeValues={":email": email},
                # Limit=1,
                IndexName="GSI1",
                KeyConditionExpression=Key("GSI1PK").eq("CREW") & Key("GSI1SK").eq(email),
                Limit=1,
            )
            items = response.get("Items", [])
            return items[0] if items else None
        except ClientError as exc:
            self._logger.error("Failed to query crew by email: %s", exc)
            raise ApiError("Could not query crew", 500, "dynamodb_error") from exc

    def update_item(self, crew_id: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update mutable crew fields.
        """

        #update_expression = "SET " + ", ".join(f"{key} = :{key}" for key in attributes)
        #expression_values = {f":{key}": value for key, value in attributes.items()}
        update_expression = "SET " + ", ".join(f"#{k} = :{k}" for k in attributes)
        expression_values = {f":{k}": v for k, v in attributes.items()}
        expression_names = {f"#{k}": k for k in attributes}

        try:
            response = self._table.update_item(
                Key={"PK": f"CREW#{crew_id}","SK": "METADATA",},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
                ConditionExpression="attribute_exists(PK)",
                ReturnValues="ALL_NEW",
            )
            return response["Attributes"]
        except ClientError as exc:
            self._logger.error("Failed to update crew: %s", exc)
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ApiError("Crew not found", 404, "crew_not_found") from exc
            raise ApiError("Could not update crew", 500, "dynamodb_error") from exc

    def list_items(
        self, limit: int, exclusive_start_key: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        List crew with pagination support using DynamoDB scan.
        Returns (items, last_evaluated_key).
        """

        query_kwargs: Dict[str, Any] = {
        "IndexName": "GSI1",
        "KeyConditionExpression": Key("GSI1PK").eq("CREW"),
        "Limit": limit,
       }
        if exclusive_start_key:
            query_kwargs["ExclusiveStartKey"] = exclusive_start_key

        try:
            response = self._table.query(**query_kwargs)
            items = response.get("Items", [])
            last_evaluated_key = response.get("LastEvaluatedKey")
            return items, last_evaluated_key
        except ClientError as exc:
            self._logger.error("Failed to list crew: %s", exc)
            raise ApiError("Could not list crew", 500, "dynamodb_error") from exc
    
    def delete_item(self, crew_id: str) -> None:
        """
        Delete an inspector record.
        """

        try:
            self._table.delete_item(
                Key={"PK": f"CREW#{crew_id}","SK": "METADATA",},
                ConditionExpression="attribute_exists(PK)",
            )
        except ClientError as exc:
            self._logger.error("Failed to delete crew: %s", exc)
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ApiError("Inspector not found", 404, "crew_not_found") from exc
            raise ApiError("Could not delete crew", 500, "dynamodb_error") from exc

