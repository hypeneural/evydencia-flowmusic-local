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
export HOME=/app/data/home XDG_CACHE_HOME=/app/data/cache XDG_CONFIG_HOME=/app/data/config DISPLAY=:99
export FLOWMUSIC_HOME="$d"
unset FLOWMUSIC_TOKEN FLOWMUSIC_BASE
Xvfb :99 -screen 0 1365x850x24 -nolisten tcp >/tmp/xvfb.log 2>&1 &
xpid=$!
cleanup() {
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
FLOW_LOGIN_VERIFIED_ALIAS="$alias" python3 - <<'PY'
import json,os,stat
from app import profiles
alias=os.environ["FLOW_LOGIN_VERIFIED_ALIAS"]
path=profiles.session_dir(alias)/"session.json"
if path.is_symlink() or not path.is_file():
    raise SystemExit("MUSIC_LOGIN_NOT_PERSISTED: session.json missing; no routing enabled")
if not path.resolve().is_relative_to(profiles.DATA.resolve()):
    raise SystemExit("MUSIC_LOGIN_NOT_PERSISTED: session outside persistent volume")
if not 0 < path.stat().st_size <= 256*1024:
    raise SystemExit("MUSIC_LOGIN_NOT_PERSISTED: invalid session file size")
# The newly saved refresh token is a secret. Restrict it on disk before
# subsequent CLI use. Never emit its bytes, email, hash or an authentication URL.
os.chmod(path,0o600)
meta=profiles.session_public_metadata(alias)
if not meta["refresh_available"] or meta["session_status"] in ("not_connected","invalid_file"):
    raise SystemExit("MUSIC_LOGIN_INCOMPLETE: persisted file lacks a usable refresh chain")
print(json.dumps({"profile":alias,"session_persisted":True,
    "refresh_present":True,"session_status":meta["session_status"],
    "generation_submitted":False}))
PY
echo 'Music session persisted in /app/data; run stackctl flow-media session-check music ALIAS (GET only) before auto-selection.'
