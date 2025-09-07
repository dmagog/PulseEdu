"""
Health check endpoints.
"""
import logging
from typing import Dict, Any

from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger("app.health")

@router.get("/healthz")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for Kubernetes/Docker health probes.
    
    Returns:
        Dict with status information
    """
    logger.info("Health check requested")
    
    return {
        "status": "ok",
        "service": "PulseEdu",
        "version": "0.1.0"
    }

@router.get("/health")
async def detailed_health() -> Dict[str, Any]:
    """
    Detailed health check with component status.
    
    Returns:
        Dict with detailed health information
    """
    logger.info("Detailed health check requested")
    
    # TODO: Add database connectivity check in future iterations
    # TODO: Add message broker connectivity check in future iterations
    
    return {
        "status": "ok",
        "service": "PulseEdu",
        "version": "0.1.0",
        "components": {
            "database": "not_implemented",
            "message_broker": "not_implemented",
            "llm_provider": "not_implemented"
        }
    }
