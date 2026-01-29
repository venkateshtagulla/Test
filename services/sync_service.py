"""
Service layer for sync operations.
"""
from typing import Dict, Any, Optional

from repository.inspection_assignment_repository import InspectionAssignmentRepository
from repository.inspection_form_repository import InspectionFormRepository
from utility.errors import ApiError
from utility.logger import get_logger


class SyncService:
    """
    Business logic for sync status checks.
    """

    def __init__(self) -> None:
        """
        Initialize the service with repository dependencies.
        """

        self._logger = get_logger(self.__class__.__name__)
        self._assignment_repo = InspectionAssignmentRepository()
        self._form_repo = InspectionFormRepository()

    def get_sync_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get sync status for an inspector or crew member.
        Checks all their assignments and forms to determine sync status.
        """

        try:
            self._logger.info("Fetching sync status for user: %s", user_id)

            # Get all assignments for this user
            assignments = []
            cursor = None
            while True:
                batch, cursor = self._assignment_repo.list_by_assignee(
                    assignee_id=user_id,
                    limit=1000,
                    cursor=cursor,
                )
                assignments.extend(batch)
                if not cursor:
                    break
                if len(assignments) >= 1000:  # Safety limit
                    break

            # Count assignments by status
            pending_uploads = 0
            synced_forms = 0
            last_synced_at: Optional[str] = None

            for assignment in assignments:
                status = assignment.get("status", "").lower()
                
                # Check if assignment is synced (completed or submitted)
                if status in ["completed", "submitted"]:
                    synced_forms += 1
                    # Track the most recent sync time
                    updated_at = assignment.get("updated_at")
                    if updated_at:
                        if not last_synced_at or updated_at > last_synced_at:
                            last_synced_at = updated_at
                else:
                    # Assignment is pending (assigned, in_progress, etc.)
                    pending_uploads += 1
                
                # Also check form's last_synced_at if available
                form_id = assignment.get("form_id")
                if form_id:
                    try:
                        form = self._form_repo.get_item(form_id)
                        if form:
                            form_sync_time = form.get("last_synced_at")
                            if form_sync_time:
                                if not last_synced_at or form_sync_time > last_synced_at:
                                    last_synced_at = form_sync_time
                    except Exception:
                        # Ignore errors when fetching form
                        pass

            # Failed syncs would typically be tracked separately, but for now we'll set to 0
            failed_syncs = 0

            return {
                "pending_uploads": pending_uploads,
                "synced_forms": synced_forms,
                "failed_syncs": failed_syncs,
                "last_synced_at": last_synced_at,
                "is_online": True,
            }
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to fetch sync status: %s", exc)
            raise ApiError("Failed to fetch sync status", 500, "sync_status_failed") from exc
