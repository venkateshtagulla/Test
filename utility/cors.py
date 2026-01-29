"""
CORS middleware for Lambda handlers.
"""
from functools import wraps
from typing import Any, Callable, Dict


def cors_middleware(origin: str = "*"):
    """
    CORS middleware decorator for Lambda handlers.
    
    Adds CORS headers to all responses and handles OPTIONS preflight requests.
    
    Args:
        origin: Allowed origin (default: http://localhost:3000)
    
    Usage:
        @cors_middleware()
        def my_handler(event, context):
            return {"statusCode": 200, "body": "..."}
    """
    def decorator(handler: Callable[[Dict[str, Any], Any], Dict[str, Any]]) -> Callable[[Dict[str, Any], Any], Dict[str, Any]]:
        @wraps(handler)
        def wrapper(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
            # Handle OPTIONS preflight requests
            if event.get("httpMethod") == "OPTIONS" or (
                event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS"
            ):
                return {
                    "statusCode": 200,
                    "headers": {
                        "Access-Control-Allow-Origin": origin,
                        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
                        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
                        "Access-Control-Allow-Credentials": "true",
                    },
                    "body": "",
                }
            
            # Call the original handler
            response = handler(event, context)
            
            # Add CORS headers to the response
            if isinstance(response, dict):
                headers = response.get("headers", {})
                headers.update({
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
                    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
                    "Access-Control-Allow-Credentials": "true",
                    "Content-Type": "application/json",  # Ensure JSON content type
                })
                response["headers"] = headers
            
            return response
        
        return wrapper
    return decorator

