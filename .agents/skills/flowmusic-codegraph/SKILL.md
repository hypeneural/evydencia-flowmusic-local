---
name: flowmusic-codegraph
description: Use when tracing call paths, SQLite state transitions, OAuth/session risks, upstream dependencies or regressions in evydencia-flowmusic-local.
---
# FlowMusic forensic CodeGraph

Read `docs/CODEGRAPH.md` for the verified static graph, then inspect source at each edge relevant to the issue. Do not assume a runtime graph, IDE-specific index, or that the upstream adapter is integrated.
Trace HTTP entry -> dependency auth -> local database transaction -> mock artifact -> response. For issues related to Chrome/Google consult `docs/UPSTREAM_AUDIT.md` and upstream pinned source only, but **never start a live generation**.
Write a concise impact matrix: entrypoint, data model, persistence, error behavior, tests, security and rollout.
Before editing, verify SHA and diff against PR #1. Prefer simple targeted corrections and tests.
