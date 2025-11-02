"""
E2E tests for complete user voting workflows.

These tests simulate real user journeys from start to finish:
- Admin creates meeting and polls
- Users check in
- Users vote
- Results are visible
"""
import pytest
from datetime import datetime, timedelta, timezone


class TestCompleteVotingFlow:
    """Test the complete voting workflow from admin creation to user voting."""

    def test_full_voting_journey(self, admin_client, client):
        """
        Test the complete journey:
        1. Admin creates a meeting
        2. Admin creates polls
        3. User checks in
        4. User votes on multiple polls
        5. Verify votes are recorded correctly
        """
        # Step 1: Admin creates a meeting
        now = datetime.now(timezone.utc)
        start_time = (now - timedelta(minutes=5)).isoformat()
        end_time = (now + timedelta(hours=2)).isoformat()

        meeting_response = admin_client.post(
            "/api/v1/meetings",
            json={"start_time": start_time, "end_time": end_time}
        )
        assert meeting_response.status_code == 200
        meeting = meeting_response.json()
        assert "meeting_id" in meeting
        assert "meeting_code" in meeting
        meeting_id = meeting["meeting_id"]
        meeting_code = meeting["meeting_code"]

        # Step 2: Admin creates multiple polls
        poll1_response = admin_client.post(
            f"/api/v1/meetings/{meeting_id}/polls",
            json={"name": "Should we approve the budget?"}
        )
        assert poll1_response.status_code == 200
        poll1_id = poll1_response.json()["poll_id"]

        poll2_response = admin_client.post(
            f"/api/v1/meetings/{meeting_id}/polls",
            json={"name": "Should we extend the deadline?"}
        )
        assert poll2_response.status_code == 200
        poll2_id = poll2_response.json()["poll_id"]

        # Step 3: User checks in to the meeting
        checkin_response = client.post(
            f"/api/v1/meetings/{meeting_id}/checkins",
            json={"meeting_code": meeting_code}
        )
        assert checkin_response.status_code == 200
        user_token = checkin_response.json()["token"]
        assert len(user_token) > 0

        # Step 4: User votes on first poll
        vote1_response = client.post(
            f"/api/v1/meetings/{meeting_id}/polls/{poll1_id}/votes",
            json={"token": user_token, "vote": "A"}
        )
        assert vote1_response.status_code == 200
        assert vote1_response.json()["success"] is True

        # Step 5: User votes on second poll
        vote2_response = client.post(
            f"/api/v1/meetings/{meeting_id}/polls/{poll2_id}/votes",
            json={"token": user_token, "vote": "B"}
        )
        assert vote2_response.status_code == 200
        assert vote2_response.json()["success"] is True

        # Step 6: Verify user cannot vote twice on same poll
        duplicate_vote_response = client.post(
            f"/api/v1/meetings/{meeting_id}/polls/{poll1_id}/votes",
            json={"token": user_token, "vote": "B"}
        )
        assert duplicate_vote_response.status_code == 400
        assert "already voted" in duplicate_vote_response.json()["detail"].lower()

        # Step 7: Verify votes are recorded in admin view
        admin_meetings_response = admin_client.get("/api/v1/admin/meetings")
        assert admin_meetings_response.status_code == 200
        meetings = admin_meetings_response.json()

        created_meeting = next(m for m in meetings if m["id"] == meeting_id)
        assert created_meeting["checkins"] == 1

        # Find the polls and verify votes
        poll1_data = next(p for p in created_meeting["polls"] if p["id"] == poll1_id)
        assert poll1_data["total_votes"] == 1
        assert poll1_data["votes"]["A"] == 1

        poll2_data = next(p for p in created_meeting["polls"] if p["id"] == poll2_id)
        assert poll2_data["total_votes"] == 1
        assert poll2_data["votes"]["B"] == 1

    def test_multiple_users_voting_on_same_poll(self, admin_client, client):
        """
        Test multiple users can check in and vote on the same poll.
        """
        # Create meeting
        now = datetime.now(timezone.utc)
        start_time = (now - timedelta(minutes=5)).isoformat()
        end_time = (now + timedelta(hours=2)).isoformat()

        meeting = admin_client.post(
            "/api/v1/meetings",
            json={"start_time": start_time, "end_time": end_time}
        ).json()
        meeting_id = meeting["meeting_id"]
        meeting_code = meeting["meeting_code"]

        # Create poll
        poll = admin_client.post(
            f"/api/v1/meetings/{meeting_id}/polls",
            json={"name": "Test Poll"}
        ).json()
        poll_id = poll["poll_id"]

        # Simulate 5 different users checking in and voting
        votes = {"A": 2, "B": 2, "C": 1}  # Expected vote distribution
        vote_choices = ["A", "A", "B", "B", "C"]

        for i, vote_choice in enumerate(vote_choices):
            # Each user gets a unique token
            checkin = client.post(
                f"/api/v1/meetings/{meeting_id}/checkins",
                json={"meeting_code": meeting_code}
            ).json()
            user_token = checkin["token"]

            # User votes
            vote_response = client.post(
                f"/api/v1/meetings/{meeting_id}/polls/{poll_id}/votes",
                json={"token": user_token, "vote": vote_choice}
            )
            assert vote_response.status_code == 200, f"User {i+1} vote failed"

        # Verify vote counts
        admin_meetings = admin_client.get("/api/v1/admin/meetings").json()
        created_meeting = next(m for m in admin_meetings if m["id"] == meeting_id)

        assert created_meeting["checkins"] == 5
        poll_data = created_meeting["polls"][0]
        assert poll_data["total_votes"] == 5
        assert poll_data["votes"]["A"] == 2
        assert poll_data["votes"]["B"] == 2
        assert poll_data["votes"]["C"] == 1

    def test_idempotent_checkin(self, admin_client, client):
        """
        Test that checking in with the same token returns the same token (idempotent).
        """
        # Create meeting
        now = datetime.now(timezone.utc)
        start_time = (now - timedelta(minutes=5)).isoformat()
        end_time = (now + timedelta(hours=2)).isoformat()

        meeting = admin_client.post(
            "/api/v1/meetings",
            json={"start_time": start_time, "end_time": end_time}
        ).json()
        meeting_id = meeting["meeting_id"]
        meeting_code = meeting["meeting_code"]

        # First check-in
        checkin1 = client.post(
            f"/api/v1/meetings/{meeting_id}/checkins",
            json={"meeting_code": meeting_code}
        ).json()
        token1 = checkin1["token"]

        # Second check-in with same token - should return same token
        checkin2 = client.post(
            f"/api/v1/meetings/{meeting_id}/checkins",
            json={"meeting_code": meeting_code, "token": token1}
        ).json()
        token2 = checkin2["token"]

        assert token1 == token2, "Idempotent check-in should return same token"

        # Verify only one check-in is recorded
        admin_meetings = admin_client.get("/api/v1/admin/meetings").json()
        created_meeting = next(m for m in admin_meetings if m["id"] == meeting_id)
        assert created_meeting["checkins"] == 1


class TestAvailableMeetingsEndpoint:
    """Test the /meetings/available endpoint with token verification."""

    def test_available_meetings_with_user_vote_status(self, admin_client, client):
        """
        Test that available meetings show correct check-in and vote status for user.
        """
        # Create meeting and poll
        now = datetime.now(timezone.utc)
        start_time = (now - timedelta(minutes=5)).isoformat()
        end_time = (now + timedelta(hours=2)).isoformat()

        meeting = admin_client.post(
            "/api/v1/meetings",
            json={"start_time": start_time, "end_time": end_time}
        ).json()
        meeting_id = meeting["meeting_id"]
        meeting_code = meeting["meeting_code"]

        poll = admin_client.post(
            f"/api/v1/meetings/{meeting_id}/polls",
            json={"name": "Test Poll"}
        ).json()
        poll_id = poll["poll_id"]

        # User checks in
        checkin = client.post(
            f"/api/v1/meetings/{meeting_id}/checkins",
            json={"meeting_code": meeting_code}
        ).json()
        user_token = checkin["token"]

        # Before voting: check available meetings
        available_before = client.post(
            "/api/v1/meetings/available",
            json={str(meeting_id): user_token}
        ).json()

        assert len(available_before) == 1
        meeting_data = available_before[0]
        assert meeting_data["id"] == meeting_id
        assert meeting_data["checked_in"] is True
        assert len(meeting_data["polls"]) == 1
        assert meeting_data["polls"][0]["vote"] is None  # Not voted yet

        # User votes
        client.post(
            f"/api/v1/meetings/{meeting_id}/polls/{poll_id}/votes",
            json={"token": user_token, "vote": "A"}
        )

        # After voting: check available meetings again
        available_after = client.post(
            "/api/v1/meetings/available",
            json={str(meeting_id): user_token}
        ).json()

        meeting_data = available_after[0]
        assert meeting_data["checked_in"] is True
        assert meeting_data["polls"][0]["vote"] == "A"  # Vote recorded
