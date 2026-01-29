"""
Business logic for inspector onboarding and authentication (Single-table DynamoDB aligned with Crew).
"""
from datetime import datetime
from typing import Dict, Optional, Any
from uuid import uuid4

from repository.inspector_repository import InspectorRepository
from utility.errors import ApiError
from utility.logger import get_logger
from utility.security import hash_password, verify_password
from config.jwt_config import generate_token_pair


class InspectorService:
    """
    Service orchestrating inspector flows.
    """

    def __init__(self, repository: InspectorRepository) -> None:
        self._repository = repository
        self._logger = get_logger(self.__class__.__name__)

    # ---------------------------------------------------------
    # REGISTER INSPECTOR (SELF SIGNUP) - ALIGNED WITH CREW
    # ---------------------------------------------------------
    def register_inspector(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        password = payload.get("password")
        confirm_password = payload.get("confirm_password")
        email = payload.get("email")

        if not email or not password:
            raise ApiError("Missing required fields", 400, "missing_fields")

        if password != confirm_password:
            raise ApiError("Password and confirm password do not match", 400, "password_mismatch")

        # existing = self._repository.get_by_email(email)
        # if existing:
        #     raise ApiError("Email already registered", 409, "email_exists")

        inspector_id = str(uuid4())
        now = datetime.utcnow().isoformat()

        # ✅ Single-table DynamoDB item (same as Crew)
        inspector = {
            "PK": f"INSPECTOR#{inspector_id}",
            "SK": "METADATA",

            "role": payload.get("role"),

            "inspector_id": inspector_id,
            "first_name": payload.get("first_name"),
            "last_name": payload.get("last_name"),
            "email": email,
            "phone_number": payload.get("phone_number"),
            "password_hash": hash_password(password),
            "company_code": payload.get("company_code"),

            "status": "ACTIVE",
            "created_at": now,
            "updated_at": now,
            "GSI1PK": "INSPECTOR",
            "GSI1SK": email,
        }

        self._repository.put_item(inspector)

        tokens = generate_token_pair(
            subject=inspector["inspector_id"],
            email=inspector["email"],
            role=inspector["role"],
        )

        response = {
            "inspector_id": inspector["inspector_id"],
            "email": inspector["email"],
            "tokens": tokens,
        }

        self._logger.info("Inspector %s registered", inspector["inspector_id"])
        return response

    # ---------------------------------------------------------
    # LOGIN INSPECTOR - ALIGNED WITH CREW
    # ---------------------------------------------------------
    def login_inspector(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        email = payload.get("email")
        password = payload.get("password")

        if not email or not password:
            raise ApiError("Email and password are required", 400, "missing_credentials")

        record = self._repository.get_by_email(email)
        if not record:
            raise ApiError("Invalid credentials", 401, "invalid_credentials")

        password_hash = record.get("password_hash")
        if not password_hash or not verify_password(password, password_hash):
            raise ApiError("Invalid credentials", 401, "invalid_credentials")

        tokens = generate_token_pair(
            subject=record["inspector_id"],
            email=record["email"],
            role=record.get("role"),
        )

        response = {
            "inspector_id": record["inspector_id"],
            "email": record["email"],
            "tokens": tokens,
        }

        self._logger.info("Inspector %s logged in", record["inspector_id"])
        return response

    # ---------------------------------------------------------
    # GET PROFILE - ALIGNED WITH CREW
    # ---------------------------------------------------------
    def get_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        inspector_id = payload.get("inspector_id")
        if not inspector_id:
            raise ApiError("Inspector ID is required", 400, "missing_inspector_id")

        record = self._repository.get_item(inspector_id)
        if not record:
            raise ApiError("Inspector not found", 404, "inspector_not_found")
        

        return {
            "inspector_id": record["inspector_id"],
            "first_name": record.get("first_name"),
            "last_name": record.get("last_name"),
            "email": record["email"],
            "phone_number": record.get("phone_number"),
            "role": record.get("role"),
        }

    # ---------------------------------------------------------
    # GET PROFILE BY ID (JWT) - ALIGNED WITH CREW
    # ---------------------------------------------------------
    def get_profile_by_id(self, inspector_id: str, email: Optional[str] = None) -> Dict[str, Any]:
        self._logger.info("Fetching inspector profile for inspector_id: %s", inspector_id)

        record = self._repository.get_item(inspector_id)

        if not record and email:
            self._logger.warning(
                "Inspector not found by ID %s, trying email %s",
                inspector_id,
                email,
            )
            record = self._repository.get_by_email(email)

            if record:
                db_id = record.get("inspector_id")
                if db_id != inspector_id:
                    raise ApiError(
                        "Token inspector ID does not match database record",
                        401,
                        "token_id_mismatch",
                    )

        if not record:
            raise ApiError("Inspector not found", 404, "inspector_not_found")

        return {
            "inspector_id": record["inspector_id"],
            "first_name": record.get("first_name"),
            "last_name": record.get("last_name"),
            "email": record["email"],
            "phone_number": record.get("phone_number"),
            "role": record.get("role"),
        }
