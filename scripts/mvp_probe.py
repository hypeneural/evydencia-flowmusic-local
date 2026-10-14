"""Windows-first, operator-invoked Flow Music MVP probe.

No imports from app/main.py and no automatic Google operations at startup.
The consumer website protocol is unofficial; explicit live consent is required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "flowmusic-cli"
ENTRY = VENDOR / "bin" / "flowmusic.mjs"
PIN = "08491dc3319ae9f530c5c05c431196bbbbb10607"
SESSION = ROOT / "data" / "flowmusic-session"  # Legacy default; overridden by --profile
MVP = ROOT / "data" / "mvp"
LEDGER = MVP / "ledger"
OUTPUT = MVP / "output"
EVENTS = MVP / "events.jsonl"
VALID_ID = re.compile(r"^[a-zA-Z0-9._-]{3,80}$")

# A script launched as scripts/mvp_probe.py needs the repository on sys.path.
sys.path.insert(0, str(ROOT))
from app import profiles


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def event(name: str, **fields: object) -> None:
    """Allow-list prevents accidentally logging credentials, lyrics or URLs."""
    accepted = {"request_id", "model", "status", "elapsed_ms", "variant_count",
                "profile",
                "artifact_count", "error_class", "phase"}
    safe = {"ts": timestamp(), "event": name}
    safe.update({key: value for key, value in fields.items() if key in accepted and value is not None})
    MVP.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(safe, ensure_ascii=False) + "\n")
        handle.flush()


def command(parts: list[str], *, timeout: int = 120, interactive: bool = False):
    env = os.environ.copy()
    # The upstream CLI accepts env access tokens and custom API endpoints.
    # Both would silently override the selected local account/session or server.
    env.pop("FLOWMUSIC_TOKEN", None)
    env.pop("FLOWMUSIC_BASE", None)
    env["FLOWMUSIC_HOME"] = str(SESSION)
    kwargs = {"cwd": ROOT, "env": env, "timeout": timeout, "check": False}
    if not interactive:
        kwargs.update(capture_output=True, text=True, encoding="utf-8", errors="replace")
    return subprocess.run(parts, **kwargs)


def check_pin() -> None:
    if not ENTRY.is_file():
        raise RuntimeError("Pinned CLI missing; run scripts/windows/install.ps1")
    git = shutil.which("git")
    node = shutil.which("node")
    if not git or not node:
        raise RuntimeError("git and node are required")
    result = subprocess.run(
        [git, "-C", str(VENDOR), "rev-parse", "HEAD"], capture_output=True,
        text=True, check=True, timeout=15,
    )
    if result.stdout.strip() != PIN:
        raise RuntimeError("Upstream commit mismatch: refuse live execution")
    version = command([node, "--version"], timeout=10)
    if version.returncode:
        raise RuntimeError("node failed")
    print("Ambiente OK; upstream fixado; nenhuma chamada Google realizada.")


def secure_session_dir() -> None:
    if SESSION.is_symlink():
        raise RuntimeError("OAuth session directory must not be a symlink")
    SESSION.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        who = subprocess.run(["whoami"], capture_output=True, text=True, check=True, timeout=15)
        principal = who.stdout.strip()
        if not principal:
            raise RuntimeError("Windows identity missing")
        # Remove inheritance and grant owner; inspect any old explicit ACEs manually.
        result = subprocess.run(
            ["icacls", str(SESSION), "/inheritance:r",
             "/grant:r", f"{principal}:(OI)(CI)F"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode:
            raise RuntimeError("Could not protect local OAuth session directory")
    else:
        SESSION.chmod(0o700)


def session_exists() -> None:
    if not (SESSION / "session.json").is_file():
        raise RuntimeError("No isolated session. Run -Mode login interactively first.")


def harden_upstream_retry() -> None:
    """Patch only known pinned upstream source, in ignored local vendor checkout.

    The original CLI retries a non-idempotent POST on the first network failure,
    which could double-charge after an ambiguous accepted submission.
    """
    source = VENDOR / "src" / "lib" / "client.mjs"
    body = source.read_text(encoding="utf-8")
    original = 'if (!idempotent && attempt >= 1) break;'
    safe = 'if (!idempotent) break;'
    original_retryable = 'const retryable = r.status === 429 || (idempotent && r.status >= 500);'
    safe_retryable = 'const retryable = idempotent && (r.status === 429 || r.status >= 500);'
    if original in body:
        body = body.replace(original, safe, 1)
    elif safe not in body:
        raise RuntimeError("Unknown upstream network retry logic: manual review required")
    if original_retryable in body:
        body = body.replace(original_retryable, safe_retryable, 1)
    elif safe_retryable not in body:
        raise RuntimeError("Unknown upstream rate-limit retry logic: manual review required")
    if safe not in body or safe_retryable not in body:
        raise RuntimeError("Unsafe upstream POST retry logic")
    temporary = source.with_suffix(".mjs.tmp")
    temporary.write_text(body, encoding="utf-8")
    os.replace(temporary, source)


def json_command(kind: str):
    node = shutil.which("node")
    result = command([node, str(ENTRY), kind, "--json"], timeout=120)
    if result.returncode:
        raise RuntimeError(f"{kind} returned a failure; inspect account locally")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Unexpected {kind} JSON response") from exc


def account(profile: str) -> None:
    session_exists()
    model_list = json_command("models")
    credits = json_command("credits")
    public_names = [v.get("public_name", "") for v in model_list if isinstance(v, dict)] if isinstance(model_list, list) else []
    remaining = credits.get("credits_remaining", "indisponível") if isinstance(credits, dict) else "indisponível"
    print("Modelos:", ", ".join(public_names) if public_names else "(verificar resposta upstream)")
    if type(remaining) is int and remaining >= 0:
        profiles.save_snapshot(profile, remaining)
    print("Créditos disponíveis:", remaining)
    event("account.readonly", status="ok", phase="account", profile=profile)


def output_metadata(data: dict, folder: Path) -> list[dict]:
    songs = data.get("songs")
    if not isinstance(songs, list) or not songs:
        raise RuntimeError("Upstream returned no songs")
    artifacts = []
    for song in songs:
        if not isinstance(song, dict) or not song.get("file"):
            raise RuntimeError("Upstream did not provide a downloaded file")
        raw_path = Path(song["file"])
        path = (ROOT / raw_path).resolve() if not raw_path.is_absolute() else raw_path.resolve()
        if not path.is_relative_to(folder.resolve()) or not path.is_file() or path.stat().st_size < 1024:
            raise RuntimeError("Provider output missing, empty or outside expected directory")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        artifacts.append({"file": str(path), "bytes": path.stat().st_size,
                          "sha256": digest.hexdigest(), "variant": song.get("variant")})
    return artifacts


def generate(args: argparse.Namespace) -> None:
    if not args.approve_live:
        raise RuntimeError("Pass -ApproveLive only after reviewing terms, credit balance and one-off expense")
    if not VALID_ID.fullmatch(args.request_id or ""):
        raise RuntimeError("request-id must contain 3-80 letters, numbers, dots, _ or -")
    if not args.prompt or len(args.prompt) < 3:
        raise RuntimeError("A music prompt is required")
    session_exists()
    harden_upstream_retry()
    LEDGER.mkdir(parents=True, exist_ok=True)
    output = OUTPUT / args.request_id
    ledger = LEDGER / (args.request_id + ".json")
    lock = MVP / "generation.lock"
    if ledger.exists() or lock.exists():
        raise RuntimeError("Existing request_id or unresolved generation lock: reconcile library manually")
    record = {"request_id": args.request_id, "profile": args.profile, "state": "submitting",
              "started_at": timestamp(), "model_requested": args.model, "artifacts": []}
    # Create exclusive lock and ledger before any remote side effect.
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps({"request_id": args.request_id, "started_at": timestamp()}))
        stream.flush()
        os.fsync(stream.fileno())
    with ledger.open("x", encoding="utf-8") as stream:
        json.dump(record, stream)
        stream.flush()
        os.fsync(stream.fileno())
    # Any future credit snapshot is stale as soon as a generation is attempted.
    profiles.invalidate_snapshot(args.profile)
    event("generation.submitting", request_id=args.request_id, model=args.model, profile=args.profile, status="submitting")
    output.mkdir(parents=True, exist_ok=True)
    node = shutil.which("node")
    argv = [node, str(ENTRY), "gen", args.prompt, "--model", args.model,
            "--length", str(args.seconds), "--format", args.format,
            "--out", str(output), "--json"]
    if args.instrumental:
        argv.append("--instrumental")
    begin = time.monotonic()
    try:
        # Only ONE CLI process. No Python retry on any ambiguous failure.
        done = command(argv, timeout=1200)
        if done.returncode:
            raise RuntimeError("CLI failed; remote acceptance is unknown")
        parsed = json.loads(done.stdout)
        artifacts = output_metadata(parsed, output)
        record.update(state="completed", finished_at=timestamp(), artifacts=artifacts)
        atomic_json(ledger, record)
        elapsed = round((time.monotonic() - begin) * 1000)
        event("generation.completed", request_id=args.request_id, model=args.model, profile=args.profile,
              status="completed", elapsed_ms=elapsed, variant_count=len(artifacts),
              artifact_count=len(artifacts))
        lock.unlink(missing_ok=True)
        print(f"MVP concluído: {len(artifacts)} arquivo(s); {elapsed / 1000:.1f}s.")
        print("Detalhes locais em", ledger)
    except Exception as exc:
        record.update(state="needs_review", finished_at=timestamp(),
                      error_class=type(exc).__name__)
        atomic_json(ledger, record)
        event("generation.needs_review", request_id=args.request_id, model=args.model, profile=args.profile,
              status="needs_review", error_class=type(exc).__name__)
        # Keep lock: do not start a second live attempt until human reconciliation.
        raise RuntimeError("Resultado remoto incerto. Verifique biblioteca do Flow Music; NÃO reenvie.") from None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["check", "accounts", "login", "account", "generate"], default="check")
    parser.add_argument("--profile", default="default", help="Local account alias; no automatic failover")
    parser.add_argument("--request-id")
    parser.add_argument("--prompt")
    parser.add_argument("--model", default="Lyria 3.5")
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--format", choices=["wav", "m4a", "mp3"], default="wav")
    parser.add_argument("--instrumental", action="store_true")
    parser.add_argument("--approve-live", action="store_true")
    args = parser.parse_args()
    global SESSION
    try:
        profiles.validate(args.profile)
        SESSION = profiles.session_dir(args.profile)
        check_pin()
        if args.mode == "check":
            event("environment.check", status="ok", phase="offline")
        elif args.mode == "accounts":
            for row in profiles.list_profiles():
                balance = row["credits_remaining"] if row["credits_remaining"] is not None else "n/d"
                print(f'{row["profile"]}: sessao={row["session_present"]} creditos={balance} ultima_consulta={row["checked_at"]} expirado={row["stale"]}')
        elif args.mode == "login":
            if (MVP / "generation.lock").exists():
                raise RuntimeError("A music generation is active or unresolved; do not alter sessions")
            secure_session_dir()
            print("Login interativo, URL de autenticação é privada. Não copie para logs.")
            result = command([shutil.which("node"), str(ENTRY), "login"], timeout=600, interactive=True)
            if result.returncode:
                raise RuntimeError("Interactive login failed")
            secure_session_dir()
            session_exists()
            event("login.completed", status="ok", phase="login", profile=args.profile)
        elif args.mode == "account":
            if (MVP / "generation.lock").exists():
                raise RuntimeError("A music generation is active or unresolved; wait before refreshing the session")
            secure_session_dir()
            account(args.profile)
        else:
            if not (60 <= args.seconds <= 600):
                raise RuntimeError("Length outside MVP safety range")
            secure_session_dir()
            generate(args)
        return 0
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(f"MVP parado: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
