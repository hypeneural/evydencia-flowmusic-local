"""Local-only account profiles and read-only credit snapshots.

No automatic account rotation or quota bypass. FLOWMUSIC_HOME is supported by
the pinned upstream CLI (src/lib/config.mjs); each profile owns an OAuth
refresh-token chain. Neither credentials nor email addresses enter snapshots.
"""
from __future__ import annotations
import json
import os
import re
from datetime import datetime, timezone, timedelta
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
    return folder.is_dir() and not folder.is_symlink() and (folder / "session.json").is_file()

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
        stale = datetime.now(timezone.utc) - when > CACHE_VALID_FOR
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
    data = []
    for name in names:
        balance = credit_snapshot(name)
        data.append({"profile": name, "session_present": is_authenticated(name),
                     "credits_remaining": balance["credits_remaining"],
                     "checked_at": balance["checked_at"], "stale": balance["stale"]})
    # Inventory only: ranking by cached credits never selects an account for execution.
    return sorted(data, key=lambda r: (r["stale"], r["credits_remaining"] is None,
                                      -(r["credits_remaining"] or 0), r["profile"]))

def invalidate_snapshot(name: str) -> None:
    """A generation may consume credits: never show an old balance as fresh."""
    validate(name)
    (SNAPSHOTS / (name + ".json")).unlink(missing_ok=True)
