"""
Repository layer for Vessel table interactions.
"""
from typing import Any, Dict, List, Optional, Tuple

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from config.aws import dynamodb_resource
from config.settings import get_settings
from utility.errors import ApiError
from utility.logger import get_logger


settings = get_settings()


class VesselRepository:
    """
    Provides CRUD and query access for vessels.
    """

    def __init__(self) -> None:
        self._table = dynamodb_resource.Table(settings.vessels_table)
        self._logger = get_logger(self.__class__.__name__)

    def put_item(self, item: Dict[str, Any]) -> None:
        """
        Persist a new vessel record.
        """
        try:
            self._table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(PK)",
            )
        except ClientError as exc:
            self._logger.error("Failed to create vessel: %s", exc)
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ApiError(
                    "Vessel already exists", 409, "vessel_exists"
                ) from exc
            raise ApiError(
                "Could not create vessel", 500, "dynamodb_error"
            ) from exc

    def get_item(self, vessel_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a vessel by its primary key.
        """
        try:
            
            pk = f"VESSEL#{vessel_id}"
            #print("Fetching vessel with PK:", pk)# must match stored PK
            response = self._table.get_item(
                Key={
                    "PK": pk,
                    "SK": "METADATA",
                }
            )
           # print("DynamoDB response:", response)
            return response.get("Item")
        except ClientError as exc:
            self._logger.error(
                "Failed to fetch vessel %s: %s", vessel_id, exc
            )
            raise ApiError(
                "Could not fetch vessel", 500, "dynamodb_error"
            ) from exc

    # ---------------------------------------------------------------------
    # Query vessels using GSI1 (GSI1PK = 'VESSEL', GSI1SK = vessel_type)
    # ---------------------------------------------------------------------

    def list_vessels_by_type(
        self,
        limit: int,
        cursor: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        List all vessels sorted by vessel_type using GSI1.
        """
        try:
            query_kwargs: Dict[str, Any] = {
                "IndexName": "GSI1",
                "KeyConditionExpression":Key("GSI1PK").eq("VESSEL"),
                "Limit": limit,
                "ScanIndexForward": True,  # Ascending by vessel_type
            }

            if cursor:
                query_kwargs["ExclusiveStartKey"] = cursor

            response = self._table.query(**query_kwargs)
            items = response.get("Items", [])
            last_evaluated_key = response.get("LastEvaluatedKey")

            return items, last_evaluated_key

        except ClientError as exc:
            self._logger.error(
                "Failed to query vessels by type: %s", exc
            )
            raise ApiError(
                "Could not query vessels", 500, "dynamodb_error"
            ) from exc

    # ---------------------------------------------------------------------
    # Scan vessels (use only for admin/dashboard purposes)
    # ---------------------------------------------------------------------

    def list_items(
        self,
        limit: int = 1000,
        cursor: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        List all vessels using scan (for dashboard aggregation).
        """
        try:
            query_kwargs: Dict[str, Any] = {
            "IndexName": "GSI1",
            "KeyConditionExpression": Key("GSI1PK").eq("VESSEL"),
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
            self._logger.error("Failed to scan vessels: %s", exc)
            raise ApiError(
                "Could not list vessels", 500, "dynamodb_error"
            ) from exc
