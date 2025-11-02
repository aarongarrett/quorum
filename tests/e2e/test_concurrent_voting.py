"""
E2E tests for concurrent voting scenarios.

These tests simulate multiple users voting simultaneously to verify:
- Race condition handling
- Database connection pool handling
- Vote uniqueness constraints
- System stability under load
"""
import pytest
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


class TestConcurrentVoting:
    """Test concurrent voting scenarios."""

    def test_concurrent_votes_on_same_poll(self, admin_client, client):
        """
        Test that 20 users can vote concurrently on the same poll.
        This tests database connection pool and transaction handling.
        """
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
        meeting_code = meeting["meeting_code"]

        poll = admin_client.post(
            f"/api/v1/meetings/{meeting_id}/polls",
            json={"name": "Concurrent Test Poll"}
        ).json()
        poll_id = poll["poll_id"]

        # Pre-create tokens for 20 users
        user_tokens = []
        for _ in range(20):
            checkin = client.post(
                f"/api/v1/meetings/{meeting_id}/checkins",
                json={"meeting_code": meeting_code}
            ).json()
            user_tokens.append(checkin["token"])

        # Define vote function
        def cast_vote(token, vote_option):
            """Cast a vote for a user."""
            response = client.post(
                f"/api/v1/meetings/{meeting_id}/polls/{poll_id}/votes",
                json={"token": token, "vote": vote_option}
            )
            return response.status_code, response.json()

        # Vote distribution: 8 for A, 7 for B, 5 for C
        vote_choices = (["A"] * 8) + (["B"] * 7) + (["C"] * 5)

        # Submit all votes concurrently
        successful_votes = 0
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(cast_vote, token, vote)
                for token, vote in zip(user_tokens, vote_choices)
            ]

            for future in as_completed(futures):
                status_code, response_data = future.result()
                if status_code == 200:
                    successful_votes += 1

        # All votes should succeed
        assert successful_votes == 20, f"Expected 20 successful votes, got {successful_votes}"

        # Verify vote counts
        meetings = admin_client.get("/api/v1/admin/meetings").json()
        created_meeting = next(m for m in meetings if m["id"] == meeting_id)

        poll_data = created_meeting["polls"][0]
        assert poll_data["total_votes"] == 20
        assert poll_data["votes"]["A"] == 8
        assert poll_data["votes"]["B"] == 7
        assert poll_data["votes"]["C"] == 5

    def test_concurrent_double_vote_attempts(self, admin_client, client):
        """
        Test that race condition in double voting is handled correctly.
        Simulates a user double-clicking the vote button (concurrent requests with same token).
        """
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
        meeting_code = meeting["meeting_code"]

        poll = admin_client.post(
            f"/api/v1/meetings/{meeting_id}/polls",
            json={"name": "Double Vote Test"}
        ).json()
        poll_id = poll["poll_id"]

        # User checks in
        checkin = client.post(
            f"/api/v1/meetings/{meeting_id}/checkins",
            json={"meeting_code": meeting_code}
        ).json()
        user_token = checkin["token"]

        # Define vote function
        def cast_vote(token):
            """Attempt to cast a vote."""
            try:
                response = client.post(
                    f"/api/v1/meetings/{meeting_id}/polls/{poll_id}/votes",
                    json={"token": token, "vote": "A"}
                )
                return response.status_code, response.json()
            except Exception as e:
                return 500, {"error": str(e)}

        # Simulate double-click: submit same vote 3 times concurrently
        results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(cast_vote, user_token) for _ in range(3)]

            for future in as_completed(futures):
                status_code, response_data = future.result()
                results.append((status_code, response_data))

        # Exactly one should succeed (200), others should fail (400)
        success_count = sum(1 for code, _ in results if code == 200)
        failure_count = sum(1 for code, _ in results if code == 400)

        assert success_count == 1, f"Expected exactly 1 success, got {success_count}"
        assert failure_count == 2, f"Expected 2 failures, got {failure_count}"

        # Verify only one vote recorded
        meetings = admin_client.get("/api/v1/admin/meetings").json()
        created_meeting = next(m for m in meetings if m["id"] == meeting_id)
        poll_data = created_meeting["polls"][0]
        assert poll_data["total_votes"] == 1, "Should have exactly 1 vote despite concurrent attempts"

    def test_concurrent_checkins(self, admin_client, client):
        """
        Test that many users can check in concurrently without issues.
        """
        # Create meeting
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

        # Define checkin function
        def checkin_user():
            """Check in a user."""
            response = client.post(
                f"/api/v1/meetings/{meeting_id}/checkins",
                json={"meeting_code": meeting_code}
            )
            return response.status_code, response.json()

        # 30 users check in concurrently
        successful_checkins = 0
        tokens = []

        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(checkin_user) for _ in range(30)]

            for future in as_completed(futures):
                status_code, response_data = future.result()
                if status_code == 200:
                    successful_checkins += 1
                    tokens.append(response_data["token"])

        # All checkins should succeed
        assert successful_checkins == 30

        # All tokens should be unique
        assert len(set(tokens)) == 30, "All tokens should be unique"

        # Verify checkin count
        meetings = admin_client.get("/api/v1/admin/meetings").json()
        created_meeting = next(m for m in meetings if m["id"] == meeting_id)
        assert created_meeting["checkins"] == 30

    def test_concurrent_poll_creation(self, admin_client):
        """
        Test that admin can create multiple polls concurrently.
        """
        # Create meeting
        now = datetime.now(timezone.utc)
        meeting = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": (now - timedelta(minutes=5)).isoformat(),
                "end_time": (now + timedelta(hours=2)).isoformat()
            }
        ).json()
        meeting_id = meeting["meeting_id"]

        # Define poll creation function
        def create_poll(poll_name):
            """Create a poll."""
            response = admin_client.post(
                f"/api/v1/meetings/{meeting_id}/polls",
                json={"name": poll_name}
            )
            return response.status_code, response.json()

        # Create 10 polls concurrently
        poll_names = [f"Poll {i+1}" for i in range(10)]
        successful_creates = 0

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_poll, name) for name in poll_names]

            for future in as_completed(futures):
                status_code, _ = future.result()
                if status_code == 200:
                    successful_creates += 1

        # All polls should be created
        assert successful_creates == 10

        # Verify all polls exist
        meetings = admin_client.get("/api/v1/admin/meetings").json()
        created_meeting = next(m for m in meetings if m["id"] == meeting_id)
        assert len(created_meeting["polls"]) == 10


class TestLoadScenarios:
    """Test system behavior under realistic load scenarios."""

    def test_realistic_meeting_scenario(self, admin_client, client):
        """
        Simulate a realistic meeting scenario:
        - Admin creates meeting with 3 polls
        - 50 users check in (some concurrently)
        - Users vote on all 3 polls (some concurrently)
        - Verify all data is correct
        """
        # Admin creates meeting
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

        # Admin creates 3 polls
        poll_ids = []
        for i in range(3):
            poll = admin_client.post(
                f"/api/v1/meetings/{meeting_id}/polls",
                json={"name": f"Poll {i+1}"}
            ).json()
            poll_ids.append(poll["poll_id"])

        # Phase 1: 50 users check in (batches to avoid overwhelming test client)
        user_tokens = []
        batch_size = 10

        for batch_start in range(0, 50, batch_size):
            batch_tokens = []

            def checkin_user():
                response = client.post(
                    f"/api/v1/meetings/{meeting_id}/checkins",
                    json={"meeting_code": meeting_code}
                )
                return response.json()["token"] if response.status_code == 200 else None

            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = [executor.submit(checkin_user) for _ in range(batch_size)]
                for future in as_completed(futures):
                    token = future.result()
                    if token:
                        batch_tokens.append(token)

            user_tokens.extend(batch_tokens)
            time.sleep(0.1)  # Small delay between batches

        assert len(user_tokens) == 50, f"Expected 50 check-ins, got {len(user_tokens)}"

        # Phase 2: Users vote on all 3 polls
        # Vote distribution varies per poll
        vote_patterns = [
            ["A"] * 20 + ["B"] * 15 + ["C"] * 15,  # Poll 1
            ["A"] * 10 + ["B"] * 25 + ["C"] * 15,  # Poll 2
            ["A"] * 15 + ["B"] * 15 + ["C"] * 20,  # Poll 3
        ]

        for poll_idx, poll_id in enumerate(poll_ids):
            votes = vote_patterns[poll_idx]

            def cast_vote(token, vote_option):
                response = client.post(
                    f"/api/v1/meetings/{meeting_id}/polls/{poll_id}/votes",
                    json={"token": token, "vote": vote_option}
                )
                return response.status_code == 200

            # Vote in batches
            for batch_start in range(0, 50, batch_size):
                batch_end = min(batch_start + batch_size, 50)
                batch_tokens = user_tokens[batch_start:batch_end]
                batch_votes = votes[batch_start:batch_end]

                with ThreadPoolExecutor(max_workers=batch_size) as executor:
                    futures = [
                        executor.submit(cast_vote, token, vote)
                        for token, vote in zip(batch_tokens, batch_votes)
                    ]
                    list(as_completed(futures))  # Wait for completion

                time.sleep(0.1)  # Small delay between batches

        # Verify results
        meetings = admin_client.get("/api/v1/admin/meetings").json()
        created_meeting = next(m for m in meetings if m["id"] == meeting_id)

        # Verify checkins
        assert created_meeting["checkins"] == 50

        # Verify each poll
        assert len(created_meeting["polls"]) == 3

        poll1 = next(p for p in created_meeting["polls"] if p["id"] == poll_ids[0])
        assert poll1["total_votes"] == 50
        assert poll1["votes"]["A"] == 20
        assert poll1["votes"]["B"] == 15
        assert poll1["votes"]["C"] == 15

        poll2 = next(p for p in created_meeting["polls"] if p["id"] == poll_ids[1])
        assert poll2["total_votes"] == 50
        assert poll2["votes"]["A"] == 10
        assert poll2["votes"]["B"] == 25
        assert poll2["votes"]["C"] == 15

        poll3 = next(p for p in created_meeting["polls"] if p["id"] == poll_ids[2])
        assert poll3["total_votes"] == 50
        assert poll3["votes"]["A"] == 15
        assert poll3["votes"]["B"] == 15
        assert poll3["votes"]["C"] == 20
