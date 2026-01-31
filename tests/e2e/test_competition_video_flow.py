"""
E2E tests for the full competition and video upload flow.
Tests run against production to verify the complete user journey.
"""
import pytest
import requests
import uuid
import time
from pathlib import Path


class TestHealthCheck:
    """Basic health checks for production"""

    def test_backend_health(self, prod_api, production_health_check):
        """Verify backend is healthy"""
        assert production_health_check["status"] == "healthy"
        assert "timestamp" in production_health_check

    def test_backend_returns_competitions(self, prod_api, api_session):
        """Verify competitions endpoint works"""
        response = api_session.get(f"{prod_api}/competitions")
        assert response.status_code == 200
        data = response.json()
        assert "competitions" in data


class TestCompetitionLifecycle:
    """Test creating and managing competitions"""

    def test_create_competition(self, prod_api, api_session, cleanup_competitions):
        """Test creating a new competition"""
        unique_id = str(uuid.uuid4())[:8]
        competition_data = {
            "name": f"E2E Test Competition {unique_id}",
            "description": "E2E Test Location",
            "start_date": "2025-06-01",
            "end_date": "2025-06-02",
            "status": "upcoming",
            "lifttypes": ["Snatch", "Clean"],
            "weightclasses": ["69kg", "77kg"],
            "gender": "male"
        }

        response = api_session.post(
            f"{prod_api}/create_competition",
            json=competition_data
        )

        assert response.status_code == 201, f"Failed to create competition: {response.text}"
        data = response.json()
        assert "competition_id" in data
        assert data["message"] == "Competition created successfully!"

        # Track for cleanup
        cleanup_competitions.append(data["competition_id"])

    def test_get_competition_by_id(self, prod_api, api_session, cleanup_competitions):
        """Test fetching a competition by ID"""
        # First create a competition
        unique_id = str(uuid.uuid4())[:8]
        create_response = api_session.post(
            f"{prod_api}/create_competition",
            json={
                "name": f"E2E Test Get Competition {unique_id}",
                "description": "Test Location",
                "start_date": "2025-06-01",
                "end_date": "2025-06-02"
            }
        )
        assert create_response.status_code == 201
        comp_id = create_response.json()["competition_id"]
        cleanup_competitions.append(comp_id)

        # Now fetch it
        response = api_session.get(f"{prod_api}/competitions/{comp_id}")
        assert response.status_code == 200
        data = response.json()
        assert "competition" in data
        assert data["competition"]["id"] == comp_id

    def test_delete_competition(self, prod_api, api_session):
        """Test deleting a competition"""
        # Create a competition
        unique_id = str(uuid.uuid4())[:8]
        create_response = api_session.post(
            f"{prod_api}/create_competition",
            json={
                "name": f"E2E Test Delete Competition {unique_id}",
                "description": "To be deleted",
                "start_date": "2025-06-01",
                "end_date": "2025-06-02"
            }
        )
        assert create_response.status_code == 201
        comp_id = create_response.json()["competition_id"]

        # Delete it
        delete_response = api_session.delete(f"{prod_api}/competitions/{comp_id}")
        assert delete_response.status_code == 200

        # Verify it's gone
        get_response = api_session.get(f"{prod_api}/competitions/{comp_id}")
        assert get_response.status_code == 404


class TestJoinCompetition:
    """Test joining competitions"""

    def test_join_competition(self, prod_api, api_session, test_user, cleanup_competitions):
        """Test a user joining a competition"""
        # Create a competition
        unique_id = str(uuid.uuid4())[:8]
        create_response = api_session.post(
            f"{prod_api}/create_competition",
            json={
                "name": f"E2E Test Join Competition {unique_id}",
                "description": "Test Location",
                "start_date": "2025-06-01",
                "end_date": "2025-06-02"
            }
        )
        assert create_response.status_code == 201
        comp_id = create_response.json()["competition_id"]
        cleanup_competitions.append(comp_id)

        # Join the competition
        join_response = api_session.post(
            f"{prod_api}/join_competition",
            json={
                "user_id": test_user["user_id"],
                "competition_id": comp_id,
                "weight_class": "77kg",
                "gender": "male"
            }
        )

        assert join_response.status_code == 201, f"Failed to join: {join_response.text}"
        data = join_response.json()
        assert "usercompetition_id" in data
        assert data["message"] == "Joined competition successfully!"


class TestVideoUpload:
    """Test video upload functionality"""

    def test_upload_with_email_only(self, prod_api, test_video_file, cleanup_competitions):
        """Test uploading with just an email (no profile required)"""
        unique_id = str(uuid.uuid4())[:8]
        unique_email = f"e2e-test-{unique_id}@example.com"
        session = requests.Session()

        # Create a competition
        create_response = session.post(
            f"{prod_api}/create_competition",
            json={
                "name": f"E2E Email Upload Test {unique_id}",
                "description": "Email Upload Test Location",
                "start_date": "2025-06-01",
                "end_date": "2025-12-31"
            },
            headers={"Content-Type": "application/json"}
        )
        assert create_response.status_code == 201
        comp_id = create_response.json()["competition_id"]
        cleanup_competitions.append(comp_id)

        # Upload with email instead of user_id
        with open(test_video_file, 'rb') as video:
            files = {'video': ('test_video.mp4', video, 'video/mp4')}
            data = {
                'email': unique_email,
                'competition_id': comp_id,
                'lift_type': 'Squat',
                'weight': '60'
            }

            upload_response = session.post(
                f"{prod_api}/upload",
                files=files,
                data=data
            )

        assert upload_response.status_code == 200, f"Email upload failed: {upload_response.text}"
        result = upload_response.json()
        assert "url" in result
        assert "attempt_id" in result
        assert result["url"].startswith("https://storage.googleapis.com/")

        # Verify video appears in competition lifts
        lifts_response = session.get(f"{prod_api}/competitions/{comp_id}/lifts")
        assert lifts_response.status_code == 200
        lifts = lifts_response.json()["lifts"]
        assert len(lifts) > 0, "No lifts found after email-based upload"

        # Upload again with the same email - should link to same user
        with open(test_video_file, 'rb') as video:
            files = {'video': ('test_video2.mp4', video, 'video/mp4')}
            data = {
                'email': unique_email,
                'competition_id': comp_id,
                'lift_type': 'Bench',
                'weight': '40'
            }

            upload_response2 = session.post(
                f"{prod_api}/upload",
                files=files,
                data=data
            )

        assert upload_response2.status_code == 200, f"Second email upload failed: {upload_response2.text}"

        # Verify both lifts appear
        lifts_response = session.get(f"{prod_api}/competitions/{comp_id}/lifts")
        lifts = lifts_response.json()["lifts"]
        assert len(lifts) >= 2, f"Expected at least 2 lifts, got {len(lifts)}"

    def test_upload_video(self, prod_api, test_user, test_video_file, cleanup_competitions):
        """Test uploading a video to a competition"""
        # Create a competition
        unique_id = str(uuid.uuid4())[:8]
        session = requests.Session()

        create_response = session.post(
            f"{prod_api}/create_competition",
            json={
                "name": f"E2E Test Upload Competition {unique_id}",
                "description": "Video Test Location",
                "start_date": "2025-06-01",
                "end_date": "2025-06-02"
            },
            headers={"Content-Type": "application/json"}
        )
        assert create_response.status_code == 201
        comp_id = create_response.json()["competition_id"]
        cleanup_competitions.append(comp_id)

        # Upload a video
        with open(test_video_file, 'rb') as video:
            files = {'video': ('test_video.mp4', video, 'video/mp4')}
            data = {
                'competition_id': comp_id,
                'user_id': test_user["user_id"],
                'lift_type': 'Snatch',
                'weight': '100'
            }

            upload_response = session.post(
                f"{prod_api}/upload",
                files=files,
                data=data
            )

        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        result = upload_response.json()
        assert "url" in result
        assert "attempt_id" in result
        assert result["url"].startswith("https://storage.googleapis.com/")

    def test_video_url_accessible(self, prod_api, test_user, test_video_file, cleanup_competitions):
        """Test that uploaded video URL is accessible"""
        # Create competition and upload video
        unique_id = str(uuid.uuid4())[:8]
        session = requests.Session()

        create_response = session.post(
            f"{prod_api}/create_competition",
            json={
                "name": f"E2E Test Video URL Competition {unique_id}",
                "description": "URL Test Location",
                "start_date": "2025-06-01",
                "end_date": "2025-06-02"
            },
            headers={"Content-Type": "application/json"}
        )
        assert create_response.status_code == 201
        comp_id = create_response.json()["competition_id"]
        cleanup_competitions.append(comp_id)

        # Upload video
        with open(test_video_file, 'rb') as video:
            files = {'video': ('test_video.mp4', video, 'video/mp4')}
            data = {
                'competition_id': comp_id,
                'user_id': test_user["user_id"],
                'lift_type': 'Snatch',
                'weight': '100'
            }

            upload_response = session.post(
                f"{prod_api}/upload",
                files=files,
                data=data
            )

        assert upload_response.status_code == 200
        video_url = upload_response.json()["url"]

        # Verify the video URL is accessible
        head_response = requests.head(video_url, allow_redirects=True)
        assert head_response.status_code == 200, f"Video URL not accessible: {video_url}"


class TestFullCompetitionFlow:
    """Test the complete user journey from competition creation to video verification"""

    def test_full_competition_lifecycle(
        self,
        prod_api,
        api_session,
        test_user,
        test_video_file,
        cleanup_competitions
    ):
        """
        Full E2E test:
        1. Create competition
        2. Join competition
        3. Upload video
        4. Verify video appears in competition lifts
        """
        unique_id = str(uuid.uuid4())[:8]

        # Step 1: Create competition
        print(f"\n[Step 1] Creating competition...")
        create_response = api_session.post(
            f"{prod_api}/create_competition",
            json={
                "name": f"E2E Full Flow Test {unique_id}",
                "description": "Full Flow Test Location",
                "start_date": "2025-06-01",
                "end_date": "2025-06-02",
                "lifttypes": ["Snatch", "Clean"],
                "weightclasses": ["77kg"],
                "gender": "male"
            }
        )
        assert create_response.status_code == 201, f"Create failed: {create_response.text}"
        comp_id = create_response.json()["competition_id"]
        cleanup_competitions.append(comp_id)
        print(f"    Created competition: {comp_id}")

        # Step 2: Join competition
        print(f"[Step 2] Joining competition...")
        join_response = api_session.post(
            f"{prod_api}/join_competition",
            json={
                "user_id": test_user["user_id"],
                "competition_id": comp_id,
                "weight_class": "77kg",
                "gender": "male"
            }
        )
        assert join_response.status_code == 201, f"Join failed: {join_response.text}"
        usercomp_id = join_response.json()["usercompetition_id"]
        print(f"    Joined with usercompetition_id: {usercomp_id}")

        # Step 3: Upload video
        print(f"[Step 3] Uploading video...")
        session = requests.Session()
        with open(test_video_file, 'rb') as video:
            files = {'video': ('test_video.mp4', video, 'video/mp4')}
            data = {
                'competition_id': comp_id,
                'user_id': test_user["user_id"],
                'lift_type': 'Snatch',
                'weight': '100'
            }

            upload_response = session.post(
                f"{prod_api}/upload",
                files=files,
                data=data
            )

        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        upload_result = upload_response.json()
        attempt_id = upload_result["attempt_id"]
        video_url = upload_result["url"]
        print(f"    Uploaded video, attempt_id: {attempt_id}")
        print(f"    Video URL: {video_url}")

        # Step 4: Verify video appears in competition lifts
        print(f"[Step 4] Verifying video in competition lifts...")
        lifts_response = api_session.get(f"{prod_api}/competitions/{comp_id}/lifts")
        assert lifts_response.status_code == 200, f"Get lifts failed: {lifts_response.text}"
        lifts_data = lifts_response.json()

        assert "lifts" in lifts_data
        assert len(lifts_data["lifts"]) > 0, "No lifts found in competition"

        # Find our uploaded attempt
        found_attempt = None
        for lift in lifts_data["lifts"]:
            if lift["id"] == attempt_id:
                found_attempt = lift
                break

        assert found_attempt is not None, f"Uploaded attempt {attempt_id} not found in lifts"
        assert found_attempt["video_url"] is not None, "Video URL not stored in attempt"
        print(f"    Found attempt in lifts with video_url: {found_attempt['video_url']}")

        # Step 5: Verify video URL is accessible
        print(f"[Step 5] Verifying video URL accessibility...")
        head_response = requests.head(video_url, allow_redirects=True)
        assert head_response.status_code == 200, f"Video not accessible: {head_response.status_code}"
        print(f"    Video URL is accessible!")

        print(f"\n[SUCCESS] Full competition lifecycle completed!")

    def test_multiple_videos_same_competition(
        self,
        prod_api,
        api_session,
        test_user,
        test_video_file,
        cleanup_competitions
    ):
        """Test uploading multiple videos to the same competition"""
        unique_id = str(uuid.uuid4())[:8]

        # Create competition
        create_response = api_session.post(
            f"{prod_api}/create_competition",
            json={
                "name": f"E2E Multiple Videos Test {unique_id}",
                "description": "Multiple Videos Location",
                "start_date": "2025-06-01",
                "end_date": "2025-06-02"
            }
        )
        assert create_response.status_code == 201
        comp_id = create_response.json()["competition_id"]
        cleanup_competitions.append(comp_id)

        # Join competition
        join_response = api_session.post(
            f"{prod_api}/join_competition",
            json={
                "user_id": test_user["user_id"],
                "competition_id": comp_id,
                "weight_class": "77kg",
                "gender": "male"
            }
        )
        assert join_response.status_code == 201

        # Upload multiple videos
        uploaded_attempts = []
        lift_types = ["Snatch", "Clean", "Deadlift"]
        weights = [100, 120, 180]

        session = requests.Session()
        for i, (lift_type, weight) in enumerate(zip(lift_types, weights)):
            with open(test_video_file, 'rb') as video:
                files = {'video': (f'test_video_{i}.mp4', video, 'video/mp4')}
                data = {
                    'competition_id': comp_id,
                    'user_id': test_user["user_id"],
                    'lift_type': lift_type,
                    'weight': str(weight)
                }

                upload_response = session.post(
                    f"{prod_api}/upload",
                    files=files,
                    data=data
                )

            assert upload_response.status_code == 200, f"Upload {i} failed: {upload_response.text}"
            uploaded_attempts.append(upload_response.json()["attempt_id"])

        # Verify all videos appear in lifts
        lifts_response = api_session.get(f"{prod_api}/competitions/{comp_id}/lifts")
        assert lifts_response.status_code == 200
        lifts = lifts_response.json()["lifts"]

        assert len(lifts) >= len(uploaded_attempts), \
            f"Expected at least {len(uploaded_attempts)} lifts, got {len(lifts)}"

        # Verify each uploaded attempt is in the lifts
        lift_ids = [lift["id"] for lift in lifts]
        for attempt_id in uploaded_attempts:
            assert attempt_id in lift_ids, f"Attempt {attempt_id} not found in lifts"


class TestParticipants:
    """Test participants endpoint"""

    def test_competition_participants_shows_user(
        self,
        prod_api,
        api_session,
        test_user,
        cleanup_competitions
    ):
        """Test that joined user appears in participants"""
        unique_id = str(uuid.uuid4())[:8]

        # Create competition
        create_response = api_session.post(
            f"{prod_api}/create_competition",
            json={
                "name": f"E2E Participants Test {unique_id}",
                "description": "Participants Test Location",
                "start_date": "2025-06-01",
                "end_date": "2025-06-02"
            }
        )
        assert create_response.status_code == 201
        comp_id = create_response.json()["competition_id"]
        cleanup_competitions.append(comp_id)

        # Join competition
        join_response = api_session.post(
            f"{prod_api}/join_competition",
            json={
                "user_id": test_user["user_id"],
                "competition_id": comp_id,
                "weight_class": "77kg",
                "gender": "male"
            }
        )
        assert join_response.status_code == 201

        # Get participants
        participants_response = api_session.get(
            f"{prod_api}/competitions/{comp_id}/participants"
        )
        assert participants_response.status_code == 200
        data = participants_response.json()

        assert "participants" in data
        assert len(data["participants"]) > 0

        # Verify our user is in participants
        user_ids = [p["id"] for p in data["participants"]]
        assert test_user["user_id"] in user_ids, \
            f"User {test_user['user_id']} not in participants: {user_ids}"


class TestRandomVideo:
    """Test random video endpoint"""

    def test_random_video_returns_video(self, prod_api, api_session):
        """Test that random video endpoint returns a video"""
        response = api_session.get(f"{prod_api}/random-video")

        # This might fail if there are no videos in the bucket
        if response.status_code == 404:
            pytest.skip("No videos available in bucket")

        assert response.status_code == 200
        data = response.json()
        assert "video_url" in data
        assert data["video_url"].startswith("https://")


class TestChallengeUploadFlow:
    """Test the direct upload flow on challenge page (no join required)"""

    def test_direct_upload_to_challenge(
        self,
        prod_api,
        api_session,
        test_user,
        test_video_file,
        cleanup_competitions
    ):
        """
        Test uploading directly to a challenge without joining first.
        This simulates the new UI flow where users can upload directly.
        """
        unique_id = str(uuid.uuid4())[:8]

        # Step 1: Create a competition
        print(f"\n[Step 1] Creating competition for direct upload test...")
        create_response = api_session.post(
            f"{prod_api}/create_competition",
            json={
                "name": f"E2E Direct Upload Test {unique_id}",
                "description": "Direct Upload Test Location",
                "start_date": "2025-06-01",
                "end_date": "2025-12-31",
                "lifttypes": ["Squat", "Bench", "Deadlift"],
                "weightclasses": ["77kg", "83kg"],
                "gender": "male"
            }
        )
        assert create_response.status_code == 201, f"Create failed: {create_response.text}"
        comp_id = create_response.json()["competition_id"]
        cleanup_competitions.append(comp_id)
        print(f"    Created competition: {comp_id}")

        # Step 2: Upload video directly (without joining first)
        # This mimics what the new UI does - the backend should auto-create UserCompetition
        print(f"[Step 2] Uploading video directly to challenge...")
        session = requests.Session()
        with open(test_video_file, 'rb') as video:
            files = {'video': ('test_video.mp4', video, 'video/mp4')}
            data = {
                'competition_id': comp_id,
                'user_id': test_user["user_id"],
                'lift_type': 'Squat',  # Default lift type
                'weight': '60'  # Default weight for Squat
            }

            upload_response = session.post(
                f"{prod_api}/upload",
                files=files,
                data=data
            )

        assert upload_response.status_code == 200, f"Direct upload failed: {upload_response.text}"
        upload_result = upload_response.json()
        assert "url" in upload_result
        assert "attempt_id" in upload_result
        assert "user_competition_id" in upload_result
        print(f"    Upload successful! attempt_id: {upload_result['attempt_id']}")

        # Step 3: Verify the video appears in competition lifts
        print(f"[Step 3] Verifying video in competition lifts...")
        lifts_response = api_session.get(f"{prod_api}/competitions/{comp_id}/lifts")
        assert lifts_response.status_code == 200
        lifts = lifts_response.json()["lifts"]
        assert len(lifts) > 0, "No lifts found after direct upload"

        # Find our uploaded attempt
        found_attempt = next(
            (lift for lift in lifts if lift["id"] == upload_result["attempt_id"]),
            None
        )
        assert found_attempt is not None, "Uploaded attempt not found in lifts"
        assert found_attempt["video_url"] is not None
        print(f"    Video found in lifts!")

        # Step 4: Verify user was auto-added as participant
        print(f"[Step 4] Verifying user was added as participant...")
        participants_response = api_session.get(
            f"{prod_api}/competitions/{comp_id}/participants"
        )
        assert participants_response.status_code == 200
        participants = participants_response.json()["participants"]
        user_ids = [p["id"] for p in participants]
        assert test_user["user_id"] in user_ids, "User not auto-added as participant"
        print(f"    User found in participants!")

        print(f"\n[SUCCESS] Direct upload flow completed!")

    def test_upload_with_default_values(
        self,
        prod_api,
        api_session,
        test_user,
        test_video_file,
        cleanup_competitions
    ):
        """
        Test uploading with default form values (Squat, 60kg).
        This tests the form's default values work correctly.
        """
        unique_id = str(uuid.uuid4())[:8]

        # Create competition
        create_response = api_session.post(
            f"{prod_api}/create_competition",
            json={
                "name": f"E2E Default Values Test {unique_id}",
                "description": "Default Values Location",
                "start_date": "2025-06-01",
                "end_date": "2025-12-31"
            }
        )
        assert create_response.status_code == 201
        comp_id = create_response.json()["competition_id"]
        cleanup_competitions.append(comp_id)

        # Upload with default values
        session = requests.Session()
        with open(test_video_file, 'rb') as video:
            files = {'video': ('test_video.mp4', video, 'video/mp4')}
            data = {
                'competition_id': comp_id,
                'user_id': test_user["user_id"],
                'lift_type': 'Squat',  # Default
                'weight': '60'  # Default for Squat
            }

            upload_response = session.post(
                f"{prod_api}/upload",
                files=files,
                data=data
            )

        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"

        # Verify the lift was created with correct values
        lifts_response = api_session.get(f"{prod_api}/competitions/{comp_id}/lifts")
        lifts = lifts_response.json()["lifts"]

        assert len(lifts) > 0
        # The backend may return weight as int, float, or string
        assert any(
            float(lift["weight"]) == 60.0
            for lift in lifts
        ), f"Expected weight 60, got {[l['weight'] for l in lifts]}"
