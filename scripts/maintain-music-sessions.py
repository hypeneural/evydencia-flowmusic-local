"""Bounded, opt-in FlowMusic session maintenance using the pinned CLI.

Dry-run by default. In execute mode, invokes only mvp_probe --mode account:
this checks models/credits and uses the upstream's own rotating Supabase
refresh-token mechanism if needed. NEVER launches an audio generation.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import profiles

STATE = ROOT / "data" / "session-maintenance"
DB = ROOT / "data" / "jobs.db"
PROBE = ROOT / "scripts" / "mvp_probe.py"
LOCK = STATE / "music-session-maintenance.lock"
MIN_SECONDS_BETWEEN_ATTEMPTS = 1800
RENEW_WITHIN_SECONDS = 900


def _read_last_attempt(alias: str) -> datetime | None:
    try:
        data=json.loads((STATE / (alias + ".json")).read_text(encoding="utf-8"))
        observed=datetime.fromisoformat(data["at"])
        return observed if observed.tzinfo else None
    except (OSError,ValueError,KeyError,TypeError):
        return None


def _write_attempt(alias: str, outcome: str) -> None:
    STATE.mkdir(parents=True,exist_ok=True)
    target=STATE / (alias + ".json")
    temp=target.with_suffix(".tmp")
    with temp.open("w",encoding="utf-8") as f:
        json.dump({"at":datetime.now(timezone.utc).isoformat(),"outcome":outcome},f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp,target)


def _busy(alias: str) -> bool:
    # Do not race with any ongoing generation or ambiguous provider attempt.
    if (ROOT/"data"/"mvp"/"generation.lock").exists():
        return True
    if not DB.is_file():
        return True
    try:
        with closing(sqlite3.connect(f"{DB.as_uri()}?mode=ro",uri=True,timeout=3)) as conn:
            active=conn.execute(
                """SELECT 1 FROM jobs WHERE run_mode='cli' AND
                   state IN ('queued','submitting','generating',
                             'downloading','validating') LIMIT 1"""
            ).fetchone()
            ambiguous=conn.execute(
                """SELECT 1 FROM jobs WHERE run_mode='cli'
                   AND account_profile=? AND state='needs_review' LIMIT 1""",
                (alias,)
            ).fetchone()
            return bool(active or ambiguous)
    except sqlite3.DatabaseError:
        return True


def decide(alias: str) -> dict:
    profiles.validate(alias)
    meta=profiles.session_public_metadata(alias)
    credits=profiles.credit_snapshot(alias)
    now=datetime.now(timezone.utc)
    last=_read_last_attempt(alias)
    retry_later=bool(last and timedelta(0)<=now-last<timedelta(seconds=MIN_SECONDS_BETWEEN_ATTEMPTS))
    expires=meta["access_expires_at"]
    due=False
    if expires:
        try:
            expiry=datetime.fromisoformat(expires.replace("Z","+00:00"))
            due=(expiry-now).total_seconds()<=RENEW_WITHIN_SECONDS
        except ValueError:
            due=True
    if meta["session_status"] in ("not_connected","invalid_file"):
        state="reauth_required"
    elif meta["session_status"]=="access_expired" and not meta["refresh_available"]:
        state="reauth_required"
    elif not meta["refresh_available"] and due:
        state="reauth_required"
    elif _busy(alias):
        state="blocked_by_generation_or_review"
    elif retry_later:
        state="cooldown"
    elif due or credits["stale"]:
        state="eligible_for_existing_cli_account_check"
    else:
        state="healthy_no_action"
    return {"profile":alias,"status":state,
            "session_status":meta["session_status"],
            "refresh_available":meta["refresh_available"],
            "access_expires_at":expires,
            "credit_snapshot_stale":credits["stale"],
            "generation_submitted":False}


def _probe_once(alias: str) -> bool:
    flags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=="nt" else 0
    child=subprocess.Popen([sys.executable,str(PROBE),"--mode","account","--profile",alias],
                           cwd=str(ROOT),stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                           creationflags=flags)
    try:
        return child.wait(timeout=180)==0
    except subprocess.TimeoutExpired:
        if os.name=="nt":
            try:
                subprocess.run(["taskkill","/PID",str(child.pid),"/T","/F"],
                               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                               check=False,timeout=10)
            except (OSError,subprocess.TimeoutExpired):
                child.kill()
        else:
            child.kill()
        try:
            child.wait(timeout=10)
        except (OSError,subprocess.TimeoutExpired):
            pass
        return False


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--profile",default="default")
    parser.add_argument("--all",action="store_true",help="check each locally registered profile")
    parser.add_argument("--execute",action="store_true",
                        help="run one authorized CLI account/credits check per eligible profile")
    args=parser.parse_args()
    names=([p["profile"] for p in profiles.list_profiles()] if args.all
           else [profiles.validate(args.profile)])
    results=[]
    STATE.mkdir(parents=True,exist_ok=True)
    # One exclusive lock for all profiles: rotating tokens must not overlap
    # with a second local maintenance process.
    from app.session_maintenance_lock import lock_maintenance
    try:
        with lock_maintenance(LOCK):
            for alias in names:
                before=decide(alias)
                if args.execute and before["status"]=="eligible_for_existing_cli_account_check":
                    if _busy(alias):
                        before["status"]="blocked_by_generation_or_review"
                    else:
                        ok=_probe_once(alias)
                        _write_attempt(alias,"ok" if ok else "failed")
                        if ok:
                            after=profiles.session_public_metadata(alias)
                            snap=profiles.credit_snapshot(alias)
                            before["status"]=("refreshed_and_checked"
                                              if after["session_status"]=="access_valid_locally"
                                              and not snap["stale"]
                                              else "reauth_or_provider_review_required")
                        else:
                            before["status"]="cli_refresh_failed_reauth_may_be_required"
                results.append(before)
    except BlockingIOError:
        print(json.dumps({"ok":False,"code":"maintenance_already_running"}))
        return 2
    print(json.dumps({"ok":True,"mode":"execute" if args.execute else "dry_run",
                      "profiles":results},ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
