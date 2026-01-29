"""
Utility to convert FastAPI requests to Lambda event format.
This allows Lambda handlers to be called from FastAPI routes.
"""
import json
from typing import Dict, Any, Optional
from fastapi import Request
import base64


async def lambda_to_fastapi_response(
    request: Request,
    path_params: Optional[Dict[str, str]] = None,
    query_params: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Convert a FastAPI Request object to AWS Lambda event format.
    
    Args:
        request: FastAPI Request object
        path_params: Optional path parameters
        query_params: Optional query parameters
        
    Returns:
        Dict in AWS Lambda event format
    """
    # Get headers
    headers = dict(request.headers)
    
    # Get body if present
    body = None
    is_base64 = False
    content_type = headers.get("content-type", "")
    
    if request.method in ["POST", "PUT", "PATCH"]:
        if "application/json" in content_type:
            try:
                body_bytes = await request.body()
                body = body_bytes.decode("utf-8") if body_bytes else None
                is_base64 = False
            except:
                body = None
        elif "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
            # For multipart, we need to preserve the raw body
            body_bytes = await request.body()
           # body = body_bytes.decode("utf-8") if body_bytes else None
            body = base64.b64encode(body_bytes).decode("utf-8")
            is_base64 = True
    
    # Build Lambda event
    event = {
        "httpMethod": request.method,
        "path": request.url.path,
        "headers": headers,
        "body": body,
        "pathParameters": path_params or {},
        "queryStringParameters": query_params or dict(request.query_params),
        "requestContext": {
            "requestId": "local-dev",
            "identity": {
                "sourceIp": request.client.host if request.client else "127.0.0.1"
            }
        },
        "isBase64Encoded": is_base64
    }
    
    return event
