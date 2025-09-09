"""
Celery tasks for student clustering.
"""
import logging
from typing import Dict, Any

from celery import Celery
from app.database.session import get_db_session
from app.services.cluster_service import ClusterService
from worker.celery_app import celery_app

logger = logging.getLogger("worker.cluster_tasks")
cluster_service = ClusterService()


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
