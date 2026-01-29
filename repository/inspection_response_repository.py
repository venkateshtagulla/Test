"""
Repository layer for Inspection Responses table interactions.
"""
from typing import Any, Dict, List

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from config.aws import get_inspection_responses_table
from utility.errors import ApiError
from utility.logger import get_logger


class InspectionResponseRepository:
    """
    Provides CRUD access for inspection responses.
    Responses are stored per inspection, enabling form template reuse.
    """

    def __init__(self) -> None:
        self._table = get_inspection_responses_table()
        self._logger = get_logger(self.__class__.__name__)

    def put_item(self, item: Dict[str, Any]) -> None:
        """
        Write a single response (idempotent).
        Overwrites existing response for the same (inspection_id, question_id).
        """

        try:
            self._table.put_item(Item=item)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown")
            error_message = exc.response.get("Error", {}).get("Message", str(exc))
            self._logger.error(
                "Failed to write response for inspection %s question %s: %s",
                item.get("inspection_id"),
                item.get("question_id"),
                error_message
            )
            raise ApiError(
                "Failed to save response",
                500,
                "response_write_failed"
            ) from exc

    def batch_put_items(self, items: List[Dict[str, Any]]) -> None:
        """
        Write multiple responses in batch (up to 25 per batch).
        Used for offline sync and bulk submissions.
        """

        try:
            self._logger.info(f"Attempting to batch write {len(items)} responses")
            self._logger.debug(f"Response items: {items}")
            
            with self._table.batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)
                    
            self._logger.info(f"Successfully wrote {len(items)} responses")
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown")
            error_message = exc.response.get("Error", {}).get("Message", str(exc))
            self._logger.error(
                "Failed to batch write responses: Code=%s, Message=%s, Full Error=%s",
                error_code,
                error_message,
                exc.response
            )
            raise ApiError(
                "Failed to save responses",
                500,
                "batch_response_write_failed"
            ) from exc
        except Exception as exc:
            self._logger.error(
                "Unexpected error during batch write: %s",
                str(exc),
                exc_info=True
            )
            raise ApiError(
                "Failed to save responses",
                500,
                "batch_response_write_failed"
            ) from exc

    def query_by_inspection(self, inspection_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all responses for a specific inspection.
        Returns list of response items.
        """
        #pk = f"FORM#{form_id}"
        try:
            response = self._table.query(
                KeyConditionExpression=Key("inspection_id").eq(inspection_id)
            )
            return response.get("Items", [])
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown")
            error_message = exc.response.get("Error", {}).get("Message", str(exc))
            self._logger.error(
                "Failed to query responses for inspection %s: %s",
                inspection_id,
                error_message
            )
            raise ApiError(
                "Failed to fetch responses",
                500,
                "response_query_failed"
            ) from exc
