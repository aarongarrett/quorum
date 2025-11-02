"""Test rate limiting functionality."""
import pytest
from datetime import datetime, timedelta, timezone


@pytest.mark.integration
@pytest.mark.rate_limit
class TestRateLimiting:
    """Test rate limiting on public endpoints."""

    def test_checkin_rate_limit(self, client, admin_client):
        """Test that check-in endpoint rate limiting works (200 per minute)."""
        # Create a meeting first
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=1)

        meeting_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        )
        assert meeting_response.status_code == 200
        meeting_id = meeting_response.json()["meeting_id"]
        meeting_code = meeting_response.json()["meeting_code"]

        # Make 200 check-ins (the limit should allow these)
        for i in range(200):
            response = client.post(
                f"/api/v1/meetings/{meeting_id}/checkins",
                json={"meeting_code": meeting_code}
            )
            assert response.status_code == 200, f"Request {i+1} should succeed under 200/min limit"

        # The 201st request should be rate limited
        response = client.post(
            f"/api/v1/meetings/{meeting_id}/checkins",
            json={"meeting_code": meeting_code}
        )
        assert response.status_code == 429, "Request 201 should be rate limited with 429 status"

    def test_available_meetings_rate_limit(self, client):
        """Test that available meetings endpoint rate limiting works (200 per minute)."""
        # Make 200 requests (the limit should allow these)
        for i in range(200):
            response = client.post(
                "/api/v1/meetings/available",
                json={}
            )
            assert response.status_code == 200, f"Request {i+1} should succeed under 200/min limit"

        # The 201st request should be rate limited
        response = client.post(
            "/api/v1/meetings/available",
            json={}
        )
        assert response.status_code == 429, "Request 201 should be rate limited with 429 status"
