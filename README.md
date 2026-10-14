# Evydencia FlowMusic Local — AI-FIRST / MVP Windows

Serviço independente do Python Workflow, com **validação real, execução supervisionada e logs claros**. Não é necessário construir mais infraestrutura antes de comprovar uma geração. O FastAPI permanece um sandbox mock para validar o contrato; o caminho de MVP real usa **um CLI fixado, chamado explicitamente pelo Windows**, sem integrar credenciais ao CRM.

## Caminho curto para o Antigravity 3.8 Flash
- Leia somente `AGENTS.md`, invoque `/flowmusic-mvp` e veja `docs/MVP_RUNBOOK.md`.
- Uma hipótese -> uma execução -> um registro JSONL -> uma correção. Evite quatro matrizes de teste a cada alteração.
- `agent.cmd` roda **checagem rápida, sem Google**. `agent.cmd test` executa suite Python + testes Node apenas sob demanda.
- `/flowmusic-local` cuida da API mock quando necessário; `/flowmusic-codegraph` apenas para bugs transversais.

## Instalação
```powershell
git clone https://github.com/hypeneural/evydencia-flowmusic-local.git
cd evydencia-flowmusic-local
git fetch origin
git switch --track origin/feat/windows-local-engine-foundation
powershell -ExecutionPolicy Bypass -File scripts/windows/install.ps1
.\agent.cmd
```
O instalador fixa `deluxebear/flowmusic-cli` (MIT) no commit `08491dc3319ae9f530c5c05c431196bbbbb10607`; `vendor/`, `data/` e sessões são ignorados pelo Git.

## Teste real supervisionado
Apenas após verificar os termos aplicáveis e o custo de crédito, consulte `docs/MVP_RUNBOOK.md`:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/mvp.ps1 -Mode login
powershell -ExecutionPolicy Bypass -File scripts/windows/mvp.ps1 -Mode account
powershell -ExecutionPolicy Bypass -File scripts/windows/mvp.ps1 -Mode generate -RequestId natal-mvp-001 -Prompt 'Trilha natalina suave' -Instrumental -ApproveLive
```
`-Mode generate` **pode consumir créditos** e requer `-ApproveLive`; nunca é invocado pelo install, boot, doctor ou CI. Logs resumidos: `data/mvp/events.jsonl`; relatório da tentativa: `data/mvp/ledger/<id>.json`. Em timeout/erro ambíguo, o script preserva um bloqueio para evitar disparos sucessivos; consulte a biblioteca antes de liberar manualmente.

**Importante:** o fluxo usa operações web internas não documentadas; não é uma API oficial garantida. AI Pro inclui o Flow Music Plus, mas assinatura não equivale a autorização automática para automatizar esse protocolo.

## API sandbox (opcional)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/start.ps1
```
Swagger em `http://127.0.0.1:8765/docs`; API mock protege rotas com token local `data/local-token.txt`. Nenhum áudio é produzido na API mock.

## Referências
- `AGENTS.md`, `.agents/skills/`, `.agents/rules/`, `.agents/agents/`: personalização enxuta para Antigravity.
- `docs/MVP_RUNBOOK.md`, `docs/ANTIGRAVITY_OPTIMIZATION.md`: experimento real e organização.
- `docs/CODEGRAPH.md`: arquitetura atual e fronteira do upstream.
- `docs/SECURITY.md`: sessões e bloqueios.
- `docs/UPSTREAM_AUDIT.md`: decisões sobre reuso do cliente.
