# Local service operations
This repository provides a **mock-tested API scaffold**, not a verified live Google Flow Music integration. Real account tests need explicit confirmation of platform permissions and user approval.
Routes: GET /health (public); GET /v1/music/status, /v1/music/credits, POST /v1/music/jobs, GET /v1/music/jobs/{id}, GET /v1/music/jobs/{id}/artifacts (X-Local-Token required).
The local token is written under data/local-token.txt on server startup; protect via Windows NTFS ACL and never commit or paste it.
The mock provider creates a JSON fixture rather than audio. The disabled live provider is an intentional safety gate; Windows Antigravity will evaluate licensing and upstream compatibility before any implementation or use.
Upstream reference: deluxebear/flowmusic-cli at commit 08491dc3319ae9f530c5c05c431196bbbbb10607 (MIT). No upstream code is copied into this repo. Pin its commit and retain LICENSE.
Never expose service beyond 127.0.0.1. Do not repeat ambiguous remote operations; use needs_review.
Known gaps: crash-safe durable live worker, FFprobe validation, Windows account login verification, production terms validation.
