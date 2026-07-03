"""Pollers no-op in tasks mode so dispatch isn't duplicated."""
import toms_gym.integrations.lifting_processor as lp
import toms_gym.integrations.bowling_processor as bp


def test_lifting_poller_stands_down_in_tasks_mode(monkeypatch):
    monkeypatch.setenv("ANALYSIS_DISPATCH_MODE", "tasks")
    monkeypatch.setattr(lp, "LIFTING_PROCESSOR_ENABLED", True)
    started = []
    monkeypatch.setattr(lp.threading, "Thread", lambda **k: started.append(k))
    lp.start_lifting_processor()
    assert started == []


def test_bowling_poller_stands_down_in_tasks_mode(monkeypatch):
    monkeypatch.setenv("ANALYSIS_DISPATCH_MODE", "tasks")
    monkeypatch.setattr(bp, "BOWLING_PROCESSOR_ENABLED", True)
    started = []
    monkeypatch.setattr(bp.threading, "Thread", lambda **k: started.append(k))
    bp.start_bowling_processor()
    assert started == []
