"""
Service layer for dashboard operations.
"""
from typing import Dict, List, Optional, Any

from datetime import datetime, timedelta, timezone

from repository.admin_repository import AdminRepository
from repository.crew_repository import CrewRepository
from repository.defect_repository import DefectRepository
from repository.inspection_assignment_repository import InspectionAssignmentRepository
from repository.inspection_form_repository import InspectionFormRepository
from repository.inspector_repository import InspectorRepository
from repository.vessel_repository import VesselRepository
from utility.errors import ApiError
from utility.logger import get_logger


class DashboardService:
    """
    Business logic for dashboard data aggregation.
    """

    def __init__(self) -> None:
        """
        Initialize the service with repository dependencies.
        """

        self._logger = get_logger(self.__class__.__name__)
        self._vessel_repo = VesselRepository()
        self._defect_repo = DefectRepository()
        self._form_repo = InspectionFormRepository()
        self._inspector_repo = InspectorRepository()
        self._crew_repo = CrewRepository()
        self._admin_repo = AdminRepository()
        self._assignment_repo = InspectionAssignmentRepository()

    def get_dashboard_data(self, admin_id: str) -> Dict[str, Any]:
        """
        Aggregate dashboard data including summary cards, recent activities, defect severity, and vessel summaries.
        """

        try:
            self._logger.info("Fetching dashboard data for admin: %s", admin_id)

            # Get all vessels (scanned) - filter by admin if needed (for now get all)
            all_vessels, _ = self._vessel_repo.list_items(limit=1000)
            # Filter by admin_id if needed (for multi-admin scenarios)
            admin_vessels = [v for v in all_vessels if v.get("admin_id") == admin_id]
            total_vessels = len(admin_vessels) if admin_vessels else len(all_vessels)

            # Get all defects (scanned)
            all_defects, _ = self._defect_repo.list_items(limit=1000)
            open_defects = [d for d in all_defects if d.get("status", "open") == "open"]
            open_defects_count = len(open_defects)

            # Get all forms (scanned) - completed audits
            all_forms, _ = self._form_repo.list_items(limit=1000)
            # Filter forms by admin_id if needed
            admin_forms = [f for f in all_forms if f.get("created_by_admin_id") == admin_id]
            completed_audits = [f for f in (admin_forms if admin_forms else all_forms) if f.get("status", "pending") == "completed"]
            completed_audits_count = len(completed_audits)

            # Calculate defect severity breakdown
            critical = 0
            major = 0
            medium = 0
            minor = 0
            
            for defect in all_defects:
                severity = defect.get("severity", "minor").lower()
                if severity == "critical":
                    critical += 1
                elif severity == "major":
                    major += 1
                elif severity == "medium":
                    medium += 1
                else:
                    minor += 1
            
            severity_breakdown = {
                "critical": critical,
                "major": major,
                "medium": medium,
                "minor": minor
            }

            # Build vessel summaries with defect and audit counts
            vessel_summaries: List[Dict[str, Any]] = []
            vessel_id_to_name = {v.get("vessel_id"): v.get("name") for v in all_vessels}

            # Count defects per vessel
            defects_by_vessel: Dict[str, int] = {}
            for defect in all_defects:
                vessel_id = defect.get("vessel_id")
                if vessel_id and vessel_id != "unassigned":
                    defects_by_vessel[vessel_id] = defects_by_vessel.get(vessel_id, 0) + 1

            # Count completed audits (forms) per vessel
            audits_by_vessel: Dict[str, int] = {}
            for form in completed_audits:
                vessel_id = form.get("vessel_id")
                if vessel_id and vessel_id != "unassigned":
                    audits_by_vessel[vessel_id] = audits_by_vessel.get(vessel_id, 0) + 1

            # Build vessel summaries (use admin_vessels if filtered, otherwise all)
            vessels_for_summary = admin_vessels if admin_vessels else all_vessels
            for vessel in vessels_for_summary[:10]:  # Limit to top 10 vessels for dashboard
                vessel_id = vessel.get("vessel_id")
                vessel_summaries.append({
                        "vessel_id": vessel_id,
                        "vessel_name": vessel.get("name"),
                        "defects_count": defects_by_vessel.get(vessel_id, 0),
                        "audits_count": audits_by_vessel.get(vessel_id, 0),
                        "last_updated": vessel.get("updated_at"),
                })

            # Build recent activities from defects and forms
            recent_activities: List[Dict[str, Any]] = []
            
            # Helper to get user name
            def get_user_name(user_id: Optional[str], user_type: Optional[str]) -> Optional[str]:
                """Get user name from inspector or crew ID."""
                if not user_id:
                    return None
                try:
                    if user_type == "inspector" or not user_type:
                        inspector = self._inspector_repo.get_item(user_id)
                        if inspector:
                            first_name = inspector.get("first_name", "")
                            last_name = inspector.get("last_name", "")
                            return f"{first_name} {last_name}".strip() if first_name or last_name else None
                    if user_type == "crew":
                        crew = self._crew_repo.get_item(user_id)
                        if crew:
                            first_name = crew.get("first_name", "")
                            last_name = crew.get("last_name", "")
                            return f"{first_name} {last_name}".strip() if first_name or last_name else None
                except Exception:
                    return None
                return None
            
            # Get recent defect activities
            for defect in sorted(all_defects, key=lambda x: x.get("updated_at", ""), reverse=True)[:10]:
                vessel_id = defect.get("vessel_id")
                vessel_name = vessel_id_to_name.get(vessel_id) if vessel_id and vessel_id != "unassigned" else None
                
                # Create activity from defect creation/updates
                status = defect.get("status", "open")
                title = defect.get("title", "Defect")
                raised_by = defect.get("raised_by_inspector_id") or defect.get("raised_by_crew_id")
                raised_by_type = "inspector" if defect.get("raised_by_inspector_id") else "crew" if defect.get("raised_by_crew_id") else None
                user_name = get_user_name(raised_by, raised_by_type)
                
                if status == "open":
                    if vessel_name:
                        activity_text = f"New defect reported - {title} - {vessel_name}"
                    else:
                        activity_text = f"New defect reported - {title}"
                elif status == "resolved":
                    activity_text = f"Defect resolved - pending approval"
                else:
                    if vessel_name:
                        activity_text = f"Defect {status} - {title} - {vessel_name}"
                    else:
                        activity_text = f"Defect {status} - {title}"
                
                recent_activities.append({
                        "action": activity_text,
                        "timestamp": defect.get("updated_at") or defect.get("created_at", ""),
                        "vessel_name": vessel_name,
                        "user_name": user_name,
                })

            # Get recent form submissions - try to find assignments to get submitter info
            for form in sorted(completed_audits, key=lambda x: x.get("updated_at", ""), reverse=True)[:5]:
                vessel_id = form.get("vessel_id")
                vessel_name = vessel_id_to_name.get(vessel_id) if vessel_id and vessel_id != "unassigned" else None
                form_title = form.get("title", "Form")
                form_id = form.get("form_id")
                
                # Try to find assignment for this form to get inspector name
                
                submitted_by_name = None
                try:
                    assignments, _ = self._assignment_repo.list_by_form(form_id=form_id, limit=1)
                    if assignments:
                        assignment = assignments[0]
                        assignee_id = assignment.get("assignee_id")
                        assignee_type = assignment.get("assignee_type", "inspector")
                        submitted_by_name = get_user_name(assignee_id, assignee_type)
                except Exception:
                    pass  # Ignore errors when fetching assignment
                
                # Build activity text
                if submitted_by_name and vessel_name:
                    activity_text = f"Form submitted by {submitted_by_name} - {vessel_name}"
                elif submitted_by_name:
                    activity_text = f"Form submitted by {submitted_by_name} - {form_title}"
                elif vessel_name:
                    activity_text = f"Form submitted - {form_title} - {vessel_name}"
                else:
                    activity_text = f"Form submitted - {form_title}"
                
                recent_activities.append({
                        "action": activity_text,
                        "timestamp": form.get("updated_at") or form.get("created_at", ""),
                        "vessel_name": vessel_name,
                        "user_name": submitted_by_name,
                })

            # Sort activities by timestamp and limit to 10 most recent
            recent_activities.sort(key=lambda x: x["timestamp"] or "", reverse=True)
            recent_activities = recent_activities[:10]

            # Build summary cards (percentage changes are placeholders - can be calculated with historical data)
            summary_cards = [
                {
                    "label": "Total Vessels",
                    "value": total_vessels,
                    "change_percentage": 0.0,  # TODO: Calculate from historical data
                    "trend": "up",
                },
                {
                    "label": "Open defects",
                    "value": open_defects_count,
                    "change_percentage": 0.0,  # TODO: Calculate from historical data
                    "trend": "down",
                },
                {
                    "label": "Completed Audits",
                    "value": completed_audits_count,
                    "change_percentage": 0.0,  # TODO: Calculate from historical data
                    "trend": "up",
                },
            ]

            return {
                "summary_cards": summary_cards,
                "recent_activities": recent_activities,
                "defect_severity": severity_breakdown,
                "vessels": vessel_summaries,
            }
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to fetch dashboard data: %s", exc)
            raise ApiError("Failed to fetch dashboard data", 500, "dashboard_fetch_failed") from exc

    def get_inspector_dashboard(self, inspector_id: str) -> Dict[str, Any]:
        """
        Get dashboard data for an inspector including task counts and assigned defects.
        """

        try:
            self._logger.info("Fetching dashboard data for inspector: %s", inspector_id)

            # Get all assignments for this inspector
            assignments = []
            cursor = None
            while True:
                batch, cursor = self._assignment_repo.list_by_assignee(
                    assignee_id=inspector_id,
                    limit=1000,
                    cursor=cursor,
                )
                assignments.extend(batch)
                if not cursor:
                    break
                if len(assignments) >= 1000:  # Safety limit
                    break

            # Count assignments by status
            task_assigned = len(assignments)
            task_completed = sum(
                1
                for a in assignments
                if a.get("status") in ["completed", "submitted"]
            )
            pending = sum(
                1
                for a in assignments
                if a.get("status") in ["assigned", "in_progress"]
            )

            # Calculate due soon (assignments due within 7 days)
            now = datetime.utcnow()
            seven_days_later = now + timedelta(days=7)
            due_soon = 0
            for assignment in assignments:
                due_date_str = assignment.get("due_date")
                if due_date_str and assignment.get("status") not in [
                    "completed",
                    "submitted",
                ]:
                    try:
                        # Handle different datetime formats
                        if due_date_str.endswith("Z"):
                            due_date_str = due_date_str.replace("Z", "+00:00")
                        elif "+" not in due_date_str and "-" in due_date_str:
                            # Assume UTC if no timezone
                            due_date_str = due_date_str + "+00:00"
                        due_date = datetime.fromisoformat(due_date_str)
                        # Make due_date timezone-aware if it's naive
                        if due_date.tzinfo is None:
                            due_date = due_date.replace(tzinfo=timezone.utc)
                        # Make now timezone-aware for comparison
                        if now.tzinfo is None:
                            now = now.replace(tzinfo=timezone.utc)
                        if now <= due_date <= seven_days_later:
                            due_soon += 1
                    except (ValueError, AttributeError, TypeError) as e:
                        self._logger.warning(
                            "Failed to parse due_date %s: %s", due_date_str, e
                        )
                        continue

            # Get defects assigned to or raised by this inspector
            all_defects = []
            cursor = None
            while True:
                batch, cursor = self._defect_repo.list_items(limit=1000, cursor=cursor)
                all_defects.extend(batch)
                if not cursor:
                    break
                if len(all_defects) >= 1000:  # Safety limit
                    break
            
            # Include defects assigned to inspector OR raised by inspector
            assigned_defects = [
                d
                for d in all_defects
                if (
                    d.get("assigned_inspector_id") == inspector_id
                    or d.get("raised_by_inspector_id") == inspector_id
                )
                and d.get("status") != "closed"
            ]

            # Get admin names for "assigned by" field
            defect_summaries: List[Dict[str, Any]] = []
            # Sort by created_at descending to get most recent first
            sorted_defects = sorted(
                assigned_defects,
                key=lambda x: x.get("created_at", ""),
                reverse=True,
            )[:10]  # Limit to 10 most recent
            
            for defect in sorted_defects:
                # Try to get admin name who assigned (from assignment or form)
                assigned_by_name = None
                
                # If defect was raised by this inspector, show inspector name
                if defect.get("raised_by_inspector_id") == inspector_id:
                    inspector = self._inspector_repo.get_item(inspector_id)
                    if inspector:
                        first_name = inspector.get("first_name", "")
                        last_name = inspector.get("last_name", "")
                        assigned_by_name = (
                            f"{first_name} {last_name}".strip()
                            if first_name or last_name
                            else "You"
                        )
                    else:
                        assigned_by_name = "You"
                else:
                    # Defect was assigned to inspector, get admin who assigned it
                    assignment_id = defect.get("assignment_id")
                    if assignment_id:
                        try:
                            assignment = self._assignment_repo.get_item(assignment_id)
                            if assignment:
                                admin_id = assignment.get("created_by_admin_id")
                                if admin_id:
                                    admin = self._admin_repo.get_item(admin_id)
                                    if admin:
                                        first_name = admin.get("first_name", "")
                                        last_name = admin.get("last_name", "")
                                        assigned_by_name = (
                                            f"{first_name} {last_name}".strip()
                                            if first_name or last_name
                                            else "Admin"
                                        )
                                    else:
                                        assigned_by_name = "Admin"
                        except Exception:
                            pass

                defect_summaries.append({
                        "defect_id": defect.get("defect_id"),
                        "title": defect.get("title", "Untitled Defect"),
                        "location": defect.get("location_on_ship"),
                        "assigned_by": assigned_by_name or "System",
                        "priority": defect.get("priority", "medium"),
                })

            return {
                "task_assigned": task_assigned,
                "task_completed": task_completed,
                "pending": pending,
                "due_soon": due_soon,
                "defects": defect_summaries,
            }
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to fetch inspector dashboard: %s", exc)
            raise ApiError(
                "Failed to fetch inspector dashboard", 500, "inspector_dashboard_failed"
            ) from exc

    def get_crew_dashboard(self, crew_id: str) -> Dict[str, Any]:
        """
        Get dashboard data for a crew member including task counts and assigned defects.
        """

        try:
            self._logger.info("Fetching dashboard data for crew: %s", crew_id)

            # Get all assignments for this crew member
            assignments = []
            cursor = None
            while True:
                batch, cursor = self._assignment_repo.list_by_assignee(
                    assignee_id=crew_id,
                    limit=1000,
                    cursor=cursor,
                )
                assignments.extend(batch)
                if not cursor:
                    break
                if len(assignments) >= 1000:  # Safety limit
                    break

            # Count assignments by status
            task_assigned = len(assignments)
            task_completed = sum(
                1
                for a in assignments
                if a.get("status") in ["completed", "submitted"]
            )
            pending = sum(
                1
                for a in assignments
                if a.get("status") in ["assigned", "in_progress"]
            )

            # Calculate due soon (assignments due within 7 days)
            now = datetime.utcnow()
            seven_days_later = now + timedelta(days=7)
            due_soon = 0
            for assignment in assignments:
                due_date_str = assignment.get("due_date")
                if due_date_str and assignment.get("status") not in [
                    "completed",
                    "submitted",
                ]:
                    try:
                        # Handle different datetime formats
                        if due_date_str.endswith("Z"):
                            due_date_str = due_date_str.replace("Z", "+00:00")
                        elif "+" not in due_date_str and "-" in due_date_str:
                            # Assume UTC if no timezone
                            due_date_str = due_date_str + "+00:00"
                        due_date = datetime.fromisoformat(due_date_str)
                        # Make due_date timezone-aware if it's naive
                        if due_date.tzinfo is None:
                            due_date = due_date.replace(tzinfo=timezone.utc)
                        # Make now timezone-aware for comparison
                        if now.tzinfo is None:
                            now = now.replace(tzinfo=timezone.utc)
                        if now <= due_date <= seven_days_later:
                            due_soon += 1
                    except (ValueError, AttributeError, TypeError) as e:
                        self._logger.warning(
                            "Failed to parse due_date %s: %s", due_date_str, e
                        )
                        continue

            # Get defects assigned to or raised by this crew member
            all_defects = []
            cursor = None
            while True:
                batch, cursor = self._defect_repo.list_items(limit=1000, cursor=cursor)
                all_defects.extend(batch)
                if not cursor:
                    break
                if len(all_defects) >= 1000:  # Safety limit
                    break
            
            # Include defects assigned to crew OR raised by crew
            assigned_defects = [
                d
                for d in all_defects
                if (
                    d.get("assigned_crew_id") == crew_id
                    or d.get("raised_by_crew_id") == crew_id
                )
                and d.get("status") != "closed"
            ]

            # Get admin names for "assigned by" field
            defect_summaries: List[Dict[str, Any]] = []
            # Sort by created_at descending to get most recent first
            sorted_defects = sorted(
                assigned_defects,
                key=lambda x: x.get("created_at", ""),
                reverse=True,
            )[:10]  # Limit to 10 most recent
            
            for defect in sorted_defects:
                # Try to get admin name who assigned (from assignment or form)
                assigned_by_name = None
                
                # If defect was raised by this crew member, show crew name
                if defect.get("raised_by_crew_id") == crew_id:
                    crew = self._crew_repo.get_item(crew_id)
                    if crew:
                        first_name = crew.get("first_name", "")
                        last_name = crew.get("last_name", "")
                        assigned_by_name = (
                            f"{first_name} {last_name}".strip()
                            if first_name or last_name
                            else "You"
                        )
                    else:
                        assigned_by_name = "You"
                else:
                    # Defect was assigned to crew, get admin who assigned it
                    assignment_id = defect.get("assignment_id")
                    if assignment_id:
                        try:
                            assignment = self._assignment_repo.get_item(assignment_id)
                            if assignment:
                                admin_id = assignment.get("created_by_admin_id")
                                if admin_id:
                                    admin = self._admin_repo.get_item(admin_id)
                                    if admin:
                                        first_name = admin.get("first_name", "")
                                        last_name = admin.get("last_name", "")
                                        assigned_by_name = (
                                            f"{first_name} {last_name}".strip()
                                            if first_name or last_name
                                            else "Admin"
                                        )
                                    else:
                                        assigned_by_name = "Admin"
                        except Exception:
                            pass

                defect_summaries.append({
                        "defect_id": defect.get("defect_id"),
                        "title": defect.get("title", "Untitled Defect"),
                        "location": defect.get("location_on_ship"),
                        "assigned_by": assigned_by_name or "System",
                        "priority": defect.get("priority", "medium"),
                })

            return {
                "task_assigned": task_assigned,
                "task_completed": task_completed,
                "pending": pending,
                "due_soon": due_soon,
                "defects": defect_summaries,
            }
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to fetch crew dashboard: %s", exc)
            raise ApiError(
                "Failed to fetch crew dashboard", 500, "crew_dashboard_failed"
            ) from exc
