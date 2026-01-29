"""
Business logic for admin onboarding and authentication.
"""
from datetime import datetime
from typing import Dict, Any
from uuid import uuid4
from boto3.dynamodb.conditions import Key

from config.jwt_config import generate_token_pair
from repository.admin_repository import AdminRepository
from utility.errors import ApiError
from utility.logger import get_logger
from utility.security import hash_password, verify_password


class AdminService:
    """
    Service orchestrating admin flows.
    """

    def __init__(self, repository: AdminRepository) -> None:
        self._repository = repository
        self._logger = get_logger(self.__class__.__name__)

    def register_admin(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a brand-new admin.
        """

        existing = self._repository.get_by_email(payload["email"])
        if existing:
            raise ApiError("Email already registered", 409, "email_exists")

        now = datetime.utcnow().isoformat()
        admin_id = str(uuid4())
        pk=f"ADMIN{admin_id}"
        email_normalized = payload["email"].strip().lower()
        admin = {
            "PK":pk,
            "SK":"METADATA",
            "admin_id": admin_id,
            "email": email_normalized,
            "password_hash": hash_password(payload["password"]),
            "first_name": payload.get("first_name"),
            "last_name": payload.get("last_name"),
            "created_at": now,
            "updated_at": now,
            "GSI1PK":"ADMIN",
            "GSI1SK":email_normalized,
            
        }

        self._repository.put_item(admin)
        tokens = generate_token_pair(admin["admin_id"])
        
        response = {
            "admin_id": admin["admin_id"],
            "email": admin["email"],
            "tokens": tokens,
        }
        
        self._logger.info("Admin %s registered", admin["admin_id"])
        return response

    def login_admin(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Authenticate an admin and generate tokens.
        """

        record = self._repository.get_by_email(payload["email"].strip().lower())
        if not record:
            raise ApiError("Invalid credentials", 401, "invalid_credentials")

        if not verify_password(payload["password"], record["password_hash"]):
            raise ApiError("Invalid credentials", 401, "invalid_credentials")

        tokens = generate_token_pair(record["admin_id"])
        
        response = {
            "admin_id": record["admin_id"],
            "email": record["email"],
            "tokens": tokens,
        }
        
        self._logger.info("Admin %s logged in", record["admin_id"])
        return response

    def get_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve admin profile details.
        """

        record = self._repository.get_item(payload["admin_id"])
        if not record:
            raise ApiError("Admin not found", 404, "admin_not_found")

        profile = {
            "admin_id": record["admin_id"],
            "email": record["email"],
            "first_name": record.get("first_name"),
            "last_name": record.get("last_name"),
        }
        return profile

    def get_profile_by_id(self, admin_id: str) -> Dict[str, Any]:
        """
        Retrieve admin profile using a raw admin_id (e.g. from JWT).
        """

        payload = {"admin_id": admin_id}
        return self.get_profile(payload)



