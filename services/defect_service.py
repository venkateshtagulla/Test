"""
Service layer for defect operations.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from repository.crew_repository import CrewRepository
from repository.defect_repository import DefectRepository
from repository.inspection_form_repository import InspectionFormRepository
from repository.inspector_repository import InspectorRepository
from repository.vessel_repository import VesselRepository
from utility.errors import ApiError
from utility.logger import get_logger
from utility.s3_utils import sign_s3_url_if_possible


class DefectService:
    """
    Business logic for defect management operations.
    """

    def __init__(self, repository: DefectRepository) -> None:
        """
        Initialize the service with its repository dependency.
        """

        self._repository = repository
        self._logger = get_logger(self.__class__.__name__)
        # Lazy-init related repositories
        self._vessel_repo = VesselRepository()
        self._inspector_repo = InspectorRepository()
        self._crew_repo = CrewRepository()
        self._form_repo = InspectionFormRepository()

    def _build_related_vessel(self, vessel_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Fetch and map minimal vessel information.
        """

        if not vessel_id:
            return None
        vessel_item = self._vessel_repo.get_item(vessel_id)
        if not vessel_item:
            vessel_item = {} # Fallback to avoid error if vessel deleted
        
        return {
            "vessel_id": vessel_item.get("vessel_id", vessel_id),
            "name": vessel_item.get("name"),
            "imo_number": vessel_item.get("imo_number"),
        }

    def _build_related_user(
        self,
        user_id: Optional[str],
        user_type: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch and map minimal user information (inspector or crew).
        """

        if not user_id:
            return None

        if user_type == "inspector":
            item = self._inspector_repo.get_item(user_id)
            if not item:
                return None
            first_name = item.get("first_name", "")
            last_name = item.get("last_name", "")
            name = f"{first_name} {last_name}".strip() if first_name or last_name else None
            return {
                "user_id": item["inspector_id"],
                "name": name,
                "email": item.get("email"),
                "user_type": "inspector",
            }

        if user_type == "crew":
            item = self._crew_repo.get_item(user_id)
            if not item:
                return None
            first_name = item.get("first_name", "")
            last_name = item.get("last_name", "")
            name = f"{first_name} {last_name}".strip() if first_name or last_name else None
            return {
                "user_id": item["crew_id"],
                "name": name,
                "email": item.get("email"),
                "user_type": "crew",
            }

        return None

    def _build_related_form(self, form_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Fetch and map minimal form information.
        """

        if not form_id:
            return None
        form_item = self._form_repo.get_item(form_id)
        if not form_item:
            return None
        return {
            "form_id": form_item["form_id"],
            "title": form_item.get("title"),
        }

    def _add_activity(self, existing_activities: Optional[List[Dict[str, str]]], action: str, performed_by: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Add an activity entry to the task activities list.
        """

        activities = existing_activities or []
        new_activity = {
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if performed_by:
            new_activity["performed_by"] = performed_by
        activities.append(new_activity)
        return activities

    def _add_admin_comment(self, existing_comments: Optional[List[str]], comment: str) -> List[str]:
        """
        Add an admin comment to the comments list.
        """

        comments = existing_comments or []
        if comment:
            comments.append(comment)
        return comments

    def _item_to_response(self, item: Dict) -> Dict[str, Any]:
        """
        Convert DynamoDB item to dictionary response with expanded relations.
        """

        vessel = self._build_related_vessel(item.get("vessel_id"))
        form = self._build_related_form(item.get("form_id"))
        raised_by_inspector = self._build_related_user(item.get("raised_by_inspector_id"), "inspector")
        raised_by_crew = self._build_related_user(item.get("raised_by_crew_id"), "crew")
        assigned_inspector = self._build_related_user(item.get("assigned_inspector_id"), "inspector")
        assigned_crew = self._build_related_user(item.get("assigned_crew_id"), "crew")

        # Sign photo URLs to ensure they open in browser
        photos = item.get("photos") or []
        signed_photos = [sign_s3_url_if_possible(url) or url for url in photos]
        
        analysis_photos = item.get("analysis_photos") or []
        signed_analysis_photos = [sign_s3_url_if_possible(url) or url for url in analysis_photos]
        
        return {
            "defect_id": item["defect_id"],
            "vessel_id": item["vessel_id"],
            "form_id": item.get("form_id"),
            "assignment_id": item.get("assignment_id"),
            "title": item["title"],
            "description": item.get("description"),
            "severity": item.get("severity", "minor"),
            "priority": item.get("priority", "medium"),
            "status": item.get("status", "open"),
            "location_on_ship": item.get("location_on_ship"),
            "equipment_name": item.get("equipment_name"),
            "raised_by_inspector_id": item.get("raised_by_inspector_id"),
            "raised_by_crew_id": item.get("raised_by_crew_id"),
            "assigned_inspector_id": item.get("assigned_inspector_id"),
            "assigned_crew_id": item.get("assigned_crew_id"),
            "triggered_question_order": item.get("triggered_question_order"),
            "triggered_question_text": item.get("triggered_question_text"),
            "photos": signed_photos if signed_photos else None,
            "inspector_comments": item.get("inspector_comments"),
            "crew_comments": item.get("crew_comments"),
            "admin_comments": item.get("admin_comments"),
            "task_activities": item.get("task_activities"),
            "due_date": item.get("due_date"),
            "analysis_root_cause": item.get("analysis_root_cause"),
            "analysis_impact_assessment": item.get("analysis_impact_assessment"),
            "analysis_recurrence_probability": item.get("analysis_recurrence_probability"),
            "analysis_notes": item.get("analysis_notes"),
            "analysis_photos": signed_analysis_photos if signed_analysis_photos else None,
            "analysis_by_inspector_id": item.get("analysis_by_inspector_id"),
            "analysis_by_crew_id": item.get("analysis_by_crew_id"),
            "analysis_created_at": item.get("analysis_created_at"),
            "analysis_updated_at": item.get("analysis_updated_at"),
            "resolved_at": item.get("resolved_at"),
            "closed_at": item.get("closed_at"),
            "approved_by_admin_id": item.get("approved_by_admin_id"),
            "closed_by_admin_id": item.get("closed_by_admin_id"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "vessel": vessel,
            "form": form,
            "raised_by_inspector": raised_by_inspector,
            "raised_by_crew": raised_by_crew,
            "assigned_inspector": assigned_inspector,
            "assigned_crew": assigned_crew,
        }

    # ---------------------------------------------------------------------
    # Creation from inspector / crew
    # ---------------------------------------------------------------------

    def _create_defect_for_user(
        self,
        *,
        payload: Dict[str, Any],
        raised_by_inspector_id: Optional[str],
        raised_by_crew_id: Optional[str],
    ) -> Dict[str, Any]:
        """
        Shared helper to create a defect raised by an inspector or crew member.
        """

        try:
            vessel_id = payload.get("vessel_id")
            form_id = payload.get("form_id")
            
            self._logger.info(
                "Creating defect for vessel=%s form=%s raised_by_inspector=%s raised_by_crew=%s",
                vessel_id,
                form_id,
                raised_by_inspector_id,
                raised_by_crew_id,
            )

            # Optional: validate that form exists and belongs to the vessel (only if form_id is provided)
            if form_id:
                form = self._form_repo.get_item(form_id)
                if not form:
                    raise ApiError("Inspection form not found", 404, "form_not_found")

                if vessel_id != form.get("vessel_id"):
                    self._logger.warning(
                        "Defect create: payload vessel_id %s does not match form %s vessel_id %s",
                        vessel_id,
                        form_id,
                        form.get("vessel_id"),
                    )

            assigned_inspector_id: Optional[str] = None
            assigned_crew_id: Optional[str] = None
            if payload.get("assignee_id") and payload.get("assignee_type"):
                if payload.get("assignee_type") == "inspector":
                    assigned_inspector_id = payload.get("assignee_id")
                elif payload.get("assignee_type") == "crew":
                    assigned_crew_id = payload.get("assignee_id")

            now = datetime.utcnow().isoformat()
            defect_id = str(uuid4())
            pk=f"DEFECT#{defect_id}"
            if raised_by_inspector_id:
                gsi3pk = raised_by_inspector_id
            elif raised_by_crew_id:
                gsi3pk = raised_by_crew_id
            else:
                gsi3pk = None  
            defect_dict = {
                "PK":pk,
                "SK":"METADATA",
                "defect_id": defect_id,
                "vessel_id": payload.get("vessel_id"),
                "form_id": payload.get("form_id"),
                "assignment_id": payload.get("assignment_id"),
                "title": payload.get("title"),
                "description": payload.get("description"),
                "severity": payload.get("severity"),
                "priority": payload.get("priority"),
                "status": "open",
                "location_on_ship": payload.get("location_on_ship"),
                "equipment_name": payload.get("equipment_name"),
                "raised_by_inspector_id": raised_by_inspector_id,
                "raised_by_crew_id": raised_by_crew_id,
                "assigned_inspector_id": assigned_inspector_id,
                "assigned_crew_id": assigned_crew_id,
                "photos": payload.get("photos"),
                "due_date": payload.get("due_date"),
                "created_at": now,
                "updated_at": now,
                "GSI1PK":"DEFECT",
                "GSI1SK":payload.get("title"),
                "GSI2PK":payload.get("vessel_id"),
                "GSI2SK":payload.get("title"),
                "GSI3PK":gsi3pk,
                "GSI3SK":payload.get("title"),
                
            }
            
            # Remove None values
            defect_dict = {k: v for k, v in defect_dict.items() if v is not None}

            self._repository.put_item(defect_dict)
            if form_id:
                self._logger.info("Created defect %s for form %s", defect_id, form_id)
            else:
                self._logger.info("Created defect %s without form for vessel %s", defect_id, vessel_id)

            return self._item_to_response(defect_dict)
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to create defect: %s", exc)
            raise ApiError("Failed to create defect", 500, "create_defect_failed") from exc

    def create_defect_for_inspector(self, inspector_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a defect raised by an inspector (mobile / web app).
        """

        return self._create_defect_for_user(
            payload=payload,
            raised_by_inspector_id=inspector_id,
            raised_by_crew_id=None,
        )

    def create_defect_for_crew(self, crew_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a defect raised by a crew member (mobile app).
        """

        return self._create_defect_for_user(
            payload=payload,
            raised_by_inspector_id=None,
            raised_by_crew_id=crew_id,
        )

    # ---------------------------------------------------------------------
    # Listing for inspector / crew
    # ---------------------------------------------------------------------

    def _list_defects_for_user(
        self,
        *,
        raised_field: str,
        user_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Shared helper to list defects raised by a specific inspector/crew with pagination.
        """

        try:
            page = payload.get("page", 1)
            limit = payload.get("limit", 20)
            status = payload.get("status")
            vessel_id = payload.get("vessel_id")
            
            fetch_limit = limit + 1
            cursor_dict = None

            for _ in range(1, page):
                _, last_key = self._repository.list_by_raised_user(
                    raised_field=raised_field,
                    user_id=user_id,
                    status=status,
                    vessel_id=vessel_id,
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

            items, _ = self._repository.list_by_raised_user(
                raised_field=raised_field,
                user_id=user_id,
                status=status,
                vessel_id=vessel_id,
                limit=fetch_limit,
                cursor=cursor_dict,
            )

            has_next = len(items) > limit
            items = items[: limit] if has_next else items

            defects = [
                self._item_to_response(item) for item in items
            ]

            return {
                "items": defects,
                "page": page,
                "limit": limit,
                "has_next": has_next,
            }
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to list defects for user %s: %s", user_id, exc)
            raise ApiError("Failed to list defects", 500, "list_defects_failed") from exc

    def list_defects_for_inspector(self, inspector_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        List defects raised by the authenticated inspector.
        """

        return self._list_defects_for_user(
            raised_field="raised_by_inspector_id",
            user_id=inspector_id,
            payload=payload,
        )

    def list_defects_for_crew(self, crew_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        List defects raised by the authenticated crew member.
        """

        return self._list_defects_for_user(
            raised_field="raised_by_crew_id",
            user_id=crew_id,
            payload=payload,
        )

    # ---------------------------------------------------------------------
    # Analysis for inspector / crew
    # ---------------------------------------------------------------------

    def _add_analysis_for_user(
        self,
        *,
        actor_type: str,
        actor_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Add or update analysis information for a defect on behalf of an inspector or crew member.
        """

        try:
            defect_id = payload.get("defect_id")
            root_cause = payload.get("root_cause")
            impact_assessment = payload.get("impact_assessment")
            recurrence_probability = payload.get("recurrence_probability")
            notes = payload.get("notes")
            photos = payload.get("photos")
            
            if not defect_id:
                 raise ApiError("Missing defect_id", 400, "missing_defect_id")

            self._logger.info(
                "Adding defect analysis for defect_id=%s by %s=%s",
                defect_id,
                actor_type,
                actor_id,
            )

            existing = self._repository.get_item(defect_id)
            if not existing:
                raise ApiError("Defect not found", 404, "defect_not_found")

            # Merge new photos with existing analysis photos, if any.
            existing_photos = existing.get("analysis_photos") or []
            new_photos = photos or []
            merged_photos = list(existing_photos) + [p for p in new_photos if p not in existing_photos]

            now = datetime.utcnow().isoformat()

            update_attributes: Dict[str, Any] = {
                "analysis_root_cause": root_cause,
                "analysis_impact_assessment": impact_assessment,
                "analysis_recurrence_probability": recurrence_probability,
                "analysis_notes": notes,
                "analysis_photos": merged_photos or None,
                "analysis_updated_at": now,
            }
            
            # Remove None values
            update_attributes = {k: v for k, v in update_attributes.items() if v is not None}

            if not existing.get("analysis_created_at"):
                update_attributes["analysis_created_at"] = now

            if actor_type == "inspector":
                update_attributes["analysis_by_inspector_id"] = actor_id
            elif actor_type == "crew":
                update_attributes["analysis_by_crew_id"] = actor_id

            # Add activity log entry
            activity_label = f"Defect analysis updated by {actor_type}"
            activities = self._add_activity(existing.get("task_activities"), activity_label, actor_id)
            update_attributes["task_activities"] = activities

            updated_item = self._repository.update_item(defect_id, update_attributes)
            return self._item_to_response(updated_item)
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to update defect analysis: %s", exc)
            raise ApiError("Failed to update defect analysis", 500, "update_defect_analysis_failed") from exc

    def add_defect_analysis_for_inspector(self, inspector_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add or update defect analysis submitted by an inspector.
        """

        return self._add_analysis_for_user(
            actor_type="inspector",
            actor_id=inspector_id,
            payload=payload,
        )

    def add_defect_analysis_for_crew(self, crew_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add or update defect analysis submitted by a crew member.
        """

        return self._add_analysis_for_user(
            actor_type="crew",
            actor_id=crew_id,
            payload=payload,
        )

    def list_defects(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        List defects with pagination and optional filtering.
        """

        try:
            page = payload.get("page", 1)
            limit = payload.get("limit", 20)
            status = payload.get("status")
            vessel_id = payload.get("vessel_id")
            
            fetch_limit = limit + 1
            cursor_dict = None

            # For page > 1, walk through previous pages
            for _ in range(1, page):
                _, last_key = self._repository.list_items(
                    status=status,
                    vessel_id=vessel_id,
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

            items, last_evaluated_key = self._repository.list_items(
                status=status,
                vessel_id=vessel_id,
                limit=fetch_limit,
                cursor=cursor_dict,
            )

            has_next = len(items) > limit
            items = items[: limit] if has_next else items

            defects = [
                self._item_to_response(item) for item in items
            ]

            return {
                "items": defects,
                "page": page,
                "limit": limit,
                "has_next": has_next,
            }
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to list defects: %s", exc)
            raise ApiError("Failed to list defects", 500, "list_defects_failed") from exc

    def get_defect(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve a single defect by ID.
        """

        try:
            defect_id = payload.get("defect_id")
            if not defect_id:
                 raise ApiError("Missing defect_id", 400, "missing_defect_id")

            self._logger.info("Fetching defect: %s", defect_id)
            item = self._repository.get_item(defect_id)
            if not item:
                raise ApiError("Defect not found", 404, "defect_not_found")
            return self._item_to_response(item)
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to fetch defect: %s", exc)
            raise ApiError("Failed to fetch defect", 500, "get_defect_failed") from exc

    def approve_defect(self, admin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Approve a defect resolution.
        Changes status to 'closed' and records approval.
        """

        try:
            defect_id = payload.get("defect_id")
            comment = payload.get("comment")
            
            if not defect_id:
                 raise ApiError("Missing defect_id", 400, "missing_defect_id")
            
            self._logger.info("Approving defect %s by admin %s", defect_id, admin_id)
            existing = self._repository.get_item(defect_id)
            if not existing:
                raise ApiError("Defect not found", 404, "defect_not_found")

            current_status = existing.get("status", "open")
            if current_status == "closed":
                raise ApiError(
                    "Defect is already closed",
                    400,
                    "defect_already_closed",
                )

            # Add admin comment if provided
            admin_comments = existing.get("admin_comments", [])
            if comment:
                admin_comments = self._add_admin_comment(admin_comments, comment)

            # Add activity log
            activities = self._add_activity(
                existing.get("task_activities"),
                f"Defect approved by admin",
                admin_id,
            )

            # Update defect
            update_attributes = {
                "status": "approved",
                "approved_by_admin_id": admin_id,
                "approved_at": datetime.utcnow().isoformat(),
                "admin_comments": admin_comments,
                "task_activities": activities,
            }

            updated_item = self._repository.update_item(defect_id, update_attributes)
            return self._item_to_response(updated_item)
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to approve defect: %s", exc)
            raise ApiError("Failed to approve defect", 500, "approve_defect_failed") from exc

    def add_comment(self, admin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add an admin comment to a defect.
        """

        try:
            defect_id = payload.get("defect_id")
            comment = payload.get("comment")
            
            if not defect_id or not comment:
                 raise ApiError("Missing defect_id or comment", 400, "missing_fields")

            self._logger.info("Adding comment to defect %s by admin %s", defect_id, admin_id)
            existing = self._repository.get_item(defect_id)
            if not existing:
                raise ApiError("Defect not found", 404, "defect_not_found")

            # Add admin comment
            admin_comments = existing.get("admin_comments", [])
            admin_comments = self._add_admin_comment(admin_comments, comment)

            # Add activity log
            comment_preview = comment[:50] + "..." if len(comment) > 50 else comment
            activities = self._add_activity(
                existing.get("task_activities"),
                f"Admin comment added: {comment_preview}",
                admin_id,
            )

            # Update defect
            update_attributes = {
                "admin_comments": admin_comments,
                "task_activities": activities,
            }

            updated_item = self._repository.update_item(defect_id, update_attributes)
            return self._item_to_response(updated_item)
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to add comment to defect: %s", exc)
            raise ApiError("Failed to add comment to defect", 500, "add_comment_failed") from exc

    def close_defect(self, admin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Close a defect.
        Changes status to 'closed' without requiring resolution.
        """

        try:
            defect_id = payload.get("defect_id")
            comment = payload.get("comment")

            if not defect_id:
                 raise ApiError("Missing defect_id", 400, "missing_defect_id")
            
            self._logger.info("Closing defect %s by admin %s", defect_id, admin_id)
            existing = self._repository.get_item(defect_id)
            if not existing:
                raise ApiError("Defect not found", 404, "defect_not_found")

            current_status = existing.get("status", "open")
            if current_status == "closed":
                raise ApiError("Defect is already closed", 400, "defect_already_closed")

            # Add admin comment if provided
            admin_comments = existing.get("admin_comments", [])
            if comment:
                admin_comments = self._add_admin_comment(admin_comments, comment)

            # Add activity log
            activities = self._add_activity(
                existing.get("task_activities"),
                f"Defect closed by admin",
                admin_id,
            )

            # Update defect
            update_attributes = {
                "status": "closed",
                "closed_by_admin_id": admin_id,
                "closed_at": datetime.utcnow().isoformat(),
                "admin_comments": admin_comments,
                "task_activities": activities,
            }

            updated_item = self._repository.update_item(defect_id, update_attributes)
            return self._item_to_response(updated_item)
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to close defect: %s", exc)
            raise ApiError("Failed to close defect", 500, "close_defect_failed") from exc

    def update_defect(self, admin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update defect fields (severity, priority, status, assignments, due_date, description).
        """

        try:
            defect_id = payload.get("defect_id")
            if not defect_id:
                 raise ApiError("Missing defect_id", 400, "missing_defect_id")
            
            self._logger.info("Updating defect %s by admin %s", defect_id, admin_id)
            existing = self._repository.get_item(defect_id)
            if not existing:
                raise ApiError("Defect not found", 404, "defect_not_found")

            # Build update attributes from provided fields
            update_attributes: Dict[str, Any] = {}
            
            severity = payload.get("severity")
            priority = payload.get("priority")
            status = payload.get("status")
            assigned_inspector_id = payload.get("assigned_inspector_id")
            assigned_crew_id = payload.get("assigned_crew_id")
            due_date = payload.get("due_date")
            description = payload.get("description")

            if severity is not None:
                update_attributes["severity"] = severity
            if priority is not None:
                update_attributes["priority"] = priority
            if status is not None:
                update_attributes["status"] = status
            if assigned_inspector_id is not None:
                update_attributes["assigned_inspector_id"] = assigned_inspector_id
            if assigned_crew_id is not None:
                update_attributes["assigned_crew_id"] = assigned_crew_id
            if due_date is not None:
                update_attributes["due_date"] = due_date
            if description is not None:
                update_attributes["description"] = description

            if not update_attributes:
                raise ApiError("At least one field must be provided for update", 400, "no_fields_provided")

            # Add activity log for status changes
            if status and status != existing.get("status"):
                activities = self._add_activity(
                    existing.get("task_activities"),
                    f"Defect status changed to {status}",
                    admin_id,
                )
                update_attributes["task_activities"] = activities

            # Update defect
            updated_item = self._repository.update_item(defect_id, update_attributes)
            return self._item_to_response(updated_item)
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to update defect: %s", exc)
            raise ApiError("Failed to update defect", 500, "update_defect_failed") from exc
