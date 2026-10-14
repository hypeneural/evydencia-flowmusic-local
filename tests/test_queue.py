"""Queue integration checks: zero remote calls, isolated SQLite and fake provider."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app import main as api
from app import queue


@pytest.fixture
def environment(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DATA", tmp_path)
    monkeypatch.setattr(api, "DB", tmp_path / "jobs.db")
    monkeypatch.setattr(api, "TOKEN", tmp_path / "local-token.txt")
    monkeypatch.setenv("FLOWMUSIC_PROVIDER", "mock")
    monkeypatch.delenv("FLOWMUSIC_ALLOW_LIVE", raising=False)
    monkeypatch.setattr(queue, "BLOCKED", None)
    with TestClient(api.app) as client:
        # Enable API live queue only AFTER lifespan, so no worker is spawned.
        monkeypatch.setenv("FLOWMUSIC_PROVIDER", "cli")
        monkeypatch.setenv("FLOWMUSIC_ALLOW_LIVE", "true")
        yield client, {"X-Local-Token": api.TOKEN.read_text(encoding="utf-8")}


def request():
    return {
        "request_id": f"queue-{uuid4().hex[:16]}",
        "prompt": "Original soft Christmas piano",
        "instrumental": True,
        "model": "Lyria 3.5",
        "output_format": "wav",
        "approve_live": True,
    }


def test_queue_requires_explicit_approval(environment):
    client, h = environment
    item = request()
    assert client.post("/v1/music/jobs", headers=h, json={**item, "approve_live": False}).status_code == 403
    first = client.post("/v1/music/jobs", headers=h, json=item)
    assert first.status_code == 202
    assert first.json()["status"] == "queued"
    second = client.post("/v1/music/jobs", headers=h, json=item)
    assert second.json()["job_id"] == first.json()["job_id"]
    assert client.post("/v1/music/jobs", headers=h, json={**item, "prompt": "Changed"}).status_code == 409
    assert client.get("/v1/music/queue", headers=h).json()["counts"]["queued"] == 1
    assert client.get("/v1/music/jobs", headers=h).json()["jobs"][0]["job_id"] == first.json()["job_id"]


def test_single_claim_and_no_retry_after_ambiguous_failure(environment):
    client, h = environment
    item = request()
    job_id = client.post("/v1/music/jobs", headers=h, json=item).json()["job_id"]
    claimed = queue.claim()
    assert claimed["id"] == job_id
    assert queue.claim() is None
    queue.finish(job_id, "needs_review")
    assert client.get(f"/v1/music/jobs/{job_id}", headers=h).json()["status"] == "needs_review"
    events = client.get(f"/v1/music/jobs/{job_id}/events", headers=h).json()["events"]
    assert [e["event"] for e in events] == ["job.accepted", "job.claimed", "job.needs_review"]
    assert queue.run_once(runner=lambda *_a, **_k: pytest.fail("No retry permitted")) is False


def test_one_successful_worker_job_with_fake_audio(environment):
    client, h = environment
    item = request()
    job_id = client.post("/v1/music/jobs", headers=h, json=item).json()["job_id"]
    assert queue.BLOCKED is None

    def fake_runner(command, **_kwargs):
        # No Node, network, browser or Google calls.
        out = api.DATA / "mvp" / "output" / item["request_id"]
        out.mkdir(parents=True)
        wav = out / "test.wav"
        wav.write_bytes(b"RIFF" + b"0" * 8192)
        ledger = api.DATA / "mvp" / "ledger"
        ledger.mkdir(parents=True)
        (ledger / (item["request_id"] + ".json")).write_text(
            json.dumps({"request_id": item["request_id"], "state": "completed",
                        "artifacts": [{"file": str(wav), "sha256": hashlib.sha256(wav.read_bytes()).hexdigest()}]}),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0)

    assert queue.run_once(runner=fake_runner)
    actual = client.get(f"/v1/music/jobs/{job_id}", headers=h).json()
    assert actual["status"] == "completed"
    assert len(actual["result"]["artifacts"]) == 1
    assert queue.run_once(runner=fake_runner) is False


def test_crash_recovery_does_not_resubmit(environment):
    client, h = environment
    item = request()
    jid = client.post("/v1/music/jobs", headers=h, json=item).json()["job_id"]
    queue.claim()
    api.bootstrap()
    queue.migrate()
    response = client.get(f"/v1/music/jobs/{jid}", headers=h)
    assert response.json()["status"] == "needs_review"
    assert queue.run_once(runner=lambda *_a, **_k: pytest.fail("Double submit")) is False


def test_historical_manual_ledger_cannot_be_overwritten(environment):
    client, h = environment
    item = request()
    old = api.DATA / "mvp" / "ledger" / (item["request_id"] + ".json")
    old.parent.mkdir(parents=True)
    old.write_text('{"state":"completed"}', encoding="utf-8")
    assert client.post("/v1/music/jobs", headers=h, json=item).status_code == 409


def test_manual_reconciliation_and_resume(environment):
    client, h = environment
    item = request()
    job_id = client.post("/v1/music/jobs", headers=h, json=item).json()["job_id"]
    queue.claim()
    queue.finish(job_id, "needs_review")
    assert client.post(
        f"/v1/music/jobs/{job_id}/reconcile", headers=h,
        json={"resolution": "abandoned", "confirmed_manual_review": False},
    ).status_code == 403
    assert client.post("/v1/music/queue/resume", headers=h).status_code == 409
    reviewed = client.post(
        f"/v1/music/jobs/{job_id}/reconcile", headers=h,
        json={"resolution": "abandoned", "confirmed_manual_review": True},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "abandoned"
    queue.BLOCKED = "unresolved_job"
    assert client.post("/v1/music/queue/resume", headers=h).status_code == 200
    assert queue.BLOCKED is None


def test_existing_manual_lock_stops_worker(environment):
    client, h = environment
    item = request()
    assert client.post("/v1/music/jobs", headers=h, json=item).status_code == 202
    lock = api.DATA / "mvp" / "generation.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text('{"request_id": "previous-manual"}', encoding="utf-8")
    assert queue.run_once(runner=lambda *_a, **_k: pytest.fail("MVP lock must stop worker")) is False
    assert queue.BLOCKED == "existing_generation_lock"
    assert client.post("/v1/music/queue/resume", headers=h).status_code == 409


def test_live_queue_is_disabled_by_default(environment, monkeypatch):
    client, h = environment
    monkeypatch.delenv("FLOWMUSIC_ALLOW_LIVE")
    assert client.post("/v1/music/jobs", headers=h, json=request()).json()["status"] == "auth_required"


def test_two_pending_jobs_cannot_run_simultaneously(environment):
    client, h = environment
    a, b = request(), request()
    assert client.post("/v1/music/jobs", headers=h, json=a).status_code == 202
    assert client.post("/v1/music/jobs", headers=h, json=b).status_code == 202
    first = queue.claim()
    assert first is not None
    # Even distinct processes must not start the second job while one is in flight.
    assert queue.claim() is None
    queue.finish(first["id"], "completed", [{"path": "simulated", "sha256": "fake"}])
    second = queue.claim()
    assert second is not None
    assert second["id"] != first["id"]
