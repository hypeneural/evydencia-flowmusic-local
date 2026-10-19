#!/usr/bin/env bash
# Human-only upstream Music Supabase login: Chrome session + rotating OAuth tokens.
set -euo pipefail
alias="${FLOW_LOGIN_PROFILE:-default}"
[[ "$alias" =~ ^[a-z][a-z0-9_-]{0,31}$ ]] || { echo invalid_profile; exit 2; }
[ ! -e /app/data/mvp/generation.lock ] || { echo 'P0 unresolved Music generation lock'; exit 2; }
if [ "$alias" = default ]; then d=/app/data/flowmusic-session; else d="/app/data/flowmusic-profiles/$alias"; fi
[ ! -L "$d" ] || { echo 'P0 symlink_session'; exit 2; }
mkdir -p "$d" /app/data/home /app/data/cache /app/data/config
chmod 0700 "$d"
# Login via pinned upstream deliberately recreates Chrome profile. Preserve
# the existing per-alias refresh-token chain until the new identity has
# been verified; never permit an accidental Google account switch.
session="$d/session.json"
previous="$d/.session-prelogin-${BASHPID}"
if [ -L "$session" ]; then echo 'P0 symlink_session_file'; exit 2; fi
if [ -f "$session" ]; then
  cp -p -- "$session" "$previous"
  chmod 0600 "$previous"
fi
export HOME=/app/data/home XDG_CACHE_HOME=/app/data/cache XDG_CONFIG_HOME=/app/data/config DISPLAY=:99
export FLOWMUSIC_HOME="$d"
unset FLOWMUSIC_TOKEN FLOWMUSIC_BASE
Xvfb :99 -screen 0 1365x850x24 -nolisten tcp >/tmp/xvfb.log 2>&1 &
xpid=$!
cleanup() {
  local rc=$?
  if [ "$rc" -ne 0 ] && [ -f "$previous" ]; then
    # Failure during browser auth must never replace a prior working
    # refresh-token chain. Restore only while the worker is stopped.
    cp -p -- "$previous" "$session" ||
      echo 'P0 could not restore prior session: manual review required'
  fi
  rm -f -- "$previous"
  if [ -n "${vpid:-}" ]; then kill "$vpid" 2>/dev/null || true; fi
  kill "$xpid" 2>/dev/null || true
}
trap cleanup EXIT
for n in $(seq 1 40); do [ -S /tmp/.X11-unix/X99 ] && break; sleep 0.25; done
[ -S /tmp/.X11-unix/X99 ] || { echo 'P0 Xvfb failed'; exit 3; }
pass=$(python3 -c 'import secrets,string; abc=string.ascii_letters+string.digits; print("".join(secrets.choice(abc) for _ in range(8)))')
x11vnc -storepasswd "$pass" /tmp/vnc-password >/dev/null 2>&1
chmod 0600 /tmp/vnc-password
x11vnc -display :99 -rfbauth /tmp/vnc-password -listen 0.0.0.0 -rfbport 5900 -forever -shared -noxdamage >/tmp/vnc.log 2>&1 &
vpid=$!
echo "TEMPORARY_VNC_PASSWORD=$pass"
echo 'Use Tailscale SSH: ssh -L 15901:127.0.0.1:15901 vps-prod'
echo 'Then open a VNC viewer on 127.0.0.1:15901.'
echo 'Close the Google login Chrome window. The upstream will perform a LOCAL headless session capture.'
# Upstream login() opens plain Chrome without remote debugging for sign-in;
# after the user closes it, it reads the authorized session into its own
# Supabase refresh chain. The CDP port remains inside the ephemeral container.
timeout -k 15s 1080s node --input-type=module --eval "import { login } from './vendor/flowmusic-cli/src/lib/auth.mjs'; await login({timeoutS:900});"
# Never claim successful login merely because upstream returned exit 0.
# Inspect the *actual persistent bind mount*, without printing session JSON.
FLOW_LOGIN_VERIFIED_ALIAS="$alias" FLOW_LOGIN_PRIOR="$previous" python3 - <<'PY'
import json,os
from pathlib import Path
from app import profiles
alias=os.environ["FLOW_LOGIN_VERIFIED_ALIAS"]
prior=Path(os.environ["FLOW_LOGIN_PRIOR"])
path=profiles.session_dir(alias)/"session.json"
if path.is_symlink() or not path.is_file():
    raise SystemExit("MUSIC_LOGIN_NOT_PERSISTED: session.json missing; no routing enabled")
if not path.resolve().is_relative_to(profiles.DATA.resolve()):
    raise SystemExit("MUSIC_LOGIN_NOT_PERSISTED: session outside persistent volume")
if not 0 < path.stat().st_size <= 256*1024:
    raise SystemExit("MUSIC_LOGIN_NOT_PERSISTED: invalid session file size")
# Refuse accidental reassignment of an existing alias to another Google
# identity. The old authorized chain is restored by the shell EXIT trap on
# any nonzero return. Do not compare access/refresh tokens; only public ID.
if prior.exists():
    try:
        previous=json.loads(prior.read_text(encoding="utf8"))
        current=json.loads(path.read_text(encoding="utf8"))
    except (OSError,ValueError,TypeError):
        raise SystemExit("MUSIC_LOGIN_IDENTITY_REVIEW_REQUIRED: session metadata invalid") from None
    old_uid=previous.get("user_id") if isinstance(previous,dict) else None
    new_uid=current.get("user_id") if isinstance(current,dict) else None
    old_mail=previous.get("email") if isinstance(previous,dict) else None
    new_mail=current.get("email") if isinstance(current,dict) else None
    if (isinstance(old_uid,str) and isinstance(new_uid,str)
            and old_uid and new_uid):
        same=old_uid==new_uid
    elif (isinstance(old_mail,str) and isinstance(new_mail,str)
            and old_mail and new_mail):
        same=old_mail.casefold()==new_mail.casefold()
    else:
        same=False
    if not same:
        raise SystemExit("MUSIC_LOGIN_DIFFERENT_GOOGLE_IDENTITY: old session preserved; use a NEW alias") from None
# The newly saved refresh token is a secret. Restrict it on disk before
# subsequent CLI use. Never emit its bytes, email, hash or an auth URL.
os.chmod(path,0o600)
meta=profiles.session_public_metadata(alias)
if not meta["refresh_available"] or meta["session_status"] in ("not_connected","invalid_file"):
    raise SystemExit("MUSIC_LOGIN_INCOMPLETE: persisted file lacks a usable refresh chain")
print(json.dumps({"profile":alias,"session_persisted":True,
    "refresh_present":True,"session_status":meta["session_status"],
    "generation_submitted":False}))
PY
echo 'Music session persisted in /app/data; run stackctl flow-media session-check music ALIAS (GET only) before auto-selection.'
