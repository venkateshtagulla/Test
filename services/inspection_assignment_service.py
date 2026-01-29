"""
Service layer for inspection assignments.
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import uuid4

from repository.admin_repository import AdminRepository
from repository.crew_repository import CrewRepository
from repository.inspection_assignment_repository import (
    InspectionAssignmentRepository,
)
from repository.inspector_repository import InspectorRepository
from repository.vessel_repository import VesselRepository
from repository.inspection_form_repository import InspectionFormRepository
from utility.errors import ApiError
from utility.logger import get_logger
from utility.s3_utils import sign_s3_url_if_possible


class InspectionAssignmentService:
    """
    Business logic for creating and retrieving inspection assignments.
    """

    def __init__(self, repository: InspectionAssignmentRepository) -> None:
        """
        Initialize the service with its repository dependency.
        """

        self._repository = repository
        self._logger = get_logger(self.__class__.__name__)
        # Lazy-init related repositories to avoid circular imports in other modules.
        self._vessel_repo = VesselRepository()
        self._inspector_repo = InspectorRepository()
        self._crew_repo = CrewRepository()
        self._admin_repo = AdminRepository()
        self._form_repo = InspectionFormRepository()

    def _build_related_vessel(self, vessel_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Fetch and map minimal vessel information for the given vessel_id.
        """

        if not vessel_id:
            return None
        vessel_item = self._vessel_repo.get_item(vessel_id)
        if not vessel_item:
            return None
        return {
            "vessel_id": vessel_item["vessel_id"],
            "name": vessel_item.get("name"),
            "vessel_type": vessel_item.get("vessel_type"),
            "imo_number": vessel_item.get("imo_number"),
        }

    def _build_related_assignee(
        self,
        assignee_id: Optional[str],
        assignee_type: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch and map minimal information for the assignee (inspector or crew).
        """

        if not assignee_id or not assignee_type:
            return None

        if assignee_type == "inspector":
            item = self._inspector_repo.get_item(assignee_id)
            if not item:
                return None
            return {
                "user_id": item["inspector_id"],
                "name": item.get("name"),
                "email": item.get("email"),
                "user_type": "inspector",
            }

        if assignee_type == "crew":
            item = self._crew_repo.get_item(assignee_id)
            if not item:
                return None
            return {
                "user_id": item["crew_id"],
                "name": item.get("name"),
                "email": item.get("email"),
                "user_type": "crew",
            }

        return None

    def _build_related_admin(self, admin_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Fetch and map minimal admin information for the creator.
        """

        if not admin_id:
            return None
        item = self._admin_repo.get_item(admin_id)
        if not item:
            return None
        return {
            "admin_id": item["admin_id"],
            "name": item.get("name"),
            "email": item.get("email"),
        }

    def _is_form_open(self, form: Dict) -> bool:
        """
        Check if a form is open (available for assignment).
        Only forms with status 'Unassigned' or 'In Progress' are available.
        Forms with status 'Closed' are not available for assignment.
        """
        status = form.get("status", "Unassigned")
        # Only "Unassigned" and "In Progress" forms are available for assignment
        return status.lower() in ("unassigned", "in progress")

    def _is_form_assigned(self, form: Dict) -> bool:
        """
        Check if a form is assigned and should appear in inspector/crew assignment lists.
        Only forms with status 'In Progress' should appear (not 'Unassigned' or 'Closed').
        """
        status = form.get("status", "Unassigned")
        # Only "In Progress" forms should appear in assignment lists
        # Normalize by stripping whitespace and converting to lowercase
        normalized_status = status.strip().lower() if isinstance(status, str) else str(status).strip().lower()
        return normalized_status == "in progress"

    def _build_related_form(self, form_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch and map form information including questions.
        """

        if not form_id:
            return None
        try:
            item = self._form_repo.get_item(form_id)
            if not item:
                return None
            
            # Ensure questions are properly formatted as list of dicts
            questions = item.get("questions", [])
            form_status = item.get("status", "Unassigned")
            progress_percentage = 0.0
            
            if questions and isinstance(questions, list):
                # Convert questions to proper dict format, handling any DynamoDB types
                questions_list = []
                total_questions = len(questions)
                answered_questions = 0
                
                for q in questions:
                    if isinstance(q, dict):
                        # Convert to regular dict, ensuring all values are JSON serializable
                        q_dict = {}
                        for key, value in q.items():
                            # Handle Decimal types from DynamoDB
                            if isinstance(value, Decimal):
                                # Convert Decimal to int if it's a whole number, else float
                                if value % 1 == 0:
                                    value = int(value)
                                else:
                                    value = float(value)
                            q_dict[str(key)] = value
                        
                        # Re-sign media_url if present (to handle expired S3 URLs)
                        if "media_url" in q_dict and q_dict["media_url"]:
                            media_url = q_dict["media_url"]
                            # Extract S3 key from URL and re-sign it
                            signed_url = sign_s3_url_if_possible(media_url, expires_in_seconds=900)
                            if signed_url:
                                q_dict["media_url"] = signed_url
                        
                        # Check if question has an answer
                        answer_value = q_dict.get("answer")
                        if answer_value:
                            # Check if answer is a non-empty string or valid value
                            answer_str = str(answer_value).strip()
                            if answer_str and answer_str.lower() not in ["", "null", "none"]:
                                answered_questions += 1
                                # Re-sign answer if it's an S3 URL (for image answers)
                                if answer_str.startswith("http") and "s3" in answer_str.lower():
                                    signed_answer_url = sign_s3_url_if_possible(answer_str, expires_in_seconds=900)
                                    if signed_answer_url:
                                        q_dict["answer"] = signed_answer_url
                        
                        questions_list.append(q_dict)
                    else:
                        questions_list.append(q)
                
                questions = questions_list if questions_list else None
                
                # Calculate progress percentage based on actual answers
                if total_questions > 0:
                    progress_percentage = round((answered_questions / total_questions) * 100, 2)
                    
                    # Determine status based on actual answers (always calculate, don't trust DB status)
                    if answered_questions == 0:
                        final_status = "start"  # No answers - show "Start Inspection"
                    elif answered_questions == total_questions:
                        final_status = "completed"  # All answered - show "View Report"
                    else:
                        final_status = "continue"  # Partial answers - show "Continue Inspection"
                else:
                    progress_percentage = 0.0
                    final_status = "start"
            else:
                questions = None
                progress_percentage = 0.0
                final_status = "start"
            
            return {
                "form_id": item["form_id"],
                "title": item.get("title"),
                "status": final_status,
                "progress_percentage": progress_percentage,
                "due_date": item.get("due_date"),
                "vessel_id": item.get("vessel_id"),
                "description": item.get("description"),
                "questions": questions,  # Include questions for assignments
            }
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to build related form for form_id=%s: %s", form_id, exc)
            # Try to return basic form info without questions if item was retrieved
            try:
                item = self._form_repo.get_item(form_id)
                if item:
                    return {
                        "form_id": item.get("form_id", form_id),
                        "title": item.get("title"),
                        "status": "start",  # Default to "start" when we can't calculate
                        "progress_percentage": 0.0,
                        "due_date": item.get("due_date"),
                        "vessel_id": item.get("vessel_id"),
                        "description": item.get("description"),
                        "questions": None,
                    }
            except Exception:  # pylint: disable=broad-exception-caught
                pass
            return None

    def _item_to_response_with_grouped_forms(self, parent_assignment_id: str, parent_item: Dict) -> Dict[str, Any]:
        """
        Convert parent assignment to response with all related forms grouped together.
        Fetches all child assignments and groups their forms.
        """
        # Get all related assignments (parent + children)
        all_assignments = self._repository.list_by_parent_assignment(parent_assignment_id)
        
        # Build forms list from all related assignments
        forms_list: List[Dict[str, Any]] = []
        for assignment in all_assignments:
            form = self._build_related_form(assignment.get("form_id"))
            if form:
                forms_list.append(form)
        
        # Use parent assignment metadata
        related_vessel = self._build_related_vessel(parent_item.get("vessel_id"))
        related_assignee = self._build_related_assignee(
            assignee_id=parent_item.get("assignee_id"),
            assignee_type=parent_item.get("assignee_type"),
        )
        related_admin = self._build_related_admin(parent_item.get("created_by_admin_id"))
        
        # Aggregate inspection status and progress from all forms
        inspection_status: Optional[str] = None
        inspection_progress: Optional[float] = None
        if forms_list:
            # Calculate overall progress as average
            total_progress = sum(f.get("progress_percentage", 0.0) for f in forms_list)
            inspection_progress = round(total_progress / len(forms_list), 2) if forms_list else 0.0
            
            # Status: if all completed, "completed"; if any started, "continue"; else "start"
            statuses = [f.get("status") for f in forms_list if f.get("status")]
            if all(s == "completed" for s in statuses):
                inspection_status = "completed"
            elif any(s in ("continue", "completed") for s in statuses):
                inspection_status = "continue"
            else:
                inspection_status = "start"
        
        # Use parent assignment's vessel_id
        final_vessel_id = parent_item.get("vessel_id")
        if not final_vessel_id and forms_list:
            # Try to get vessel from first form
            first_form = forms_list[0]
            if first_form.get("vessel_id") and first_form.get("vessel_id").lower() != "unassigned":
                final_vessel_id = first_form.get("vessel_id")
        
        return {
            "assignment_id": parent_assignment_id,
            "form_id": parent_item.get("form_id"),  # Primary form_id from parent
            "vessel_id": final_vessel_id,
            "created_by_admin_id": parent_item.get("created_by_admin_id"),
            "assignee_id": parent_item.get("assignee_id"),
            "assignee_type": parent_item.get("assignee_type"),
            "role": parent_item.get("role"),
            "priority": parent_item.get("priority"),
            "due_date": parent_item.get("due_date"),
            "status": parent_item.get("status", "assigned"),
            "inspection_name": parent_item.get("inspection_name"),
            "inspection_status": inspection_status,
            "inspection_progress_percentage": inspection_progress,
            "created_at": parent_item.get("created_at"),
            "updated_at": parent_item.get("updated_at"),
            "vessel": related_vessel,
            "assignee": related_assignee,
            "admin": related_admin,
            "forms": forms_list,
        }

    def _item_to_response(self, item: Dict) -> Dict[str, Any]:
        """
        Convert DynamoDB item to dict response, with expanded relations.
        If the assignment has a parent_assignment_id, groups all related forms.
        """

        # Check if this assignment is a child of another assignment
        parent_assignment_id = item.get("parent_assignment_id")
        if parent_assignment_id:
            # This is a child assignment, return the parent with all grouped forms
            parent_item = self._repository.get_item(parent_assignment_id)
            if parent_item:
                return self._item_to_response_with_grouped_forms(parent_assignment_id, parent_item)
        
        # Check if this assignment has children
        child_assignments = self._repository.list_by_parent_assignment(item["assignment_id"])
        if len(child_assignments) > 1:  # More than just itself
            # This is a parent with children, group all forms
            return self._item_to_response_with_grouped_forms(item["assignment_id"], item)

        # First try to get vessel from assignment's vessel_id
        related_vessel = self._build_related_vessel(item.get("vessel_id"))
        
        related_assignee = self._build_related_assignee(
            assignee_id=item.get("assignee_id"),
            assignee_type=item.get("assignee_type"),
        )
        related_admin = self._build_related_admin(item.get("created_by_admin_id"))
        related_form = self._build_related_form(item.get("form_id"))

        # Build forms list (currently one form per assignment, but structured as list for future expansion)
        forms_list: List[Dict[str, Any]] = []
        if related_form:
            forms_list.append(related_form)

        # If assignment doesn't have vessel but form does, use form's vessel_id
        if not related_vessel and related_form and related_form.get("vessel_id"):
            form_vessel_id = related_form.get("vessel_id")
            # Skip if vessel_id is "unassigned"
            if form_vessel_id and form_vessel_id.lower() != "unassigned":
                related_vessel = self._build_related_vessel(form_vessel_id)

        # Derive assignment-level inspection status and progress from forms
        # For now, use the first form (or aggregate if multiple forms in future)
        inspection_status: Optional[str] = None
        inspection_progress: Optional[float] = None
        if related_form:
            inspection_status = related_form.get("status")
            inspection_progress = related_form.get("progress_percentage")

        # Use form's vessel_id if assignment doesn't have one (for vessel_id field)
        final_vessel_id = item.get("vessel_id")
        if not final_vessel_id and related_form and related_form.get("vessel_id"):
            form_vessel_id = related_form.get("vessel_id")
            if form_vessel_id and form_vessel_id.lower() != "unassigned":
                final_vessel_id = form_vessel_id

        return {
            "assignment_id": item["assignment_id"],
            "form_id": item["form_id"],
            "vessel_id": final_vessel_id,
            "created_by_admin_id": item.get("created_by_admin_id"),
            "assignee_id": item.get("assignee_id"),
            "assignee_type": item.get("assignee_type"),
            "role": item.get("role"),
            "priority": item.get("priority"),
            "due_date": item.get("due_date"),
            "status": item.get("status", "assigned"),
            "inspection_name": item.get("inspection_name"),
            "inspection_status": inspection_status,
            "inspection_progress_percentage": inspection_progress,
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "vessel": related_vessel,
            "assignee": related_assignee,
            "admin": related_admin,
            "forms": forms_list,
        }

    def create_assignment(self, admin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an inspection assignment.
        Validates that the form is open (not completed/closed).
        If assignment_id is provided, adds the form to that existing assignment.
        """

        try:
            form_id = payload.get("form_id")
            assignment_id = payload.get("assignment_id")
            assignee_id = payload.get("assignee_id")
            assignee_type = payload.get("assignee_type")
            vessel_id = payload.get("vessel_id")

            self._logger.info(
                "Creating inspection assignment for admin_id=%s form_id=%s assignment_id=%s",
                admin_id,
                form_id,
                assignment_id,
            )
            
            # Verify form exists and is open
            form = self._form_repo.get_item(form_id)
            if not form:
                raise ApiError("Inspection form not found", 404, "form_not_found")
            
            if not self._is_form_open(form):
                raise ApiError(
                    "Cannot assign closed or completed forms. Only open forms can be assigned.",
                    400,
                    "form_closed",
                )
            
            # Explicitly check for "Closed" status which might not be caught by _is_form_open depending on implementation
            if form.get("status", "").lower() == "closed":
                 raise ApiError(
                    "Cannot create inspection from a closed form.",
                    400,
                    "form_closed"
                )
            
            parent_assignment_id = None
            # If assignment_id is provided, validate it exists and matches assignee/vessel
            if assignment_id:
                existing_assignment = self._repository.get_item(assignment_id)
                if not existing_assignment:
                    raise ApiError("Assignment not found", 404, "assignment_not_found")
                
                # Validate that the existing assignment matches the new assignment's assignee and vessel
                if existing_assignment.get("assignee_id") != assignee_id:
                    raise ApiError(
                        "Assignment assignee does not match. Cannot add form to assignment with different assignee.",
                        400,
                        "assignee_mismatch",
                    )
                if existing_assignment.get("assignee_type") != assignee_type:
                    raise ApiError(
                        "Assignment assignee type does not match. Cannot add form to assignment with different assignee type.",
                        400,
                        "assignee_type_mismatch",
                    )
                if vessel_id and existing_assignment.get("vessel_id") != vessel_id:
                    raise ApiError(
                        "Assignment vessel does not match. Cannot add form to assignment with different vessel.",
                        400,
                        "vessel_mismatch",
                    )
                
                # Use the existing assignment_id as parent
                parent_assignment_id = assignment_id
            
            new_assignment_id = str(uuid4())
            now = datetime.utcnow().isoformat()
            pk=f"INSPECTION#{new_assignment_id}"
            assignment_dict = {
                "PK":pk,
                "SK":"METADATA",
                "assignment_id": new_assignment_id,
                "form_id": form_id,
                "vessel_id": vessel_id,
                "created_by_admin_id": admin_id,
                "assignee_id": assignee_id,
                "assignee_type": assignee_type,
                "role": payload.get("role"),
                "priority": payload.get("priority"),
                "due_date": payload.get("due_date"),
                "inspection_name": payload.get("inspection_name"),
                "parent_assignment_id": parent_assignment_id,
                "created_at": now,
                "updated_at": now,
                "status": "assigned", # Default status
                "GSI1PK":"INSPECTION",
                "GSI1SK":now,
                "GSI2PK":assignee_id,
                "GSI2SK":now,
                "GSI3PK":vessel_id,
                "GSI3SK":now,
                "GSI4PK":form_id,
                "GSI4SK":now,
                "GSI5PK":parent_assignment_id,
                "GSI5SK":now,
            }

            # Exclude None values
            assignment_dict = {k: v for k, v in assignment_dict.items() if v is not None}
            
            self._logger.info("Saving new inspection assignment. Vessel ID: '%s', Form ID: '%s'", assignment_dict.get("vessel_id"), form_id)
            self._repository.put_item(assignment_dict)
            
            # Update form status to "In Progress" when assigned (if not already)
            current_form_status = form.get("status", "Unassigned")
            if current_form_status.lower() == "unassigned":
                self._form_repo.update_item(
                    form_id,
                    {   "GSI3PK":assignee_id,
                        "GSI3SK":now,
                        "status": "In Progress",
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                )
            
            # If this is adding to an existing assignment, return the parent assignment with all forms
            if parent_assignment_id:
                parent_assignment = self._repository.get_item(parent_assignment_id)
                if parent_assignment:
                    return self._item_to_response_with_grouped_forms(parent_assignment_id, parent_assignment)
            
            return self._item_to_response(assignment_dict)
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to create inspection assignment: %s", exc)
            raise ApiError("Failed to create inspection assignment", 500, "create_assignment_failed") from exc

    def get_assignment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve a single inspection assignment.
        """

        try:
            assignment_id = payload.get("assignment_id")
            if not assignment_id:
                 raise ApiError("Missing assignment_id", 400, "missing_assignment_id")

            self._logger.info("Fetching inspection assignment: %s", assignment_id)
            item = self._repository.get_item(assignment_id)
            if not item:
                raise ApiError("Inspection assignment not found", 404, "assignment_not_found")
            return self._item_to_response(item)
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to fetch inspection assignment: %s", exc)
            raise ApiError("Failed to fetch inspection assignment", 500, "get_assignment_failed") from exc

    def list_assignments(self, admin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        List inspection assignments with searching, sorting, and pagination.
        """

        try:
            form_id = payload.get("form_id")
            page = payload.get("page", 1)
            limit = payload.get("limit", 20)
            search = payload.get("search")

            # Fetch all assignments for the admin to allow global sorting and searching
            all_items = []
            cursor = None
            while True:
                if form_id:
                    items, cursor = self._repository.list_by_form(
                        form_id=form_id, limit=1000, cursor=cursor
                    )
                else:
                    items, cursor = self._repository.list_by_admin(
                        admin_id=admin_id, limit=1000, cursor=cursor
                    )
                all_items.extend(items)
                if not cursor:
                    break

            # Group assignments and deduplicate (only show parent assignments, not children)
            seen_parent_ids = set()
            unique_top_items = []
            for item in all_items:
                parent_id = item.get("parent_assignment_id")
                if parent_id:
                    if parent_id not in seen_parent_ids:
                        parent = self._repository.get_item(parent_id)
                        if parent:
                            unique_top_items.append(parent)
                            seen_parent_ids.add(parent_id)
                else:
                    assignment_id = item.get("assignment_id")
                    if assignment_id not in seen_parent_ids:
                        unique_top_items.append(item)
                        seen_parent_ids.add(assignment_id)

            assignments = [
                self._item_to_response(item) for item in unique_top_items
            ]

            # Apply search filter if provided
            if search:
                search_term = search.lower().strip()
                filtered_assignments = []
                for a in assignments:
                    # Search in form title, vessel name, assignee name
                    form_title = ""
                    if a.get("forms") and len(a["forms"]) > 0:
                         form_title = a["forms"][0].get("title", "")
                    
                    vessel_name = ""
                    if a.get("vessel"):
                         vessel_name = a["vessel"].get("name", "")

                    assignee_name = ""
                    if a.get("assignee"):
                         assignee_name = a["assignee"].get("name", "")
                    
                    search_text = (
                        form_title.lower() + 
                        vessel_name.lower() +
                        assignee_name.lower() +
                        str(a.get("assignment_id", "")).lower()
                    )
                    if search_term in search_text:
                        filtered_assignments.append(a)
                assignments = filtered_assignments

            # Sort by created_at descending (newest first)
            assignments.sort(key=lambda x: x.get("created_at") or "", reverse=True)

            # Apply pagination
            total_items = len(assignments)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            
            paged_assignments = assignments[start_idx:end_idx]
            has_next = total_items > end_idx

            return {
                "items": paged_assignments,
                "page": page,
                "limit": limit,
                "has_next": has_next,
            }
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to list inspection assignments: %s", exc)
            raise ApiError("Failed to list inspection assignments", 500, "list_assignments_failed") from exc

    def list_assignments_for_inspector(self, inspector_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        List inspection assignments for a specific inspector with searching, sorting, and pagination.
        Only forms with status 'In Progress' should appear.
        """

        try:
            page = payload.get("page", 1)
            limit = payload.get("limit", 20)
            search = payload.get("search")

            # Fetch all assignments for the inspector
            all_items = []
            cursor = None
            while True:
                items, cursor = self._repository.list_by_assignee(
                    assignee_id=inspector_id, limit=1000, cursor=cursor
                )
                all_items.extend(items)
                if not cursor:
                    break

            # Group assignments and deduplicate
            seen_parent_ids = set()
            unique_top_items = []
            for item in all_items:
                parent_id = item.get("parent_assignment_id")
                if parent_id:
                    if parent_id not in seen_parent_ids:
                        parent = self._repository.get_item(parent_id)
                        if parent:
                            unique_top_items.append(parent)
                            seen_parent_ids.add(parent_id)
                else:
                    assignment_id = item.get("assignment_id")
                    if assignment_id not in seen_parent_ids:
                        unique_top_items.append(item)
                        seen_parent_ids.add(assignment_id)

            # Filter by form status (at least one 'In Progress' form in group)
            open_items = []
            for item in unique_top_items:
                assignment_id = item.get("assignment_id")
                child_assignments = self._repository.list_by_parent_assignment(assignment_id)
                
                has_assigned_form = False
                for assignment in child_assignments:
                    form_id = assignment.get("form_id")
                    if form_id:
                        form = self._form_repo.get_item(form_id)
                        if form and self._is_form_assigned(form):
                            has_assigned_form = True
                            break
                
                if has_assigned_form:
                    open_items.append(item)

            assignments = [
                self._item_to_response(item) for item in open_items
            ]

            # Apply search filter if provided
            if search:
                search_term = search.lower().strip()
                filtered_assignments = []
                for a in assignments:
                    form_title = ""
                    if a.get("forms") and len(a["forms"]) > 0:
                         form_title = a["forms"][0].get("title", "")
                    
                    vessel_name = ""
                    if a.get("vessel"):
                         vessel_name = a["vessel"].get("name", "")

                    search_text = (
                        form_title.lower() + 
                        vessel_name.lower() +
                        str(a.get("assignment_id", "")).lower()
                    )
                    if search_term in search_text:
                        filtered_assignments.append(a)
                assignments = filtered_assignments

            # Sort by created_at descending (newest first)
            assignments.sort(key=lambda x: x.get("created_at") or "", reverse=True)

            # Apply pagination
            total_items = len(assignments)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            
            paged_assignments = assignments[start_idx:end_idx]
            has_next = total_items > end_idx

            return {
                "items": paged_assignments,
                "page": page,
                "limit": limit,
                "has_next": has_next,
            }
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to list inspection assignments for inspector: %s", exc)
            raise ApiError("Failed to list inspection assignments", 500, "list_assignments_failed") from exc

    def list_assignments_for_crew(self, crew_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        List inspection assignments for a specific crew member with page-based pagination.
        """

        try:
            page = payload.get("page", 1)
            limit = payload.get("limit", 20)
            
            fetch_limit = limit + 1
            cursor_dict = None

            for _ in range(1, page):
                _, last_key = self._repository.list_by_assignee(
                    assignee_id=crew_id,
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

            items, _ = self._repository.list_by_assignee(
                assignee_id=crew_id,
                limit=fetch_limit,
                cursor=cursor_dict,
            )

            # Group assignments first, then filter by form status
            # Group assignments and deduplicate (only show parent assignments, not children)
            seen_parent_ids = set()
            grouped_items = []
            for item in items:
                parent_id = item.get("parent_assignment_id")
                if parent_id:
                    # This is a child assignment, skip it (parent will be shown)
                    if parent_id not in seen_parent_ids:
                        # Fetch parent
                        parent = self._repository.get_item(parent_id)
                        if parent:
                            grouped_items.append(parent)
                            seen_parent_ids.add(parent_id)
                else:
                    # This is a parent assignment (or standalone)
                    assignment_id = item.get("assignment_id")
                    if assignment_id not in seen_parent_ids:
                        grouped_items.append(item)
                        seen_parent_ids.add(assignment_id)

            # Filter out assignments where ALL forms are unassigned or closed
            open_items = []
            for item in grouped_items:
                assignment_id = item.get("assignment_id")
                # Check if this assignment has children (grouped)
                child_assignments = self._repository.list_by_parent_assignment(assignment_id)
                if len(child_assignments) > 1:  # Has children (more than just itself)
                    # Check if ANY form in the group is "In Progress"
                    has_assigned_form = False
                    for assignment in child_assignments:
                        form_id = assignment.get("form_id")
                        if not form_id:
                            continue
                        form = self._form_repo.get_item(form_id)
                        if form:
                            if self._is_form_assigned(form):
                                has_assigned_form = True
                                break
                    
                    if has_assigned_form:
                        open_items.append(item)
                else:
                    # Single assignment
                    form_id = item.get("form_id")
                    if form_id:
                        form = self._form_repo.get_item(form_id)
                        if form and self._is_form_assigned(form):
                            open_items.append(item)

            # Convert to response objects
            assignments = [
                self._item_to_response(item) for item in open_items
            ]

            # Apply pagination manually on the filtered/grouped list (since filtering might reduce count)
            # NOTE: this logic mixes DB pagination with in-memory filtering which is tricky. 
            # Ideally we paginate AFTER grouping/filtering but that requires fetching all.
            # Given we fetch paginated from DB, and then filter, the page size might shrink.
            # For simplicity, we stick to the DB returned items subset.
            
            # Since we fetched limit+1, check if we have more
            has_next = len(items) > limit
            paged_items = assignments[:limit] # Take up to limit

            return {
                "items": paged_items,
                "page": page,
                "limit": limit,
                "has_next": has_next,
            }
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to list inspection assignments for crew: %s", exc)
            raise ApiError("Failed to list inspection assignments", 500, "list_assignments_failed") from exc

    def bulk_create_assignments(self, admin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create multiple assignments for a single inspector.
        """

        try:
            inspector_id = payload.get("inspector_id")
            form_ids = payload.get("form_ids")
            vessel_id = payload.get("vessel_id")
            priority = payload.get("priority")
            due_date = payload.get("due_date")
            role = payload.get("role")
            
            if not inspector_id or not form_ids:
                 raise ApiError("Missing inspector_id or form_ids", 400, "missing_fields")

            self._logger.info(
                "Bulk creating assignments for inspector %s, forms: %s",
                inspector_id,
                form_ids,
            )

            inspector = self._inspector_repo.get_item(inspector_id)
            if not inspector:
                raise ApiError("Inspector not found", 404, "inspector_not_found")

            # Check for existing open assignment for this inspector and vessel (if provided)
            # This is a simplification; ideally we check if we should merge into an existing assignment group
            # payload.assignment_id logic is not exposed in bulk create request yet, 
            # assuming new group creation or individual.
            
            # Requirement: "Create one parent assignment, and link all forms to it"
            # Create parent assignment first
            
            parent_assignment_id = str(uuid4())
            now = datetime.utcnow().isoformat()
            
            # 1. Create Parent Assignment (acts as the container)
            # The parent itself is also an assignment record, usually for the first form, or a placeholder?
            # Existing logic: "parent_assignment_id" links siblings.
            # "One of the assignments is the 'parent'?" or "There is a distinct parent?"
            # From list_by_parent_assignment logic: it returns items where assignment_id=parent OR parent_assignment_id=parent
            # So the first assignment created can be the parent.
            
            created_count = 0
            
            # Use the first form to create the "Parent" assignment
            first_form_id = form_ids[0]
            
            # Create payload for create_assignment
            first_payload = {
                "form_id": first_form_id,
                "vessel_id": vessel_id,
                "assignee_id": inspector_id,
                "assignee_type": "inspector",
                "role": role,
                "priority": priority,
                "due_date": due_date,
                "inspection_name": f"Inspection - {datetime.now().strftime('%Y-%m-%d')}", # default name
                "parent_assignment_id": None # This will be the parent
            }
            
            # Use service method to ensure all checks pass
            # But we need to capture IDs.
            # Let's call create_assignment for the first one.
            response = self.create_assignment(admin_id, first_payload)
            parent_id = response.get("assignment_id")
            created_count += 1
            
            # Now create the rest, linking to parent_id
            for form_id in form_ids[1:]:
                next_payload = {
                    "form_id": form_id,
                    "vessel_id": vessel_id,
                    "assignee_id": inspector_id,
                    "assignee_type": "inspector",
                    "role": role,
                    "priority": priority,
                    "due_date": due_date,
                    "assignment_id": parent_id # Link to parent
                }
                self.create_assignment(admin_id, next_payload)
                created_count += 1

            return {"success": True, "count": created_count, "parent_assignment_id": parent_id}
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to bulk create assignments: %s", exc)
            raise ApiError("Failed to bulk create assignments", 500, "bulk_create_failed") from exc

    def create_crew_assignment(self, admin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a single inspection assignment to a crew member.
        Validates that crew has no pending assignments before creating a new one.
        """

        try:
            crew_id = payload.get("crew_id")
            form_id = payload.get("form_id")
            vessel_id = payload.get("vessel_id")
            
            if not crew_id or not form_id:
                 raise ApiError("Missing crew_id or form_id", 400, "missing_fields")

            self._logger.info("Creating assignment for crew %s form %s", crew_id, form_id)

            crew = self._crew_repo.get_item(crew_id)
            if not crew:
                raise ApiError("Crew member not found", 404, "crew_not_found")
            
            # Check if crew already has any incomplete assignment
            # (Simplification: list all assignments and check status)
            # Ideally we have a better query index for this.
            # For now, list keys and check.
            assignments, _ = self._repository.list_by_assignee(crew_id, limit=50) # check recent
            for asm in assignments:
                status = asm.get("status", "assigned").lower()
                if status not in ("completed", "closed", "cancelled"):
                    # Check the FORM status too, effectively
                    # If assignment is just "assigned", it's pending.
                    raise ApiError(
                        "Crew member already has an active assignment. Complete it first.",
                        400,
                        "crew_has_active_assignment"
                    )

            # Create new assignment
            # Crew assignments must have a vessel_id (usually the crew's vessel)
            if not vessel_id:
                # Fallback to crew's assigned vessel if not provided
                # Assuming crew object has it? CrewDBModel usually has 'vessel_id' or we look up?
                # CrewDBModel usually doesn't store vessel_id directly? Actually it does.
                pass # Payload vessel_id is optional but recommended.
            
            payload_dict = {
                "form_id": form_id,
                "vessel_id": vessel_id,
                "assignee_id": crew_id,
                "assignee_type": "crew",
                "role": "crew_lead", # Default role
                "priority": "medium",
                "due_date": payload.get("due_date"),
                "inspection_name": f"Crew Inspection - {datetime.now().strftime('%Y-%m-%d')}",
            }
            
            return self.create_assignment(admin_id, payload_dict)
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to create crew assignment: %s", exc)
            raise ApiError("Failed to create crew assignment", 500, "create_crew_assignment_failed") from exc

    def remove_form_from_assignment(self, admin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove a form from its assignment by form_id.
        Deletes the assignment record and updates form status to "Unassigned".
        """

        try:
            form_id = payload.get("form_id")
            if not form_id:
                 raise ApiError("Missing form_id", 400, "missing_form_id")
            
            self._logger.info("Removing form %s from assignment by admin %s", form_id, admin_id)
            
            # Find the assignment for this form
            items, _ = self._repository.list_by_form(form_id, limit=1)
            if not items:
                raise ApiError("Assignment not found for this form", 404, "assignment_not_found")
            
            assignment = items[0]
            assignment_id = assignment["assignment_id"]
            
            # Check owner
            if assignment.get("created_by_admin_id") != admin_id:
                 raise ApiError("Not authorized to modify this assignment", 403, "forbidden")

            # Delete the assignment
            self._repository.delete_item(assignment_id)
            
            # Update form status back to "Unassigned"
            self._form_repo.update_item(
                form_id,
                {
                    "status": "Unassigned",
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            
            return {"success": True, "message": "Form removed from assignment"}
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to remove form from assignment: %s", exc)
            raise ApiError("Failed to remove form from assignment", 500, "remove_assignment_failed") from exc
