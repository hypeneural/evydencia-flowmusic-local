---
name: flowmusic-mvp
description: Operate the pinned Flow Music CLI on Windows with separate local account aliases, on-demand balance checks and redacted logs.
---
# MVP supervisionado
Usar `scripts/windows/mvp.ps1`. Modos: `accounts` (cache offline), `login -Profile <alias>` (interativo), `account -Profile <alias>` (saldo sob demanda), `generate -Profile <alias> -ApproveLive` (apenas com autorização).
Cada alias mantém sua própria sessão `FLOWMUSIC_HOME`. Registre somente alias, timestamps, estado e hash. Nunca imprimir cookies, refresh token ou callback. Em resultado remoto incerto, parar para reconciliação manual; sem reenviar pela mesma ou outra conta.
