---
name: flowmusic-local
description: Maintain Windows FastAPI SQLite FIFO jobs, OAuth session profiles and local credit snapshots through minimal targeted changes and operational logs.
---
# API, fila e contas
Ler AGENTS.md. Selecionar somente os arquivos relevantes:
`app/main.py` (REST), `app/queue.py` (transações e worker), `app/profiles.py` (aliases, cache), `scripts/mvp_probe.py` (geração), `docs/ACCOUNTS.md` (comandos).
Preservar histórico/áudio real. Sempre um job ativo; sem failover automático, retry de POST ambíguo ou rotação para contornar limites. Verificar apenas o necessário no Windows; sem GitHub Actions.
