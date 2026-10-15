---
name: flowmusic-local
description: Maintain Windows FastAPI SQLite FIFO jobs, OAuth session profiles and local credit snapshots through minimal targeted changes and operational logs.
---
# API, fila e contas
Ler AGENTS.md. Selecionar somente os arquivos relevantes:
`app/main.py` (REST), `app/queue.py` (transações e worker), `app/profiles.py` (aliases, cache), `scripts/mvp_probe.py` (geração), `docs/ACCOUNTS.md` (comandos).
Preservar histórico/áudio real. Sempre um job ativo; sem failover automático, retry de POST ambíguo ou rotação para contornar limites. Verificar apenas o necessário no Windows; sem GitHub Actions.

## Antes da segunda conta (ordem obrigatoria)
1. Conferir git status e HEAD, sem descartar dados locais.
2. Executar `python scripts/preflight_accounts.py` (somente leitura); se houver queued, needs_review, submitting ou lock, resolver antes do login.
3. Conferir `app/profiles.py` / `queue.migrate` e o backup automatico antes da primeira migracao.
4. Validar `mvp.ps1 -Mode accounts`, depois `-Mode login -Profile studio02` apenas com a autorizacao do operador.
5. Nao gerar musica nem rodar toda a suite por habito. Verificar saldo por `-Mode account -Profile studio02`, listar inventory e observar `stale`.
6. Primeiro `start.ps1` promove schema e grava backup em `data/backups`. LIVE com pendentes exige `-ResumePending` explicitamente.
