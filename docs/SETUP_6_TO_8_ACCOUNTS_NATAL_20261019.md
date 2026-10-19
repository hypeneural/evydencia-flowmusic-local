# FlowMusic Natal 2026 — preparar 6 a 8 contas próprias, elegíveis e ativas

**Onde executar:** VPS FlowMusic, com sua stack Docker/CLI canônica e credenciais privadas. Este documento **não** cria contas Google, não faz login automático, não copia cookies/tokens e não troca contas após bloqueios do provedor. O gestor precisa autenticar individualmente cada conta que controla e verificar as condições de uso correspondentes.

## O que já existe na PR #3/#5
- Pastas isoladas por alias `default`, `studio02` ... `studio08`: `data/flowmusic-session` para default e `data/flowmusic-profiles/<alias>` para demais contas.
- `GET /v1/music/accounts` informa `session_status`, `credits_remaining`, `stale`, `enabled`, `auto_select`, `eligible`, motivos e `next_auth_action`.
- `POST /v1/music/accounts/{alias}/routing` com token local de integração altera apenas a preferência `enabled`/`auto_select` da conta. **Não** autentica o Google e **não** gera música.
- O gateway Flow `:8766` implementa `GET /v1/media/audio/selection` e `POST /v1/media/audio` com `account_profile=auto`. A escolha é persistida em `audio_dispatches` pelo `request_id` antes do primeiro POST ao Music; qualquer resultado incerto fica em revisão **na mesma conta**, sem reapresentação automática.

## Procedimento curto, na sequência
1. Antes de configurar, conferir `git status`, versão do container (PR #3 + #5 e gateway PR #4 + #5), backups SQLite e as rotas /health. Não confundir código do GitHub com imagem Docker efetivamente instalada.
2. Planejar aliases claros: `default`, `studio02`, `studio03`, `studio04`, `studio05`, `studio06`, `studio07`, `studio08`. Pode usar menos contas até que cada uma esteja realmente autenticada.
3. Entrar **interativamente** em cada conta por seu perfil separado, com o login legítimo do CLI `scripts/mvp_probe.py --mode login --profile <alias>` ou o procedimento VNC privado `scripts/linux/login-music.sh` já existente no container. Nunca registrar links privados de login, senha do VNC, session.json, e-mail, access token ou refresh token em issue/PR.
4. Com a fila sem jobs ativos ou `needs_review`, verificar a saúde e créditos de cada perfil com `scripts/mvp_probe.py --mode account --profile <alias>`. Para manutenção periódica sem geração: `python scripts/maintain-music-sessions.py --all` (dry-run) e `python scripts/maintain-music-sessions.py --all --execute` somente se a fila estiver apta. Ambos usam lock global de manutenção.
5. No endpoint protegido `POST /v1/music/accounts/{alias}/routing`, habilitar `enabled=true,auto_select=true` somente para cada perfil com `access_valid_locally`, `stale=false`, saldo recente > 0, `blocking_jobs_count=0`. O token de integração nunca deve constar na URL ou nos comandos registrados.
6. Consultar `GET /v1/media/audio/selection` no gateway: `selected_profile` não nulo e listagem de perfis elegíveis. A UI `/painel-contas` informa quantas das contas registradas estão pré-aptas e a ação necessária quando não estão.
7. No computador Windows EvydFlow, depois de instalar a PR #53, configurar o env **privado** `EVYDFLOW_FLOWMUSIC_ACCOUNT_PROFILE=auto`. O padrão `default` é mantido quando a variável não existe. Reiniciar o worker canônico e conferir que herdou a variável; não colocá-la em credenciais versionadas.
8. Validar **um único pedido novo** com consentimento de crédito persistido, MP3 com SHA e recibo. Se falha pré-POST por nenhuma conta elegível: mostrar instrução de login/refresh ao gestor, seguir com fotos. Se uma conta estiver ocupada/pendente, o gateway pode selecionar outra para um **novo** pedido independente; se a tentativa de um pedido for incerta, manter o mesmo request_id e consultar por GET — nunca trocar de conta nem repetir cobrança.
9. Reconciliar jobs/etapas anteriores antes de habilitar a seleção automática para novos pedidos. O gateway e o FlowMusic são autoridades distintas para roteamento versus geração.

## Testes focados sem consumo
```bash
python -m pytest tests/test_account_refresh_noninteractive.py tests/test_queue.py tests/test_api.py -q
node --check app/static/accounts.js
# no gateway Flow, homologar audio_routing e idempotência dos dispatches
```

A seleção de conta não prova autorização ou saldo remoto: cada execução real ainda pode ser rejeitada pelo provedor. 403/429, bloqueio de políticas, CAPTCHA, revogação de sessão ou resultado desconhecido são situações para reconciliação; não usar outra conta para contorná-las.

Referências: docs/ACCOUNTS_DASHBOARD.md, docs/API_QUEUE.md, docs do gateway Flow sobre `audio_dispatches`; documentação de sessões Supabase: https://supabase.com/docs/guides/auth/sessions
