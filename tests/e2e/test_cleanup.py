"""
Cleanup utilities for E2E tests.
Can be run standalone to clean up test data from production.
"""
import pytest
import requests
import re
from datetime import datetime


class TestCleanup:
    """Cleanup test data from production"""

    def test_cleanup_e2e_test_competitions(self, prod_api, api_session, production_health_check):
        """
        Clean up competitions created by E2E tests.
        Identifies test competitions by name pattern.
        """
        # Get all competitions
        response = api_session.get(f"{prod_api}/competitions")
        assert response.status_code == 200

        competitions = response.json().get("competitions", [])

        # Find E2E test competitions
        e2e_pattern = re.compile(r"E2E.*(Test|test)", re.IGNORECASE)
        test_competitions = [
            c for c in competitions
            if e2e_pattern.search(c.get("name", ""))
        ]

        print(f"\nFound {len(test_competitions)} E2E test competitions to clean up")

        deleted = []
        failed = []

        for comp in test_competitions:
            comp_id = comp["id"]
            comp_name = comp.get("name", "Unknown")

            try:
                delete_response = api_session.delete(f"{prod_api}/competitions/{comp_id}")
                if delete_response.status_code in [200, 404]:
                    deleted.append(comp_name)
                    print(f"  Deleted: {comp_name} ({comp_id})")
                else:
                    failed.append((comp_name, delete_response.status_code))
                    print(f"  Failed to delete: {comp_name} - Status {delete_response.status_code}")
            except Exception as e:
                failed.append((comp_name, str(e)))
                print(f"  Error deleting {comp_name}: {e}")

        print(f"\nCleanup complete: {len(deleted)} deleted, {len(failed)} failed")

        # Report but don't fail the test
        if failed:
            print(f"Warning: Could not delete: {failed}")


def cleanup_all_test_data():
    """
    Standalone function to clean up all E2E test data.
    Can be called directly: python -c "from test_cleanup import cleanup_all_test_data; cleanup_all_test_data()"
    """
    import os

    PROD_BACKEND_URL = os.getenv(
        "PROD_BACKEND_URL",
        "https://my-python-backend-quyiiugyoq-ue.a.run.app"
    )

    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json"
    })

    print(f"Cleaning up E2E test data from {PROD_BACKEND_URL}")

    # Health check
    health_response = session.get(f"{PROD_BACKEND_URL}/health")
    if health_response.status_code != 200:
        print(f"Error: Production not healthy - {health_response.status_code}")
        return

    # Get all competitions
    response = session.get(f"{PROD_BACKEND_URL}/competitions")
    if response.status_code != 200:
        print(f"Error: Could not fetch competitions - {response.status_code}")
        return

    competitions = response.json().get("competitions", [])

    # Find and delete E2E test competitions
    e2e_pattern = re.compile(r"E2E.*(Test|test)", re.IGNORECASE)
    test_competitions = [
        c for c in competitions
        if e2e_pattern.search(c.get("name", ""))
    ]

    print(f"Found {len(test_competitions)} E2E test competitions")

    for comp in test_competitions:
        comp_id = comp["id"]
        comp_name = comp.get("name", "Unknown")

        delete_response = session.delete(f"{PROD_BACKEND_URL}/competitions/{comp_id}")
        if delete_response.status_code in [200, 404]:
            print(f"  Deleted: {comp_name}")
        else:
            print(f"  Failed: {comp_name} - {delete_response.status_code}")

    print("Cleanup complete!")


if __name__ == "__main__":
    cleanup_all_test_data()
