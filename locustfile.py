from locust import HttpUser, task, between, events
import random
import os
import requests
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    from dotenv import load_dotenv
    load_dotenv()

    tz = ZoneInfo(os.getenv("QUORUM_TIMEZONE", "America/New_York"))
    admin_pwd = os.getenv("QUORUM_ADMIN_PASSWORD")
    base_url = os.getenv("LOCUST_HOST")

    print("Clearing the current database...")
    response = requests.post(f"{base_url}/_test/reset-db")
    if response.status_code != 200:
        raise RuntimeError(f"Failed to reset DB: {response.status_code} {response.text}")

    print("Seeding test data...")
    # Use a session to persist cookies (like Flask session)
    session = requests.Session()
    response = session.post(
        f"{base_url}/api/login",
        json={"password": admin_pwd}
    )
    if response.status_code != 200:
        print(response.json())
        raise RuntimeError(f"Failed to login as admin in test setup: {response.status_code} {response.text}")


    now = datetime.now(tz)
    for i in range(3):
        start_time = now + timedelta(minutes=(5*i))
        end_time = now + timedelta(hours=2)
        meeting_response = session.post(
            f"{base_url}/api/admin/meetings",
            json={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        )
        if meeting_response.status_code != 201:
            raise RuntimeError(f"Failed to create meeting {i+1} in test setup: {meeting_response.status_code} {meeting_response.text}")
        data = meeting_response.json()
        mid, _ = data["meeting_id"], data["meeting_code"]
        for j in range(2):
            poll_response = session.post(
                f"{base_url}/api/admin/meetings/{mid}/polls",
                json={
                    "name": f"Poll {i}{j}"
                }
            )
            if poll_response.status_code != 201:
                raise RuntimeError(f"Failed to create poll {j+1} in test setup: {poll_response.status_code} {poll_response.text}")



class VotingUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        """Step 1: List meetings"""
        response = self.client.get("/api/meetings", name="GET /api/meetings")
        self.meetings = []

        if response.status_code == 200:
            try:
                data = response.json()
                self.meetings = data
            except Exception:
                response.failure("Failed to parse meeting list JSON")
        else:
            response.failure("Failed to get meeting list")

    @task
    def check_in_and_vote(self):
        if not self.meetings:
            return  # No meetings, nothing to do

        meeting = random.choice([m for m in self.meetings if not m["checked_in"]])
        meeting_id = meeting["id"]
        meeting_code = meeting["meeting_code"]

        # Step 2: Check in to the meeting
        with self.client.post(
            f"/api/meetings/{meeting_id}/checkins",
            json={
                "meeting_code": meeting_code
            },
            name="POST /api/meetings/<meeting_id>/checkins",
            catch_response=True
        ) as checkin_response:
            if checkin_response.status_code != 200:
                checkin_response.failure(f"Check-in failed for meeting {meeting_id}")
                return

            try:
                vote_token = checkin_response.json().get("token")
            except Exception:
                checkin_response.failure(f"Failed to parse checkin JSON  {checkin_response.text}")

            # Step 3: Vote in each poll
            for poll in meeting["polls"]:
                poll_id = poll["id"]
                with self.client.post(
                    f"/api/meetings/{meeting_id}/polls/{poll_id}/votes",
                    json={
                        "token": vote_token,
                        "vote": random.choice("ABCDEFGH")
                    },
                    name="POST /api/meetings/<meeting_id>/polls/<poll_id>/votes",
                    catch_response=True
                ) as vote_response:
                    if vote_response.status_code != 200:
                        vote_response.failure(f"Vote failed for poll {poll_id}  {vote_response.text}")
                        return
