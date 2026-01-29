"""
Business logic for vessel management flows.
"""
from datetime import datetime
from uuid import uuid4
from typing import Dict, List, Optional, Any
from boto3.dynamodb.conditions import Key


from repository.crew_repository import CrewRepository
from repository.defect_repository import DefectRepository
from repository.inspection_assignment_repository import InspectionAssignmentRepository
from repository.inspection_form_repository import InspectionFormRepository
from repository.inspector_repository import InspectorRepository
from repository.vessel_repository import VesselRepository
from utility.errors import ApiError
from utility.logger import get_logger
from utility.s3_utils import sign_s3_url_if_possible


class VesselService:
    """
    Service orchestrating vessel creation and listing for admins.
    """

    def __init__(
        self,
        repository: VesselRepository,
        form_repository: Optional[InspectionFormRepository] = None,
        inspector_repository: Optional[InspectorRepository] = None,
        crew_repository: Optional[CrewRepository] = None,
        defect_repository: Optional[DefectRepository] = None,
        inspection_assignment_repository: Optional[InspectionAssignmentRepository] = None,
    ) -> None:
        """
        Initialize the service with its repository dependencies.
        """

        self._repository = repository
        self._form_repository = form_repository or InspectionFormRepository()
        self._inspector_repository = inspector_repository or InspectorRepository()
        self._crew_repository = crew_repository or CrewRepository()
        self._defect_repository = defect_repository or DefectRepository()
        self._inspection_assignment_repository = inspection_assignment_repository or InspectionAssignmentRepository()
        self._logger = get_logger(self.__class__.__name__)

    def _item_to_response(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a raw DynamoDB vessel item into a `VesselResponse` dict.
        """

        return {
            "vessel_id": item["vessel_id"],
            "name": item.get("name") or item.get("vessel_name") or "Unknown Vessel",
            "vessel_type": item["vessel_type"],
            "description": item["description"],
            "imo_number": item.get("imo_number"),
            "status": item.get("status"),
        }

    def create_vessel(self, admin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new vessel owned by the given admin.
        """
        
        # Manual validation
        name = payload.get("name")
        vessel_type = payload.get("vessel_type")
        if not name or not vessel_type:
             raise ApiError("Name and vessel_type are required", 400, "missing_fields")

        now = datetime.utcnow().isoformat()
        uid = str(uuid4())
        pk = f"VESSEL#{uid}"
        vessel = {
            "PK": pk,
            "SK": "METADATA",
            "vessel_id": uid,
            "admin_id": admin_id,
            "name": name,
            "vessel_type": vessel_type,
            "description": payload.get("message"),
            "imo_number": payload.get("imo_number"),
            "status": "ACTIVE",
            "created_at": now,
            "entity":"VESSEL",
            "updated_at": now,
            "GSI1PK": "VESSEL",
            "GSI1SK": vessel_type,
        }
        
        self._repository.put_item(vessel)
        self._logger.info("Vessel %s created by admin %s", vessel["vessel_id"], admin_id)
        response = self._item_to_response(vessel)
        return response

    def get_vessel(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch a single vessel by its identifier with detailed information including inspections.
        """
        vessel_id = payload.get("vessel_id")
        if not vessel_id:
             raise ApiError("vessel_id is required", 400, "missing_vessel_id")

        item = self._repository.get_item(vessel_id)
        if not item:
            raise ApiError("Vessel not found", 404, "vessel_not_found")

        # Fetch all inspection assignments for this vessel
        inspections_data: List[Dict[str, Any]] = []
        try:
            # Fetch all inspection assignments for this vessel
            self._logger.info("Fetching inspections for vessel %s", vessel_id)
            inspection_items, _ = self._inspection_assignment_repository.list_by_vessel(
                vessel_id=vessel_id, limit=1000
            )
            self._logger.info("Found %d inspection assignments for vessel %s", len(inspection_items), vessel_id)

            for inspection_item in inspection_items:
                try:
                    # Get form details
                    form_title = "Unknown Form"
                    form_id = inspection_item.get("form_id")
                    if form_id:
                        try:
                            form = self._form_repository.get_item(form_id)
                            if form:
                                form_title = form.get("title", "Unknown Form")
                        except Exception as form_exc:
                            self._logger.warning(
                                "Failed to fetch form %s: %s", form_id, form_exc
                            )

                    # Get assignee name
                    assignee_name = "Unknown"
                    assignee_id = inspection_item.get("assignee_id")
                    assignee_type = inspection_item.get("assignee_type", "")
                    
                    if assignee_id and assignee_type == "inspector":
                        try:
                            inspector = self._inspector_repository.get_item(assignee_id)
                            if inspector:
                                assignee_name = (
                                    f"{inspector.get('first_name', '')} "
                                    f"{inspector.get('last_name', '')}".strip()
                                )
                        except Exception as exc:
                            self._logger.warning(
                                "Failed to fetch inspector %s: %s", assignee_id, exc
                            )
                    elif assignee_id and assignee_type == "crew":
                        try:
                            crew = self._crew_repository.get_item(assignee_id)
                            if crew:
                                assignee_name = (
                                    f"{crew.get('first_name', '')} "
                                    f"{crew.get('last_name', '')}".strip()
                                )
                        except Exception as exc:
                            self._logger.warning(
                                "Failed to fetch crew %s: %s", assignee_id, exc
                            )

                    inspection_response = {
                        "assignment_id": inspection_item["assignment_id"],
                        "inspection_name": inspection_item.get("inspection_name", "Unnamed Inspection"),
                        "form_id": form_id or "",
                        "form_title": form_title,
                        "assignee_type": assignee_type,
                        "assignee_name": assignee_name,
                        "role": inspection_item.get("role", ""),
                        "priority": inspection_item.get("priority", "Medium"),
                        "due_date": inspection_item.get("due_date", ""),
                        "status": inspection_item.get("status", "Pending"),
                        "created_at": inspection_item.get("created_at", ""),
                    }
                    inspections_data.append(inspection_response)
                except Exception as item_exc:
                    self._logger.warning(
                        "Failed to process inspection %s: %s",
                        inspection_item.get("assignment_id", "unknown"),
                        item_exc
                    )
                    continue
        except Exception as exc:
            self._logger.warning(
                "Failed to fetch inspections for vessel %s: %s", vessel_id, exc
            )
            # Continue even if inspections fetch fails

        # Fetch all defects for this vessel
        defects_data: List[Dict[str, Any]] = []
        try:
            # Fetch all defects with pagination (scan with filter requires pagination)
            # Scan operations apply filters after scanning, so we need to paginate
            defect_items: List[Dict] = []
            cursor = None
            max_iterations = 10  # Limit iterations to prevent infinite loops
            
            self._logger.info(
                "Fetching defects for vessel %s with pagination", vessel_id
            )
            
            for iteration in range(max_iterations):
                try:
                    batch_items, last_key = self._defect_repository.list_items(
                        vessel_id=vessel_id, limit=100, cursor=cursor
                    )
                    self._logger.info(
                        "Batch %d: Fetched %d defects, has_more: %s",
                        iteration + 1,
                        len(batch_items),
                        last_key is not None,
                    )
                    defect_items.extend(batch_items)
                    
                    # Continue pagination if there's a last_key (more items to scan)
                    # Don't break on empty batch_items because filter might have filtered them all
                    if not last_key:
                        break
                    cursor = last_key
                except Exception as batch_exc:
                    self._logger.error(
                        "Error fetching defect batch %d for vessel %s: %s",
                        iteration + 1,
                        vessel_id,
                        batch_exc,
                        exc_info=True,
                    )
                    break
            
            self._logger.info(
                "Total defects fetched for vessel %s: %d", vessel_id, len(defect_items)
            )

            for defect_item in defect_items:
                try:
                    # Sign photo URLs to ensure they open in browser
                    photos = defect_item.get("photos") or []
                    signed_photos = [
                        sign_s3_url_if_possible(url) or url for url in photos
                    ] if photos else None

                    defect_response = {
                        "defect_id": defect_item["defect_id"],
                        "title": defect_item["title"],
                        "description": defect_item.get("description"),
                        "severity": defect_item.get("severity", "minor"),
                        "priority": defect_item.get("priority", "medium"),
                        "status": defect_item.get("status", "open"),
                        "location_on_ship": defect_item.get("location_on_ship"),
                        "equipment_name": defect_item.get("equipment_name"),
                        "form_id": defect_item.get("form_id"),
                        "due_date": defect_item.get("due_date"),
                        "photos": signed_photos,
                        "created_at": defect_item.get("created_at"),
                        "updated_at": defect_item.get("updated_at"),
                    }
                    defects_data.append(defect_response)
                except Exception as item_exc:
                    self._logger.error(
                        "Error processing defect item %s: %s",
                        defect_item.get("defect_id", "unknown"),
                        item_exc,
                        exc_info=True,
                    )
                    continue
        except Exception as exc:
            self._logger.error(
                "Failed to fetch defects for vessel %s: %s",
                vessel_id,
                exc,
                exc_info=True,
            )
            # Continue even if defects fetch fails - return empty list

        detail_response = {
            "vessel_id": item["vessel_id"],
            "name": item.get("name") or item.get("vessel_name") or "Unknown Vessel",
            "vessel_type": item["vessel_type"],
            "other_vessel_type": item.get("other_vessel_type"),
            "imo_number": item.get("imo_number"),
            "status": item.get("status"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "inspections": inspections_data,
            "defects": defects_data,
        }
        return detail_response
    def list_vessels(self,admin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    
        try:
            page = payload.get("page", 1)
            limit = payload.get("limit", 20)
            fetch_limit = limit + 1
            cursor_dict = None

            # Walk previous pages to get the cursor for current page
            for _ in range(1, page):
                _, last_key = self._repository.list_vessels_by_type(
                    limit=limit,
                    cursor=cursor_dict,
                )
                if not last_key:
                    return {
                        "items": [],
                        "page": page,
                        "limit": limit,
                        "has_next": False,
                    }
                cursor_dict = last_key

            # Fetch current page items
            items, last_key = self._repository.list_vessels_by_type(
                limit=fetch_limit,
                cursor=cursor_dict,
            )

            has_next = len(items) > limit
            items = items[:limit] if has_next else items

            vessels = [self._item_to_response(item) for item in items]

            return {
                "items": vessels,
                "page": page,
                "limit": limit,
                "has_next": has_next,
            }

        except ApiError:
            raise
        except Exception as exc:
            self._logger.error("Failed to list vessels: %s", exc, exc_info=True)
            raise ApiError("Failed to list vessels", 500, "list_vessels_failed") from exc

    