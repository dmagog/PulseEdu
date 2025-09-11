"""
Tests for API endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint returns 200."""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestStudentEndpoints:
    """Test student-related endpoints."""
    
    def test_student_dashboard(self, client):
        """Test student dashboard endpoint."""
        response = client.get("/student/?student_id=01")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_student_assignments(self, client):
        """Test student assignments endpoint."""
        response = client.get("/student/assignments?student_id=01")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_student_course_details(self, client):
        """Test student course details endpoint."""
        response = client.get("/student/course/1?student_id=01")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestTeacherEndpoints:
    """Test teacher-related endpoints."""
    
    def test_teacher_dashboard(self, client):
        """Test teacher dashboard endpoint."""
        response = client.get("/teacher/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_teacher_students(self, client):
        """Test teacher students endpoint."""
        response = client.get("/teacher/students")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_teacher_courses(self, client):
        """Test teacher courses endpoint."""
        response = client.get("/teacher/courses")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_teacher_course_details(self, client):
        """Test teacher course details endpoint."""
        response = client.get("/teacher/course/1")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestAdminEndpoints:
    """Test admin-related endpoints."""
    
    def test_admin_dashboard(self, client):
        """Test admin dashboard endpoint."""
        response = client.get("/admin/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_admin_users(self, client):
        """Test admin users endpoint."""
        response = client.get("/admin/users")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_admin_students(self, client):
        """Test admin students endpoint."""
        response = client.get("/admin/students")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestClusterEndpoints:
    """Test cluster-related API endpoints."""
    
    def test_cluster_students_api(self, client):
        """Test cluster students API endpoint."""
        response = client.get("/api/cluster/students/1")
        assert response.status_code == 200
        data = response.json()
        assert "clusters" in data
    
    def test_trigger_clustering(self, client):
        """Test trigger clustering endpoint."""
        response = client.post("/api/cluster/trigger-clustering", 
                             json={"course_id": 1})
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestMLMonitoringEndpoints:
    """Test ML monitoring endpoints."""
    
    def test_student_clusters_monitoring(self, client):
        """Test student clusters monitoring endpoint."""
        response = client.get("/api/ml-monitoring/student-clusters")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestHomeEndpoint:
    """Test home page endpoint."""
    
    def test_home_page(self, client):
        """Test home page endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestErrorHandling:
    """Test error handling in endpoints."""
    
    def test_nonexistent_student(self, client):
        """Test handling of nonexistent student."""
        response = client.get("/student/?student_id=nonexistent")
        assert response.status_code == 200  # Should still render page
    
    def test_nonexistent_course(self, client):
        """Test handling of nonexistent course."""
        response = client.get("/student/course/999?student_id=01")
        assert response.status_code == 200  # Should still render page
    
    def test_invalid_course_id(self, client):
        """Test handling of invalid course ID."""
        response = client.get("/student/course/invalid?student_id=01")
        # Should handle gracefully, might return 422 or 200 with error
        assert response.status_code in [200, 422]
