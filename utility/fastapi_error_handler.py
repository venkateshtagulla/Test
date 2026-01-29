from fastapi import Request
from fastapi.responses import JSONResponse
from utility.errors import ApiError
from utility.response import format_response

# FastAPI version - do NOT add CORS here
async def fastapi_api_error_handler(request: Request, exc: ApiError):
    body = format_response(
        success=False,
        data=None,
        message=exc.message,
        error={"code": exc.error_code},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=body,
    )
