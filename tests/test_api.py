import os
os.environ["FLOWMUSIC_PROVIDER"] = "mock"
import uuid
from fastapi.testclient import TestClient
from app.main import app, TOKEN, db, bootstrap

def test_health():
    with TestClient(app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"ok": True}

def test_status():
    with TestClient(app) as client:
        assert client.get("/v1/music/status").status_code == 401
        h = {"X-Local-Token": TOKEN.read_text(encoding="utf-8")}
        res = client.get("/v1/music/status", headers=h)
        assert res.status_code == 200
        data = res.json()
        assert data["provider"] == "mock"
        assert data["live_enabled"] is False

def test_credits():
    with TestClient(app) as client:
        assert client.get("/v1/music/credits").status_code == 401
        h = {"X-Local-Token": TOKEN.read_text(encoding="utf-8")}
        res = client.get("/v1/music/credits", headers=h)
        assert res.status_code == 200
        data = res.json()
        assert data["available"] is False

def test_mock_job_lifecycle_and_idempotency():
    with TestClient(app) as client:
        h = {"X-Local-Token": TOKEN.read_text(encoding="utf-8")}
        req_id = f"test-lifecycle-{uuid.uuid4().hex[:8]}"
        payload = {"request_id": req_id, "prompt": "Lo-fi beats for studying"}

        # 1. Unauthenticated creation must fail
        assert client.post("/v1/music/jobs", json=payload).status_code == 401

        # 2. Create job
        res1 = client.post("/v1/music/jobs", json=payload, headers=h)
        assert res1.status_code == 202
        body1 = res1.json()
        assert body1["request_id"] == req_id
        assert body1["status"] == "completed"
        job_id = body1["job_id"]

        # 3. Fetch job by ID
        get_res = client.get(f"/v1/music/jobs/{job_id}", headers=h)
        assert get_res.status_code == 200
        assert get_res.json()["job_id"] == job_id

        # 4. Fetch artifacts
        art_res = client.get(f"/v1/music/jobs/{job_id}/artifacts", headers=h)
        assert art_res.status_code == 200
        assert art_res.json()["mock"] is True

        # 5. Idempotent repeat: same request_id and identical payload returns same job
        res2 = client.post("/v1/music/jobs", json=payload, headers=h)
        assert res2.status_code == 202
        assert res2.json()["job_id"] == job_id

        # 6. Payload conflict: same request_id with different payload returns 409
        conflict_payload = {**payload, "prompt": "Heavy metal guitar solo"}
        conflict_res = client.post("/v1/music/jobs", json=conflict_payload, headers=h)
        assert conflict_res.status_code == 409
        assert "request_id already used" in conflict_res.json()["detail"]

def test_job_not_found():
    with TestClient(app) as client:
        h = {"X-Local-Token": TOKEN.read_text(encoding="utf-8")}
        res = client.get("/v1/music/jobs/non-existent-uuid", headers=h)
        assert res.status_code == 404
        assert res.json()["detail"] == "Unknown job"

def test_artifacts_not_completed():
    with TestClient(app) as client:
        h = {"X-Local-Token": TOKEN.read_text(encoding="utf-8")}
        fake_id = str(uuid.uuid4())
        with db() as c:
            c.execute(
                "INSERT INTO jobs (id, request_id, hash, payload, state) VALUES (?, ?, ?, ?, ?)",
                (fake_id, f"req-{fake_id}", "dummyhash", "{}", "queued"),
            )
        res = client.get(f"/v1/music/jobs/{fake_id}/artifacts", headers=h)
        assert res.status_code == 409
        assert res.json()["detail"] == "Not completed"

def test_restart_recovery_needs_review():
    # Insert test jobs in transient interrupted states
    j1, j2, j3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    with db() as c:
        c.execute("INSERT INTO jobs (id, request_id, hash, payload, state) VALUES (?, ?, ?, ?, ?)", (j1, f"req-{j1}", "h1", "{}", "submitting"))
        c.execute("INSERT INTO jobs (id, request_id, hash, payload, state) VALUES (?, ?, ?, ?, ?)", (j2, f"req-{j2}", "h2", "{}", "generating"))
        c.execute("INSERT INTO jobs (id, request_id, hash, payload, state) VALUES (?, ?, ?, ?, ?)", (j3, f"req-{j3}", "h3", "{}", "downloading"))

    # Execute server restart/bootstrap
    bootstrap()

    with db() as c:
        for jid in (j1, j2, j3):
            row = c.execute("SELECT state, error FROM jobs WHERE id=?", (jid,)).fetchone()
            assert row["state"] == "needs_review"
            assert "interrupted; remote acceptance unknown" in row["error"]

def test_provider_disabled_gate(monkeypatch):
    monkeypatch.setenv("FLOWMUSIC_PROVIDER", "live_unsupported")
    with TestClient(app) as client:
        h = {"X-Local-Token": TOKEN.read_text(encoding="utf-8")}
        req_id = f"test-gate-{uuid.uuid4().hex[:8]}"
        res = client.post("/v1/music/jobs", json={"request_id": req_id, "prompt": "Piano"}, headers=h)
        assert res.status_code == 202
        data = res.json()
        assert data["status"] == "auth_required"
        assert data["error"] == "Provider not activated"
