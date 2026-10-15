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
from app import profiles


@pytest.fixture
def environment(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DATA", tmp_path)
    monkeypatch.setattr(api, "DB", tmp_path / "jobs.db")
    monkeypatch.setattr(api, "TOKEN", tmp_path / "local-token.txt")
    monkeypatch.setattr(profiles, "DATA", tmp_path)
    monkeypatch.setattr(profiles, "PROFILES", tmp_path / "flowmusic-profiles")
    monkeypatch.setattr(profiles, "SNAPSHOTS", tmp_path / "account-snapshots")
    # Isolated fixture only: never read or write real OAuth credentials in tests.
    session = tmp_path / "flowmusic-session"
    session.mkdir()
    (session / "session.json").write_text("{}", encoding="utf-8")
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
            json.dumps({"request_id": item["request_id"], "state": "completed", "profile": item.get("account_profile", "default"),
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


def test_profiles_sorted_by_fresh_credit_snapshot(environment):
    client, headers = environment
    second = profiles.session_dir("studio02")
    second.mkdir(parents=True)
    (second / "session.json").write_text("{}", encoding="utf-8")
    profiles.save_snapshot("default", 120)
    profiles.save_snapshot("studio02", 900)
    listing = client.get("/v1/music/accounts", headers=headers)
    assert listing.status_code == 200
    accounts = listing.json()["profiles"]
    assert [account["profile"] for account in accounts[:2]] == ["studio02", "default"]
    assert listing.json()["automatic_failover"] is False


def test_profile_explicit_and_existing_job_replay_without_session(environment):
    client, headers = environment
    profile = profiles.session_dir("studio03")
    profile.mkdir(parents=True)
    (profile / "session.json").write_text("{}", encoding="utf-8")
    payload = {**request(), "account_profile": "studio03"}
    posted = client.post("/v1/music/jobs", headers=headers, json=payload)
    assert posted.status_code == 202
    (profile / "session.json").unlink()
    retried = client.post("/v1/music/jobs", headers=headers, json=payload)
    assert retried.json()["job_id"] == posted.json()["job_id"]
    blocked = client.post("/v1/music/jobs", headers=headers,
                          json={**request(), "account_profile": "studio03"})
    assert blocked.status_code == 409


def test_music_account_eligibility_contract(environment):
    """The gateway must receive eligible=true only for live local preflight."""
    from datetime import datetime, timezone, timedelta
    client, headers = environment
    session = profiles.session_dir("default") / "session.json"
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
    session.write_text(json.dumps({"email": "test@example.invalid",
                                   "expires_at": expires}), encoding="utf-8")
    profiles.save_snapshot("default", 97)
    result = client.get("/v1/music/accounts", headers=headers)
    assert result.status_code == 200
    row = next(p for p in result.json()["profiles"] if p["profile"] == "default")
    assert row["eligible"] is True
    assert row["eligibility_basis"] == "local_preflight_only"
    assert row["credits_remaining"] == 97

    # Provider mock must NEVER make a profile selectable as a real live account.
    from app import queue
    old_mode = api.get_provider()
    try:
        import os
        os.environ["FLOWMUSIC_PROVIDER"] = "mock"
        blocked = client.get("/v1/music/accounts", headers=headers).json()
        p = next(x for x in blocked["profiles"] if x["profile"] == "default")
        assert p["eligible"] is False
        assert "music_live_provider_disabled" in p["eligibility_reasons"]
    finally:
        os.environ["FLOWMUSIC_PROVIDER"] = old_mode


def test_music_session_presence_does_not_prove_eligible(environment):
    client, headers = environment
    profiles.save_snapshot("default", 900)
    result = client.get("/v1/music/accounts", headers=headers).json()
    p = next(x for x in result["profiles"] if x["profile"] == "default")
    assert p["session_present"] is True
    assert p["eligible"] is False
    assert "session_not_locally_current" in p["eligibility_reasons"]


def test_uncertain_music_job_only_blocks_own_profile(environment):
    client, headers = environment
    studio=profiles.session_dir("studio02")
    studio.mkdir(parents=True)
    (studio/"session.json").write_text("{}", encoding="utf-8")
    first={**request(), "account_profile":"default"}
    second={**request(), "account_profile":"studio02"}
    jid1=client.post("/v1/music/jobs",headers=headers,json=first).json()["job_id"]
    jid2=client.post("/v1/music/jobs",headers=headers,json=second).json()["job_id"]
    a=queue.claim()
    assert a["id"]==jid1
    queue.finish(jid1,"needs_review")
    b=queue.claim()
    assert b is not None and b["id"]==jid2
    queue.finish(jid2,"completed",[{"path":"fixture","sha256":"fixture"}])
    assert client.get(f"/v1/music/jobs/{jid1}",headers=headers).json()["status"]=="needs_review"
    assert client.get(f"/v1/music/jobs/{jid2}",headers=headers).json()["status"]=="completed"
    blocked={**request(),"account_profile":"default"}
    assert client.post("/v1/music/jobs",headers=headers,json=blocked).status_code==409


def test_music_opt_in_policy_does_not_change_existing_jobs(environment):
    client,headers=environment
    from datetime import datetime,timezone,timedelta
    p=profiles.session_dir("default")/"session.json"
    p.write_text(json.dumps({"expires_at":(datetime.now(timezone.utc)+timedelta(hours=1)).timestamp()}),
                 encoding="utf-8")
    profiles.save_snapshot("default",123)
    before=client.get("/v1/music/accounts",headers=headers).json()["profiles"]
    existing=next(x for x in before if x["profile"]=="default")
    assert existing["eligible"] is False
    assert "auto_selection_not_enabled" in existing["eligibility_reasons"]
    changed=client.post("/v1/music/accounts/default/routing",headers=headers,
                        json={"enabled":True,"auto_select":True})
    assert changed.status_code==200
    assert changed.json()["affects_existing_jobs"] is False
    after=client.get("/v1/music/accounts",headers=headers).json()["profiles"]
    current=next(x for x in after if x["profile"]=="default")
    assert current["eligible"] is True
    denied=client.post("/v1/music/accounts/default/routing",json={"enabled":False,"auto_select":False})
    assert denied.status_code==401
