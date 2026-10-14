# Evydencia FlowMusic Local — AI-first / Gemini 3.8 Flash

Objetivo: desenvolver somente este serviço Windows com logs de execução e poucas verificações por alteração. Não alterar CRM/Workflow.

## Fluxo
1. Escolher UMA skill em .agents/skills e ler só os arquivos relevantes.
2. Um problema -> hipótese -> diagnóstico Windows dirigido -> menor correção -> evidência.
3. Sem GitHub Actions ou bateria extensa de testes simulados por padrão. Preservar as duas gerações reais anteriores: natal-mvp-001 e natal-api-002.

## Invariantes
- FastAPI 127.0.0.1, FIFO SQLite, request_id UNIQUE, um envio ativo.
- Live somente com start.ps1 -EnableLive e approve_live=true por job.
- Contas: FLOWMUSIC_HOME isolado, account_profile por pedido e ledger, snapshots de créditos ordenados e com indicação de validade.
- Não alternar contas automaticamente para contornar limitações; erros ambíguos = needs_review e fila parada, sem novo POST.
- Nunca versionar/mostrar tokens, sessões, callbacks OAuth, prompts privados ou áudio de clientes.
- Não executar geração remota sem autorização explícita; cumprir os termos aplicáveis.
- Não alterar main nem fazer merge automático.

Arquivos: app/main.py (HTTP), app/queue.py (SQLite/FIFO), app/profiles.py (contas/saldos), scripts/mvp_probe.py (motor), docs/ACCOUNTS.md e docs/API_QUEUE.md (operação).
## Pré-login studio02 e migração
Antes de pedir novo login: rodar `scripts/preflight_accounts.py` localmente (sem rede), conferir `generation.lock`, jobs `submitting/needs_review/queued` e executar somente o diagnóstico necessário. O primeiro startup migra SQLite com backup em `data/backups/`; nunca apagar banco, tokens ou WAVs antigos. `start.ps1 -EnableLive` nunca retoma pendentes sem `-ResumePending`. Não gastar créditos para testar a nova estrutura de perfis.

## Painel de contas
Para UI, ler apenas `app/static/accounts.html`, `app/static/accounts.css`,
`app/static/accounts.js`, `app/profiles.py`, `app/main.py` e
`docs/ACCOUNTS_DASHBOARD.md`. O HTML não pode conter tokens ou e-mails
pré-renderizados. API exige header `X-Local-Token`; manter token só na
memória do navegador. Status da sessão é LOCAL, nunca afirmar login online sem
consulta upstream autorizada. Um teste real de saldo sob demanda basta para
validar a interface; não gastar créditos de geração nesta mudança.
