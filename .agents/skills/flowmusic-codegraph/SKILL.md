---
name: flowmusic-codegraph
description: Traces a specific bug across FastAPI routes, SQLite job states, upstream Node CLI and Windows scripts only when a dependency boundary is unclear.
---
# Minimal codegraph
Read `docs/CODEGRAPH.md` only if the call path is uncertain; follow one path at a time. Identify entrypoint, state transition, remote side effect, logging and recovery. Output a five-line impact summary, then patch only necessary files. No full-repository scan.
