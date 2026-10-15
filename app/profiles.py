"""Local-only account profiles and read-only credit snapshots.

No automatic account rotation or quota bypass. FLOWMUSIC_HOME is supported by
the pinned upstream CLI (src/lib/config.mjs); each profile owns an OAuth
refresh-token chain. Neither credentials nor email addresses enter snapshots.
"""
from __future__ import annotations
import json
import os
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ALIASES = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
PROFILES = DATA / "flowmusic-profiles"
SNAPSHOTS = DATA / "account-snapshots"
CACHE_VALID_FOR = timedelta(minutes=30)

def validate(name: str) -> str:
    if not isinstance(name, str) or not ALIASES.fullmatch(name):
        raise ValueError("Use an account alias with 1-32 lowercase letters, digits, - or _; starting with a letter")
    return name

def session_dir(name: str) -> Path:
    validate(name)
    if name == "default":
        return DATA / "flowmusic-session"
    return PROFILES / name

def is_authenticated(name: str) -> bool:
    folder = session_dir(name)
    token_file = folder / "session.json"
    return folder.is_dir() and not folder.is_symlink() and token_file.is_file() and not token_file.is_symlink()

def session_public_metadata(name: str) -> dict:
    """Inspect only non-secret fields of a locally saved CLI session.

    A file on disk does NOT prove online authentication. Never return tokens
    or raw session JSON. No remote call or token refresh happens here.
    """
    folder = session_dir(name)
    session = folder / "session.json"
    empty = {"email": None, "session_status": "not_connected",
             "access_expires_at": None, "refresh_available": False}
    if (not folder.is_dir() or folder.is_symlink() or
            not session.is_file() or session.is_symlink()):
        return empty
    try:
        if session.stat().st_size > 256 * 1024:
            raise ValueError("Session metadata too large")
        record = json.loads(session.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise ValueError("Invalid session format")
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {**empty, "session_status": "invalid_file"}
    email = record.get("email")
    if not isinstance(email, str) or len(email) > 254 or "@" not in email:
        email = None
    expires = record.get("expires_at")
    if not isinstance(expires, (int, float)) or isinstance(expires, bool):
        expires = None
    has_refresh = isinstance(record.get("refresh_token"), str) and bool(record["refresh_token"])
    if expires is None:
        status = "metadata_incomplete"
    elif expires > datetime.now(timezone.utc).timestamp() + 30:
        status = "access_valid_locally"
    elif has_refresh:
        status = "access_expired_refreshable"
    else:
        status = "access_expired"
    return {
        "email": email, "session_status": status,
        "access_expires_at": (
            datetime.fromtimestamp(expires, timezone.utc).isoformat(timespec="seconds")
            if expires is not None and 0 < expires < 4102444800 else None
        ),
        "refresh_available": has_refresh,
    }


def credit_snapshot(name: str) -> dict:
    validate(name)
    target = SNAPSHOTS / (name + ".json")
    try:
        record = json.loads(target.read_text(encoding="utf-8"))
        value = record["credits_remaining"]
        if type(value) is not int or value < 0 or not isinstance(record.get("checked_at"), str):
            raise ValueError("Invalid credit snapshot")
        when = datetime.fromisoformat(record["checked_at"])
        if when.tzinfo is None:
            raise ValueError("Credit check must have a timezone")
        age = datetime.now(timezone.utc) - when
        stale = bool(record.get("invalidated_at")) or age > CACHE_VALID_FOR or age < -timedelta(minutes=5)
        return {"credits_remaining": value, "checked_at": record["checked_at"], "stale": stale}
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return {"credits_remaining": None, "checked_at": None, "stale": True}

def save_snapshot(name: str, remaining: int) -> None:
    validate(name)
    if type(remaining) is not int or remaining < 0:
        raise ValueError("Cannot store a non-numeric credit balance")
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOTS / (name + ".json")
    temporary = SNAPSHOTS / (name + ".tmp")
    payload = {"credits_remaining": remaining, "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)

def list_profiles() -> list[dict]:
    names = {"default"}
    if PROFILES.is_dir() and not PROFILES.is_symlink():
        for directory in PROFILES.iterdir():
            if directory.is_dir() and not directory.is_symlink() and ALIASES.fullmatch(directory.name):
                names.add(directory.name)
    # Database identities survive session loss. The DB stores aliases only;
    # no passwords, OAuth credentials or duplicated credit snapshot sources.
    database = DATA / "jobs.db"
    if database.is_file():
        try:
            with closing(sqlite3.connect(database, timeout=3)) as conn:
                try:
                    names.update(row[0] for row in conn.execute(
                        "SELECT alias FROM account_profiles"
                    ) if ALIASES.fullmatch(row[0]))
                except sqlite3.OperationalError as exc:
                    if "no such table" not in str(exc):
                        raise
        except sqlite3.DatabaseError:
            # The inventory must not pretend a broken SQLite file is a valid
            # fresh credits result; profiles on disk remain queryable.
            pass
    data = []
    for name in names:
        balance = credit_snapshot(name)
        metadata = session_public_metadata(name)
        data.append({"profile": name, "session_present": is_authenticated(name),
                     **metadata,
                     "credits_remaining": balance["credits_remaining"],
                     "checked_at": balance["checked_at"], "stale": balance["stale"],
                     "recent_account_check": (
                         metadata["session_status"] not in {"not_connected", "invalid_file"}
                         and balance["credits_remaining"] is not None and not balance["stale"]
                     )})
    # Inventory only: ranking by cached credits never selects an account for execution.
    return sorted(data, key=lambda r: (r["stale"], r["credits_remaining"] is None,
                                      -(r["credits_remaining"] or 0), r["profile"]))

def invalidate_snapshot(name: str) -> None:
    """A generation may consume credits: never show an old balance as fresh."""
    validate(name)
    path = SNAPSHOTS / (name + ".json")
    if not path.is_file():
        return
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(old, dict) or type(old.get("credits_remaining")) is not int:
            raise ValueError("Malformed cached credits")
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        path.unlink(missing_ok=True)
        return
    # Keep the last known balance and timestamp as historical evidence, but
    # mark it stale as soon as a generation might have spent credits.
    old["invalidated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    tmp = path.with_suffix(".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(old, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
