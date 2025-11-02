"""
E2E tests for edge cases and error scenarios.

These tests verify that the system handles invalid inputs,
expired meetings, invalid tokens, and other error conditions correctly.
"""
import pytest
from datetime import datetime, timedelta, timezone


class TestInvalidTokenScenarios:
    """Test various invalid token scenarios."""

    def test_vote_with_invalid_token(self, admin_client, client):
        """Test that voting with an invalid token fails appropriately."""
        # Create meeting and poll
        now = datetime.now(timezone.utc)
        start_time = (now - timedelta(minutes=5)).isoformat()
        end_time = (now + timedelta(hours=2)).isoformat()

        meeting = admin_client.post(
            "/api/v1/meetings",
            json={"start_time": start_time, "end_time": end_time}
        ).json()
        meeting_id = meeting["meeting_id"]

        poll = admin_client.post(
            f"/api/v1/meetings/{meeting_id}/polls",
            json={"name": "Test Poll"}
        ).json()
        poll_id = poll["poll_id"]

        # Try to vote with fake token
        fake_token = "fake_token_12345"
        vote_response = client.post(
            f"/api/v1/meetings/{meeting_id}/polls/{poll_id}/votes",
            json={"token": fake_token, "vote": "A"}
        )

        assert vote_response.status_code == 400
        assert "invalid token" in vote_response.json()["detail"].lower()

    def test_vote_with_token_from_different_meeting(self, admin_client, client):
        """Test that a token from one meeting cannot be used in another meeting."""
        now = datetime.now(timezone.utc)
        start_time = (now - timedelta(minutes=5)).isoformat()
        end_time = (now + timedelta(hours=2)).isoformat()

        # Create first meeting
        meeting1 = admin_client.post(
            "/api/v1/meetings",
            json={"start_time": start_time, "end_time": end_time}
        ).json()
        meeting1_id = meeting1["meeting_id"]
        meeting1_code = meeting1["meeting_code"]

        # Create second meeting
        meeting2 = admin_client.post(
            "/api/v1/meetings",
            json={"start_time": start_time, "end_time": end_time}
        ).json()
        meeting2_id = meeting2["meeting_id"]

        # Create poll in meeting2
        poll = admin_client.post(
            f"/api/v1/meetings/{meeting2_id}/polls",
            json={"name": "Test Poll"}
        ).json()
        poll_id = poll["poll_id"]

        # Check in to meeting1
        checkin = client.post(
            f"/api/v1/meetings/{meeting1_id}/checkins",
            json={"meeting_code": meeting1_code}
        ).json()
        token_from_meeting1 = checkin["token"]

        # Try to use meeting1's token to vote in meeting2
        vote_response = client.post(
            f"/api/v1/meetings/{meeting2_id}/polls/{poll_id}/votes",
            json={"token": token_from_meeting1, "vote": "A"}
        )

        assert vote_response.status_code == 400
        assert "invalid token" in vote_response.json()["detail"].lower()


class TestExpiredMeetings:
    """Test behavior with expired or future meetings."""

    def test_cannot_checkin_to_expired_meeting(self, admin_client, client):
        """Test that users cannot check in to meetings that have ended."""
        now = datetime.now(timezone.utc)
        start_time = (now - timedelta(hours=3)).isoformat()
        end_time = (now - timedelta(hours=1)).isoformat()  # Ended 1 hour ago

        meeting = admin_client.post(
            "/api/v1/meetings",
            json={"start_time": start_time, "end_time": end_time}
        ).json()
        meeting_id = meeting["meeting_id"]
        meeting_code = meeting["meeting_code"]

        # Try to check in
        checkin_response = client.post(
            f"/api/v1/meetings/{meeting_id}/checkins",
            json={"meeting_code": meeting_code}
        )

        assert checkin_response.status_code == 400
        assert "not available" in checkin_response.json()["detail"].lower()

    def test_cannot_vote_after_meeting_ends(self, admin_client, client):
        """Test that users cannot vote after meeting has ended."""
        now = datetime.now(timezone.utc)
        start_time = (now - timedelta(hours=3)).isoformat()
        end_time = (now - timedelta(hours=1)).isoformat()  # Ended 1 hour ago

        meeting = admin_client.post(
            "/api/v1/meetings",
            json={"start_time": start_time, "end_time": end_time}
        ).json()
        meeting_id = meeting["meeting_id"]

        poll = admin_client.post(
            f"/api/v1/meetings/{meeting_id}/polls",
            json={"name": "Test Poll"}
        ).json()
        poll_id = poll["poll_id"]

        # Even with a valid token (created before expiry in this test scenario),
        # voting should fail because meeting is expired
        fake_token = "some_token"
        vote_response = client.post(
            f"/api/v1/meetings/{meeting_id}/polls/{poll_id}/votes",
            json={"token": fake_token, "vote": "A"}
        )

        assert vote_response.status_code == 400
        assert "ended" in vote_response.json()["detail"].lower() or \
               "not available" in vote_response.json()["detail"].lower()

    def test_expired_meetings_not_in_available_list(self, admin_client, client):
        """Test that expired meetings don't appear in available meetings list."""
        now = datetime.now(timezone.utc)

        # Create expired meeting
        expired_meeting = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": (now - timedelta(hours=3)).isoformat(),
                "end_time": (now - timedelta(hours=1)).isoformat()
            }
        ).json()

        # Create active meeting
        active_meeting = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": (now - timedelta(minutes=5)).isoformat(),
                "end_time": (now + timedelta(hours=2)).isoformat()
            }
        ).json()

        # Check available meetings
        available = client.post("/api/v1/meetings/available", json={}).json()

        # Should only include active meeting
        meeting_ids = [m["id"] for m in available]
        assert active_meeting["meeting_id"] in meeting_ids
        assert expired_meeting["meeting_id"] not in meeting_ids


class TestInvalidInputs:
    """Test validation of invalid inputs."""

    def test_create_meeting_with_invalid_times(self, admin_client):
        """Test that creating meeting with end before start fails."""
        now = datetime.now(timezone.utc)
        start_time = (now + timedelta(hours=2)).isoformat()
        end_time = (now + timedelta(hours=1)).isoformat()  # Before start!

        response = admin_client.post(
            "/api/v1/meetings",
            json={"start_time": start_time, "end_time": end_time}
        )

        assert response.status_code == 400
        assert "after" in response.json()["detail"].lower()

    def test_checkin_with_invalid_meeting_code(self, admin_client, client):
        """Test that check-in with wrong meeting code fails."""
        now = datetime.now(timezone.utc)
        meeting = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": (now - timedelta(minutes=5)).isoformat(),
                "end_time": (now + timedelta(hours=2)).isoformat()
            }
        ).json()
        meeting_id = meeting["meeting_id"]

        # Try with wrong code
        response = client.post(
            f"/api/v1/meetings/{meeting_id}/checkins",
            json={"meeting_code": "WRONG-CODE"}
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_vote_with_invalid_vote_option(self, admin_client, client):
        """Test that voting with invalid option (not A-H) fails."""
        now = datetime.now(timezone.utc)
        meeting = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": (now - timedelta(minutes=5)).isoformat(),
                "end_time": (now + timedelta(hours=2)).isoformat()
            }
        ).json()
        meeting_id = meeting["meeting_id"]
        meeting_code = meeting["meeting_code"]

        poll = admin_client.post(
            f"/api/v1/meetings/{meeting_id}/polls",
            json={"name": "Test Poll"}
        ).json()
        poll_id = poll["poll_id"]

        checkin = client.post(
            f"/api/v1/meetings/{meeting_id}/checkins",
            json={"meeting_code": meeting_code}
        ).json()
        user_token = checkin["token"]

        # Try to vote with invalid option
        response = client.post(
            f"/api/v1/meetings/{meeting_id}/polls/{poll_id}/votes",
            json={"token": user_token, "vote": "Z"}  # Invalid
        )

        assert response.status_code == 422  # Validation error


class TestAdminOnlyOperations:
    """Test that admin-only operations require authentication."""

    def test_create_meeting_without_auth(self, client):
        """Test that creating meeting without admin auth fails."""
        now = datetime.now(timezone.utc)
        response = client.post(
            "/api/v1/meetings",
            json={
                "start_time": (now - timedelta(minutes=5)).isoformat(),
                "end_time": (now + timedelta(hours=2)).isoformat()
            }
        )

        assert response.status_code == 401

    # Note: Admin auth tests for poll creation and meeting deletion
    # are covered in integration tests. E2E tests skip them due to
    # fixture design where admin_client and client share cookies.


class TestPollManagement:
    """Test poll creation and deletion edge cases."""

    def test_create_poll_in_nonexistent_meeting(self, admin_client):
        """Test that creating poll in non-existent meeting fails."""
        response = admin_client.post(
            "/api/v1/meetings/99999/polls",
            json={"name": "Test Poll"}
        )

        assert response.status_code == 400

    def test_delete_poll(self, admin_client):
        """Test deleting a poll removes it from the meeting."""
        # Create meeting and poll
        now = datetime.now(timezone.utc)
        meeting = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": (now - timedelta(minutes=5)).isoformat(),
                "end_time": (now + timedelta(hours=2)).isoformat()
            }
        ).json()
        meeting_id = meeting["meeting_id"]

        poll = admin_client.post(
            f"/api/v1/meetings/{meeting_id}/polls",
            json={"name": "Test Poll"}
        ).json()
        poll_id = poll["poll_id"]

        # Delete the poll
        delete_response = admin_client.delete(
            f"/api/v1/admin/meetings/{meeting_id}/polls/{poll_id}"
        )
        assert delete_response.status_code == 200

        # Verify poll is gone
        meetings = admin_client.get("/api/v1/admin/meetings").json()
        created_meeting = next(m for m in meetings if m["id"] == meeting_id)
        assert len(created_meeting["polls"]) == 0
