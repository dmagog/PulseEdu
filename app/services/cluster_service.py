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

logger = logging.getLogger("app.cluster")


class ClusterService:
    """Service for clustering students based on performance metrics."""
    
    def __init__(self):
        self.metrics_service = MetricsService()
        self.logger = logger
    
    def cluster_students_by_course(self, course_id: int, db: Session, import_job_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Cluster students in a course based on performance metrics.
        
        Uses KISS approach with 2-3 features:
        - Attendance rate
        - Task completion rate
        - Overall progress
        
        Args:
            course_id: Course ID to cluster students for
            db: Database session
            import_job_id: Optional import job ID that triggered clustering
            
        Returns:
            Dictionary with clustering results
        """
        try:
            self.logger.info(f"Starting clustering for course {course_id}")
            
            # Get course
            course = db.query(Course).filter(Course.id == course_id).first()
            if not course:
                return {"error": f"Course {course_id} not found"}
            
            # Get students in course
            students = db.query(Student).join(TaskCompletion).filter(
                TaskCompletion.course_id == course_id
            ).distinct().all()
            
            if not students:
                return {"error": f"No students found in course {course_id}"}
            
            # Collect features for clustering
            student_features = []
            for student in students:
                features = self._extract_student_features(student.id, course_id, db)
                if features:
                    student_features.append({
                        "student_id": student.id,
                        "features": features
                    })
            
            if not student_features:
                return {"error": "No valid student features found"}
            
            # Perform KISS clustering
            clusters = self._kiss_clustering(student_features)
            
            # Save cluster assignments
            saved_clusters = self._save_cluster_assignments(
                course_id, clusters, db, import_job_id
            )
            
            result = {
                "course_id": course_id,
                "course_name": course.name,
                "total_students": len(students),
                "clustered_students": len(saved_clusters),
                "clusters": self._summarize_clusters(clusters),
                "import_job_id": import_job_id,
                "clustered_at": config_service.now()
            }
            
            self.logger.info(f"Clustering completed for course {course_id}: {len(saved_clusters)} students clustered")
            return result
            
        except Exception as e:
            self.logger.error(f"Error clustering students for course {course_id}: {e}")
            return {"error": str(e)}
    
    def cluster_all_courses(self, db: Session, import_job_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Cluster students for all courses.
        
        Args:
            db: Database session
            import_job_id: Optional import job ID that triggered clustering
            
        Returns:
            Dictionary with clustering results for all courses
        """
        try:
            self.logger.info("Starting clustering for all courses")
            
            # Get all courses
            courses = db.query(Course).all()
            
            results = []
            total_students = 0
            total_clustered = 0
            
            for course in courses:
                course_result = self.cluster_students_by_course(course.id, db, import_job_id)
                if "error" not in course_result:
                    results.append(course_result)
                    total_students += course_result["total_students"]
                    total_clustered += course_result["clustered_students"]
                else:
                    self.logger.warning(f"Failed to cluster course {course.id}: {course_result['error']}")
            
            return {
                "total_courses": len(courses),
                "successful_courses": len(results),
                "total_students": total_students,
                "total_clustered": total_clustered,
                "course_results": results,
                "import_job_id": import_job_id,
                "clustered_at": config_service.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error clustering all courses: {e}")
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
