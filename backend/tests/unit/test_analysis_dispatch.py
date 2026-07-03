"""enqueue_analysis_job builds an OIDC HTTP task targeting /jobs/<kind>/<id>."""
import pytest

from toms_gym.services import analysis_dispatch


class FakeTasksClient:
    created = []
    def create_task(self, parent=None, task=None):
        FakeTasksClient.created.append((parent, task))


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("ANALYSIS_DISPATCH_MODE", "tasks")
    monkeypatch.setenv("ANALYSIS_TASKS_QUEUE",
                       "projects/toms-gym/locations/us-east1/queues/analysis-jobs")
    monkeypatch.setenv("TASKS_TARGET_BASE_URL",
                       "https://my-python-backend-quyiiugyoq-ue.a.run.app")
    monkeypatch.setenv("TASKS_SERVICE_ACCOUNT",
                       "toms-gym-service@toms-gym.iam.gserviceaccount.com")
    FakeTasksClient.created = []


def test_noop_when_mode_is_poller(monkeypatch):
    monkeypatch.setenv("ANALYSIS_DISPATCH_MODE", "poller")
    monkeypatch.setattr(analysis_dispatch, "_tasks_client", lambda: FakeTasksClient())
    analysis_dispatch.enqueue_analysis_job("lifting", "r-1")
    assert FakeTasksClient.created == []


def test_enqueues_oidc_http_task(monkeypatch):
    monkeypatch.setattr(analysis_dispatch, "_tasks_client", lambda: FakeTasksClient())
    analysis_dispatch.enqueue_analysis_job("lifting", "r-1")
    (parent, task), = FakeTasksClient.created
    assert parent.endswith("queues/analysis-jobs")
    http = task["http_request"]
    assert http["url"] == ("https://my-python-backend-quyiiugyoq-ue.a.run.app/jobs/lifting/r-1")
    assert http["oidc_token"]["service_account_email"].startswith("toms-gym-service@")
    assert task["dispatch_deadline"]["seconds"] == 900


def test_enqueue_errors_are_swallowed(monkeypatch):
    class Boom:
        def create_task(self, **kwargs):
            raise RuntimeError("tasks API down")
    monkeypatch.setattr(analysis_dispatch, "_tasks_client", lambda: Boom())
    analysis_dispatch.enqueue_analysis_job("bowling", "r-2")  # must not raise
