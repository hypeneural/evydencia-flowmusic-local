"""Mock-first local music job API. No upstream network calls are implemented."""
from __future__ import annotations
import hashlib
import json
import os
import re
import secrets
import sqlite3
import subprocess
import threading
import uuid
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
DATA = ROOT / "data"
DB = DATA / "jobs.db"
TOKEN = DATA / "local-token.txt"
MUTEX = threading.Lock()

def get_provider() -> str:
    return os.getenv("FLOWMUSIC_PROVIDER", "mock")

def secure_token_file(path: Path) -> None:
    """Fail closed if the local API token cannot be restricted to its owner."""
    if os.name == "nt":
        user = os.getenv("USERNAME")
        if not user:
            raise RuntimeError("Cannot identify Windows user for token ACL")
        domain = os.getenv("USERDOMAIN")
        principal = f"{domain}\\{user}" if domain else user
        try:
            outcome = subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", f"{principal}:(F)"],
                capture_output=True, text=True, timeout=15, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("Cannot secure local API token with icacls") from exc
        if outcome.returncode != 0:
            raise RuntimeError("icacls rejected the local API token ACL")
    else:
        path.chmod(0o600)

class MusicRequest(BaseModel):
    request_id: str = Field(min_length=3, max_length=120, pattern=r"^[a-zA-Z0-9._:-]+$")
    prompt: str = Field(min_length=3, max_length=4000)
    model: str = Field(default="Lyria 3.5", max_length=100)
    title: str | None = Field(default=None, max_length=160)
    lyrics: str | None = Field(default=None, max_length=12000)
    instrumental: bool = False
    duration_seconds: int = Field(default=120, ge=60, le=600)
    output_format: str = Field(default="wav", pattern=r"^(wav|m4a|mp3)$")
    approve_live: bool = False
    account_profile: str = Field(default="default", pattern=r"^[a-z][a-z0-9_-]{0,31}$")

    @model_validator(mode="after")
    def validate_inline_music(self):
        """Fail before mock/live queue and before any paid provider submission."""
        if self.instrumental and self.lyrics is not None:
            raise ValueError("instrumental=true conflicts with lyrics")
        for label, value in (("title", self.title), ("lyrics", self.lyrics)):
            if value is None:
                continue
            if not value.strip():
                raise ValueError(f"{label} cannot be empty")
            # The pinned CLI treats a leading @ as a file reference.
            if value.lstrip().startswith("@"):
                raise ValueError(f"{label} must be inline text, not @file")
            if any(ord(char) < 32 and char not in ("\n", "\r", "\t") for char in value):
                raise ValueError(f"{label} contains control characters")
            if label == "title" and ("\n" in value or "\r" in value):
                raise ValueError("title must be on one line")
        # The public Flow Media gateway rejects payloads above 16 KiB.
        # Leave headroom for JSON escaping/headers and future fields.
        body = json.dumps(self.model_dump(), ensure_ascii=False, separators=(",", ":"))
        if len(body.encode("utf-8")) > 14 * 1024:
            raise ValueError("music payload exceeds safe gateway limit")
        return self


@contextmanager
def db():
    connection = sqlite3.connect(DB, timeout=15)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA busy_timeout=15000")
        with connection:
            yield connection
    finally:
        connection.close()

def bootstrap() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "output").mkdir(exist_ok=True)
    try:
        with TOKEN.open("x", encoding="utf-8") as handle:
            handle.write(secrets.token_urlsafe(48))
    except FileExistsError:
        pass
    # Re-check every startup, including tokens created by an earlier version.
    secure_token_file(TOKEN)
    with db() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                request_id TEXT UNIQUE NOT NULL,
                hash TEXT NOT NULL,
                payload TEXT NOT NULL,
                state TEXT NOT NULL,
                result TEXT,
                error TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        connection.execute(
            """UPDATE jobs SET state='needs_review',
                error='interrupted; remote acceptance unknown'
                WHERE state IN ('submitting','generating','downloading','validating')"""
        )

@asynccontextmanager
async def life(_app: FastAPI):
    bootstrap()
    from app import queue
    queue.migrate()
    queue.start()
    try:
        yield
    finally:
        queue.stop()

app = FastAPI(title="Evydencia FlowMusic Local", version="0.2.2", lifespan=life)
app.mount("/assets", StaticFiles(directory=str(STATIC)), name="assets")


@app.get("/painel-contas", response_class=HTMLResponse, include_in_schema=False)
def accounts_dashboard():
    """Public static shell only; the browser must authenticate for account data."""
    return HTMLResponse(
        content=(STATIC / "accounts.html").read_text(encoding="utf-8"),
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Content-Security-Policy": (
                "default-src 'none'; style-src 'self'; script-src 'self'; "
                "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; "
                "form-action 'none'"
            ),
        },
    )


def auth(x_local_token: str | None = Header(default=None)) -> None:
    try:
        expected = TOKEN.read_text(encoding="utf-8")
    except OSError:
        raise HTTPException(503, "Local authentication is not initialized") from None
    if not x_local_token or not secrets.compare_digest(x_local_token, expected):
        raise HTTPException(401, "Local token required")

def result(row: sqlite3.Row) -> dict:
    return {
        "job_id": row["id"],
        "account_profile": row["account_profile"],
        "request_id": row["request_id"],
        "status": row["state"],
        "result": json.loads(row["result"]) if row["result"] else None,
        "error": row["error"],
    }

def get_row(job_id: str) -> sqlite3.Row:
    with db() as connection:
        row = connection.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Unknown job")
    return row

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/v1/music/status", dependencies=[Depends(auth)])
def status():
    from app import queue
    return {"provider": get_provider(), **queue.overview(),
            "note": "Live queue only with server enablement and per-job approval"}

def make_mock_artifact(job_id: str, prompt: str) -> dict:
    """Publish the mock artifact atomically; never pretend it is audio."""
    artifact = DATA / "output" / f"{job_id}.json"
    temporary = DATA / "output" / f"{job_id}.tmp"
    contents = json.dumps({"mock": True, "prompt": prompt}, ensure_ascii=False).encode("utf-8")
    try:
        temporary.write_bytes(contents)
        os.replace(temporary, artifact)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "mock": True,
        "artifacts": [{"path": str(artifact), "sha256": hashlib.sha256(contents).hexdigest()}],
    }

@app.post("/v1/music/jobs", status_code=202, dependencies=[Depends(auth)])
def create(req: MusicRequest):
    payload = json.dumps(req.model_dump(), ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    from app import queue
    if queue.enabled():
        return queue.create_live(req, digest, payload)
    job_id = str(uuid.uuid4())
    with MUTEX:
        with db() as connection:
            # SQLite UNIQUE constraint is authoritative across processes.
            connection.execute("INSERT OR IGNORE INTO account_profiles(alias) VALUES(?)", (req.account_profile,))
            cursor = connection.execute(
                "INSERT OR IGNORE INTO jobs(id,request_id,hash,payload,state,account_profile) VALUES(?,?,?,?,?,?)",
                (job_id, req.request_id, digest, payload, "queued", req.account_profile),
            )
            row = connection.execute(
                "SELECT * FROM jobs WHERE request_id=?", (req.request_id,)
            ).fetchone()
            if row["hash"] != digest:
                raise HTTPException(409, "request_id already used")
            if cursor.rowcount == 0:
                return result(row)

    if get_provider() == "mock":
        try:
            value = make_mock_artifact(job_id, req.prompt)
        except OSError:
            with db() as connection:
                connection.execute(
                    "UPDATE jobs SET state='failed', error='Local mock artifact write failed' WHERE id=?",
                    (job_id,),
                )
        else:
            with db() as connection:
                connection.execute(
                    "UPDATE jobs SET state='completed',result=? WHERE id=?",
                    (json.dumps(value), job_id),
                )
    else:
        with db() as connection:
            connection.execute(
                "UPDATE jobs SET state='auth_required',error='Provider not activated' WHERE id=?",
                (job_id,),
            )
    return result(get_row(job_id))


@app.get("/v1/music/jobs", dependencies=[Depends(auth)])
def list_jobs(limit: int = 30):
    if not 1 <= limit <= 100:
        raise HTTPException(422, "limit must be 1..100")
    with db() as connection:
        rows = connection.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC,rowid DESC LIMIT ?", (limit,)
        ).fetchall()
    return {"jobs": [result(row) for row in rows]}

@app.get("/v1/music/accounts", dependencies=[Depends(auth)])
def accounts_inventory(response: Response):
    """Only public session metadata, last-known credits and alias; never tokens."""
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    from app import profiles, queue
    live_available = queue.enabled()
    inventory = profiles.list_profiles()
    with db() as connection:
        policy = {
            row["alias"]: dict(row) for row in connection.execute(
                "SELECT alias,enabled,auto_select FROM account_profiles")
        }
        pending = {
            row["account_profile"]:row["num"] for row in connection.execute(
                """SELECT account_profile,COUNT(*) AS num FROM jobs
                   WHERE run_mode='cli' AND state IN ('queued','submitting',
                            'generating','downloading','validating','needs_review')
                   GROUP BY account_profile""")
        }
    for profile in inventory:
        options = policy.get(profile["profile"], {})
        profile["enabled"] = bool(options.get("enabled", 1))
        profile["auto_select"] = bool(options.get("auto_select", 0))
        profile["blocking_jobs_count"] = pending.get(profile["profile"], 0)
        reasons = []
        if profile["blocking_jobs_count"]:
            reasons.append("profile_has_pending_or_uncertain_job")
        if not profile["enabled"]:
            reasons.append("account_disabled")
        if not profile["auto_select"]:
            reasons.append("auto_selection_not_enabled")
        if not live_available:
            reasons.append("music_live_provider_disabled")
        if profile["session_present"] is not True:
            reasons.append("session_not_present")
        # Locally unexpired token metadata and a recent provider account check
        # are only preflight indicators, NEVER proof of generation permission.
        if profile["session_status"] != "access_valid_locally":
            reasons.append("session_not_locally_current")
        if profile["stale"] or not profile["recent_account_check"]:
            reasons.append("credit_snapshot_stale")
        if type(profile["credits_remaining"]) is not int or profile["credits_remaining"] < 1:
            reasons.append("insufficient_known_credits")
        profile["eligible"] = not reasons
        profile["eligibility_reasons"] = reasons
        profile["eligibility_basis"] = "local_preflight_only"
        profile["next_auth_action"] = (
            "run_serialized_cli_account_check"
            if profile["session_status"]=="access_expired_refreshable"
            else "interactive_login_required"
            if profile["session_status"] in ("not_connected","invalid_file","access_expired")
            else "refresh_credit_snapshot_when_idle"
            if profile["stale"] else "none")
        profile["next_auth_action_is_non_generating"] = True
    return {"profiles": inventory, "live_enabled": live_available,
            "selection": "eligible_profiles_for_new_gateway_requests_only",
            "automatic_failover": False,
            "note": "Local eligibility is not live Google authentication or authorization; balances are cached."}


class MusicAccountRouting(BaseModel):
    enabled: bool = True
    auto_select: bool = False


@app.post("/v1/music/accounts/{alias}/routing", dependencies=[Depends(auth)])
def configure_music_account_routing(alias: str, body: MusicAccountRouting):
    """Local opt-in only. No OAuth, provider calls or session-file writes."""
    from app import profiles
    try:
        profiles.validate(alias)
    except ValueError:
        raise HTTPException(422, "invalid_music_profile") from None
    known = {r["profile"] for r in profiles.list_profiles()}
    if alias not in known:
        raise HTTPException(404, "music_profile_not_registered")
    with db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        if not body.enabled and connection.execute(
            """SELECT 1 FROM jobs WHERE account_profile=? AND run_mode='cli'
               AND state IN ('queued','submitting','generating','downloading','validating')
               LIMIT 1""", (alias,)
        ).fetchone():
            raise HTTPException(409, "music_profile_has_active_job")
        connection.execute("INSERT OR IGNORE INTO account_profiles(alias) VALUES(?)", (alias,))
        connection.execute("UPDATE account_profiles SET enabled=?,auto_select=? WHERE alias=?",
                           (int(body.enabled), int(body.auto_select), alias))
    return {"profile": alias, "enabled": body.enabled, "auto_select": body.auto_select,
            "affects_existing_jobs": False, "provider_login_changed": False}


@app.get("/v1/music/queue", dependencies=[Depends(auth)])
def queue_status():
    from app import queue
    return queue.overview()

@app.get("/v1/music/jobs/by-request/{request_id}", dependencies=[Depends(auth)])
def get_job_by_request_id(request_id: str):
    """Read-only, indexed reconciliation for gateway timeouts; no generation."""
    if len(request_id) < 3 or len(request_id) > 120 or re.fullmatch(r"[a-zA-Z0-9._:-]+", request_id) is None:
        raise HTTPException(422, "Invalid request_id")
    with db() as connection:
        row = connection.execute(
            "SELECT * FROM jobs WHERE request_id=? LIMIT 1", (request_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(404, "Unknown request_id")
    return result(row)


@app.get("/v1/music/jobs/{job_id}/events", dependencies=[Depends(auth)])
def job_events(job_id: str):
    get_row(job_id)
    with db() as connection:
        rows = connection.execute(
            "SELECT event,state,created_at FROM job_events WHERE job_id=? ORDER BY id LIMIT 200",
            (job_id,),
        ).fetchall()
    return {"events": [dict(row) for row in rows]}

@app.get("/v1/music/jobs/{job_id}", dependencies=[Depends(auth)])
def get_job(job_id: str):
    return result(get_row(job_id))

@app.get("/v1/music/jobs/{job_id}/artifacts", dependencies=[Depends(auth)])
def artifacts(job_id: str):
    record = get_job(job_id)
    if record["status"] != "completed":
        raise HTTPException(409, "Not completed")
    return record["result"]

class Reconciliation(BaseModel):
    resolution: Literal["abandoned", "completed"]
    confirmed_manual_review: bool = False


@app.post("/v1/music/jobs/{job_id}/reconcile", dependencies=[Depends(auth)])
def reconcile_job(job_id: str, body: Reconciliation):
    if not body.confirmed_manual_review:
        raise HTTPException(403, "Manual review confirmation required")
    from app import queue
    return queue.reconcile(job_id, body.resolution)


@app.post("/v1/music/queue/resume", dependencies=[Depends(auth)])
def resume_queue():
    from app import queue
    return queue.resume()


@app.get("/v1/music/credits", dependencies=[Depends(auth)])
def credits():
    return {
        "available": False,
        "reason": "Manual account diagnostic required; no remote calls from the server",
    }
