# Audited Upstream Candidates & Technical Analysis

## Primary Reference: `deluxebear/flowmusic-cli`
- **Repository**: `https://github.com/deluxebear/flowmusic-cli`
- **Pinned SHA**: `08491dc3319ae9f530c5c05c431196bbbbb10607`
- **License**: MIT (Preserved in `vendor/flowmusic-cli/LICENSE`)
- **Unit Tests**: 15/15 tests passing on Windows under Node.js v24.20.0 via native test runner (`node --test test/*.test.mjs`).

### Detailed Code Audit Findings
1. **Windows Chrome Binary Discovery (`src/lib/auth.mjs`)**:
   - `chromeBinary()` checks only `process.env.CHROME_BIN` and hardcoded POSIX paths:
     - `/usr/bin/google-chrome-stable`
     - `/usr/bin/google-chrome`
     - `/opt/google/chrome/chrome`
     - `/usr/bin/chromium`
     - `/usr/bin/chromium-browser`
   - On Windows, automated headless authentication will fail unless `CHROME_BIN` is explicitly configured to point to `chrome.exe` (e.g. `C:\Program Files\Google\Chrome\Application\chrome.exe`).

2. **Browser Opening on Windows (`src/lib/auth.mjs`)**:
   - `loginWithBrowser()` attempts to launch the browser using `spawnSync("which", [opener])` across `xdg-open`, `open`, and `wslview`.
   - On native Windows, `which` is not present and these openers do not exist. While the authentication URL is logged to stderr, automatic browser opening will silently fail on Windows unless updated to use Windows `cmd.exe /c start ""` or `explorer.exe`.

3. **Session Storage and Credentials (`src/lib/config.mjs`)**:
   - Config directory defaults to `~/.config/gfmusic/session.json`.
   - On Windows, `os.homedir()` resolves to `C:\Users\<user>`.
   - `saveSession()` attempts POSIX permission modes (`0o700`, `0o600`), which are ignored by Windows NTFS. NTFS DACLs should be used when multi-user protection is necessary.
   - Supabase OAuth refresh tokens rotate on every refresh. Concurrent workers will trigger token race conditions; a strict single-worker architecture is required.

4. **Remote POST Idempotency and Credit Protection (`src/lib/client.mjs`)**:
   - Upstream client issues `POST /conversation` and `POST /producer/tool-call` to `https://api.flowmusic.app`.
   - Retries on network errors or timeouts can cause duplicated generations and consume Google AI Pro credits repeatedly.
   - Remediation: The local FastAPI service enforces local SQLite idempotency, payload SHA-256 validation, and marks interrupted jobs as `needs_review` rather than auto-retrying.

5. **Terms of Service & Safety Gates**:
   - Upstream interacts with private endpoints (`api.flowmusic.app` and Supabase backend `ednjccqcmbxeaxbidinr.supabase.co`).
   - Consumer automation without official API keys carries account suspension risks and must not bypass rate limits or CAPTCHA challenges.
   - The live provider remains strictly disabled in this repository until user consent and terms compliance are established.

## Alternatives Evaluated
- `south1907/flowmusic-toolkit` (`4052207077089368ba329b9ca389a74703094cd1`): Python/FastAPI but missing local auth and broken Makefile CI on Windows.
- `genz27/FlowMusic2API` (`34296d89e830e42b1b9582215404c7c5fae2ed27`): Go implementation binding to `0.0.0.0` by default; excessive scope and exposure.
