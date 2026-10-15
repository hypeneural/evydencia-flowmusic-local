# Perfis de contas no Windows

O flowmusic-cli fixado suporta `FLOWMUSIC_HOME` para diretório de sessão isolado.

Perfis:
- `default`: preserva `data/flowmusic-session` da validação anterior.
- `studio02`, `studio03`: `data/flowmusic-profiles/<alias>`.

Comandos:
```powershell
.\scripts\windows\mvp.ps1 -Mode accounts
.\scripts\windows\mvp.ps1 -Mode login -Profile studio02
.\scripts\windows\mvp.ps1 -Mode account -Profile studio02
```

Cada login é individual. A consulta de créditos registra somente valor e timestamp em `data/account-snapshots/`, sem email ou token. `GET /v1/music/accounts` ordena saldos recentes, marcando cache com mais de 30 minutos como `stale`; não faz chamadas remotas automaticamente.

Na fila API, cada pedido define `account_profile` (padrão `default`), que é mantido no ledger. Sem escolha/alternância automática: o operador decide qual conta usar. `request_id` é único globalmente. Em falha incerta, suspender a fila e revisar a biblioteca; não reenviar para outro perfil.

Os diretórios de sessão e ledger permanecem locais e ignorados pelo Git. Use a conta somente conforme suas permissões e as condições de uso do serviço.

## Auditoria pré-login e normalização do SQLite (14/10/2026)
Antes de autenticar `studio02`, execute `& .\.venv\Scripts\python.exe scripts/preflight_accounts.py`. O diagnóstico é **offline**, não renova tokens, consulta a integridade SQLite, jobs pendentes/incertos, presença de sessões e saldos conhecidos sem revelar credenciais. Se retornar erro, revise antes de continuar.

Na primeira inicialização da API com a atualização, `queue.migrate()` cria uma **cópia SQLite** em `data/backups/` ANTES da migração, executa as alterações em uma transação e adiciona `account_profiles(alias,registered_at)` e `jobs.account_profile` com índice. Registros anteriores continuam associados ao alias `default`, preservando request_id, resultado, estado e SHA-256. Perfis novos só são registrados no banco quando há um job; o inventário também localiza diretórios de sessões ainda não usados.

O valor/hora de saldo continua armazenado em snapshot JSON local: **não há duas fontes concorrentes do mesmo saldo no banco**. Após uma tentativa de geração, o saldo anterior é preservado apenas para histórico, marcado como `stale`; é preciso consultar novamente para obter saldo recente. Nunca usar saldo cacheado para automação de alternância.

O probe elimina `FLOWMUSIC_TOKEN` e `FLOWMUSIC_BASE` herdados do Windows antes de iniciar o CLI, porque o upstream os aceita como substituições de token e servidor. Assim o login/consulta da conta segue somente o `FLOWMUSIC_HOME` selecionado.

## Painel visual
A tela de inventário agora está em **http://127.0.0.1:8765/painel-contas**.
`GET /v1/music/accounts` (protegido por `X-Local-Token`) retorna o e-mail
derivado dos metadados da sessão, status de expiração local, último saldo e
`checked_at`. A página não tem dependências adicionais: HTML, CSS e JavaScript
servidos pelo FastAPI.

**Importante:** presença de `session.json` não prova uma sessão Google online.
`access_valid_locally` significa apenas que a expiração registrada ainda
não passou. `access_expired_refreshable` significa token expirado com refresh
token presente (renovação ainda não testada). `recent_account_check`
indica consulta de saldo recente registrada; não garante saldo atual após
outra janela usar a conta.

Para verificar uma conta junto ao provedor, execute voluntariamente
`mvp.ps1 -Mode account -Profile <alias>`, depois clique "Atualizar painel".
Isso NÃO produz música, mas pode renovar a sessão no disco. Não rode enquanto
há geração ativa; não execute automaticamente em intervalos. Veja
[ACCOUNTS_DASHBOARD.md](ACCOUNTS_DASHBOARD.md).
