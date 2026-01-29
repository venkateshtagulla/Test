"""
Utility to convert Lambda responses to FastAPI responses.
"""
import json
from typing import Dict, Any
from fastapi.responses import JSONResponse


def lambda_response_to_fastapi(lambda_response: Dict[str, Any]) -> JSONResponse:
    """
    Convert AWS Lambda response format to FastAPI JSONResponse.
    
    Args:
        lambda_response: Lambda response dict with statusCode, body, headers
        
    Returns:
        FastAPI JSONResponse
    """
    status_code = lambda_response.get("statusCode", 200)
    body = lambda_response.get("body", "{}")
    headers = lambda_response.get("headers", {})
    
    # Parse JSON body if it's a string
    if isinstance(body, str):
        try:
            content = json.loads(body)
        except json.JSONDecodeError:
            content = {"error": "Invalid JSON response"}
    else:
        content = body
    
    return JSONResponse(
        content=content,
        status_code=status_code,
        headers=headers
    )
