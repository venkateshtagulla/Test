"""
Multipart form-data parser for API Gateway Lambda events.
"""
import base64
import email
from email import message_from_bytes
from typing import Dict, Optional, Tuple
from urllib.parse import unquote

from utility.errors import ApiError
from utility.logger import get_logger


logger = get_logger("MultipartParser")


def parse_multipart_form_data(event: Dict) -> Tuple[Dict[str, str], Dict[str, Tuple[bytes, str]]]:
    """
    Parse multipart/form-data from API Gateway event.
    
    Returns:
        Tuple of (form_fields, files) where:
        - form_fields: dict of field_name -> field_value (strings)
        - files: dict of field_name -> (file_content_bytes, filename)
    """
    try:
        # Get content type from various possible header formats
        headers = event.get("headers", {}) or {}
        content_type = (
            headers.get("Content-Type") or 
            headers.get("content-type") or 
            headers.get("Content-type") or
            ""
        )
        
        if not content_type or "multipart/form-data" not in content_type.lower():
            logger.error("Invalid content type: %s. Headers: %s", content_type, list(headers.keys()))
            raise ApiError(f"Content-Type must be multipart/form-data, got: {content_type}", 400, "invalid_content_type")
        
        # Extract boundary from Content-Type header
        boundary = None
        for part in content_type.split(";"):
            part = part.strip()
            if part.startswith("boundary="):
                boundary = part.split("=", 1)[1].strip('"')
                break
        
        if not boundary:
            raise ApiError("Could not find boundary in Content-Type header", 400, "missing_boundary")
        
        # Get and decode body
        body = event.get("body")
        if not body:
            raise ApiError("Request body is required", 400, "missing_body")
        
        # API Gateway with binary media types always base64 encodes binary data.
        # Some configurations may forget to set isBase64Encoded=True; in that
        # case we attempt a safe fallback decode if the boundary is not found.
        is_b64 = event.get("isBase64Encoded", False)
        if is_b64:
            try:
                body_bytes = base64.b64decode(body)
            except Exception as exc:
                logger.error("Failed to decode base64 body: %s", exc)
                raise ApiError("Invalid base64 encoded body", 400, "invalid_base64") from exc
        else:
            # If not base64 encoded, treat as bytes or encode string
            if isinstance(body, str):
                body_bytes = body.encode("utf-8")
            elif isinstance(body, bytes):
                body_bytes = body
            else:
                logger.error("Unexpected body type: %s", type(body))
                raise ApiError("Invalid body format", 400, "invalid_body_type")

        # Parse multipart message using email parser for robustness
        form_fields: Dict[str, str] = {}
        files: Dict[str, Tuple[bytes, str]] = {}

        try:
            mime_message = message_from_bytes(
                f"Content-Type: {content_type}\r\n\r\n".encode("utf-8") + body_bytes
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("Failed to create MIME message from body: %s", exc)
            raise ApiError("Failed to parse form data", 400, "parse_error") from exc

        for part in mime_message.walk():
            # Some email parsers return a Header object instead of a plain str,
            # so we always coerce to string before inspection.
            raw_cd = part.get("Content-Disposition")
            content_disposition = str(raw_cd) if raw_cd is not None else ""
            if not content_disposition or "form-data" not in content_disposition:
                continue

            field_name = part.get_param("name", header="Content-Disposition")
            filename = part.get_param("filename", header="Content-Disposition")

            if not field_name:
                continue

            payload = part.get_payload(decode=True) or b""

            if filename:
                # File field. Support multiple files for the same logical field
                # name (e.g., "photo" with multiple uploads) by creating
                # unique keys like photo, photo_2, photo_3, ...
                key = field_name
                if key in files:
                    index = 2
                    while f"{field_name}_{index}" in files:
                        index += 1
                    key = f"{field_name}_{index}"
                files[key] = (payload, unquote(filename))
            else:
                # Text field
                try:
                    form_fields[field_name] = payload.decode(part.get_content_charset() or "utf-8")
                except UnicodeDecodeError:
                    form_fields[field_name] = payload.decode("latin-1")

        logger.info(
            "Parsed multipart form-data fields: %s, files: %s",
            list(form_fields.keys()),
            list(files.keys()),
        )

        return form_fields, files
        
    except ApiError:
        raise
    except Exception as exc:
        logger.error("Failed to parse multipart form data: %s", exc)
        raise ApiError("Failed to parse form data", 400, "parse_error") from exc

