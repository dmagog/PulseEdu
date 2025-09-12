"""
Tests for health check endpoint.
"""


def test_health_check(client):
    """Test health check endpoint returns correct response."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    # Health endpoint returns service info, not just {"status": "ok"}
    assert "service" in data
    assert data["service"] == "PulseEdu"


def test_health_check_content_type(client):
    """Test health check endpoint returns JSON."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
