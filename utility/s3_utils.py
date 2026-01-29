"""
S3 helper utilities for pre-signed URL generation and file uploads.
"""
import re
import unicodedata
from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

from botocore.exceptions import ClientError

from config.aws import get_s3_client
from config.settings import get_settings
from utility.errors import ApiError
from utility.logger import get_logger
from urllib.parse import urlparse, urlunparse


logger = get_logger("S3Utils")
settings = get_settings()
_s3_client = get_s3_client()


def _sanitize_s3_filename(file_name: str) -> str:
    """
    Sanitize an incoming filename so it is safe and readable in S3 keys.

    - Normalizes unicode characters (NFKD) and strips non-ASCII characters.
    - Replaces whitespace with underscores.
    - Removes characters that are unsafe for S3/object URLs.
    """

    # Normalize and strip to basic ASCII
    normalized = (
        unicodedata.normalize("NFKD", file_name)
        .encode("ascii", "ignore")
        .decode("ascii")
    )

    # Split name and extension
    if "." in normalized:
        base, ext = normalized.rsplit(".", 1)
        ext = ext.lower()
    else:
        base, ext = normalized, ""

    # Replace whitespace with underscores
    base = re.sub(r"\s+", "_", base.strip())

    # Remove any remaining invalid chars (keep letters, digits, - _ .)
    base = re.sub(r"[^A-Za-z0-9_\-\.]", "", base)

    # Fallback if file name becomes empty
    if not base:
        base = "file"

    return f"{base}.{ext}" if ext else base


def _extract_s3_key_from_url(url: str) -> Optional[str]:
    """
    Extract the S3 object key from a full S3 HTTPS URL.
    Strips query parameters if present.

    Returns None if the URL does not match the expected bucket/region pattern.
    """

    # Remove query parameters if present
    url_clean = url.split("?")[0]
    
    # Support both regional and legacy global endpoint forms:
    # - https://bucket.s3.<region>.amazonaws.com/<key>
    # - https://bucket.s3.amazonaws.com/<key>
    pattern = (
        rf"^https://{re.escape(settings.media_bucket)}"
        r"\.s3(?:[.-](?P<region>[-a-z0-9]+))?\.amazonaws\.com/(?P<key>.+)$"
    )
    match = re.match(pattern, url_clean)
    if not match:
        return None
    return match.group("key")


def generate_presigned_put_url(key: str, content_type: str, expires_in_seconds: int = 900) -> Dict[str, str]:
    """
    Generate a pre-signed PUT URL for uploading to S3.
    """

    try:
        url = _s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.media_bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in_seconds,
        )
        return {
            "upload_url": url,
            "key": key,
            "bucket": settings.media_bucket,
        }
    except ClientError as exc:
        logger.error("Failed to generate presigned URL for key=%s: %s", key, exc)
        raise ApiError("Could not generate upload URL", 500, "presign_failed") from exc


def _get_content_type_from_key(key: str) -> str:
    """
    Infer content type from file extension in S3 key.
    Returns a default content type if extension is not recognized.
    """
    # Common content types for media files
    content_type_map = {
        # Images
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
        "svg": "image/svg+xml",
        "bmp": "image/bmp",
        "ico": "image/x-icon",
        "tiff": "image/tiff",
        "tif": "image/tiff",
        # Documents
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "ppt": "application/vnd.ms-powerpoint",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        # Text
        "txt": "text/plain",
        "html": "text/html",
        "htm": "text/html",
        "css": "text/css",
        "js": "text/javascript",
        "json": "application/json",
        "xml": "application/xml",
        "csv": "text/csv",
        # Video
        "mp4": "video/mp4",
        "avi": "video/x-msvideo",
        "mov": "video/quicktime",
        "wmv": "video/x-ms-wmv",
        "flv": "video/x-flv",
        "webm": "video/webm",
        # Audio
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "m4a": "audio/mp4",
    }
    
    # Extract extension from key (handle query params if any)
    key_part = key.split("?")[0]
    if "." in key_part:
        ext = key_part.rsplit(".", 1)[-1].lower()
        return content_type_map.get(ext, "application/octet-stream")
    return "application/octet-stream"


def _get_s3_object_metadata(key: str) -> tuple:
    """
    Get Content-Type and filename from S3 object metadata.
    Returns (content_type, filename) tuple.
    """
    # Extract filename from key first (remove path and query params)
    key_clean = key.split("?")[0]  # Remove any existing query params
    filename = key_clean.split("/")[-1]  # Get the last part (filename)
    
    try:
        response = _s3_client.head_object(
            Bucket=settings.media_bucket,
            Key=key.split("?")[0],  # Use clean key without query params
        )
        content_type = response.get("ContentType")
        # If Content-Type is missing or binary, try to infer from extension
        if not content_type or content_type == "binary/octet-stream" or content_type == "application/octet-stream":
            content_type = _get_content_type_from_key(key_clean)
        
        # Try to get filename from Content-Disposition metadata if available
        content_disposition_meta = response.get("ContentDisposition", "")
        if content_disposition_meta and "filename=" in content_disposition_meta:
            # Extract filename from Content-Disposition header
            import re
            match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition_meta)
            if match:
                filename = match.group(1).strip('"\'')
        
        return content_type, filename
    except ClientError as exc:
        logger.warning("Could not get metadata for key %s: %s, inferring from key", key, exc)
        # Fallback: infer from key
        content_type = _get_content_type_from_key(key_clean)
        return content_type, filename


def generate_presigned_get_url(key: str, expires_in_seconds: int = 900) -> str:
    """
    Generate a pre-signed GET URL for an existing S3 object.
    Uses ResponseContentDisposition: 'inline' with filename to allow files to open in browser.
    Also sets ResponseContentType to ensure proper browser handling.

    NOTE:
    - We must not modify the host/URL after boto3 signs it, otherwise the
      signature will no longer match and S3 will return SignatureDoesNotMatch.
    """

    if not key:
        raise ApiError("S3 key is required", 400, "missing_key")
    
    try:
        # Clean key (remove any query params if present)
        clean_key = key.split("?")[0]
        if not clean_key:
            raise ApiError("Invalid S3 key", 400, "invalid_key")
        
        # Get content type and filename from S3 object metadata
        content_type, filename = _get_s3_object_metadata(clean_key)
        
        # Escape filename for Content-Disposition header (escape quotes and backslashes)
        escaped_filename = filename.replace('\\', '\\\\').replace('"', '\\"')
        
        # Build ResponseContentDisposition with inline and filename
        # Format: inline; filename="filename.ext"
        content_disposition = f'inline; filename="{escaped_filename}"'
        
        params = {
            "Bucket": settings.media_bucket,
            "Key": clean_key,
            "ResponseContentDisposition": content_disposition,
        }
        
        # Always set ResponseContentType to ensure browser handles it correctly
        params["ResponseContentType"] = content_type
        
        presigned = _s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params=params,
            ExpiresIn=expires_in_seconds,
        )
        return presigned
    except (ClientError, ApiError) as exc:
        logger.error("Failed to generate presigned GET URL for key=%s: %s", key, exc)
        raise ApiError("Could not generate download URL", 500, "presign_get_failed") from exc
    except Exception as exc:
        logger.error("Unexpected error generating presigned GET URL for key=%s: %s", key, exc)
        raise ApiError("Could not generate download URL", 500, "presign_get_failed") from exc


def sign_s3_url_if_possible(url: Optional[str], expires_in_seconds: int = 900) -> Optional[str]:
    """
    If the provided URL points to the configured media bucket, return a
    pre-signed GET URL; otherwise return the original URL.
    If signing fails for any reason, returns the original URL as fallback.
    """

    if not url:
        return None
    
    # Handle non-string URLs
    if not isinstance(url, str):
        logger.warning("sign_s3_url_if_possible received non-string URL: %s", type(url))
        return None
    
    key = _extract_s3_key_from_url(url)
    if not key:
        return url
    try:
        return generate_presigned_get_url(key, expires_in_seconds=expires_in_seconds)
    except Exception as exc:
        # Log the error but fall back to original URL to prevent breaking the API
        logger.warning("Failed to sign S3 URL %s, using original URL: %s", url, exc)
        return url


def upload_file_to_s3(file_content: bytes, file_name: str, folder: Optional[str] = None, content_type: Optional[str] = None) -> str:
    """
    Upload a file directly to S3 and return the public URL.
    Automatically infers Content-Type from filename if not provided.
    
    Args:
        file_content: Binary content of the file.
        file_name: Original file name as received from the client.
        folder: Optional folder/prefix (e.g., "docs", "inspectors").
        content_type: MIME type of the file (optional, will be inferred from filename if not provided).
    
    Returns:
        S3 public URL of the uploaded file.
    """
    try:
        # Sanitize filename for safe S3 key usage
        safe_file_name = _sanitize_s3_filename(file_name)

        # Generate S3 key with folder prefix and unique identifier
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        unique_id = str(uuid4())[:8]
        extension = safe_file_name.split(".")[-1] if "." in safe_file_name else ""
        
        prefix = f"{folder}/" if folder else ""
        key = f"{prefix}{timestamp}/{unique_id}_{safe_file_name}" if extension else f"{prefix}{timestamp}/{unique_id}"
        
        # Infer content type from filename if not provided
        if not content_type:
            content_type = _get_content_type_from_key(safe_file_name)
        
        upload_params = {
            "Bucket": settings.media_bucket,
            "Key": key,
            "Body": file_content,
            "ContentType": content_type,  # Always set ContentType for proper browser handling
        }
        
        _s3_client.put_object(**upload_params)
        
        # Return public S3 URL
        url = f"https://{settings.media_bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"
        logger.info("File uploaded to S3: %s", url)
        return url
        
    except ClientError as exc:
        logger.error("Failed to upload file to S3: %s", exc)
        raise ApiError("Could not upload file to S3", 500, "s3_upload_failed") from exc

