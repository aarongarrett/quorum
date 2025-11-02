"""Integration tests for meetings API."""
import pytest
from datetime import datetime, timezone, timedelta


@pytest.mark.integration
class TestMeetingCreation:
    """Test meeting creation endpoint."""

    def test_create_meeting_success(self, admin_client):
        """Admin should be able to create meeting."""
        start_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        end_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

        response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": start_time,
                "end_time": end_time
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "meeting_id" in data
        assert "meeting_code" in data
        assert len(data["meeting_code"]) == 8

    def test_create_meeting_unauthorized(self, client):
        """Non-admin should not be able to create meeting."""
        start_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        end_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

        response = client.post(
            "/api/v1/meetings",
            json={
                "start_time": start_time,
                "end_time": end_time
            }
        )

        assert response.status_code == 401

    def test_create_meeting_invalid_times(self, admin_client):
        """End time before start time should fail."""
        start_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        end_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": start_time,
                "end_time": end_time
            }
        )

        assert response.status_code == 400


@pytest.mark.integration
class TestGetAvailableMeetings:
    """Test available meetings endpoint."""

    def test_get_available_meetings_empty(self, client):
        """Should return empty list when no meetings."""
        response = client.post(
            "/api/v1/meetings/available",
            json={}
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_get_available_meetings_with_meeting(self, client, admin_client):
        """Should return available meetings."""
        # Create a meeting
        start_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        end_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        create_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": start_time,
                "end_time": end_time
            }
        )
        assert create_response.status_code == 200

        # Get available meetings
        response = client.post(
            "/api/v1/meetings/available",
            json={}
        )

        assert response.status_code == 200
        meetings = response.json()
        assert len(meetings) == 1
        assert "checked_in" in meetings[0]
        assert meetings[0]["checked_in"] is False


@pytest.mark.integration
class TestCheckin:
    """Test check-in endpoint."""

    def test_checkin_success(self, client, admin_client):
        """Should successfully check in to meeting."""
        # Create meeting
        start_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        end_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        create_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": start_time,
                "end_time": end_time
            }
        )
        meeting_data = create_response.json()

        # Check in
        response = client.post(
            f"/api/v1/meetings/{meeting_data['meeting_id']}/checkins",
            json={
                "meeting_code": meeting_data["meeting_code"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert len(data["token"]) > 40

    def test_checkin_invalid_code(self, client, admin_client):
        """Invalid meeting code should fail."""
        # Create meeting
        start_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        end_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        create_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": start_time,
                "end_time": end_time
            }
        )
        meeting_data = create_response.json()

        # Check in with wrong code
        response = client.post(
            f"/api/v1/meetings/{meeting_data['meeting_id']}/checkins",
            json={
                "meeting_code": "WRONG123"
            }
        )

        assert response.status_code == 400

    def test_checkin_idempotent(self, client, admin_client):
        """Checking in twice with same token should return same token."""
        # Create meeting
        start_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        end_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        create_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": start_time,
                "end_time": end_time
            }
        )
        meeting_data = create_response.json()

        # First check-in
        response1 = client.post(
            f"/api/v1/meetings/{meeting_data['meeting_id']}/checkins",
            json={
                "meeting_code": meeting_data["meeting_code"]
            }
        )
        token1 = response1.json()["token"]

        # Second check-in with same token
        response2 = client.post(
            f"/api/v1/meetings/{meeting_data['meeting_id']}/checkins",
            json={
                "meeting_code": meeting_data["meeting_code"],
                "token": token1
            }
        )
        token2 = response2.json()["token"]

        assert token1 == token2
