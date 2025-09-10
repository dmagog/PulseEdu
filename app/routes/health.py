"""
Health check endpoints.
"""
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
import psutil
import time
import pytz

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.session import get_session

router = APIRouter()
logger = logging.getLogger("app.health")

# Templates
templates = Jinja2Templates(directory="app/ui/templates")

# GMT+5 timezone (UTC+5)
GMT_PLUS_5 = pytz.timezone('Asia/Karachi')  # GMT+5

def get_gmt_plus_5_time() -> datetime:
    """Get current time in GMT+5 timezone."""
    return datetime.now(GMT_PLUS_5)

def format_gmt_plus_5_time(dt: datetime, format_str: str = "%d.%m.%Y %H:%M:%S") -> str:
    """Format datetime in GMT+5 timezone."""
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(GMT_PLUS_5).strftime(format_str)

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
        "version": "0.1.1"
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
        "version": "0.1.1",
        "components": {
            "database": "not_implemented",
            "message_broker": "not_implemented",
            "llm_provider": "not_implemented"
        }
    }


@router.get("/status", response_class=HTMLResponse)
async def system_status(
    request: Request,
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    System status web interface.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        HTML response with system status
    """
    logger.info("System status page requested")
    
    try:
        # Get system metrics
        system_metrics = await get_system_metrics()
        
        # Get component status
        component_status = await get_component_status(db)
        
        # Get performance metrics
        performance_metrics = await get_performance_metrics()
        
        # Get incident history
        incident_history = await get_incident_history()
        
        return templates.TemplateResponse("status.html", {
            "request": request,
            "title": "Статус системы",
            "system_metrics": system_metrics,
            "component_status": component_status,
            "performance_metrics": performance_metrics,
            "incident_history": incident_history,
            "last_updated": get_gmt_plus_5_time().strftime("%d.%m.%Y %H:%M:%S")
        })
        
    except Exception as e:
        logger.error(f"Error loading system status: {e}")
        return templates.TemplateResponse("status.html", {
            "request": request,
            "title": "Статус системы",
            "error": str(e),
            "last_updated": get_gmt_plus_5_time().strftime("%d.%m.%Y %H:%M:%S")
        })


async def get_system_metrics() -> Dict[str, Any]:
    """Get system resource metrics."""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # System uptime
        boot_time = psutil.boot_time()
        uptime = datetime.now() - datetime.fromtimestamp(boot_time)
        
        return {
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "memory_available": memory.available // (1024**3),  # GB
            "memory_total": memory.total // (1024**3),  # GB
            "disk_usage": disk.percent,
            "disk_free": disk.free // (1024**3),  # GB
            "disk_total": disk.total // (1024**3),  # GB
            "uptime": str(uptime).split('.')[0],  # Remove microseconds
            "boot_time": format_gmt_plus_5_time(datetime.fromtimestamp(boot_time)) + " GMT+5"
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return {
            "cpu_usage": 0,
            "memory_usage": 0,
            "memory_available": 0,
            "memory_total": 0,
            "disk_usage": 0,
            "disk_free": 0,
            "disk_total": 0,
            "uptime": "N/A",
            "boot_time": "N/A"
        }


async def get_component_status(db: Session) -> Dict[str, Any]:
    """Get status of system components."""
    try:
        # Test database connection
        db_status = "healthy"
        db_response_time = 0
        db_version = "unknown"
        db_size = "unknown"
        try:
            from sqlalchemy import text
            start_time = time.time()
            db.execute(text("SELECT 1"))
            db_response_time = round((time.time() - start_time) * 1000, 2)  # ms
            
            # Get database version
            try:
                result = db.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                db_version = version.split(',')[0]  # Get just the main version info
            except:
                pass
            
            # Get database size
            try:
                result = db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))"))
                db_size = result.fetchone()[0]
            except:
                pass
                
        except Exception as e:
            db_status = "unhealthy"
            logger.error(f"Database health check failed: {e}")
        
        # Get real component status
        components = {
            "database": {
                "status": db_status,
                "response_time": db_response_time,
                "version": db_version,
                "size": db_size,
                "last_check": get_gmt_plus_5_time().strftime("%H:%M:%S GMT+5")
            }
        }
        
        # Test RabbitMQ connection
        try:
            import pika
            start_time = time.time()
            connection = pika.BlockingConnection(pika.ConnectionParameters('mq', 5672, '/', pika.PlainCredentials('pulseedu', 'pulseedu')))
            connection.close()
            rabbitmq_response_time = round((time.time() - start_time) * 1000, 2)  # ms
            components["rabbitmq"] = {
                "status": "healthy",
                "response_time": rabbitmq_response_time,
                "last_check": get_gmt_plus_5_time().strftime("%H:%M:%S GMT+5")
            }
        except Exception as e:
            components["rabbitmq"] = {
                "status": "unhealthy",
                "response_time": 0,
                "last_check": get_gmt_plus_5_time().strftime("%H:%M:%S GMT+5"),
                "error": str(e)
            }
        
        # Test Celery (Flower) connection
        try:
            import httpx
            start_time = time.time()
            response = httpx.get("http://flower:5555/", timeout=5.0)
            celery_response_time = round((time.time() - start_time) * 1000, 2)  # ms
            if response.status_code == 200:
                components["celery"] = {
                    "status": "healthy",
                    "response_time": celery_response_time,
                    "last_check": get_gmt_plus_5_time().strftime("%H:%M:%S GMT+5")
                }
            else:
                components["celery"] = {
                    "status": "unhealthy",
                    "response_time": celery_response_time,
                    "last_check": get_gmt_plus_5_time().strftime("%H:%M:%S GMT+5"),
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            components["celery"] = {
                "status": "unhealthy",
                "response_time": 0,
                "last_check": get_gmt_plus_5_time().strftime("%H:%M:%S GMT+5"),
                "error": str(e)
            }
        
        return components
    except Exception as e:
        logger.error(f"Error getting component status: {e}")
        return {}


async def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics."""
    try:
        # Get real performance data
        import os
        
        # Get process information
        current_process = psutil.Process(os.getpid())
        
        return {
            "process_info": {
                "cpu_percent": current_process.cpu_percent(),
                "memory_mb": round(current_process.memory_info().rss / 1024 / 1024, 2),
                "threads": current_process.num_threads(),
                "open_files": len(current_process.open_files()) if hasattr(current_process, 'open_files') else 0
            },
            "system_load": {
                "load_1min": os.getloadavg()[0] if hasattr(os, 'getloadavg') else "N/A",
                "load_5min": os.getloadavg()[1] if hasattr(os, 'getloadavg') else "N/A",
                "load_15min": os.getloadavg()[2] if hasattr(os, 'getloadavg') else "N/A"
            }
        }
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return {}


async def get_incident_history() -> list:
    """Get incident history."""
    try:
        # For now, return empty list - will be implemented when we have real incident tracking
        return []
    except Exception as e:
        logger.error(f"Error getting incident history: {e}")
        return []


@router.get("/status/diagnostics", response_class=HTMLResponse)
async def system_diagnostics(
    request: Request,
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    System diagnostics page with detailed technical information.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        HTML response with system diagnostics
    """
    logger.info("System diagnostics page requested")
    
    try:
        # Get detailed system information
        system_info = await get_detailed_system_info()
        
        # Get database diagnostics
        db_diagnostics = await get_database_diagnostics(db)
        
        # Get service diagnostics
        service_diagnostics = await get_service_diagnostics()
        
        # Get network diagnostics
        network_diagnostics = await get_network_diagnostics()
        
        return templates.TemplateResponse("diagnostics.html", {
            "request": request,
            "title": "Техническая диагностика",
            "system_info": system_info,
            "db_diagnostics": db_diagnostics,
            "service_diagnostics": service_diagnostics,
            "network_diagnostics": network_diagnostics,
            "last_updated": get_gmt_plus_5_time().strftime("%d.%m.%Y %H:%M:%S")
        })
        
    except Exception as e:
        logger.error(f"Error loading system diagnostics: {e}")
        return templates.TemplateResponse("diagnostics.html", {
            "request": request,
            "title": "Техническая диагностика",
            "error": str(e),
            "last_updated": get_gmt_plus_5_time().strftime("%d.%m.%Y %H:%M:%S")
        })


async def get_detailed_system_info() -> Dict[str, Any]:
    """Get detailed system information."""
    try:
        # System information
        import platform
        import os
        
        # Only include meaningful values
        info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "processes": len(psutil.pids()),
        }
        
        # Add processor only if it's not empty
        processor = platform.processor()
        if processor and processor.strip():
            info["processor"] = processor
            
        # Add load average only if available
        if hasattr(os, 'getloadavg'):
            load_avg = os.getloadavg()
            info["load_average"] = f"{load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}"
            
        return info
    except Exception as e:
        logger.error(f"Error getting detailed system info: {e}")
        return {}


async def get_database_diagnostics(db: Session) -> Dict[str, Any]:
    """Get database diagnostics."""
    try:
        diagnostics = {
            "connection": "unknown",
            "version": "unknown",
            "size": "unknown",
            "tables": [],
            "connections": 0,
            "locks": 0
        }
        
        # Test connection
        try:
            from sqlalchemy import text
            result = db.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            diagnostics["connection"] = "connected"
            diagnostics["version"] = version
        except Exception as e:
            diagnostics["connection"] = f"error: {str(e)}"
        
        # Get database size
        try:
            from sqlalchemy import text
            result = db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))"))
            size = result.fetchone()[0]
            diagnostics["size"] = size
        except Exception as e:
            diagnostics["size"] = f"error: {str(e)}"
        
        # Get table list
        try:
            from sqlalchemy import text
            result = db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"))
            tables = [row[0] for row in result.fetchall()]
            diagnostics["tables"] = tables
        except Exception as e:
            diagnostics["tables"] = [f"error: {str(e)}"]
        
        # Get connection count
        try:
            from sqlalchemy import text
            result = db.execute(text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"))
            connections = result.fetchone()[0]
            diagnostics["connections"] = connections
        except Exception as e:
            diagnostics["connections"] = f"error: {str(e)}"
        
        return diagnostics
    except Exception as e:
        logger.error(f"Error getting database diagnostics: {e}")
        return {"error": str(e)}


async def get_service_diagnostics() -> Dict[str, Any]:
    """Get service diagnostics."""
    try:
        # Get real service information
        services = {}
        
        # Web server info
        current_process = psutil.Process()
        services["web_server"] = {
            "status": "running",
            "port": 8000,
            "pid": current_process.pid,
            "uptime": str(datetime.now() - datetime.fromtimestamp(current_process.create_time())).split('.')[0]
        }
        
        # Database info (already tested in component status)
        services["database"] = {
            "status": "running",
            "port": 5432,
            "uptime": "N/A"  # Would need to query PostgreSQL for this
        }
        
        # RabbitMQ info
        try:
            import pika
            connection = pika.BlockingConnection(pika.ConnectionParameters('mq', 5672, '/', pika.PlainCredentials('pulseedu', 'pulseedu')))
            connection.close()
            services["rabbitmq"] = {
                "status": "running",
                "port": 5672,
                "uptime": "N/A"  # Would need to query RabbitMQ management API
            }
        except Exception as e:
            services["rabbitmq"] = {
                "status": "unhealthy",
                "port": 5672,
                "error": str(e)
            }
        
        # Celery info
        try:
            import httpx
            response = httpx.get("http://flower:5555/", timeout=5.0)
            if response.status_code == 200:
                services["celery"] = {
                    "status": "running",
                    "port": 5555,
                    "uptime": "N/A"  # Would need to query Flower API
                }
            else:
                services["celery"] = {
                    "status": "unhealthy",
                    "port": 5555,
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            services["celery"] = {
                "status": "unhealthy",
                "port": 5555,
                "error": str(e)
            }
        
        return services
    except Exception as e:
        logger.error(f"Error getting service diagnostics: {e}")
        return {}


async def get_network_diagnostics() -> Dict[str, Any]:
    """Get network diagnostics."""
    try:
        import socket
        
        # Get network interfaces
        interfaces = []
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    interfaces.append({
                        "name": interface,
                        "ip": addr.address,
                        "netmask": addr.netmask
                    })
        
        # Get network connections
        connections = len(psutil.net_connections())
        
        # Get network I/O
        net_io = psutil.net_io_counters()
        
        return {
            "interfaces": interfaces,
            "connections": connections,
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        }
    except Exception as e:
        logger.error(f"Error getting network diagnostics: {e}")
        return {}
