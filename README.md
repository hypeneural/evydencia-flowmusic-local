# Evydencia FlowMusic Local — MVP Windows, API + fila

O MVP real no Windows já foi demonstrado pelo operador: geração instrumental Lyria 3.5 com WAV e consumo de créditos. **Este repositório não fornece uma API oficial Google**, apenas integra de forma controlada o cliente open-source fixado `deluxebear/flowmusic-cli`.

## Rápido no Windows
```powershell
git fetch origin
git switch feat/windows-local-engine-foundation
git pull --ff-only
.\agent.cmd
.\scripts\windows\start.ps1
```
O comando sem parâmetros abre API **mock** em `http://127.0.0.1:8765/docs` sem créditos. `agent.cmd` é diagnóstico rápido; `agent.cmd test` roda a suíte completa somente se necessário.

## Fila real — somente se autorizada
Após a decisão consciente de uso da conta e dos créditos, o operador pode iniciar:
```powershell
.\scripts\windows\start.ps1 -EnableLive
```
Isso não gera música sozinho. Cada `POST /v1/music/jobs` precisa do header `X-Local-Token` e de `approve_live=true`. Um worker recupera os jobs aprovados em ordem, dispara o `mvp_probe.py` **uma vez**, registra ledger/artefatos e suspende toda a fila em resultado incerto. Não reutilizar `natal-mvp-001` (já consumido no teste anterior).

**Documentação operacional completa e exemplo HTTP:** [docs/API_QUEUE.md](docs/API_QUEUE.md). Consulte também [docs/MVP_RUNBOOK.md](docs/MVP_RUNBOOK.md), [docs/CODEGRAPH.md](docs/CODEGRAPH.md) e [docs/SECURITY.md](docs/SECURITY.md).

**Sem novas assinaturas:** Python, SQLite, FastAPI e upstream MIT. A disponibilidade e a permissão dos endpoints privados podem mudar; AI Pro não implica autorização de automação desassistida.
