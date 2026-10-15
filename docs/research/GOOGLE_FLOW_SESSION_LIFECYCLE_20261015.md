# Google Flow — sessão e resiliência, auditoria forense 15/10/2026

**Escopo:** documentação de interface/arquitetura. Repositório de geração de vídeo separado, não publicado em `hypeneural/evydencia-flow-local`; não modificar o runtime de música nem as sessões reais.

## Evidências Windows do operador
- O usuário informou leitura real do saldo 916 por RPC HTTP `nzlxg`, com comprovação SQLite.
- Um job de imagem foi gerado com mídia remota, JPEG físico, hash e SQLite.
- A prova Omni Flash (`request_id=omni-flash-video-validation-001`, job `326fd7d2-5265-49ce-a5c2-7ff883337b4a`) terminou em `needs_review` e `remote_media_id=None`; o sidecar mostrou `auth_unavailable`. Saldo observado não mudou. NÃO interpretar como autorização para replay, apagar ou abandonar sem conciliação.
- O Antigravity identificou um vencimento de cookie `*PSIDTS` e redirect para landing page. **Isso não prova que a conta Google expira globalmente a cada 15 minutos.** Leitura de créditos HTTP não prova login na interface de geração.

## Auditoria de upstream (repositórios e funções examinadas)
- [flow2api @ f6f201c](https://github.com/TheSmallHanCat/flow2api/tree/f6f201c298ee6ee4b28a7d36adf3a8d49cfb2844):
  - `src/services/protocol_login.py:36-123`: cookie jar por atributos (domain/path/expires) versus snapshot de texto.
  - `src/services/protocol_login.py:145-204`: valida a resposta e as atualizações de sessão permitidas pelo servidor; falha quando não autentica.
  - `src/services/token_manager.py:917-1055`: operações por conta, locks e atualização condicional, **mas inclui fallback de navegador** que não devemos copiar para contornar proteção.
  - `src/services/flow_current.py:121-140`: `st_to_at` constrói timestamp sintético de +55min; esse valor **não é TTL real** de cookie/sessão Google.
  - `src/services/flow_frontend.py:665-735`: bootstrap atual + RPC; a prova `nzlxg` não confirma operações pagas; geração tem outras verificações.
- [RohaanA/google-flow-mcp](https://github.com/RohaanA/google-flow-mcp): perfil Chromium persistente e fluxo UI, mas não oferece credencial backend duradoura nem substitui políticas Google.
- [Google OAuth Policies](https://developers.google.com/identity/protocols/oauth2/policies) proíbem embedded user-agent controlado no login; [Chrome 136](https://developer.chrome.com/blog/remote-debugging-port) restringe depuração do diretório de perfil normal.

## Risco encontrado na implementação local
`data/http-sessions/default.json` é uma **fotografia estática** dos cookies de uma conta, que o sidecar reproduz no navegador gerenciado. Isso pode perder mudanças/atributos da sessão, especialmente se a origem atualizar um cookie de curta duração. O cliente HTTP base também utilizou formato distinto `data/flow-http-sessions/default.cookie`. NÃO converter um formato em outro automaticamente.

## Correção entregue como artefato de conversa
- `evydencia-flow-local-session-reliability-20261015.zip` (71 arquivos) e `evydencia-flow-local-session-reliability.patch` (8 arquivos delta).
- Novo `app/session_health.py`: leitura **somente de metadados** e cookie names da sessão local; não revela valores e nunca interpreta cookie TS vencido como prova de logout global.
- `GET /v1/flow/accounts/{alias}/session-health` autenticado, apenas SQLite/arquivos locais; sem consulta Google, geração, extração de cookies ou renovação.
- `scripts/windows/session-doctor.ps1`: checa GET de saúde e o request_id original; não envia novo POST; skill `flow-session-reliability`, README/AGENTS.md e runbook.
- `app/operations.py` inclui diagnóstico como subcampo do preflight, sem fingir autenticação de geração.
- Verificações executadas localmente: compileall Python PASS, respostas FastAPI 401/200/404, SQL status jobs, não exposição de valores de sessão, ZIP integrity PASS, patch semântico idêntico em 8 arquivos. **Não houve conexão Google neste ambiente.**

## Instruções Antigravity
1. Inspecionar `git status`, `bridge/flow-cli.mjs`, `app/worker.py`, `app/flow_http_readonly.py` e os **arquivos reais** de sessão Windows; backup antes de qualquer alteração. Esta versão ZIP é anterior a parte do código já editada no Windows.
2. Aplicar *apenas delta compatível*; não sobrescrever a geração de imagem que funcionou ou os segredos.
3. Executar `.\scripts\windows\session-doctor.ps1 -Profile default -RequestId omni-flash-video-validation-001` e conferir `needs_review` por GET.
4. Examinar eventos do mesmo request ID e indícios remotos sem novo POST; não limpar job, copiar cookies Chrome pessoal, prolongar artificialmente validade, fazer CAPTCHA bypass ou trocar conta para contornar bloqueio.
5. Se sessão revogada pelo Google, exigir autenticação permitida; não insistir em refresh não suportado nem concluir que “15 minutos” é valor universal. Para vídeo, permanecer com prova bloqueada até reconciliação.

**Estado GitHub:** documentação versionada na branch do PR musical, sem deploy/código do novo gateway no projeto musical. A aplicação de código deve ocorrer no workspace Windows e posteriormente em repositório dedicado quando estiver acessível.
