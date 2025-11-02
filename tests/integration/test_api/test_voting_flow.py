"""End-to-end integration test for complete voting flow."""
import pytest
from datetime import datetime, timezone, timedelta


@pytest.mark.integration
class TestCompleteVotingFlow:
    """Test the complete voting workflow."""

    def test_complete_voting_flow(self, client, admin_client):
        """Test: Create meeting → Create poll → Check in → Vote."""
        # Step 1: Admin creates a meeting
        start_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        end_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        meeting_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": start_time,
                "end_time": end_time
            }
        )
        assert meeting_response.status_code == 200
        meeting_data = meeting_response.json()
        meeting_id = meeting_data["meeting_id"]
        meeting_code = meeting_data["meeting_code"]

        # Step 2: Admin creates a poll
        poll_response = admin_client.post(
            f"/api/v1/meetings/{meeting_id}/polls",
            json={"name": "Test Poll"}
        )
        assert poll_response.status_code == 200
        poll_data = poll_response.json()
        poll_id = poll_data["poll_id"]

        # Step 3: User checks in
        checkin_response = client.post(
            f"/api/v1/meetings/{meeting_id}/checkins",
            json={"meeting_code": meeting_code}
        )
        assert checkin_response.status_code == 200
        token = checkin_response.json()["token"]

        # Step 4: User votes
        vote_response = client.post(
            f"/api/v1/meetings/{meeting_id}/polls/{poll_id}/votes",
            json={
                "token": token,
                "vote": "A"
            }
        )
        assert vote_response.status_code == 200

        # Step 5: Verify user cannot vote again
        duplicate_vote_response = client.post(
            f"/api/v1/meetings/{meeting_id}/polls/{poll_id}/votes",
            json={
                "token": token,
                "vote": "B"
            }
        )
        assert duplicate_vote_response.status_code == 400

        # Step 6: Verify check-in status persists
        available_response = client.post(
            "/api/v1/meetings/available",
            json={str(meeting_id): token}
        )
        assert available_response.status_code == 200
        meetings = available_response.json()
        assert len(meetings) == 1
        assert meetings[0]["checked_in"] is True
        assert meetings[0]["polls"][0]["vote"] == "A"

    def test_multiple_users_voting(self, client, admin_client):
        """Test multiple users voting on same poll."""
        # Create meeting and poll
        start_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        end_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        meeting_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": start_time,
                "end_time": end_time
            }
        )
        meeting_data = meeting_response.json()
        meeting_id = meeting_data["meeting_id"]
        meeting_code = meeting_data["meeting_code"]

        poll_response = admin_client.post(
            f"/api/v1/meetings/{meeting_id}/polls",
            json={"name": "Test Poll"}
        )
        poll_id = poll_response.json()["poll_id"]

        # Three users check in and vote
        votes = ["A", "B", "A"]  # Two A's, one B
        for vote_choice in votes:
            checkin_response = client.post(
                f"/api/v1/meetings/{meeting_id}/checkins",
                json={"meeting_code": meeting_code}
            )
            token = checkin_response.json()["token"]

            vote_response = client.post(
                f"/api/v1/meetings/{meeting_id}/polls/{poll_id}/votes",
                json={
                    "token": token,
                    "vote": vote_choice
                }
            )
            assert vote_response.status_code == 200

        # Verify admin can see results
        admin_meetings_response = admin_client.get(
            "/api/v1/admin/meetings"
        )
        assert admin_meetings_response.status_code == 200
        meetings = admin_meetings_response.json()
        poll = meetings[0]["polls"][0]

        assert poll["total_votes"] == 3
        assert poll["votes"]["A"] == 2
        assert poll["votes"]["B"] == 1
