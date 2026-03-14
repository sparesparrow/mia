"""
Contract tests verifying RPi API response shapes match what Android expects.
Uses FastAPI TestClient to test endpoints without a running server.
"""
import sys
import os
import pytest

# Add py-api to path so we can import the app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'apps', 'rpi-backend', 'py-api'))

from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestDevicesContract:
    """GET /devices must return {devices: [...], count: int, timestamp: str}."""

    def test_list_devices_shape(self, client):
        resp = client.get("/devices")
        assert resp.status_code == 200
        body = resp.json()
        assert "devices" in body
        assert isinstance(body["devices"], list)
        assert "count" in body
        assert isinstance(body["count"], int)
        assert "timestamp" in body

    def test_get_device_alias_404(self, client):
        resp = client.get("/devices/nonexistent-device")
        assert resp.status_code in (404, 503)

    def test_delete_device_alias_404(self, client):
        resp = client.delete("/devices/nonexistent-device")
        assert resp.status_code in (404, 503)


class TestCommandContract:
    """POST /command accepts both 'device' and 'device_id' fields."""

    def test_command_with_device_field(self, client):
        resp = client.post("/command", json={
            "device": "test-device",
            "action": "ping"
        })
        # May timeout on ZMQ but should not be a 422 validation error
        assert resp.status_code != 422

    def test_command_with_device_id_field(self, client):
        resp = client.post("/command", json={
            "device_id": "test-device",
            "action": "ping"
        })
        assert resp.status_code != 422

    def test_command_without_device_rejects(self, client):
        resp = client.post("/command", json={
            "action": "ping"
        })
        assert resp.status_code == 422


class TestStatusContract:
    """GET /status must return nested memory/cpu structure."""

    def test_status_shape(self, client):
        resp = client.get("/status")
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body
        assert "uptime_seconds" in body
        assert "memory" in body
        assert isinstance(body["memory"], dict)
        assert "cpu" in body
        assert isinstance(body["cpu"], dict)
        assert "timestamp" in body


class TestSessionLifecycle:
    """Session CRUD + handoff/resume flow."""

    def test_create_session(self, client):
        resp = client.post("/sessions", json={
            "client_type": "android",
            "client_name": "Test Phone"
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "session" in body
        session = body["session"]
        assert "session_id" in session
        assert session["client_type"] == "android"
        assert session["client_name"] == "Test Phone"

    def test_get_session(self, client):
        # Create first
        create_resp = client.post("/sessions", json={
            "client_type": "android",
            "client_name": "Test Phone"
        })
        sid = create_resp.json()["session"]["session_id"]

        resp = client.get(f"/sessions/{sid}")
        assert resp.status_code == 200
        assert resp.json()["session"]["session_id"] == sid

    def test_update_session_subscriptions(self, client):
        create_resp = client.post("/sessions", json={
            "client_type": "android",
            "client_name": "Test Phone"
        })
        sid = create_resp.json()["session"]["session_id"]

        resp = client.patch(f"/sessions/{sid}", json={
            "device_subscriptions": ["esp32-obd-001", "pi-gateway-001"]
        })
        assert resp.status_code == 200
        assert resp.json()["session"]["device_subscriptions"] == [
            "esp32-obd-001", "pi-gateway-001"
        ]

    def test_handoff_and_resume(self, client):
        # Create session
        create_resp = client.post("/sessions", json={
            "client_type": "android",
            "client_name": "Phone"
        })
        sid = create_resp.json()["session"]["session_id"]

        # Generate handoff token
        handoff_resp = client.post(f"/sessions/{sid}/handoff")
        assert handoff_resp.status_code == 200
        token = handoff_resp.json()["handoff_token"]
        assert handoff_resp.json()["expires_in_seconds"] == 300

        # Resume with token
        resume_resp = client.post("/sessions/resume", json={
            "handoff_token": token
        })
        assert resume_resp.status_code == 200
        assert resume_resp.json()["session"]["session_id"] == sid

        # Token is consumed — second resume fails
        resume_resp2 = client.post("/sessions/resume", json={
            "handoff_token": token
        })
        assert resume_resp2.status_code == 401

    def test_delete_session(self, client):
        create_resp = client.post("/sessions", json={
            "client_type": "web",
            "client_name": "Dashboard"
        })
        sid = create_resp.json()["session"]["session_id"]

        resp = client.delete(f"/sessions/{sid}")
        assert resp.status_code == 200

        # Should be gone
        resp2 = client.get(f"/sessions/{sid}")
        assert resp2.status_code == 404

    def test_get_nonexistent_session(self, client):
        resp = client.get("/sessions/nonexistent-id")
        assert resp.status_code == 404

    def test_resume_invalid_token(self, client):
        resp = client.post("/sessions/resume", json={
            "handoff_token": "invalid-token-123"
        })
        assert resp.status_code == 401
