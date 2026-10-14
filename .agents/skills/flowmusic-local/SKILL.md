---
name: flowmusic-local
description: Makes small, evidence-driven fixes to the Windows FastAPI mock/local music service and its API without unrelated refactors or large test batches.
---
# Local API maintenance
Read AGENTS.md. Inspect the relevant call path in `app/main.py` and one targeted test. Make the smallest fix, execute one focused check (`python -m pytest -q tests/test_api.py`) only if code changed, and examine results. Full tests only before merge/release or for broad changes. Do not conflate mock service with real Google music generation.
