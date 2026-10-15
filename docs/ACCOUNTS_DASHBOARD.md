# Painel visual de contas — FlowMusic Local

## Iniciar
No repositório, use `scripts/windows/start.ps1` (mock, sem créditos), abra
`http://127.0.0.1:8765/painel-contas` e digite o token local do arquivo
`data/local-token.txt`. Não coloque esse token na URL. **Não use o Google
OAuth como autenticação do painel**: o token é uma credencial local distinta.

## Estrutura simples
- `GET /painel-contas`: shell HTML estático, sem e-mail, saldo ou segredos.
- `/assets/accounts.css` e `/assets/accounts.js`: UI local sem CDN, React,
  npm ou dependências extras; frontend simples, adequado para Gemini Flash.
- `GET /v1/music/accounts` (**requer X-Local-Token**): dados redigidos
  derivados da sessão, aliases SQLite e snapshots de créditos.
- `GET /v1/music/queue` (**requer X-Local-Token**): estado da fila existente.
- Nada atualiza créditos ou login automaticamente: botão de recarregar só faz
  GETs locais.
- `GET /v1/music/accounts` inclui `eligible`, `eligibility_reasons`,
  `blocking_jobs_count`, `enabled` e `auto_select`. **Eligible é apenas
  pré-checagem local**, exige LIVE do motor, opt-in, sessão com token
  localmente no prazo, crédito fresco e nenhuma pendência neste perfil.
- `POST /v1/music/accounts/{alias}/routing` requer X-Local-Token Music
  e altera apenas a política local (`enabled`, `auto_select`) no SQLite;
  nunca faz OAuth ou transfere conta, e não altera jobs existentes.

## Colunas
Perfil | E-mail | Status da sessão local | Últimos créditos | Última consulta.

O e-mail é lido em memória do `session.json` sem repassar o conteúdo do arquivo
ao navegador. **NUNCA devolver `access_token`/`refresh_token` ou `user_id`**
para a API/HTML. O status `access_valid_locally` refere-se à expiração
registrada na sessão; não significa que o servidor Google confirmou o token.
`access_expired_refreshable` significa token de acesso vencido, mas refresh
token presente; o sucesso da renovação não está provado. Um saldo consultado
há até 30 minutos é `recent_account_check=true` (verificação histórica).

Para saber se uma conta está **autenticada realmente agora**, rode no terminal
`mvp.ps1 -Mode account -Profile <alias>`; isso consulta os modelos e créditos
da conta escolhida e atualiza seu snapshot. Não abra sessões/renove tokens
enquanto há geração ativa. Recarregue o painel depois.

## Segurança
- Servidor em `127.0.0.1`, jamais `0.0.0.0`.
- No navegador, token apenas em memória até desconectar/fechar aba; sem
  armazenamento persistente nem URL com segredo.
- Headers `Content-Security-Policy`, `Cache-Control: no-store`,
  `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`.
- Sem `innerHTML` para conteúdo vindo da sessão; somente `textContent`,
  reduzindo risco de XSS por e-mail ou alias.
- A shell não requer autenticação para carregar, mas **dados exigem token**.
  Cuidado com extensões maliciosas e máquinas Windows compartilhadas.
- O painel é intencionalmente de leitura: não executa OAuth, geração, exclusão
  de sessão, troca de conta ou ajuste da fila.

## Validação Windows pontual (sem nova música)
1. Checar `git status`, `agent.cmd`, `preflight_accounts.py`.
2. Iniciar `start.ps1` em mock e abrir a tela; confirmar que, sem token,
   nenhuma linha com e-mail aparece; token inválido retorna erro 401.
3. Colar token local no browser e conferir `default` e `studio02` com
   último saldo/hora, status de acesso local e fila.
4. Se desejar confirmação online, executar **uma única** consulta de saldo
   para um perfil, fora do worker, depois clicar `Atualizar painel`.
5. Conferir que `session.json`, WAVs, tokens e banco não entraram no Git.
6. Se falhar, corrigir a causa demonstrada. Sem baterias de testes nem
   geração de novos áudios para comprovar UI.

Referências técnicas: FastAPI `HTMLResponse`/`StaticFiles`,
MDN `Content-Security-Policy`, fonte upstream
`deluxebear/flowmusic-cli/src/lib/auth.mjs` (normalização de `email`,
`expires_at` e `refresh_token`).


## Integração multicontas com o gateway :8766

A PR #3 exporta consulta indexada `GET /v1/music/jobs/by-request/{id}`.
O gateway `:8766` obtém a lista Music com seu próprio token de integração,
escolhe entre as contas **opted-in e pré-aptas**, grava o alias em
`audio_dispatches` antes do POST e nunca troca de perfil se o envio
ficar incerto. O motor musical ainda valida a sessão/provedor ao executar.

Um job musical `needs_review` agora impede novos pedidos **na mesma
conta**, sem congelar outras contas com pedidos realmente independentes.
A geração global segue serializada; cada `request_id` preserva seu
alias original. A desativação de uma conta com jobs ativos é recusada.

Painel unificado read-only do gateway Flow: `http://127.0.0.1:8766/painel`.
Painel Music deste serviço: `http://127.0.0.1:8765/painel-contas`.

**Ordem de homologação Windows:** primeiro PR #1 Music, depois PR #3,
em seguida PR #2 e PR #4 Flow. Backup do banco `data/jobs.db` antes de
rodar a migração de `account_profiles(enabled,auto_select)`. Ela preserva
`session.json`, jobs históricos e saldos, e deixa opt-in desligado.

Testes dirigidos:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api.py tests/test_queue.py -q
node --check app/static/accounts.js
```
Não declarar Music LIVE se `FLOWMUSIC_PROVIDER=mock`. Não gravar tokens
nem credenciais no GitHub.
