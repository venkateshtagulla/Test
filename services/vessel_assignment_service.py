"""
Service layer for vessel assignment operations.
"""
from datetime import datetime
from uuid import uuid4
from typing import Dict, List, Any

from repository.crew_repository import CrewRepository
from repository.inspector_repository import InspectorRepository
from repository.vessel_assignment_repository import VesselAssignmentRepository
from repository.vessel_repository import VesselRepository
from utility.errors import ApiError
from utility.logger import get_logger


class VesselAssignmentService:
    """
    Business logic for vessel assignment operations.
    """

    def __init__(self) -> None:
        """
        Initialize the service with repository dependencies.
        """

        self._logger = get_logger(self.__class__.__name__)
        self._repository = VesselAssignmentRepository()
        self._vessel_repo = VesselRepository()
        self._inspector_repo = InspectorRepository()
        self._crew_repo = CrewRepository()

    def create_assignment(self, admin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assign a crew member or inspector to a vessel.
        """

        try:
            vessel_id = payload.get("vessel_id")
            user_id = payload.get("user_id")
            user_type = payload.get("user_type")
            
            if not all([vessel_id, user_id, user_type]):
                raise ApiError("Missing required fields", 400, "missing_fields")

            self._logger.info(
                "Creating vessel assignment - vessel_id: %s, user_id: %s, user_type: %s",
                vessel_id,
                user_id,
                user_type,
            )

            # Verify vessel exists
            vessel = self._vessel_repo.get_item(vessel_id)
            if not vessel:
                raise ApiError("Vessel not found", 404, "vessel_not_found")

            # Verify user exists
            if user_type == "inspector":
                user = self._inspector_repo.get_item(user_id)
                if not user:
                    raise ApiError("Inspector not found", 404, "inspector_not_found")
            else:  # crew
                user = self._crew_repo.get_item(user_id)
                if not user:
                    raise ApiError("Crew member not found", 404, "crew_not_found")

            # Check if assignment already exists
            assignments, _ = self._repository.list_by_vessel(
                vessel_id=vessel_id,
                limit=1000,
            )
            for existing in assignments:
                if (
                    existing.get("user_id") == user_id
                    and existing.get("user_type") == user_type
                ):
                    raise ApiError(
                        f"{user_type.capitalize()} already assigned to this vessel",
                        409,
                        "assignment_exists",
                    )

            # Create assignment
            assignment_id = str(uuid4())
            now = datetime.utcnow().isoformat()
            
            assignment = {
                "PK": f"USER_ASSIGNMENT#{assignment_id}",
                "SK": "METADATA",
                "GSI1PK": vessel_id,
                "GSI1SK": now,
                "assignment_id": assignment_id,
                "vessel_id": vessel_id,
                "user_id": user_id,
                "user_type": user_type,
                "created_by_admin_id": admin_id,
                "created_at": now,
                "updated_at": now
            }
            
            self._repository.put_item(assignment)

            # Get user name for response
            user_name = None
            if user_type == "inspector":
                first_name = user.get("first_name", "")
                last_name = user.get("last_name", "")
                user_name = f"{first_name} {last_name}".strip() if first_name or last_name else None
            else:
                first_name = user.get("first_name", "")
                last_name = user.get("last_name", "")
                user_name = f"{first_name} {last_name}".strip() if first_name or last_name else None

            response = {
                "assignment_id": assignment["assignment_id"],
                "vessel_id": assignment["vessel_id"],
                "user_id": assignment["user_id"],
                "user_type": assignment["user_type"],
                "user_name": user_name,
                "user_email": user.get("email"),
                "created_by_admin_id": assignment["created_by_admin_id"],
                "created_at": assignment["created_at"],
                "updated_at": assignment["updated_at"],
            }

            self._logger.info(
                "Created vessel assignment %s for vessel %s",
                assignment["assignment_id"],
                vessel_id,
            )
            return response
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to create vessel assignment: %s", exc)
            raise ApiError(
                "Failed to create vessel assignment", 500, "create_assignment_failed"
            ) from exc

    def get_assignments(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get all assignments for a vessel.
        """

        try:
            vessel_id = payload.get("vessel_id")
            if not vessel_id:
                raise ApiError("vessel_id is required", 400, "missing_vessel_id")

            self._logger.info("Fetching vessel assignments for vessel_id: %s", vessel_id)

            # Verify vessel exists
            vessel = self._vessel_repo.get_item(vessel_id)
            if not vessel:
                raise ApiError("Vessel not found", 404, "vessel_not_found")

            # Get all assignments for this vessel
            assignments = []
            cursor = None
            while True:
                batch, cursor = self._repository.list_by_vessel(
                    vessel_id=vessel_id,
                    limit=1000,
                    cursor=cursor,
                )
                assignments.extend(batch)
                if not cursor:
                    break
                if len(assignments) >= 1000:  # Safety limit
                    break

            # Build response with user details
            assignment_responses: List[Dict[str, Any]] = []
            for assignment in assignments:
                user_id = assignment.get("user_id")
                user_type = assignment.get("user_type")

                user_name = None
                user_email = None

                if user_type == "inspector":
                    try:
                        user = self._inspector_repo.get_item(user_id)
                        if user:
                            first_name = user.get("first_name", "")
                            last_name = user.get("last_name", "")
                            user_name = (
                                f"{first_name} {last_name}".strip()
                                if first_name or last_name
                                else None
                            )
                            user_email = user.get("email")
                    except Exception:
                        pass
                else:  # crew
                    try:
                        user = self._crew_repo.get_item(user_id)
                        if user:
                            first_name = user.get("first_name", "")
                            last_name = user.get("last_name", "")
                            user_name = (
                                f"{first_name} {last_name}".strip()
                                if first_name or last_name
                                else None
                            )
                            user_email = user.get("email")
                    except Exception:
                        pass

                assignment_responses.append({
                    "assignment_id": assignment.get("assignment_id"),
                    "vessel_id": assignment.get("vessel_id"),
                    "user_id": assignment.get("user_id"),
                    "user_type": assignment.get("user_type"),
                    "user_name": user_name,
                    "user_email": user_email,
                    "created_by_admin_id": assignment.get("created_by_admin_id"),
                    "created_at": assignment.get("created_at"),
                    "updated_at": assignment.get("updated_at"),
                })

            response = {
                "vessel_id": vessel_id,
                "assignments": assignment_responses,
            }

            return response
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to get vessel assignments: %s", exc)
            raise ApiError(
                "Failed to get vessel assignments", 500, "get_assignments_failed"
            ) from exc

    def delete_assignment(self, assignment_id: str) -> Dict[str, Any]:
        """
        Delete a vessel assignment by assignment_id.
        """

        try:
            self._logger.info("Deleting vessel assignment %s", assignment_id)

            # Verify assignment exists
            assignment = self._repository.get_item(assignment_id)
            if not assignment:
                raise ApiError("Assignment not found", 404, "assignment_not_found")

            # Delete the assignment
            self._repository.delete_item(assignment_id)

            self._logger.info("Deleted vessel assignment %s", assignment_id)
            return {"assignment_id": assignment_id, "deleted": True}
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to delete vessel assignment: %s", exc)
            raise ApiError(
                "Failed to delete vessel assignment", 500, "delete_assignment_failed"
            ) from exc
