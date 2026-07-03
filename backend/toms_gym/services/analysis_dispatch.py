"""Enqueue analysis jobs onto Cloud Tasks.

Replaces the in-process daemon pollers (integrations/lifting_processor.py,
integrations/bowling_processor.py): job creation enqueues an OIDC-authenticated
HTTP task that POSTs back to this backend's /jobs/<kind>/<result_id> handler.
Gated by ANALYSIS_DISPATCH_MODE=tasks so cutover is a config change.
"""
import logging
import os

logger = logging.getLogger(__name__)

# All env reads happen at call time (not import) so tests and Cloud Run
# revisions can flip modes without module reloads.


def dispatch_enabled() -> bool:
    return os.environ.get('ANALYSIS_DISPATCH_MODE', 'poller') == 'tasks'


def _tasks_client():
    from google.cloud import tasks_v2
    return tasks_v2.CloudTasksClient()


def enqueue_analysis_job(kind: str, result_id: str) -> None:
    """kind: 'lifting' | 'bowling'. No-op unless ANALYSIS_DISPATCH_MODE=tasks.

    Never raises: an enqueue failure must not fail the user-facing request
    that created the job row; the row stays 'queued' for manual re-trigger.
    """
    if not dispatch_enabled():
        return
    if kind not in ('lifting', 'bowling'):
        logger.error(f"enqueue_analysis_job: unknown kind {kind!r}")
        return
    try:
        from google.cloud import tasks_v2
        queue = os.environ['ANALYSIS_TASKS_QUEUE']
        base_url = os.environ['TASKS_TARGET_BASE_URL'].rstrip('/')
        sa_email = os.environ['TASKS_SERVICE_ACCOUNT']
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{base_url}/jobs/{kind}/{result_id}",
                "oidc_token": {
                    "service_account_email": sa_email,
                    "audience": base_url,
                },
            },
            # Must exceed the longest analysis hold (~620s poller timeout today).
            "dispatch_deadline": {"seconds": 900},
        }
        _tasks_client().create_task(parent=queue, task=task)
        logger.info(f"Enqueued {kind} analysis job {result_id}")
    except Exception as e:
        logger.error(f"Failed to enqueue {kind} job {result_id}: {e}")
