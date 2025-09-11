"""
ML-based clustering service for student clustering using scikit-learn.
"""
import logging
import pickle
import time
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, calinski_harabasz_score
from sklearn.model_selection import ParameterGrid

from app.models.student import Student, Course, Task, Attendance, TaskCompletion
from app.models.cluster import StudentCluster
from app.services.metrics_service import MetricsService
from app.services.config_service import config_service
from app.services.ml_monitoring_service import MLMonitoringService

logger = logging.getLogger("app.ml_cluster")


class MLClusterService:
    """ML-based service for clustering students using scikit-learn algorithms."""
    
    def __init__(self):
        self.metrics_service = MetricsService()
        self.monitoring_service = MLMonitoringService()
        self.logger = logger
        self.scaler = StandardScaler()
        self.models = {}
        self.cluster_quality_metrics = {}
        
        # Unified ML clustering solution - KMeans with optimal parameters
        self.algorithm = "KMeans"
        self.params = {
            "n_clusters": 3,
            "random_state": 42,
            "n_init": 10,
            "max_iter": 300
        }
        self.quality_threshold = 0.3  # Minimum silhouette score to accept
    
    def cluster_students_by_course(self, course_id: int, db: Session, import_job_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Cluster students in a course using unified ML solution.
        
        Uses KMeans clustering with optimal parameters:
        - n_clusters=3 for risk zones (A, B, C)
        - StandardScaler for feature normalization
        - Quality metrics tracking and monitoring
        
        Args:
            course_id: Course ID to cluster students for
            db: Database session
            import_job_id: Optional import job ID that triggered clustering
            
        Returns:
            Dictionary with clustering results
        """
        try:
            self.logger.info(f"Starting ML clustering for course {course_id}")
            
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
            
            if len(student_features) < 3:
                # Fallback to simple clustering for small datasets
                return self._simple_clustering_fallback(student_features, course_id, db, import_job_id)
            
            # Perform ML clustering with predefined optimal parameters
            start_time = time.time()
            best_clusters, best_algorithm, quality_metrics = self._optimized_ml_clustering(student_features)
            processing_time = time.time() - start_time
            
            # Save cluster assignments
            saved_clusters = self._save_cluster_assignments(
                course_id, best_clusters, db, import_job_id, best_algorithm, quality_metrics
            )
            
            # Record metrics for monitoring
            clustering_results = {
                "total_students": len(students),
                "clustered_students": len(saved_clusters)
            }
            
            self.monitoring_service.record_clustering_metrics(
                course_id=course_id,
                algorithm_used=best_algorithm,
                algorithm_params=quality_metrics.get("parameters", {}),
                quality_metrics=quality_metrics,
                clustering_results=clustering_results,
                processing_time=processing_time,
                db=db,
                import_job_id=import_job_id
            )
            
            result = {
                "course_id": course_id,
                "course_name": course.name,
                "total_students": len(students),
                "clustered_students": len(saved_clusters),
                "algorithm_used": best_algorithm,
                "quality_metrics": quality_metrics,
                "clusters": self._summarize_clusters(best_clusters),
                "import_job_id": import_job_id,
                "clustered_at": config_service.now()
            }
            
            self.logger.info(f"ML clustering completed for course {course_id}: {len(saved_clusters)} students clustered using {best_algorithm}")
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
            
            # Get all courses
            courses = db.query(Course).all()
            
            results = []
            total_students = 0
            total_clustered = 0
            algorithm_summary = {}
            
            for course in courses:
                course_result = self.cluster_students_by_course(course.id, db, import_job_id)
                if "error" not in course_result:
                    results.append(course_result)
                    total_students += course_result["total_students"]
                    total_clustered += course_result["clustered_students"]
                    
                    # Track algorithm usage
                    algorithm = course_result.get("algorithm_used", "unknown")
                    algorithm_summary[algorithm] = algorithm_summary.get(algorithm, 0) + 1
                else:
                    self.logger.warning(f"Failed to cluster course {course.id}: {course_result['error']}")
            
            return {
                "total_courses": len(courses),
                "successful_courses": len(results),
                "total_students": total_students,
                "total_clustered": total_clustered,
                "algorithm_summary": algorithm_summary,
                "course_results": results,
                "import_job_id": import_job_id,
                "clustered_at": config_service.now()
            }
            
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
    
    def _extract_student_features(self, student_id: str, course_id: int, db: Session) -> Optional[Dict[str, float]]:
        """Extract features for ML clustering a student."""
        try:
            # Get student progress
            progress = self.metrics_service.calculate_student_progress(student_id, db)
            
            if "error" in progress:
                return None
            
            # Extract course-specific data
            course = db.query(Course).filter(Course.id == course_id).first()
            if not course:
                return None
                
            course_data = None
            if "courses" in progress:
                course_data = next((c for c in progress["courses"] if c["course_name"] == course.name), None)
            
            if not course_data:
                return None
            
            # Extract comprehensive features for ML
            attendance_rate = course_data.get("attendance_progress", 0)
            completion_rate = course_data.get("task_progress", 0)
            overall_progress = progress.get("overall_progress", 0)
            
            # Additional features for better clustering
            task_count = course_data.get("task_count", 0)
            completed_tasks = course_data.get("completed_tasks", 0)
            late_submissions = course_data.get("late_submissions", 0)
            average_score = course_data.get("average_score", 0)
            
            # Calculate derived features
            task_completion_ratio = completed_tasks / max(task_count, 1)
            punctuality_score = max(0, 100 - (late_submissions * 10))  # Penalty for late submissions
            performance_consistency = min(attendance_rate, completion_rate, overall_progress)  # Minimum of key metrics
            
            return {
                "attendance_rate": attendance_rate,
                "completion_rate": completion_rate,
                "overall_progress": overall_progress,
                "task_completion_ratio": task_completion_ratio,
                "punctuality_score": punctuality_score,
                "performance_consistency": performance_consistency,
                "average_score": average_score
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting features for student {student_id}: {e}")
            return None
    
    def _optimized_ml_clustering(self, student_features: List[Dict[str, Any]]) -> Tuple[Dict[str, List[Dict[str, Any]]], str, Dict[str, float]]:
        """
        Perform optimized ML clustering using predefined parameters.
        
        Uses the optimal algorithm and parameters determined through testing.
        Falls back to alternative algorithms only if quality is below threshold.
        
        Returns:
            Tuple of (best_clusters, best_algorithm, quality_metrics)
        """
        try:
            # Prepare feature matrix
            feature_matrix = np.array([list(student["features"].values()) for student in student_features])
            feature_names = list(student_features[0]["features"].keys())
            
            # Normalize features
            feature_matrix_scaled = self.scaler.fit_transform(feature_matrix)
            
            # Try optimal algorithm first
            try:
                model = KMeans(**self.optimal_params)
                cluster_labels = model.fit_predict(feature_matrix_scaled)
                
                # Calculate quality metrics
                if len(set(cluster_labels)) > 1:
                    silhouette = silhouette_score(feature_matrix_scaled, cluster_labels)
                    calinski_harabasz = calinski_harabasz_score(feature_matrix_scaled, cluster_labels)
                    
                    # Check if quality meets threshold
                    if silhouette >= self.quality_threshold:
                        self.logger.info(f"Optimal algorithm {self.optimal_algorithm} achieved quality {silhouette:.3f}")
                        
                        quality_metrics = {
                            "silhouette_score": silhouette,
                            "calinski_harabasz_score": calinski_harabasz,
                            "combined_score": 0.7 * silhouette + 0.3 * (calinski_harabasz / 1000),
                            "n_clusters": len(set(cluster_labels)),
                            "parameters": self.optimal_params,
                            "algorithm": self.optimal_algorithm
                        }
                        
                        clusters = self._convert_to_cluster_format(
                            student_features, cluster_labels, feature_matrix, feature_names
                        )
                        
                        return clusters, f"{self.optimal_algorithm}_optimal", quality_metrics
                    else:
                        self.logger.warning(f"Optimal algorithm quality {silhouette:.3f} below threshold {self.quality_threshold}")
                else:
                    self.logger.warning("Optimal algorithm produced single cluster")
                    
            except Exception as e:
                self.logger.warning(f"Optimal algorithm failed: {e}")
            
            # Fallback to alternative algorithms if optimal fails
            self.logger.info("Trying alternative algorithms...")
            return self._fallback_ml_clustering(student_features, feature_matrix_scaled)
            
        except Exception as e:
            self.logger.error(f"Error in optimized ML clustering: {e}")
            return self._simple_clustering_fallback(student_features, None, None, None)
    
    def _fallback_ml_clustering(self, student_features: List[Dict[str, Any]], feature_matrix_scaled: np.ndarray) -> Tuple[Dict[str, List[Dict[str, Any]]], str, Dict[str, float]]:
        """
        Fallback ML clustering with alternative algorithms.
        
        Returns:
            Tuple of (best_clusters, best_algorithm, quality_metrics)
        """
        try:
            feature_matrix = np.array([list(student["features"].values()) for student in student_features])
            feature_names = list(student_features[0]["features"].keys())
            
            # Alternative algorithms with simpler parameters
            fallback_algorithms = [
                {
                    "name": "KMeans_Simple",
                    "model": KMeans,
                    "params": {"n_clusters": 3, "random_state": 42, "n_init": 5}
                },
                {
                    "name": "Agglomerative_Simple", 
                    "model": AgglomerativeClustering,
                    "params": {"n_clusters": 3, "linkage": "ward"}
                },
                {
                    "name": "DBSCAN_Simple",
                    "model": DBSCAN,
                    "params": {"eps": 0.5, "min_samples": 2}
                }
            ]
            
            best_score = -1
            best_clusters = None
            best_algorithm = "KMeans_Simple"
            best_quality_metrics = {}
            
            for algo_config in fallback_algorithms:
                try:
                    model = algo_config["model"](**algo_config["params"])
                    cluster_labels = model.fit_predict(feature_matrix_scaled)
                    
                    # Skip if all points are in one cluster or noise
                    unique_labels = set(cluster_labels)
                    if len(unique_labels) < 2 or (algo_config["name"].startswith("DBSCAN") and -1 in unique_labels and len(unique_labels) == 2):
                        continue
                    
                    # Calculate quality metrics
                    if len(unique_labels) > 1:
                        silhouette = silhouette_score(feature_matrix_scaled, cluster_labels)
                        calinski_harabasz = calinski_harabasz_score(feature_matrix_scaled, cluster_labels)
                        combined_score = 0.7 * silhouette + 0.3 * (calinski_harabasz / 1000)
                        
                        if combined_score > best_score:
                            best_score = combined_score
                            best_algorithm = algo_config["name"]
                            best_quality_metrics = {
                                "silhouette_score": silhouette,
                                "calinski_harabasz_score": calinski_harabasz,
                                "combined_score": combined_score,
                                "n_clusters": len(unique_labels),
                                "parameters": algo_config["params"],
                                "algorithm": algo_config["name"]
                            }
                            
                            best_clusters = self._convert_to_cluster_format(
                                student_features, cluster_labels, feature_matrix, feature_names
                            )
                            
                except Exception as e:
                    self.logger.warning(f"Fallback algorithm {algo_config['name']} failed: {e}")
                    continue
            
            if best_clusters is None:
                self.logger.warning("All fallback algorithms failed, using simple clustering")
                return self._simple_clustering_fallback(student_features, None, None, None)
            
            self.logger.info(f"Fallback algorithm {best_algorithm} achieved quality {best_quality_metrics.get('silhouette_score', 0):.3f}")
            return best_clusters, best_algorithm, best_quality_metrics
            
        except Exception as e:
            self.logger.error(f"Error in fallback ML clustering: {e}")
            return self._simple_clustering_fallback(student_features, None, None, None)
    
    def _ml_clustering(self, student_features: List[Dict[str, Any]]) -> Tuple[Dict[str, List[Dict[str, Any]]], str, Dict[str, float]]:
        """
        Perform ML clustering using unified KMeans solution.
        
        Returns:
            Tuple of (clusters, algorithm_name, quality_metrics)
        """
        try:
            # Prepare feature matrix
            feature_matrix = np.array([list(student["features"].values()) for student in student_features])
            feature_names = list(student_features[0]["features"].keys())
            
            # Normalize features
            feature_matrix_scaled = self.scaler.fit_transform(feature_matrix)
            
            # Use unified KMeans solution
            model = KMeans(**self.params)
            cluster_labels = model.fit_predict(feature_matrix_scaled)
            
            # Calculate quality metrics
            unique_labels = set(cluster_labels)
            if len(unique_labels) > 1:
                silhouette = silhouette_score(feature_matrix_scaled, cluster_labels)
                calinski_harabasz = calinski_harabasz_score(feature_matrix_scaled, cluster_labels)
                
                # Combined score (weighted average)
                combined_score = 0.7 * silhouette + 0.3 * (calinski_harabasz / 1000)  # Normalize CH score
                
                quality_metrics = {
                    "silhouette_score": silhouette,
                    "calinski_harabasz_score": calinski_harabasz,
                    "combined_score": combined_score,
                    "n_clusters": len(unique_labels),
                    "parameters": self.params
                }
                
                # Convert to our cluster format
                clusters = self._convert_to_cluster_format(
                    student_features, cluster_labels, feature_matrix, feature_names
                )
                
                return clusters, self.algorithm, quality_metrics
            else:
                self.logger.warning("KMeans produced only one cluster, using simple fallback")
                return self._simple_clustering_fallback(student_features, None, None, None)
            
        except Exception as e:
            self.logger.error(f"Error in ML clustering: {e}")
            return self._simple_clustering_fallback(student_features, None, None, None)
    
    def _convert_to_cluster_format(self, student_features: List[Dict[str, Any]], cluster_labels: np.ndarray, 
                                 feature_matrix: np.ndarray, feature_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Convert ML clustering results to our standard format with A, B, C risk zones."""
        try:
            clusters = {"A": [], "B": [], "C": []}
            
            # Group students by cluster label
            cluster_groups = {}
            for i, (student_data, label) in enumerate(zip(student_features, cluster_labels)):
                if label not in cluster_groups:
                    cluster_groups[label] = []
                cluster_groups[label].append(student_data)
            
            # Calculate average performance for each cluster to assign risk zones
            cluster_performance = {}
            for label, students in cluster_groups.items():
                if students:
                    avg_attendance = sum(s["features"]["attendance_rate"] for s in students) / len(students)
                    avg_completion = sum(s["features"]["completion_rate"] for s in students) / len(students)
                    avg_progress = sum(s["features"]["overall_progress"] for s in students) / len(students)
                    cluster_performance[label] = (avg_attendance + avg_completion + avg_progress) / 3
            
            # Sort clusters by performance and assign risk zones
            sorted_clusters = sorted(cluster_performance.items(), key=lambda x: x[1], reverse=True)
            risk_zones = ["A", "B", "C"]
            
            for i, (label, performance) in enumerate(sorted_clusters):
                risk_zone = risk_zones[i] if i < len(risk_zones) else "C"
                
                for student_data in cluster_groups[label]:
                    features = student_data["features"]
                    confidence = min(1.0, max(0.0, (features["attendance_rate"] + features["completion_rate"] + features["overall_progress"]) / 300))
                    
                    clusters[risk_zone].append({
                        "student_id": student_data["student_id"],
                        "attendance_rate": features["attendance_rate"],
                        "completion_rate": features["completion_rate"],
                        "overall_progress": features["overall_progress"],
                        "cluster_score": confidence,
                        "ml_features": features
                    })
            
            return clusters
            
        except Exception as e:
            self.logger.error(f"Error converting to cluster format: {e}")
            return {"A": [], "B": [], "C": []}
    
    def _simple_clustering_fallback(self, student_features: List[Dict[str, Any]], course_id: Optional[int], 
                                  db: Optional[Session], import_job_id: Optional[str]) -> Dict[str, Any]:
        """Fallback to simple clustering when ML fails."""
        try:
            # Simple rule-based clustering as fallback
            clusters = {"A": [], "B": [], "C": []}
            
            for student_data in student_features:
                features = student_data["features"]
                attendance = features["attendance_rate"]
                completion = features["completion_rate"]
                overall = features["overall_progress"]
                
                # Simple rules
                if (attendance > 70 and completion > 60 and overall > 70):
                    cluster_label = "A"
                elif (attendance > 50 or completion > 40 or overall > 50):
                    cluster_label = "B"
                else:
                    cluster_label = "C"
                
                confidence = (attendance + completion + overall) / 300
                
                clusters[cluster_label].append({
                    "student_id": student_data["student_id"],
                    "attendance_rate": attendance,
                    "completion_rate": completion,
                    "overall_progress": overall,
                    "cluster_score": confidence
                })
            
            if course_id and db:
                saved_clusters = self._save_cluster_assignments(
                    course_id, clusters, db, import_job_id, "Simple_Fallback", {}
                )
                
                return {
                    "course_id": course_id,
                    "total_students": len(student_features),
                    "clustered_students": len(saved_clusters),
                    "algorithm_used": "Simple_Fallback",
                    "quality_metrics": {"fallback": True},
                    "clusters": self._summarize_clusters(clusters),
                    "import_job_id": import_job_id,
                    "clustered_at": config_service.now()
                }
            else:
                return clusters
                
        except Exception as e:
            self.logger.error(f"Error in simple clustering fallback: {e}")
            return {"A": [], "B": [], "C": []}
    
    def _save_cluster_assignments(self, course_id: int, clusters: Dict[str, List[Dict[str, Any]]], 
                                 db: Session, import_job_id: Optional[str] = None, 
                                 algorithm: str = "ML", quality_metrics: Dict[str, Any] = None) -> List[StudentCluster]:
        """Save cluster assignments to database with ML metadata."""
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
                    
                    # Add ML-specific metadata if available
                    if "ml_features" in student_data:
                        # Store additional ML features as JSON
                        import json
                        cluster.ml_metadata = json.dumps({
                            "algorithm": algorithm,
                            "quality_metrics": quality_metrics or {},
                            "features": student_data["ml_features"]
                        })
                    
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
    
    def get_clustering_quality_report(self, course_id: int, db: Session) -> Dict[str, Any]:
        """Get quality report for clustering results."""
        try:
            clusters = self.get_course_clusters(course_id, db)
            
            if not clusters:
                return {"error": "No clusters found for this course"}
            
            # Analyze cluster quality
            cluster_analysis = {}
            for cluster in clusters:
                if cluster.ml_metadata:
                    import json
                    metadata = json.loads(cluster.ml_metadata)
                    algorithm = metadata.get("algorithm", "Unknown")
                    quality_metrics = metadata.get("quality_metrics", {})
                    
                    if algorithm not in cluster_analysis:
                        cluster_analysis[algorithm] = {
                            "count": 0,
                            "quality_metrics": quality_metrics
                        }
                    cluster_analysis[algorithm]["count"] += 1
            
            return {
                "course_id": course_id,
                "total_clusters": len(clusters),
                "cluster_analysis": cluster_analysis,
                "generated_at": config_service.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating quality report: {e}")
            return {"error": str(e)}
    
    def update_optimal_parameters(self, algorithm: str = "KMeans", params: Dict[str, Any] = None, 
                                quality_threshold: float = 0.3) -> bool:
        """
        Update optimal clustering parameters.
        
        Args:
            algorithm: Algorithm name (KMeans, DBSCAN, Agglomerative)
            params: Algorithm parameters
            quality_threshold: Minimum quality threshold
            
        Returns:
            True if parameters updated successfully
        """
        try:
            if params is None:
                if algorithm == "KMeans":
                    params = {"n_clusters": 3, "random_state": 42, "n_init": 10, "max_iter": 300}
                elif algorithm == "DBSCAN":
                    params = {"eps": 0.5, "min_samples": 2}
                elif algorithm == "Agglomerative":
                    params = {"n_clusters": 3, "linkage": "ward"}
                else:
                    self.logger.error(f"Unknown algorithm: {algorithm}")
                    return False
            
            self.optimal_algorithm = algorithm
            self.optimal_params = params
            self.quality_threshold = quality_threshold
            
            self.logger.info(f"Updated optimal parameters: {algorithm} with {params}, threshold: {quality_threshold}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating optimal parameters: {e}")
            return False
    
    def get_current_parameters(self) -> Dict[str, Any]:
        """Get current optimal parameters."""
        return {
            "algorithm": self.optimal_algorithm,
            "parameters": self.optimal_params,
            "quality_threshold": self.quality_threshold
        }
    
    def get_monitoring_reports(self, course_id: int, days: int = 30, db: Session = None) -> Dict[str, Any]:
        """
        Get comprehensive monitoring reports for a course.
        
        Args:
            course_id: Course ID
            days: Number of days to look back
            db: Database session
            
        Returns:
            Dictionary with monitoring reports
        """
        try:
            if db is None:
                from app.database.session import get_session
                db = next(get_session())
            
            # Get quality history
            quality_history = self.monitoring_service.get_course_quality_history(course_id, days, db)
            
            # Get active alerts
            active_alerts = self.monitoring_service.get_active_alerts(course_id, db)
            
            # Get algorithm performance summary
            performance_summary = self.monitoring_service.get_algorithm_performance_summary(days, db)
            
            return {
                "course_id": course_id,
                "period_days": days,
                "quality_history": quality_history,
                "active_alerts": active_alerts,
                "performance_summary": performance_summary,
                "generated_at": config_service.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting monitoring reports: {e}")
            return {"error": str(e)}
