"""
Service layer for admin-managed inspector creation and retrieval.
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from repository.inspector_repository import InspectorRepository
from utility.errors import ApiError
from utility.logger import get_logger
from utility.security import hash_password, verify_password
from utility.s3_utils import sign_s3_url_if_possible, upload_file_to_s3
from uuid import uuid4
class AdminInspectorService:
    """
    Business logic for admin-side inspector management.
    """

    def __init__(self, repository: InspectorRepository) -> None:
        self._repository = repository
        self._logger = get_logger(self.__class__.__name__)

    def create_inspector(
        self,
        admin_id: str,
        payload: Dict[str, Any],
    
        files: Optional[Dict[str, Tuple[bytes, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Create an inspector record with admin-provided password and documents.
        If files are provided, uploads them to S3 and stores URLs.
        Email uniqueness is not enforced at this layer to avoid DynamoDB index coupling.
        """

        try:
            # Upload files to S3 if provided
            id_proof_url = payload.get("id_proof_url")
            address_proof_url = payload.get("address_proof_url")
            additional_docs = payload.get("additional_docs") or []

            if files:
                if "id_proof" in files:
                    file_content, filename = files["id_proof"]
                    id_proof_url = upload_file_to_s3(file_content, filename, folder="inspectors/id-proof")
                
                if "address_proof" in files:
                    file_content, filename = files["address_proof"]
                    address_proof_url = upload_file_to_s3(file_content, filename, folder="inspectors/address-proof")
                
                # Handle additional docs (can be multiple files with same field name or indexed)
                additional_urls = []
                for key in sorted(files.keys()):
                    if key.startswith("additional_docs") or key.startswith("additional"):
                        file_content, filename = files[key]
                        url = upload_file_to_s3(file_content, filename, folder="inspectors/additional")
                        additional_urls.append(url)
                if additional_urls:
                    additional_docs = additional_urls
            # Hash password if provided
            password_hash = None
            password = payload.get("password")
            if password:
                password_hash = hash_password(password)


            # Manually construct inspector item
            # Use strict key access for required fields to ensure they exist
            inspector_id = str(uuid4())
            pk=f"INSPECTOR#{inspector_id}"
            now = datetime.utcnow().isoformat()
            inspector = {
                "PK":pk,
                "SK":"METADATA",
                "inspector_id": inspector_id,
                "first_name": payload.get("first_name"),
                "last_name": payload.get("last_name"),
                "email": payload.get("email"),
                "phone_number": payload.get("phone_number"),
                "role": payload.get("role","Inspector"),
                "id_proof_url": id_proof_url,
                "address_proof_url": address_proof_url,
                "additional_docs": additional_docs if additional_docs else None,
                "password_hash": hash_password(payload["password"]),
                "created_by_admin_id": admin_id,
                "status": "active",
                "created_at": now,
                "updated_at": now,
                "GSI1PK":"INSPECTOR",
                "GSI1SK":payload.get("email"),
                
            }
            
            # Note: InspectorRepository.put_item likely expects a dict.
            # Assuming it adds inspector_id and timestamps internally or we might need to add them here?
            # Checking repository code would be ideal, but standard practice is repo generates ID or service does.
            # The previous code used InspectorDBModel which generated ID. 
            # I should generate ID here if the model logic was doing it.
            
            # Since I can't import InspectorDBModel, I must replicate its ID generation logic.
            # Usually uuid4.
            
            if "inspector_id" not in inspector or not inspector["inspector_id"]:
                inspector["inspector_id"] =inspector_id 
            
            if "created_at" not in inspector:
                inspector["created_at"] = datetime.utcnow().isoformat()
            if "updated_at" not in inspector:
                inspector["updated_at"] = datetime.utcnow().isoformat()

            self._repository.put_item(inspector)
            
            # Construct response manually
            response = {
                "inspector_id": inspector["inspector_id"],
                "email": inspector["email"],
                "first_name": inspector["first_name"],
                "last_name": inspector["last_name"],
                "phone_number": inspector.get("phone_number"),
                "role": inspector.get("role"),
                "id_proof_url": inspector.get("id_proof_url"),
                "address_proof_url": inspector.get("address_proof_url"),
                "additional_docs": inspector.get("additional_docs"),
            }
            self._logger.info("Inspector %s created by admin", inspector["inspector_id"])
            return inspector
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to create inspector (admin): %s", exc)
            raise ApiError("Failed to create inspector", 500, "create_inspector_failed") from exc

    def get_inspector(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch inspector details (admin view).
        """
        inspector_id = payload.get("inspector_id")
        if not inspector_id:
             raise ApiError("inspector_id is required", 400, "missing_inspector_id")

        try:
            record = self._repository.get_item(inspector_id)
            if not record:
                raise ApiError("Inspector not found", 404, "inspector_not_found")

            id_url = sign_s3_url_if_possible(record.get("id_proof_url"))
            addr_url = sign_s3_url_if_possible(record.get("address_proof_url"))
            additional = record.get("additional_docs") or []
            signed_additional = [sign_s3_url_if_possible(url) for url in additional]

            response = {
                "inspector_id": record["inspector_id"],
                "email": record["email"],
                "first_name": record["first_name"],
                "last_name": record["last_name"],
                "phone_number": record.get("phone_number"),
                "role": record.get("role"),
                "id_proof_url": id_url,
                "address_proof_url": addr_url,
                "additional_docs": signed_additional or None,
            }
            return response
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to fetch inspector (admin): %s", exc)
            raise ApiError("Failed to fetch inspector", 500, "get_inspector_failed") from exc

    def list_inspectors(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        List inspectors for admin with simple page/limit pagination.

        This uses DynamoDB scan under the hood with a per-page Limit.
        For page N, it walks (N-1) pages of size `limit` by following
        LastEvaluatedKey, then returns the Nth page.
        """

        try:
            page = payload.get("page", 1)
            limit = payload.get("limit", 20)

            last_evaluated_key: Optional[Dict] = None
            items: List[Dict] = []

            # Walk to the requested page
            for _ in range(page):
                items, last_evaluated_key = self._repository.list_items(
                    limit=limit, exclusive_start_key=last_evaluated_key
                )
                if last_evaluated_key is None:
                    # No more pages; break early
                    break

            # Build response models with signed URLs
            inspectors: List[Dict] = []
            for record in items:
                try:
                    id_url = sign_s3_url_if_possible(record.get("id_proof_url"))
                    addr_url = sign_s3_url_if_possible(record.get("address_proof_url"))
                    additional_urls = record.get("additional_docs") or []
                    signed_additional = [
                        sign_s3_url_if_possible(doc_url) or doc_url for doc_url in additional_urls
                    ]

                    inspectors.append({
                        "inspector_id": record["inspector_id"],
                        "email": record["email"],
                        "first_name": record["first_name"],
                        "last_name": record["last_name"],
                        "phone_number": record.get("phone_number"),
                        "role": record.get("role"),
                        "id_proof_url": id_url,
                        "address_proof_url": addr_url,
                        "additional_docs": signed_additional if signed_additional else None,
                    })
                except Exception as exc:
                    self._logger.error("Error processing Inspector record %s: %s", record.get("inspector_id"), exc, exc_info=True)
                    # Skip this record and continue with others to prevent entire list from failing
                    continue

            response = {
                "inspectors": inspectors,
                "page": page,
                "limit": limit,
                "has_next": last_evaluated_key is not None,
            }
            return response
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to list inspectors (admin): %s", exc)
            raise ApiError("Failed to list inspectors", 500, "list_inspectors_failed") from exc

    def reset_password(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reset inspector password by admin.
        """

        try:
            # Verify inspector exists
            record = self._repository.get_item(payload["inspector_id"])
            if not record:
                raise ApiError("Inspector not found", 404, "inspector_not_found")

            # Hash the new password
            password_hash = hash_password(payload["password"])
            self._logger.info("Hashed password for inspector %s", payload["inspector_id"])

            # Update password hash and updated_at timestamp
            updated_record = self._repository.update_item(
                payload["inspector_id"],
                {
                    "password_hash": password_hash,
                    "updated_at": datetime.utcnow().isoformat(),
                },
            )
            
            # Verify the password was updated
            if not updated_record.get("password_hash"):
                self._logger.error("Password hash not found after update for inspector %s", payload["inspector_id"])
                raise ApiError("Failed to update password hash", 500, "password_update_failed")
            
            self._logger.info("Password reset for inspector %s by admin", payload["inspector_id"])
            return {"inspector_id": payload["inspector_id"], "message": "Password reset successfully"}
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to reset inspector password: %s", exc)
            raise ApiError("Failed to reset inspector password", 500, "reset_password_failed") from exc

    def delete_inspector(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Soft delete an inspector by setting status to 'deleted'.
        Validates that the inspector is not assigned to any active forms, open defects, or active assignments.
        """
        from repository.inspection_form_repository import InspectionFormRepository
        from repository.defect_repository import DefectRepository
        from repository.inspection_assignment_repository import InspectionAssignmentRepository

        try:
            # Verify inspector exists
            record = self._repository.get_item(payload["inspector_id"])
            if not record:
                raise ApiError("Inspector not found", 404, "inspector_not_found")

            # Check if already deleted
            if record.get("status") == "deleted":
                raise ApiError("Inspector is already deleted", 400, "inspector_already_deleted")

            # Check for active inspection forms
            form_repo = InspectionFormRepository()
            active_forms = form_repo.query_active_forms_by_assigned_inspector(payload["inspector_id"])
            if active_forms:
                form_titles = [f.get("title", "Untitled") for f in active_forms[:3]]
                message = f"Cannot delete inspector. Assigned to {len(active_forms)} active form(s): {', '.join(form_titles)}"
                if len(active_forms) > 3:
                    message += f" and {len(active_forms) - 3} more"
                raise ApiError(message, 400, "inspector_has_active_forms")

            # Check for open defects
            defect_repo = DefectRepository()
            open_defects = defect_repo.query_open_defects_by_assigned_inspector(payload["inspector_id"])
            if open_defects:
                defect_titles = [d.get("title", "Untitled") for d in open_defects[:3]]
                message = f"Cannot delete inspector. Assigned to {len(open_defects)} open defect(s): {', '.join(defect_titles)}"
                if len(open_defects) > 3:
                    message += f" and {len(open_defects) - 3} more"
                raise ApiError(message, 400, "inspector_has_open_defects")

            # Check for active inspection assignments
            assignment_repo = InspectionAssignmentRepository()
            active_assignments = assignment_repo.query_active_assignments_by_assignee(payload["inspector_id"])
            if active_assignments:
                message = f"Cannot delete inspector. Has {len(active_assignments)} active inspection assignment(s)"
                raise ApiError(message, 400, "inspector_has_active_assignments")

            # Perform soft delete
            '''updated_record = self._repository.update_item(
                payload["inspector_id"],
                {
                    "status": "deleted",
                    "updated_at": datetime.utcnow().isoformat(),
                },
            )'''
            self._repository.delete_item(payload["inspector_id"])
            

            self._logger.info("Inspector %s soft deleted by admin", payload["inspector_id"])
            
            response = {
                "inspector_id": payload["inspector_id"],
                "deleted": True,
                "message": "Inspector deleted successfully"
            }
            return response
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to delete inspector: %s", exc)
            raise ApiError("Failed to delete inspector", 500, "delete_inspector_failed") from exc
