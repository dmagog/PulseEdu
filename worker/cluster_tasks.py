"""
Celery tasks for student clustering.
"""
import logging
from typing import Dict, Any

from celery import Celery
from app.database.session import get_db_session
from app.services.cluster_service import ClusterService
from app.services.ml_cluster_service import MLClusterService
from app.services.ml_monitoring_service import MLMonitoringService
from app.services.config_service import config_service
from worker.celery_cluster import celery_app

logger = logging.getLogger("worker.cluster_tasks")
cluster_service = ClusterService()
ml_cluster_service = MLClusterService()
monitoring_service = MLMonitoringService()


@celery_app.task(bind=True, name="cluster.cluster_students_after_import")
def cluster_students_after_import(self, import_job_id: str) -> Dict[str, Any]:
    """
    Cluster students after successful data import.
    
    This task is triggered after import completion to update student clusters
    based on the newly imported data.
    
    Args:
        import_job_id: ID of the import job that completed
        
    Returns:
        Dictionary with clustering results
    """
    logger.info(f"Starting clustering task for import job: {import_job_id}")
    
    try:
        with get_db_session() as db:
            # Cluster students for all courses
            result = cluster_service.cluster_all_courses(db, import_job_id)
            
            if "error" in result:
                logger.error(f"Clustering failed: {result['error']}")
                return {
                    "status": "failed",
                    "error": result["error"],
                    "import_job_id": import_job_id
                }
            
            logger.info(f"Clustering completed successfully: {result['total_clustered']} students clustered across {result['successful_courses']} courses")
            
            return {
                "status": "success",
                "import_job_id": import_job_id,
                "total_courses": result["total_courses"],
                "successful_courses": result["successful_courses"],
                "total_students": result["total_students"],
                "total_clustered": result["total_clustered"],
                "clustered_at": result["clustered_at"]
            }
            
    except Exception as e:
        logger.error(f"Error in clustering task: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "import_job_id": import_job_id
        }


@celery_app.task(bind=True, name="cluster.cluster_course_students")
def cluster_course_students(self, course_id: int, import_job_id: str = None) -> Dict[str, Any]:
    """
    Cluster students for a specific course.
    
    Args:
        course_id: Course ID to cluster students for
        import_job_id: Optional import job ID that triggered clustering
        
    Returns:
        Dictionary with clustering results
    """
    logger.info(f"Starting clustering task for course: {course_id}")
    
    try:
        with get_db_session() as db:
            # Cluster students for specific course
            result = cluster_service.cluster_students_by_course(course_id, db, import_job_id)
            
            if "error" in result:
                logger.error(f"Clustering failed for course {course_id}: {result['error']}")
                return {
                    "status": "failed",
                    "error": result["error"],
                    "course_id": course_id,
                    "import_job_id": import_job_id
                }
            
            logger.info(f"Clustering completed for course {course_id}: {result['clustered_students']} students clustered")
            
            return {
                "status": "success",
                "course_id": course_id,
                "course_name": result["course_name"],
                "total_students": result["total_students"],
                "clustered_students": result["clustered_students"],
                "clusters": result["clusters"],
                "import_job_id": import_job_id,
                "clustered_at": result["clustered_at"]
            }
            
    except Exception as e:
        logger.error(f"Error in course clustering task: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "course_id": course_id,
            "import_job_id": import_job_id
        }


@celery_app.task(bind=True, name="cluster.periodic_cluster_update")
def periodic_cluster_update(self) -> Dict[str, Any]:
    """
    Periodic task to update student clusters.
    
    This task runs periodically to ensure clusters are up-to-date
    with the latest student performance data.
    
    Returns:
        Dictionary with clustering results
    """
    logger.info("Starting periodic cluster update")
    
    try:
        with get_db_session() as db:
            # Cluster students for all courses
            result = cluster_service.cluster_all_courses(db)
            
            if "error" in result:
                logger.error(f"Periodic clustering failed: {result['error']}")
                return {
                    "status": "failed",
                    "error": result["error"]
                }
            
            logger.info(f"Periodic clustering completed: {result['total_clustered']} students clustered across {result['successful_courses']} courses")
            
            return {
                "status": "success",
                "total_courses": result["total_courses"],
                "successful_courses": result["successful_courses"],
                "total_students": result["total_students"],
                "total_clustered": result["total_clustered"],
                "clustered_at": result["clustered_at"]
            }
            
    except Exception as e:
        logger.error(f"Error in periodic clustering task: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


@celery_app.task(bind=True, name="cluster.ml_cluster_students_after_import")
def ml_cluster_students_after_import(self, import_job_id: str) -> Dict[str, Any]:
    """
    ML-based clustering task after successful data import.
    
    Uses advanced ML algorithms for more accurate student clustering.
    
    Args:
        import_job_id: ID of the import job that completed
        
    Returns:
        Dictionary with ML clustering results
    """
    logger.info(f"Starting ML clustering task for import job: {import_job_id}")
    
    try:
        with get_db_session() as db:
            # Use ML service directly for advanced clustering
            result = ml_cluster_service.cluster_all_courses(db, import_job_id)
            
            if "error" in result:
                logger.error(f"ML clustering failed: {result['error']}")
                return {
                    "status": "failed",
                    "error": result["error"],
                    "import_job_id": import_job_id
                }
            
            logger.info(f"ML clustering completed successfully: {result['total_clustered']} students clustered across {result['successful_courses']} courses using algorithms: {result.get('algorithm_summary', {})}")
            
            return {
                "status": "success",
                "import_job_id": import_job_id,
                "total_courses": result["total_courses"],
                "successful_courses": result["successful_courses"],
                "total_students": result["total_students"],
                "total_clustered": result["total_clustered"],
                "algorithm_summary": result.get("algorithm_summary", {}),
                "clustered_at": result["clustered_at"]
            }
            
    except Exception as e:
        logger.error(f"Error in ML clustering task: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "import_job_id": import_job_id
        }


@celery_app.task(bind=True, name="cluster.ml_cluster_course_students")
def ml_cluster_course_students(self, course_id: int, import_job_id: str = None) -> Dict[str, Any]:
    """
    ML-based clustering for a specific course.
    
    Args:
        course_id: Course ID to cluster students for
        import_job_id: Optional import job ID that triggered clustering
        
    Returns:
        Dictionary with ML clustering results
    """
    logger.info(f"Starting ML clustering task for course: {course_id}")
    
    try:
        with get_db_session() as db:
            # Use ML service directly for advanced clustering
            result = ml_cluster_service.cluster_students_by_course(course_id, db, import_job_id)
            
            if "error" in result:
                logger.error(f"ML clustering failed for course {course_id}: {result['error']}")
                return {
                    "status": "failed",
                    "error": result["error"],
                    "course_id": course_id,
                    "import_job_id": import_job_id
                }
            
            logger.info(f"ML clustering completed for course {course_id}: {result['clustered_students']} students clustered using {result.get('algorithm_used', 'Unknown')}")
            
            return {
                "status": "success",
                "course_id": course_id,
                "course_name": result["course_name"],
                "total_students": result["total_students"],
                "clustered_students": result["clustered_students"],
                "algorithm_used": result.get("algorithm_used", "Unknown"),
                "quality_metrics": result.get("quality_metrics", {}),
                "clusters": result["clusters"],
                "import_job_id": import_job_id,
                "clustered_at": result["clustered_at"]
            }
            
    except Exception as e:
        logger.error(f"Error in ML course clustering task: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "course_id": course_id,
            "import_job_id": import_job_id
        }


@celery_app.task(bind=True, name="cluster.periodic_ml_cluster_update")
def periodic_ml_cluster_update(self) -> Dict[str, Any]:
    """
    Periodic ML-based clustering task.
    
    Uses advanced ML algorithms for periodic cluster updates.
    
    Returns:
        Dictionary with ML clustering results
    """
    logger.info("Starting periodic ML cluster update")
    
    try:
        with get_db_session() as db:
            # Use ML service directly for advanced clustering
            result = ml_cluster_service.cluster_all_courses(db)
            
            if "error" in result:
                logger.error(f"Periodic ML clustering failed: {result['error']}")
                return {
                    "status": "failed",
                    "error": result["error"]
                }
            
            logger.info(f"Periodic ML clustering completed: {result['total_clustered']} students clustered across {result['successful_courses']} courses using algorithms: {result.get('algorithm_summary', {})}")
            
            return {
                "status": "success",
                "total_courses": result["total_courses"],
                "successful_courses": result["successful_courses"],
                "total_students": result["total_students"],
                "total_clustered": result["total_clustered"],
                "algorithm_summary": result.get("algorithm_summary", {}),
                "clustered_at": result["clustered_at"]
            }
            
    except Exception as e:
        logger.error(f"Error in periodic ML clustering task: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


@celery_app.task(bind=True, name="cluster.generate_clustering_quality_report")
def generate_clustering_quality_report(self, course_id: int) -> Dict[str, Any]:
    """
    Generate quality report for clustering results.
    
    Args:
        course_id: Course ID to generate report for
        
    Returns:
        Dictionary with quality report
    """
    logger.info(f"Generating clustering quality report for course: {course_id}")
    
    try:
        with get_db_session() as db:
            # Generate quality report
            result = ml_cluster_service.get_clustering_quality_report(course_id, db)
            
            if "error" in result:
                logger.error(f"Quality report generation failed for course {course_id}: {result['error']}")
                return {
                    "status": "failed",
                    "error": result["error"],
                    "course_id": course_id
                }
            
            logger.info(f"Quality report generated for course {course_id}: {result['total_clusters']} clusters analyzed")
            
            return {
                "status": "success",
                "course_id": course_id,
                "total_clusters": result["total_clusters"],
                "cluster_analysis": result["cluster_analysis"],
                "generated_at": result["generated_at"]
            }
            
    except Exception as e:
        logger.error(f"Error generating quality report: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "course_id": course_id
        }


@celery_app.task(bind=True, name="cluster.update_ml_parameters")
def update_ml_parameters(self, algorithm: str = "KMeans", params: Dict[str, Any] = None, 
                        quality_threshold: float = 0.3) -> Dict[str, Any]:
    """
    Update ML clustering parameters.
    
    Args:
        algorithm: Algorithm name (KMeans, DBSCAN, Agglomerative)
        params: Algorithm parameters
        quality_threshold: Minimum quality threshold
        
    Returns:
        Dictionary with update result
    """
    logger.info(f"Updating ML parameters: algorithm={algorithm}, threshold={quality_threshold}")
    
    try:
        # Update parameters in ML service
        success = ml_cluster_service.update_optimal_parameters(algorithm, params, quality_threshold)
        
        if success:
            current_params = ml_cluster_service.get_current_parameters()
            logger.info(f"ML parameters updated successfully: {current_params}")
            
            return {
                "status": "success",
                "algorithm": algorithm,
                "parameters": params,
                "quality_threshold": quality_threshold,
                "current_parameters": current_params
            }
        else:
            logger.error(f"Failed to update ML parameters: algorithm={algorithm}")
            return {
                "status": "failed",
                "error": "Failed to update parameters",
                "algorithm": algorithm
            }
            
    except Exception as e:
        logger.error(f"Error updating ML parameters: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "algorithm": algorithm
        }


@celery_app.task(bind=True, name="cluster.generate_monitoring_report")
def generate_monitoring_report(self, course_id: int, days: int = 30) -> Dict[str, Any]:
    """
    Generate comprehensive monitoring report for a course.
    
    Args:
        course_id: Course ID to generate report for
        days: Number of days to look back
        
    Returns:
        Dictionary with monitoring report
    """
    logger.info(f"Generating monitoring report for course: {course_id}, days: {days}")
    
    try:
        with get_db_session() as db:
            # Generate comprehensive monitoring report
            result = ml_cluster_service.get_monitoring_reports(course_id, days, db)
            
            if "error" in result:
                logger.error(f"Monitoring report generation failed for course {course_id}: {result['error']}")
                return {
                    "status": "failed",
                    "error": result["error"],
                    "course_id": course_id
                }
            
            logger.info(f"Monitoring report generated for course {course_id}: {len(result.get('quality_history', []))} quality records, {len(result.get('active_alerts', []))} active alerts")
            
            return {
                "status": "success",
                "course_id": course_id,
                "period_days": days,
                "quality_history_count": len(result.get("quality_history", [])),
                "active_alerts_count": len(result.get("active_alerts", [])),
                "performance_summary": result.get("performance_summary", {}),
                "generated_at": result.get("generated_at")
            }
            
    except Exception as e:
        logger.error(f"Error generating monitoring report: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "course_id": course_id
        }


@celery_app.task(bind=True, name="cluster.check_quality_alerts")
def check_quality_alerts(self) -> Dict[str, Any]:
    """
    Check for quality alerts across all courses.
    
    Returns:
        Dictionary with alert summary
    """
    logger.info("Checking quality alerts across all courses")
    
    try:
        with get_db_session() as db:
            # Get all active alerts
            active_alerts = monitoring_service.get_active_alerts(db=db)
            
            # Group alerts by level
            alert_summary = {
                "critical": 0,
                "error": 0,
                "warning": 0,
                "total": len(active_alerts)
            }
            
            for alert in active_alerts:
                level = alert.get("alert_level", "warning")
                if level in alert_summary:
                    alert_summary[level] += 1
            
            logger.info(f"Quality alert check completed: {alert_summary['total']} total alerts ({alert_summary['critical']} critical, {alert_summary['error']} error, {alert_summary['warning']} warning)")
            
            return {
                "status": "success",
                "alert_summary": alert_summary,
                "active_alerts": active_alerts,
                "checked_at": config_service.now()
            }
            
    except Exception as e:
        logger.error(f"Error checking quality alerts: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


@celery_app.task(bind=True, name="cluster.resolve_alert")
def resolve_alert(self, alert_id: int, resolution_notes: str) -> Dict[str, Any]:
    """
    Resolve a clustering quality alert.
    
    Args:
        alert_id: Alert ID to resolve
        resolution_notes: Notes about how the alert was resolved
        
    Returns:
        Dictionary with resolution result
    """
    logger.info(f"Resolving alert: {alert_id}")
    
    try:
        with get_db_session() as db:
            # Resolve the alert
            success = monitoring_service.resolve_alert(alert_id, resolution_notes, db)
            
            if success:
                logger.info(f"Alert {alert_id} resolved successfully: {resolution_notes}")
                return {
                    "status": "success",
                    "alert_id": alert_id,
                    "resolution_notes": resolution_notes,
                    "resolved_at": config_service.now()
                }
            else:
                logger.error(f"Failed to resolve alert {alert_id}")
                return {
                    "status": "failed",
                    "error": "Failed to resolve alert",
                    "alert_id": alert_id
                }
            
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "alert_id": alert_id
        }


@celery_app.task(bind=True, name="cluster.update_monitoring_thresholds")
def update_monitoring_thresholds(self, thresholds: Dict[str, float]) -> Dict[str, Any]:
    """
    Update monitoring quality thresholds.
    
    Args:
        thresholds: Dictionary with new threshold values
        
    Returns:
        Dictionary with update result
    """
    logger.info(f"Updating monitoring thresholds: {thresholds}")
    
    try:
        # Update thresholds
        success = monitoring_service.update_quality_thresholds(thresholds)
        
        if success:
            current_thresholds = monitoring_service.get_quality_thresholds()
            logger.info(f"Monitoring thresholds updated successfully: {current_thresholds}")
            
            return {
                "status": "success",
                "updated_thresholds": thresholds,
                "current_thresholds": current_thresholds,
                "updated_at": config_service.now()
            }
        else:
            logger.error("Failed to update monitoring thresholds")
            return {
                "status": "failed",
                "error": "Failed to update thresholds"
            }
            
    except Exception as e:
        logger.error(f"Error updating monitoring thresholds: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }
