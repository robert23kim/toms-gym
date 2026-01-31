"""
Production test fixtures for E2E tests against the live backend.
"""
import pytest
import requests
import uuid
import os
from pathlib import Path

# Production URLs
PROD_BACKEND_URL = os.getenv(
    "PROD_BACKEND_URL",
    "https://my-python-backend-quyiiugyoq-ue.a.run.app"
)
PROD_FRONTEND_URL = os.getenv(
    "PROD_FRONTEND_URL",
    "https://my-frontend-quyiiugyoq-ue.a.run.app"
)
GCS_BUCKET = "jtr-lift-u-4ever-cool-bucket"


@pytest.fixture(scope="session")
def prod_api():
    """Production API base URL"""
    return PROD_BACKEND_URL


@pytest.fixture(scope="session")
def prod_frontend():
    """Production frontend base URL"""
    return PROD_FRONTEND_URL


@pytest.fixture(scope="session")
def api_session():
    """Requests session with common headers"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json"
    })
    return session


@pytest.fixture(scope="function")
def test_user(prod_api, api_session):
    """
    Create a test user via the register endpoint.
    Returns user data including access_token.
    """
    unique_id = str(uuid.uuid4())[:8]
    user_data = {
        "email": f"e2e-test-{unique_id}@test.com",
        "password": "TestPassword123!",
        "name": f"E2E Test User {unique_id}"
    }

    response = api_session.post(
        f"{prod_api}/auth/register",
        json=user_data
    )

    if response.status_code == 201:
        result = response.json()
        return {
            "user_id": result["user_id"],
            "access_token": result["access_token"],
            "email": user_data["email"],
            "name": user_data["name"]
        }
    elif response.status_code == 409:
        # User already exists, try to login
        login_response = api_session.post(
            f"{prod_api}/auth/login",
            json={
                "username": user_data["email"],
                "password": user_data["password"]
            }
        )
        if login_response.status_code == 200:
            result = login_response.json()
            return {
                "user_id": result["user_id"],
                "access_token": result["access_token"],
                "email": user_data["email"],
                "name": user_data["name"]
            }

    # If we can't create or login, return a mock user for basic tests
    return {
        "user_id": "1",
        "access_token": None,
        "email": user_data["email"],
        "name": user_data["name"]
    }


@pytest.fixture
def auth_headers(test_user):
    """Authorization headers for authenticated requests"""
    if test_user.get("access_token"):
        return {"Authorization": f"Bearer {test_user['access_token']}"}
    return {}


@pytest.fixture
def test_video_file():
    """
    Load test video file for upload.
    Returns a tuple of (file_path, file_bytes) for upload testing.
    """
    video_path = Path(__file__).parent.parent / "fixtures" / "test_video.mp4"

    if not video_path.exists():
        pytest.skip(f"Test video not found at {video_path}")

    return video_path


@pytest.fixture(scope="function")
def cleanup_competitions(prod_api, api_session):
    """
    Track and cleanup competitions created during test.
    Yields a list that tests can append competition IDs to.
    After the test, all tracked competitions are deleted.
    """
    created_ids = []
    yield created_ids

    # Cleanup after test
    for comp_id in created_ids:
        try:
            response = api_session.delete(f"{prod_api}/competitions/{comp_id}")
            if response.status_code in [200, 404]:
                print(f"Cleaned up competition: {comp_id}")
            else:
                print(f"Warning: Failed to cleanup competition {comp_id}: {response.status_code}")
        except Exception as e:
            print(f"Warning: Error cleaning up competition {comp_id}: {e}")


@pytest.fixture(scope="session")
def production_health_check(prod_api):
    """
    Verify production is healthy before running tests.
    This runs once at the start of the test session.
    """
    try:
        response = requests.get(f"{prod_api}/health", timeout=10)
        if response.status_code != 200:
            pytest.fail(f"Production health check failed: {response.status_code}")

        health_data = response.json()
        print(f"\nProduction health: {health_data}")
        return health_data
    except requests.RequestException as e:
        pytest.fail(f"Could not reach production: {e}")
