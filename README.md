# Evydencia FlowMusic Local — Windows API + fila

Serviço independente com FastAPI, SQLite e flowmusic-cli fixado. Duas validações reais foram relatadas pelo Antigravity: `natal-mvp-001` via CLI e `natal-api-002` via HTTP/FIFO. Os áudios e credenciais ficam somente no Windows.

## Operação curta
```powershell
git fetch origin
git switch feat/windows-local-engine-foundation
git pull --ff-only
.\agent.cmd
.\scripts\windows\mvp.ps1 -Mode accounts
```

Não há GitHub Actions. Testes/diagnósticos locais apenas conforme necessidade. `agent.cmd test` é opcional.

## Perfis isolados e créditos
```powershell
.\scripts\windows\mvp.ps1 -Mode login -Profile studio02
.\scripts\windows\mvp.ps1 -Mode account -Profile studio02
.\scripts\windows\mvp.ps1 -Mode accounts
```

`default` preserva a sessão antiga. Outros perfis usam `data/flowmusic-profiles/<alias>`. `GET /v1/music/accounts` retorna snapshots de crédito, ordenados do maior saldo **recente** para o menor, assinalando os desatualizados. A conta é escolhida explicitamente por `account_profile` no POST e nunca alternada automaticamente. Consulte [docs/ACCOUNTS.md](docs/ACCOUNTS.md).

## API local
```powershell
.\scripts\windows\start.ps1
# Somente quando conscientemente autorizado:
.\scripts\windows\start.ps1 -EnableLive
```

`127.0.0.1:8765/docs`: API protegida por header `X-Local-Token` (arquivo `data/local-token.txt`). Cada pedido real exige `approve_live=true`. Fila bloqueada em resultados remotos incertos; não repetir usando outra conta.

Detalhes: [docs/API_QUEUE.md](docs/API_QUEUE.md), [docs/ACCOUNTS.md](docs/ACCOUNTS.md), [docs/SECURITY.md](docs/SECURITY.md). O uso de endpoints internos do provedor não é API oficial e depende dos termos aplicáveis.
## Antes do segundo login — preflight offline
```powershell
.\.venv\Scripts\python.exe scripts/preflight_accounts.py
.\scripts\windows\mvp.ps1 -Mode accounts
```
O preflight não chama o Google. O primeiro `start.ps1` após a atualização cria backup da base SQLite em `data/backups/` antes da migração da tabela de perfis. `start.ps1 -EnableLive` bloqueia pedidos já pendentes; somente após revisão use `-ResumePending`. Ver [docs/ACCOUNTS.md](docs/ACCOUNTS.md).
