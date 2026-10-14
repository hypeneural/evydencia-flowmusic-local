"""Durable, single-consumer Windows queue around the already-proven MVP probe.

The provider process is NEVER retried here. An uncertain upstream submission is
quarantined as needs_review and freezes future work until a human reconciles it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from app import main as api

PROBE = api.ROOT / "scripts" / "mvp_probe.py"
STOP = threading.Event()
WORKER: threading.Thread | None = None
BLOCKED: str | None = None


def enabled() -> bool:
    return api.get_provider() == "cli" and os.getenv("FLOWMUSIC_ALLOW_LIVE", "").lower() == "true"


def event(conn: Any, job_id: str, name: str, state: str) -> None:
    """Controlled codes only; never log raw prompts, headers or provider responses."""
    conn.execute(
        "INSERT INTO job_events(job_id,event,state) VALUES(?,?,?)",
        (job_id, name, state),
    )


def migrate() -> None:
    """Non-destructive migration of the original MVP SQLite database."""
    with api.db() as conn:
        columns = {r[1] for r in conn.execute("PRAGMA table_info(jobs)")}
        if "run_mode" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN run_mode TEXT NOT NULL DEFAULT 'mock'")
        if "approved_live" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN approved_live INTEGER NOT NULL DEFAULT 0")
        if "attempt_count" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0")
        if "updated_at" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN updated_at TEXT")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS job_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            event TEXT NOT NULL,
            state TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_queue ON jobs(run_mode,state,created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_job_events ON job_events(job_id,id)")
        # Historical queued mock records must not be promoted to live.
        conn.execute(
            """UPDATE jobs SET state='needs_review',
               error='interrupted queue submission: confirm whether upstream accepted'
               WHERE run_mode='cli' AND state='submitting'"""
        )


def create_live(req: Any, digest: str, payload: str) -> dict:
    """Persist approval and intent atomically before the background worker can claim."""
    from uuid import uuid4

    if not enabled():
        raise api.HTTPException(503, "Live queue is disabled")
    if not req.approve_live:
        raise api.HTTPException(403, "Explicit approve_live=true required")
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,80}", req.request_id):
        raise api.HTTPException(422, "request_id is incompatible with pinned MVP probe")
    if req.lyrics:
        raise api.HTTPException(422, "Live custom lyrics require a reviewed adapter; not silently ignored")
    job_id = str(uuid4())
    with api.db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM jobs WHERE request_id=?", (req.request_id,)).fetchone()
        if row:
            if row["hash"] != digest:
                raise api.HTTPException(409, "request_id already used")
            return api.result(row)
        pending = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE run_mode='cli' AND state IN ('queued','submitting','generating')"
        ).fetchone()[0]
        if (api.DATA / "mvp" / "ledger" / (req.request_id + ".json")).exists():
            raise api.HTTPException(409, "Existing MVP ledger requires manual reconciliation")
        if pending >= 25:
            raise api.HTTPException(429, "Local queue full (25); reduce requests")
        conn.execute(
            """INSERT INTO jobs(id,request_id,hash,payload,state,run_mode,approved_live,updated_at)
               VALUES(?,?,?,?,?,'cli',1,CURRENT_TIMESTAMP)""",
            (job_id, req.request_id, digest, payload, "queued"),
        )
        event(conn, job_id, "job.accepted", "queued")
    return api.result(api.get_row(job_id))


def claim() -> dict | None:
    """BEGIN IMMEDIATE provides single-consumer claim even with distinct processes."""
    with api.db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        # Cross-process single-flight: never claim while another job is submitting.
        if conn.execute("SELECT 1 FROM jobs WHERE run_mode='cli' AND state='submitting' LIMIT 1").fetchone():
            return None
        row = conn.execute(
            """SELECT * FROM jobs WHERE state='queued' AND run_mode='cli'
               AND approved_live=1 ORDER BY created_at, rowid LIMIT 1"""
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """UPDATE jobs SET state='submitting',attempt_count=attempt_count+1,
               updated_at=CURRENT_TIMESTAMP WHERE id=? AND state='queued'""",
            (row["id"],),
        )
        event(conn, row["id"], "job.claimed", "submitting")
        return dict(row)


def finish(job_id: str, state: str, artifacts: list[dict] | None = None) -> None:
    if state not in {"completed", "needs_review"}:
        raise ValueError("Unsupported worker state")
    with api.db() as conn:
        conn.execute(
            """UPDATE jobs SET state=?,result=?,error=?,updated_at=CURRENT_TIMESTAMP
               WHERE id=? AND state='submitting'""",
            (state, json.dumps({"artifacts": artifacts}, ensure_ascii=False) if artifacts else None,
             "Remote outcome uncertain; reconcile MVP ledger and provider library" if state != "completed" else None,
             job_id),
        )
        event(conn, job_id, "job.completed" if state == "completed" else "job.needs_review", state)


def verified_artifacts(request_id: str) -> list[dict]:
    ledger_file = api.DATA / "mvp" / "ledger" / (request_id + ".json")
    ledger = json.loads(ledger_file.read_text(encoding="utf-8"))
    if ledger.get("state") != "completed" or ledger.get("request_id") != request_id:
        raise ValueError("MVP ledger is not completed for this request")
    output = (api.DATA / "mvp" / "output" / request_id).resolve()
    artifacts = ledger.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("No audio artifacts")
    verified = []
    for item in artifacts:
        path = Path(item["file"]).resolve()
        if not path.is_relative_to(output) or not path.is_file() or path.stat().st_size < 1024:
            raise ValueError("Missing/outside/empty artifact")
        digest = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != item.get("sha256"):
            raise ValueError("SHA-256 mismatch")
        verified.append({"path": str(path), "bytes": path.stat().st_size,
                         "sha256": digest.hexdigest(), "variant": item.get("variant")})
    return verified


def execute(record: dict, *, runner=None) -> None:
    """Run exactly once; discard raw stderr/stdout to keep secrets out of logs."""
    global BLOCKED
    req = json.loads(record["payload"])
    request_id = record["request_id"]
    command = [
        sys.executable, str(PROBE), "--mode", "generate",
        "--request-id", request_id, "--prompt", req["prompt"],
        "--model", req.get("model", "Lyria 3.5"),
        "--seconds", str(req.get("duration_seconds", 120)),
        "--format", req.get("output_format", "wav"), "--approve-live",
    ]
    if req.get("instrumental"):
        command.append("--instrumental")
    process = runner if runner is not None else subprocess.run
    try:
        done = process(command, cwd=str(api.ROOT), capture_output=True,
                       text=True, timeout=1320, check=False)
        if done.returncode != 0:
            raise RuntimeError("MVP probe did not complete")
        artifacts = verified_artifacts(request_id)
    except Exception:
        # Any failure (including timeout) could follow remote acceptance.
        finish(record["id"], "needs_review")
        BLOCKED = "needs_review"
        return
    finish(record["id"], "completed", artifacts)


def run_once(*, runner=None) -> bool:
    """Return True only when one job was claimed; never retry."""
    global BLOCKED
    if BLOCKED or not enabled():
        return False
    if (api.DATA / "mvp" / "generation.lock").exists():
        BLOCKED = "existing_generation_lock"
        return False
    with api.db() as conn:
        if conn.execute(
            "SELECT 1 FROM jobs WHERE run_mode='cli' AND state='needs_review' LIMIT 1"
        ).fetchone():
            BLOCKED = "unresolved_job"
            return False
    record = claim()
    if not record:
        return False
    execute(record, runner=runner)
    return True


def loop() -> None:
    global BLOCKED
    while not STOP.is_set():
        try:
            worked = run_once()
        except Exception:
            # DB, permissions or local I/O failures are not reasons to retry a
            # possibly-accepted Google generation.
            BLOCKED = "worker_error"
            worked = False
        STOP.wait(0.2 if worked else 0.75)


def start() -> None:
    global WORKER, BLOCKED
    if not enabled():
        return
    if not PROBE.is_file():
        raise RuntimeError("MVP probe is missing")
    if WORKER is not None and WORKER.is_alive():
        return
    BLOCKED = None
    STOP.clear()
    WORKER = threading.Thread(target=loop, name="flowmusic-single-worker", daemon=True)
    WORKER.start()


def stop() -> None:
    STOP.set()
    if WORKER is not None and WORKER.is_alive():
        WORKER.join(timeout=0.5)



def reconcile(job_id: str, resolution: str) -> dict:
    """Manual audit of uncertain work; never re-enqueues or repeats a generation."""
    if resolution not in {"completed", "abandoned"}:
        raise api.HTTPException(422, "resolution must be completed or abandoned")
    row = api.get_row(job_id)
    if row["run_mode"] != "cli" or row["state"] != "needs_review":
        raise api.HTTPException(409, "Only unresolved live jobs may be reconciled")
    artifacts = None
    if resolution == "completed":
        try:
            artifacts = verified_artifacts(row["request_id"])
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            raise api.HTTPException(409, "Completed MVP ledger and matching audio required") from None
    with api.db() as conn:
        conn.execute(
            """UPDATE jobs SET state=?, result=?, error=?, updated_at=CURRENT_TIMESTAMP
               WHERE id=? AND state='needs_review'""",
            (resolution, json.dumps({"artifacts": artifacts}) if artifacts else None,
             "Reviewed and abandoned; no re-submission performed" if resolution == "abandoned" else None, job_id),
        )
        event(conn, job_id, "job.reconciled", resolution)
    return api.result(api.get_row(job_id))


def resume() -> dict:
    global BLOCKED
    if not enabled():
        raise api.HTTPException(503, "Live queue disabled")
    if (api.DATA / "mvp" / "generation.lock").exists():
        raise api.HTTPException(409, "MVP generation lock remains; stop and inspect process/library")
    with api.db() as conn:
        if conn.execute(
            "SELECT 1 FROM jobs WHERE run_mode='cli' AND state='needs_review' LIMIT 1"
        ).fetchone():
            raise api.HTTPException(409, "Unresolved jobs remain; reconcile first")
    BLOCKED = None
    return overview()


def overview() -> dict:
    with api.db() as conn:
        counts = {r[0]: r[1] for r in conn.execute(
            "SELECT state,COUNT(*) FROM jobs GROUP BY state"
        )}
    return {"live_enabled": enabled(), "worker_running": bool(WORKER and WORKER.is_alive()),
            "blocked": BLOCKED, "counts": counts, "max_pending": 25}
