from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import get_settings
from routers.fastapi.main_router import api_router
from utility.fastapi_error_handler import fastapi_api_error_handler
from utility.errors import ApiError

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# Add CORS middleware for localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

 # Register your custom error handler for ApiError here (comment or remove on production)
app.add_exception_handler(ApiError, fastapi_api_error_handler)

# Include all API routers
app.include_router(api_router)


@app.get("/")
async def root():
    """
    Root endpoint - Public endpoint (no authentication required)
    """
    return {"message": "Welcome", "status": "running"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint - Public endpoint (no authentication required)
    """
    return {"status": "healthy", "message": "API is running properly"}
