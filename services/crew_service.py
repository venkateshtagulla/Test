"""
Service layer for crew management.
"""
from typing import Dict, Optional, Tuple, Any, List
from datetime import datetime
from uuid import uuid4

from config.jwt_config import generate_token_pair
from repository.crew_repository import CrewRepository
from utility.errors import ApiError
from utility.logger import get_logger
from utility.s3_utils import sign_s3_url_if_possible, upload_file_to_s3
from utility.security import hash_password, verify_password


class CrewService:
    """
    Business logic for crew creation and retrieval.
    """

    def __init__(self, repository: CrewRepository) -> None:
        self._repository = repository
        self._logger = get_logger(self.__class__.__name__)

    def register_crew(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a brand-new crew member.
        """
        email = payload.get("email")
        password = payload.get("password")
        confirm_password = payload.get("confirm_password")
        
        if not email or not password:
            raise ApiError("Email and password are required", 400, "missing_fields")

        if password != confirm_password:
            raise ApiError("Password and confirm password do not match", 400, "password_mismatch")

        existing = self._repository.get_by_email(email)
        if existing:
            raise ApiError("Email already registered", 409, "email_exists")

        now = datetime.utcnow().isoformat()
        crew_id = str(uuid4())
        pk=f"CREW#{crew_id}"
        crew = {
            "PK":pk,
            "SK":"METADATA",
            "crew_id": crew_id,
            "created_at": now,
            "updated_at": now,
            "first_name": payload.get("first_name"),
            "last_name": payload.get("last_name"),
            "email": email,
            "phone_number": payload.get("phone_number"),
            "password_hash": hash_password(password),
            "role": payload.get("role", "CREW"),
            "company_code": payload.get("company_code"),
            "status": "active",
            "GSI1PK":"CREW",
            "GSI1SK":email,
            
        }
        
        self._repository.put_item(crew)
        tokens = generate_token_pair(
            subject=crew["crew_id"],
            email=crew["email"],
            role=crew["role"],
        )
        response = {
            "crew_id": crew["crew_id"],
            "email": crew["email"],
            "tokens": tokens,
        }
        self._logger.info("Crew %s registered", crew["crew_id"])
        return response

    def login_crew(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Authenticate a crew member and generate tokens.
        """
        email = payload.get("email")
        password = payload.get("password")
        
        if not email or not password:
             raise ApiError("Email and password are required", 400, "missing_credentials")

        record = self._repository.get_by_email(email)
        if not record:
            raise ApiError("Invalid credentials", 401, "invalid_credentials")

        if not record.get("password_hash"):
            raise ApiError("Invalid credentials", 401, "invalid_credentials")

        if not verify_password(password, record["password_hash"]):
            raise ApiError("Invalid credentials", 401, "invalid_credentials")

        tokens = generate_token_pair(
            subject=record["crew_id"],
            email=record["email"],
            role=record.get("role"),
        )
        response = {
            "crew_id": record["crew_id"],
            "email": record["email"],
            "tokens": tokens,
        }
        self._logger.info("Crew %s logged in", record["crew_id"])
        return response

    def create_crew(
        self,
        admin_id: str,
        payload: Dict[str, Any],
        files: Optional[Dict[str, Tuple[bytes, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Create a crew member.
        If files are provided, uploads them to S3 and stores URLs.
        """

        try:
            # Upload files to S3 if provided
            id_proof_url = payload.get("id_proof_url")
            address_proof_url = payload.get("address_proof_url")
            additional_docs = payload.get("additional_docs") or []

            if files:
                if "id_proof" in files:
                    file_content, filename = files["id_proof"]
                    id_proof_url = upload_file_to_s3(file_content, filename, folder="crew/id-proof")
                
                if "address_proof" in files:
                    file_content, filename = files["address_proof"]
                    address_proof_url = upload_file_to_s3(file_content, filename, folder="crew/address-proof")
                
                # Handle additional docs
                additional_urls = []
                for key in sorted(files.keys()):
                    if key.startswith("additional_docs") or key.startswith("additional"):
                        file_content, filename = files[key]
                        url = upload_file_to_s3(file_content, filename, folder="crew/additional")
                        additional_urls.append(url)
                if additional_urls:
                    additional_docs = additional_urls

            # Hash password if provided
            password_hash = None
            password = payload.get("password")
            if password:
                password_hash = hash_password(password)

            now = datetime.utcnow().isoformat()
            crew_id = str(uuid4())
            pk=f"CREW#{crew_id}"
            crew = {
                "PK":pk,
                "SK":"METADATA",
                "crew_id": crew_id,
                "created_at": now,
                "updated_at": now,
                "first_name": payload.get("first_name"),
                "last_name": payload.get("last_name"),
                "email": payload.get("email"),
                "phone_number": payload.get("phone_number"),
                "password_hash": password_hash,
                "role": payload.get("role", "CREW"),
                "id_proof_url": id_proof_url,
                "address_proof_url": address_proof_url,
                "additional_docs": additional_docs if additional_docs else None,
                "created_by_admin_id": admin_id,
                "status": "active",
                "GSI1PK":"CREW",
                "GSI1SK":payload.get("email"),
            }
            
            self._repository.put_item(crew)
            
            self._logger.info("Crew %s created by admin %s", crew_id, admin_id)
            return crew
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to create crew: %s", exc)
            raise ApiError("Failed to create crew", 500, "create_crew_failed") from exc

    def get_crew(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve crew by id.
        """
        crew_id = payload.get("crew_id")
        if not crew_id:
             raise ApiError("crew_id is required", 400, "missing_crew_id")

        try:
            record = self._repository.get_item(crew_id)
            if not record:
                raise ApiError("Crew not found", 404, "crew_not_found")

            id_url = sign_s3_url_if_possible(record.get("id_proof_url"))
            addr_url = sign_s3_url_if_possible(record.get("address_proof_url"))
            additional = record.get("additional_docs") or []
            signed_additional = [sign_s3_url_if_possible(url) for url in additional]

            response = {
                "crew_id": record["crew_id"],
                "first_name": record["first_name"],
                "last_name": record["last_name"],
                "email": record.get("email"),
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
            self._logger.error("Failed to fetch crew: %s", exc)
            raise ApiError("Failed to fetch crew", 500, "get_crew_failed") from exc

    def list_crew(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        List crew with page/limit pagination and signed URLs for documents.
        """

        try:
            page = payload.get("page", 1)
            limit = payload.get("limit", 20)

            last_evaluated_key: Optional[Dict] = None
            items: list = []

            for _ in range(page):
                items, last_evaluated_key = self._repository.list_items(
                    limit=limit, exclusive_start_key=last_evaluated_key
                )
                if last_evaluated_key is None:
                    break

            crew_list = []
            for record in items:
                try:
                    # Validate required fields exist
                    crew_id = record.get("crew_id")
                    first_name = record.get("first_name")
                    last_name = record.get("last_name")
                    
                    if not crew_id or not first_name or not last_name:
                        self._logger.warning("Skipping crew record with missing required fields: %s", record.get("crew_id"))
                        continue
                    
                    # Safely sign URLs - if signing fails, use original URL or None
                    id_url = sign_s3_url_if_possible(record.get("id_proof_url"))
                    addr_url = sign_s3_url_if_possible(record.get("address_proof_url"))
                    additional_urls = record.get("additional_docs") or []
                    signed_additional = [
                        sign_s3_url_if_possible(doc_url) or doc_url 
                        for doc_url in additional_urls 
                        if doc_url  # Skip None/empty URLs
                    ]
                    
                    crew_list.append({
                        "crew_id": crew_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": record.get("email"),
                        "phone_number": record.get("phone_number"),
                        "role": record.get("role"),
                        "id_proof_url": id_url,
                        "address_proof_url": addr_url,
                        "additional_docs": signed_additional if signed_additional else None,
                    })
                except Exception as exc:
                    self._logger.error("Error processing crew record %s: %s", record.get("crew_id"), exc, exc_info=True)
                    # Skip this record and continue with others to prevent entire list from failing
                    continue

            response = {
                "crew": crew_list,
                "page": page,
                "limit": limit,
                "has_next": last_evaluated_key is not None,
            }
            return response
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to list crew: %s", exc)
            raise ApiError("Failed to list crew", 500, "list_crew_failed") from exc

    def reset_password(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reset crew password by admin.
        """
        crew_id = payload.get("crew_id")
        password = payload.get("password")
        
        if not crew_id or not password:
             raise ApiError("Missing crew_id or password", 400, "missing_fields")

        try:
            # Verify crew exists
            record = self._repository.get_item(crew_id)
            if not record:
                raise ApiError("Crew not found", 404, "crew_not_found")

            # Hash the new password
            password_hash = hash_password(password)
            self._logger.info("Hashed password for crew %s", crew_id)

            # Update password hash and updated_at timestamp
            updated_record = self._repository.update_item(
                crew_id,
                {
                    "password_hash": password_hash,
                    "updated_at": datetime.utcnow().isoformat(),
                },
            )
            
            # Verify the password was updated
            if not updated_record.get("password_hash"):
                self._logger.error("Password hash not found after update for crew %s", crew_id)
                raise ApiError("Failed to update password hash", 500, "password_update_failed")
            
            self._logger.info("Password reset for crew %s by admin", crew_id)
            return {"crew_id": crew_id, "message": "Password reset successfully"}
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to reset crew password: %s", exc)
            raise ApiError("Failed to reset crew password", 500, "reset_password_failed") from exc

    def delete_crew(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Soft delete a crew member by setting status to 'deleted'.
        Validates that the crew is not assigned to any active forms, open defects, or active assignments.
        """
        from repository.inspection_form_repository import InspectionFormRepository
        from repository.defect_repository import DefectRepository
        from repository.inspection_assignment_repository import InspectionAssignmentRepository
        
        crew_id = payload.get("crew_id")
        if not crew_id:
            raise ApiError("crew_id is required", 400, "missing_crew_id")

        try:
            # Verify crew exists
            record = self._repository.get_item(crew_id)
            if not record:
                raise ApiError("Crew not found", 404, "crew_not_found")

            # Check if already deleted
            if record.get("status") == "deleted":
                raise ApiError("Crew is already deleted", 400, "crew_already_deleted")

            # Check for active inspection forms
            form_repo = InspectionFormRepository()
            active_forms = form_repo.query_active_forms_by_assigned_crew(crew_id)
            if active_forms:
                form_titles = [f.get("title", "Untitled") for f in active_forms[:3]]
                message = f"Cannot delete crew. Assigned to {len(active_forms)} active form(s): {', '.join(form_titles)}"
                if len(active_forms) > 3:
                    message += f" and {len(active_forms) - 3} more"
                raise ApiError(message, 400, "crew_has_active_forms")

            # Check for open defects
            defect_repo = DefectRepository()
            open_defects = defect_repo.query_open_defects_by_assigned_crew(crew_id)
            if open_defects:
                defect_titles = [d.get("title", "Untitled") for d in open_defects[:3]]
                message = f"Cannot delete crew. Assigned to {len(open_defects)} open defect(s): {', '.join(defect_titles)}"
                if len(open_defects) > 3:
                    message += f" and {len(open_defects) - 3} more"
                raise ApiError(message, 400, "crew_has_open_defects")

            # Check for active inspection assignments
            assignment_repo = InspectionAssignmentRepository()
            active_assignments = assignment_repo.query_active_assignments_by_assignee(crew_id)
            if active_assignments:
                message = f"Cannot delete crew. Has {len(active_assignments)} active inspection assignment(s)"
                raise ApiError(message, 400, "crew_has_active_assignments")

            # Perform soft delete
            '''updated_record = self._repository.update_item(
                crew_id,
                {
                    "status": "deleted",
                    "updated_at": datetime.utcnow().isoformat(),
                },
            )'''
            self._repository.delete_item(crew_id)
            

            self._logger.info("Crew %s soft deleted by admin", crew_id)
            
            response = {
                "crew_id": crew_id,
                "deleted": True,
                "message": "Crew deleted successfully"
            }
            return response
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to delete crew: %s", exc)
            raise ApiError("Failed to delete crew", 500, "delete_crew_failed") from exc

    def get_profile_by_id(self, crew_id: str) -> Dict[str, Any]:
        """
        Retrieve crew profile using a raw crew_id (e.g. from JWT).
        """

        try:
            record = self._repository.get_item(crew_id)
            if not record:
                raise ApiError("Crew not found", 404, "crew_not_found")

            profile = {
                "crew_id": record["crew_id"],
                "first_name": record["first_name"],
                "last_name": record["last_name"],
                "email": record.get("email"),
                "phone_number": record.get("phone_number"),
                "role": record.get("role"),
            }
            return profile
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to fetch crew profile: %s", exc)
            raise ApiError("Failed to fetch crew profile", 500, "get_crew_profile_failed") from exc
