"""
Application settings and environment loading utilities.
Pydantic-free implementation for Lambda compatibility.
"""
import os
from functools import lru_cache
from dotenv import load_dotenv
load_dotenv()


class Settings:
    """
    Centralized settings loaded from environment variables.
    Pydantic-free for Lambda cold-start optimization.
    """
    
    def __init__(self):
        # FastAPI Application Settings
        self.APP_NAME: str = os.getenv("APP_NAME", "ARKA Backend API")
        self.APP_DESCRIPTION: str = os.getenv("APP_DESCRIPTION", "Backend API for ARKA")
        self.APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
        self.DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
        
        # AWS Settings (required)
        self.aws_region: str = self._get_required("AWS_REGION")
        self.inspectors_table: str = self._get_required("DYNAMODB_TABLE_INSPECTORS")
        self.admins_table: str = self._get_required("DYNAMODB_TABLE_ADMINS")
        self.vessels_table: str = self._get_required("DYNAMODB_TABLE_VESSELS")
        self.inspection_forms_table: str = self._get_required("DYNAMODB_TABLE_INSPECTION_FORMS")
        self.inspection_assignments_table: str = self._get_required("DYNAMODB_TABLE_INSPECTION_ASSIGNMENTS")
        self.crew_table: str = self._get_required("DYNAMODB_TABLE_CREW")
        self.defects_table: str = self._get_required("DYNAMODB_TABLE_DEFECTS")
        self.vessel_assignments_table: str = self._get_required("DYNAMODB_TABLE_VESSEL_ASSIGNMENTS")
        self.inspection_responses_table: str = self._get_required("DYNAMODB_TABLE_INSPECTION_RESPONSES")
        self.media_bucket: str = self._get_required("S3_MEDIA_BUCKET")
        
        # JWT Settings
        self.jwt_secret_key: str = self._get_required("JWT_SECRET_KEY")
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_exp_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
        self.refresh_token_exp_minutes: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "43200"))  # 30 days
    
    @staticmethod
    def _get_required(key: str) -> str:
        """
        Get required environment variable or raise error.
        
        Args:
            key: Environment variable name
            
        Returns:
            Environment variable value
            
        Raises:
            ValueError: If environment variable is not set
        """
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"Required environment variable {key} is not set")
        return value


@lru_cache
def get_settings() -> Settings:
    """
    Return cached settings instance to avoid reloading environment variables.
    Uses lru_cache to ensure settings are loaded only once per Lambda container.
    
    Returns:
        Settings instance with all environment variables loaded
    """
    return Settings()
