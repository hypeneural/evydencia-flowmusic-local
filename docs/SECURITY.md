# Security / release gates

## Scope
Localhost-only FastAPI mock. `flowmusic-cli` under `vendor/` is pinned, separately testable and **not** a live provider here. Never claim that passing mock tests confirms Google Lyria generation.

## Credentials
- `data/local-token.txt` is never committed. `bootstrap()` reapplies access restrictions on every start. On Windows, `icacls` failure blocks startup instead of silently continuing.
- The current `icacls` grants to the Windows user and removes inherited ACEs, but **does not prove removal of unrelated explicit ACL entries**. The Windows MVP script restricts a separate OAuth session directory and avoids logging sensitive stdout, but does not guarantee the absence of old explicit ACLs. Before deploying in a shared/multi-user Windows workstation, inspect `icacls data\\local-token.txt` and inherited permissions on `data/` (and protect secrets in the future CLI session directory separately).
- Keep NTFS ACLs on secret directories, not just the token file; do not send token or OAuth sessions to GitHub, logs or chat.
- Loopback binding is not a security boundary against malicious software running as the same Windows user.
- `GET /health` and FastAPI `/docs` remain publicly accessible on loopback; actual jobs and status require X-Local-Token. Do not expose through LAN/reverse proxy.
- Existing session tokens stored by upstream may rotate; no simultaneous producers. Do not copy main Chrome cookies.

## Reliability
- SQLite `request_id` UNIQUE enforces idempotent **creation**, even across processes. It is not a provider-side idempotency guarantee.
- No retry of possibly accepted remote POSTs. Fail/unknown -> `needs_review` until manually reconciled.
- Mock stage saves atomic JSON artifacts, not audio. Do not use mock artifacts in the production media pipeline.
- An opt-in FastAPI FIFO worker now invokes the previously validated one-shot probe. Live requires Windows start.ps1 -EnableLive and per-request approve_live=true. An uncertain result blocks the queue pending manual reconciliation, with no repeat submission. This remains an operational MVP, not an officially supported public API or a distributed queue.

## Product compliance
Flow Music consumer subscription does not provide an officially documented unlimited public generation API. Validate applicable service terms before any UI automation/private endpoint use. Stop for challenge, 403, 429 or account restrictions; never bypass platform controls. Obtain explicit operator approval of every credit-consuming live test through the -ApproveLive flag. The CLI uses undocumented endpoints; authorization to automate them is not implied by the subscription. Never paste prompt or OAuth callback into logs.

## Real API queue boundaries
SQLite stores prompts locally and requires suitable directory NTFS permissions. The worker has one active submission, does not log raw provider stdout/stderr and verifies local output hashes before completion. Remote job IDs are not yet persisted, so ambiguous crashes still require review in the Flow Music library. Do not expose the HTTP API on LAN.


## Múltiplos perfis
Cada conta usa sua própria sessão OAuth em `FLOWMUSIC_HOME`, reduzindo conflitos de renovação de token entre contas. Inventário de créditos contém apenas alias/valor/data e pode estar desatualizado; nunca implica acesso válido.

Não realizar consultas de saldo durante uma geração ativa; scripts bloqueiam login/consulta se `generation.lock` existir. Um erro remoto incerto bloqueia a fila; nunca alternar automaticamente de perfil. Proteja também `data/flowmusic-profiles/`, `data/account-snapshots/` e o banco SQLite com ACLs NTFS em Windows compartilhado.
