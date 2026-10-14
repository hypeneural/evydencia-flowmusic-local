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
