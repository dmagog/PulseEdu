"""
PulseEdu FastAPI application entry point.
"""
import logging
import uuid
from contextvars import ContextVar
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.routes.health import router as health_router
from app.routes.admin import router as admin_router

# Request ID context variable
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# Custom logging filter to add request_id
class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get("")
        return True

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s level=%(levelname)s logger=%(name)s msg=%(message)s request_id=%(request_id)s"
)

# Add filter to root logger
root_logger = logging.getLogger()
root_logger.addFilter(RequestIDFilter())

# Create FastAPI app
app = FastAPI(
    title="PulseEdu",
    description="Educational analytics and recommendation system",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    
    # Log request start
    logger = logging.getLogger("app.request")
    logger.info(
        f"Request started method={request.method} url={str(request.url)} client_ip={request.client.host if request.client else 'unknown'}"
    )
    
    response = await call_next(request)
    
    # Log request completion
    logger.info(
        f"Request completed status_code={response.status_code}"
    )
    
    return response

# Include routers
app.include_router(health_router, tags=["health"])
app.include_router(admin_router, tags=["admin"])

@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with basic info."""
    return {
        "service": "PulseEdu",
        "version": "0.1.0",
        "status": "running"
    }
