# Antigravity 2026 / Gemini Flash

Documentação oficial: https://antigravity.google/docs/rules/ e https://antigravity.google/docs/skills

- `AGENTS.md` sempre ativo e curto; apenas UMA skill é aberta quando a tarefa exigir.
- Preferir `.agents/skills/` ao legado de workflows, com desativação prevista em 19/10/2026.
- Não há GitHub Actions: `agent.cmd` é diagnóstico local rápido, `agent.cmd test` é opcional.
- Use um ciclo curto: hipótese -> comando Windows -> log -> correção.
- Perfis múltiplos por `FLOWMUSIC_HOME` e consulta pontual de saldo; não atualizar várias sessões em paralelo nem alternar automaticamente contas.
- A API live só inicia com `-EnableLive` e `approve_live=true`; logs sem tokens/senhas/URLs OAuth.
