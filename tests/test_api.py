"""All tests use an isolated temporary DB; never touch real Windows data."""
import hashlib
import uuid
import os
import pytest
from fastapi.testclient import TestClient
from app import main

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DATA", tmp_path)
    monkeypatch.setattr(main, "DB", tmp_path / "jobs.db")
    monkeypatch.setattr(main, "TOKEN", tmp_path / "local-token.txt")
    monkeypatch.setenv("FLOWMUSIC_PROVIDER", "mock")
    with TestClient(main.app) as api:
        yield api, {"X-Local-Token": main.TOKEN.read_text(encoding="utf-8")}

def unique_payload():
    return {"request_id": "test-" + uuid.uuid4().hex, "prompt": "Piano natalino"}

def test_health(client):
    api, _ = client
    assert api.get("/health").json() == {"ok": True}

def test_auth_status_credits(client):
    api, headers = client
    assert api.get("/v1/music/status").status_code == 401
    assert api.get("/v1/music/status", headers=headers).json()["live_enabled"] is False
    assert api.get("/v1/music/credits", headers=headers).json()["available"] is False
    assert api.get("/v1/music/credits").status_code == 401

def test_idempotency_and_artifacts(client):
    api, headers = client
    payload = unique_payload()
    assert api.post("/v1/music/jobs", json=payload).status_code == 401
    first = api.post("/v1/music/jobs", headers=headers, json=payload)
    assert first.status_code == 202
    assert first.json()["status"] == "completed"
    job_id = first.json()["job_id"]
    second = api.post("/v1/music/jobs", headers=headers, json=payload)
    assert second.json()["job_id"] == job_id
    artifact = api.get(f"/v1/music/jobs/{job_id}/artifacts", headers=headers).json()
    assert artifact["mock"] is True
    file = main.DATA / "output" / (job_id + ".json")
    assert artifact["artifacts"][0]["sha256"] == hashlib.sha256(file.read_bytes()).hexdigest()
    conflict = api.post("/v1/music/jobs", headers=headers, json={**payload, "prompt": "Other"})
    assert conflict.status_code == 409

def test_missing_and_not_completed(client):
    api, headers = client
    assert api.get("/v1/music/jobs/invalid", headers=headers).status_code == 404
    job_id = str(uuid.uuid4())
    with main.db() as connection:
        connection.execute(
            "INSERT INTO jobs (id,request_id,hash,payload,state) VALUES(?,?,?,?,?)",
            (job_id, "queued-" + job_id, "x", "{}", "queued"),
        )
    assert api.get(f"/v1/music/jobs/{job_id}/artifacts", headers=headers).status_code == 409

def test_restart_recovery(client):
    _, _headers = client
    ids = [str(uuid.uuid4()) for _ in range(4)]
    with main.db() as connection:
        for uid, state in zip(ids, ["submitting", "generating", "downloading", "validating"]):
            connection.execute(
                "INSERT INTO jobs (id,request_id,hash,payload,state) VALUES(?,?,?,?,?)",
                (uid, uid, "x", "{}", state),
            )
    main.bootstrap()
    with main.db() as connection:
        assert all(
            connection.execute("SELECT state FROM jobs WHERE id=?", (uid,)).fetchone()["state"] == "needs_review"
            for uid in ids
        )

def test_unsupported_provider(client, monkeypatch):
    api, headers = client
    monkeypatch.setenv("FLOWMUSIC_PROVIDER", "cli")
    job = api.post("/v1/music/jobs", json=unique_payload(), headers=headers)
    assert job.json()["status"] == "auth_required"

def test_mock_disk_failure(client, monkeypatch):
    api, headers = client
    def fail(_id, _prompt):
        raise OSError("disk error")
    monkeypatch.setattr(main, "make_mock_artifact", fail)
    payload = unique_payload()
    response = api.post("/v1/music/jobs", json=payload, headers=headers)
    assert response.status_code == 202
    assert response.json()["status"] == "failed"
    repeat = api.post("/v1/music/jobs", json=payload, headers=headers)
    assert repeat.json()["job_id"] == response.json()["job_id"]

def test_existing_token_acl_reapplied(client, monkeypatch):
    _, _ = client
    calls = []
    monkeypatch.setattr(main, "secure_token_file", lambda path: calls.append(path))
    main.bootstrap()
    assert calls == [main.TOKEN]

def test_token_acl_failure_prevents_startup(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DATA", tmp_path)
    monkeypatch.setattr(main, "DB", tmp_path / "jobs.db")
    monkeypatch.setattr(main, "TOKEN", tmp_path / "local-token.txt")
    def fail(_):
        raise RuntimeError("Cannot apply ACL")
    monkeypatch.setattr(main, "secure_token_file", fail)
    with pytest.raises(RuntimeError, match="Cannot apply ACL"):
        main.bootstrap()
    assert not main.DB.exists()

def test_token_file_permission_on_posix(client):
    if os.name == "nt":
        pytest.skip("POSIX-only permission check")
    assert main.TOKEN.stat().st_mode & 0o077 == 0


def test_get_job_by_request_id_is_direct_and_never_generates(client):
    api, headers = client
    payload = unique_payload()
    created = api.post("/v1/music/jobs", json=payload, headers=headers)
    assert created.status_code == 202
    expected = created.json()["job_id"]
    denied = api.get(f"/v1/music/jobs/by-request/{payload['request_id']}")
    assert denied.status_code == 401
    found = api.get(f"/v1/music/jobs/by-request/{payload['request_id']}", headers=headers)
    assert found.status_code == 200
    assert found.json()["job_id"] == expected
    assert found.json()["request_id"] == payload["request_id"]
    assert api.get("/v1/music/jobs/by-request/unknown-xyz",headers=headers).status_code == 404
    assert api.get("/v1/music/jobs/by-request/invalid!",headers=headers).status_code == 422


def test_request_id_lookup_is_not_limited_to_last_100_jobs(client):
    api, headers = client
    with main.db() as connection:
        for i in range(111):
            rid = f"long-history-{i:03d}"
            connection.execute(
                "INSERT INTO jobs(id,request_id,hash,payload,state) VALUES(?,?,?,?,?)",
                (str(uuid.uuid4()), rid, "fixture-hash", "{}", "queued"),
            )
    found = api.get("/v1/music/jobs/by-request/long-history-000", headers=headers)
    assert found.status_code == 200
    assert found.json()["request_id"] == "long-history-000"
    listed = api.get("/v1/music/jobs?limit=100",headers=headers)
    assert listed.status_code == 200
    assert all(x["request_id"] != "long-history-000" for x in listed.json()["jobs"])
