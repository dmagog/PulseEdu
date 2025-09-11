"""
Cluster service for student clustering based on performance metrics.
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.student import Student, Course, Task, Attendance, TaskCompletion
from app.models.cluster import StudentCluster
from app.services.metrics_service import MetricsService
from app.services.config_service import config_service
from app.services.ml_cluster_service import MLClusterService

logger = logging.getLogger("app.cluster")


class ClusterService:
    """Service for clustering students based on performance metrics."""
    
    def __init__(self):
        self.metrics_service = MetricsService()
        self.ml_cluster_service = MLClusterService()
        self.logger = logger
    
    def cluster_students_by_course(self, course_id: int, db: Session, import_job_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Cluster students in a course using ML algorithms.
        
        Delegates to MLClusterService for advanced clustering with multiple algorithms:
        - KMeans clustering
        - DBSCAN clustering  
        - Agglomerative clustering
        
        Args:
            course_id: Course ID to cluster students for
            db: Database session
            import_job_id: Optional import job ID that triggered clustering
            
        Returns:
            Dictionary with clustering results
        """
        try:
            self.logger.info(f"Starting ML clustering for course {course_id}")
            
            # Delegate to ML service
            result = self.ml_cluster_service.cluster_students_by_course(course_id, db, import_job_id)
            
            if "error" not in result:
                self.logger.info(f"ML clustering completed for course {course_id}: {result.get('clustered_students', 0)} students clustered using {result.get('algorithm_used', 'Unknown')}")
            else:
                self.logger.error(f"ML clustering failed for course {course_id}: {result['error']}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in ML clustering for course {course_id}: {e}")
            return {"error": str(e)}
    
    def cluster_all_courses(self, db: Session, import_job_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Cluster students for all courses using ML algorithms.
        
        Args:
            db: Database session
            import_job_id: Optional import job ID that triggered clustering
            
        Returns:
            Dictionary with clustering results for all courses
        """
        try:
            self.logger.info("Starting ML clustering for all courses")
            
            # Delegate to ML service
            result = self.ml_cluster_service.cluster_all_courses(db, import_job_id)
            
            if "error" not in result:
                self.logger.info(f"ML clustering completed for all courses: {result.get('total_clustered', 0)} students clustered across {result.get('successful_courses', 0)} courses")
            else:
                self.logger.error(f"ML clustering failed for all courses: {result['error']}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in ML clustering for all courses: {e}")
            return {"error": str(e)}
    
    def get_student_cluster(self, student_id: str, course_id: int, db: Session) -> Optional[StudentCluster]:
        """
        Get cluster assignment for a specific student in a course.
        
        Args:
            student_id: Student ID
            course_id: Course ID
            db: Database session
            
        Returns:
            StudentCluster object or None if not found
        """
        try:
            cluster = db.query(StudentCluster).filter(
                and_(
                    StudentCluster.student_id == student_id,
                    StudentCluster.course_id == course_id
                )
            ).first()
            
            return cluster
            
        except Exception as e:
            self.logger.error(f"Error getting student cluster: {e}")
            return None
    
    def get_course_clusters(self, course_id: int, db: Session) -> List[StudentCluster]:
        """
        Get all cluster assignments for a course.
        
        Args:
            course_id: Course ID
            db: Database session
            
        Returns:
            List of StudentCluster objects
        """
        try:
            clusters = db.query(StudentCluster).filter(
                StudentCluster.course_id == course_id
            ).all()
            
            return clusters
            
        except Exception as e:
            self.logger.error(f"Error getting course clusters: {e}")
            return []
    
    def get_clustering_quality_report(self, course_id: int, db: Session) -> Dict[str, Any]:
        """
        Get quality report for clustering results.
        
        Args:
            course_id: Course ID
            db: Database session
            
        Returns:
            Dictionary with clustering quality metrics
        """
        try:
            return self.ml_cluster_service.get_clustering_quality_report(course_id, db)
        except Exception as e:
            self.logger.error(f"Error getting clustering quality report: {e}")
            return {"error": str(e)}
    
    def _extract_student_features(self, student_id: str, course_id: int, db: Session) -> Optional[Dict[str, float]]:
        """Extract features for clustering a student."""
        try:
            # Get student progress
            progress = self.metrics_service.calculate_student_progress(student_id, db)
            
            if "error" in progress:
                return None
            
            # Extract course-specific data
            course_data = None
            if "courses" in progress:
                course_data = next((c for c in progress["courses"] if c["course_name"] == db.query(Course).filter(Course.id == course_id).first().name), None)
            
            if not course_data:
                return None
            
            # Extract features
            attendance_rate = course_data.get("attendance_progress", 0)
            completion_rate = course_data.get("task_progress", 0)
            overall_progress = progress.get("overall_progress", 0)
            
            return {
                "attendance_rate": attendance_rate,
                "completion_rate": completion_rate,
                "overall_progress": overall_progress
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting features for student {student_id}: {e}")
            return None
    
    def _kiss_clustering(self, student_features: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        KISS clustering algorithm using simple thresholds.
        
        Clusters students into 3 groups:
        - A: High performers (attendance > 70% AND completion > 60% AND overall > 70%)
        - B: Medium performers (attendance > 50% OR completion > 40% OR overall > 50%)
        - C: Low performers (everything else)
        """
        try:
            clusters = {"A": [], "B": [], "C": []}
            
            for student_data in student_features:
                features = student_data["features"]
                attendance = features["attendance_rate"]
                completion = features["completion_rate"]
                overall = features["overall_progress"]
                
                # Determine cluster based on simple rules
                if (attendance > 70 and completion > 60 and overall > 70):
                    cluster_label = "A"
                elif (attendance > 50 or completion > 40 or overall > 50):
                    cluster_label = "B"
                else:
                    cluster_label = "C"
                
                # Calculate confidence score (simple average of normalized features)
                confidence = (attendance + completion + overall) / 300  # Normalize to 0-1
                
                clusters[cluster_label].append({
                    "student_id": student_data["student_id"],
                    "attendance_rate": attendance,
                    "completion_rate": completion,
                    "overall_progress": overall,
                    "cluster_score": confidence
                })
            
            return clusters
            
        except Exception as e:
            self.logger.error(f"Error in KISS clustering: {e}")
            return {"A": [], "B": [], "C": []}
    
    def _save_cluster_assignments(self, course_id: int, clusters: Dict[str, List[Dict[str, Any]]], 
                                 db: Session, import_job_id: Optional[str] = None) -> List[StudentCluster]:
        """Save cluster assignments to database."""
        try:
            saved_clusters = []
            
            # Clear existing clusters for this course
            db.query(StudentCluster).filter(StudentCluster.course_id == course_id).delete()
            
            # Save new cluster assignments
            for cluster_label, students in clusters.items():
                for student_data in students:
                    cluster = StudentCluster(
                        student_id=student_data["student_id"],
                        course_id=course_id,
                        cluster_label=cluster_label,
                        cluster_score=student_data["cluster_score"],
                        attendance_rate=student_data["attendance_rate"],
                        completion_rate=student_data["completion_rate"],
                        overall_progress=student_data["overall_progress"],
                        import_job_id=import_job_id,
                        created_at=config_service.now(),
                        updated_at=config_service.now()
                    )
                    
                    db.add(cluster)
                    saved_clusters.append(cluster)
            
            db.commit()
            return saved_clusters
            
        except Exception as e:
            self.logger.error(f"Error saving cluster assignments: {e}")
            db.rollback()
            return []
    
    def _summarize_clusters(self, clusters: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Summarize clustering results."""
        try:
            summary = {}
            
            for cluster_label, students in clusters.items():
                if students:
                    avg_attendance = sum(s["attendance_rate"] for s in students) / len(students)
                    avg_completion = sum(s["completion_rate"] for s in students) / len(students)
                    avg_overall = sum(s["overall_progress"] for s in students) / len(students)
                    avg_confidence = sum(s["cluster_score"] for s in students) / len(students)
                    
                    summary[cluster_label] = {
                        "count": len(students),
                        "avg_attendance": avg_attendance,
                        "avg_completion": avg_completion,
                        "avg_overall": avg_overall,
                        "avg_confidence": avg_confidence
                    }
                else:
                    summary[cluster_label] = {
                        "count": 0,
                        "avg_attendance": 0,
                        "avg_completion": 0,
                        "avg_overall": 0,
                        "avg_confidence": 0
                    }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error summarizing clusters: {e}")
            return {}
